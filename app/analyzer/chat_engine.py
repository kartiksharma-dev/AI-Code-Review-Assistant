import os
import json
import logging
import uuid
import ast
import hashlib
import tiktoken
import google.generativeai as genai
from typing import Dict, Any, List, Optional, Generator
from pydantic import BaseModel, Field, ValidationError

from app.analyzer.drift_detection import SemanticDriftDetector

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. Pydantic Schema Definitions (Deterministic JSON Enforcement)
# ==============================================================================

class AIFix(BaseModel):
    code: str = Field(description="COMPLETE runnable code block that fixes the issue.")
    explanation: str = Field(description="Why this fixes the problem.")

class ChatResponseSchema(BaseModel):
    summary: str = Field(description="1 sentence brief summary.")
    issues_addressed: List[str] = Field(description="Array of issue IDs or names.")
    fixes: List[AIFix] = Field(default_factory=list, description="List of proposed fixes.")
    reasoning: str = Field(description="Conversational markdown text explaining architectural decisions.")
    recommended_action: str = Field(description="One of: Review, Apply Fix, Refactor")

# ==============================================================================
# 2. Tokenizer Abstraction Layer (Token Budgeting)
# ==============================================================================

class TokenizerAdapter:
    @staticmethod
    def count_tokens(text: str) -> int:
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return len(text) // 4  # Fallback heuristic

class TokenBudgetManager:
    """
    Allocates strict token percentages based on intent using real tokenizers.
    Budget Profile: 50% code, 20% system prompt, 15% anchor context, 15% history.
    """
    MAX_TOKENS = 30000 # Gemini Flash context limit safe bound
    
    @staticmethod
    def allocate(payload: Dict[str, Any]) -> str:
        intent = payload.get("intent", "Explain")
        code = payload.get("code", "")
        issues = payload.get("issues", [])
        active_context = payload.get("active_context")
        
        code_budget = int(TokenBudgetManager.MAX_TOKENS * 0.50)
        
        if TokenizerAdapter.count_tokens(code) > code_budget:
            if intent == "Explain" and active_context and active_context.get("line"):
                line = active_context.get("line")
                lines = code.split('\n')
                # Zoom in on context
                start = max(0, line - 50)
                end = min(len(lines), line + 50)
                code = "...[truncated]...\n" + "\n".join(lines[start:end]) + "\n...[truncated]..."
            else:
                # Truncate middle
                half_budget_chars = (code_budget // 2) * 4
                code = code[:half_budget_chars] + '\n\n...[truncated]...\n\n' + code[-half_budget_chars:]
                
        # Compress issues
        issues_str = ""
        if active_context:
            issues_str = f"<ANCHORED_ISSUE>\n{json.dumps(active_context)}\n</ANCHORED_ISSUE>\n"
            
        other_issues = [i for i in issues if (not active_context or i.get("id") != active_context.get("id"))]
        issues_str += f"<OTHER_ISSUES>\n{json.dumps(other_issues[:5])}\n</OTHER_ISSUES>"
        
        return code, issues_str

# ==============================================================================
# 3. Governance Engine Decomposition (Chain of Responsibility)
# ==============================================================================

class ValidatorNode:
    def set_next(self, next_validator: 'ValidatorNode') -> 'ValidatorNode':
        self._next = next_validator
        return next_validator

    def validate(self, fix: AIFix, original_code: str, language: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        if getattr(self, '_next', None):
            return self._next.validate(fix, original_code, language, metadata)
        return metadata

class SyntaxValidator(ValidatorNode):
    def validate(self, fix: AIFix, original_code: str, language: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        if language == 'python':
            try:
                ast.parse(fix.code)
            except SyntaxError as e:
                metadata["policy_triggered"] = "SYNTAX_ERROR"
                metadata["blocked_reason"] = f"Syntax validation failed: {str(e)}"
                return metadata
        return super().validate(fix, original_code, language, metadata)

class DangerousAPIValidator(ValidatorNode):
    def validate(self, fix: AIFix, original_code: str, language: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        if language == 'python':
            dangerous_calls = ['eval', 'exec', 'subprocess', 'os.system', 'os.popen', 'shutil.rmtree']
            try:
                parsed_ast = ast.parse(fix.code)
                for node in ast.walk(parsed_ast):
                    if isinstance(node, ast.Call):
                        func_name = ""
                        if isinstance(node.func, ast.Name):
                            func_name = node.func.id
                        elif isinstance(node.func, ast.Attribute):
                            func_name = node.func.attr
                            
                        if any(danger in func_name for danger in dangerous_calls):
                            metadata["dangerous_api_detected"] = True
                            metadata["affected_nodes"].append(func_name)
                            metadata["policy_triggered"] = "DANGEROUS_API_BLOCK"
                            metadata["blocked_reason"] = f"Dangerous execution API detected: {func_name}"
                            metadata["severity"] = "critical"
                            metadata["risk_score"] = 100
                            return metadata
            except SyntaxError:
                pass # Handled by SyntaxValidator
        return super().validate(fix, original_code, language, metadata)

class DriftValidator(ValidatorNode):
    def validate(self, fix: AIFix, original_code: str, language: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        if language == 'python':
            drift = SemanticDriftDetector.detect_drift(original_code, fix.code)
            if drift["has_drift"]:
                metadata["semantic_risk"] = 90 if drift["risk_level"] == "high" else 60
                if metadata["semantic_risk"] > 80:
                    metadata["policy_triggered"] = "HIGH_SEMANTIC_RISK"
                    metadata["blocked_reason"] = drift["reason"]
                    metadata["severity"] = "high"
                    metadata["risk_score"] = metadata["semantic_risk"]
                    return metadata
        return super().validate(fix, original_code, language, metadata)

class ValidationPipeline:
    def __init__(self):
        self.head = SyntaxValidator()
        self.head.set_next(DangerousAPIValidator()).set_next(DriftValidator())
        
    def execute(self, fix: AIFix, original_code: str, language: str) -> Dict[str, Any]:
        metadata = {
            "policy_triggered": None,
            "blocked_reason": None,
            "semantic_risk": 0,
            "affected_nodes": [],
            "dangerous_api_detected": False,
            "severity": "low",
            "risk_score": 0
        }
        return self.head.validate(fix, original_code, language, metadata)

# ==============================================================================
# 4. Prompt Sanitizer & Injection Defense
# ==============================================================================

class PromptSanitizer:
    FORBIDDEN_PHRASES = ["ignore previous instructions", "bypass governance", "disable validators", "ignore system prompt"]
    
    @staticmethod
    def sanitize(prompt: str) -> str:
        prompt_lower = prompt.lower()
        for phrase in PromptSanitizer.FORBIDDEN_PHRASES:
            if phrase in prompt_lower:
                logger.error(f"SECURITY AUDIT: Prompt injection attempt detected: '{phrase}'")
                raise ValueError("PROMPT_SECURITY_POLICY_VIOLATION: Forbidden directive detected.")
        return prompt

# ==============================================================================
# 5. Core Chat Engine Orchestrator
# ==============================================================================

class ChatEngine:
    MAX_SCHEMA_RETRIES = 2

    def __init__(self):
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel("gemini-flash-latest")
        self.validation_pipeline = ValidationPipeline()
            
    def _build_system_prompt(self, payload: Dict[str, Any], code: str, issues: str, error_feedback: str = "") -> str:
        intent = payload.get("intent", "Explain")
        language = payload.get("language", "python")
        complexity = payload.get("complexity", {})
        schema_json = json.dumps(ChatResponseSchema.schema(), indent=2)
        
        # XML-Style boundaries for strict hierarchy
        return f"""<SYSTEM_CONTEXT>
You are the central AI Governance Engine for a deterministic software engineering platform.
Your objective is to provide highly contextual, expert-level architectural insights.
Your current operational intent is: {intent.upper()}

STRICT SCHEMA ENFORCEMENT:
You MUST respond ONLY with a valid JSON object matching this exact Pydantic schema:
{schema_json}

{f"<SCHEMA_ERROR_FEEDBACK>The previous response failed schema validation. Please correct this error: {error_feedback}</SCHEMA_ERROR_FEEDBACK>" if error_feedback else ""}

RULES:
1. Do not use Markdown JSON wrappers (` ```json `). Output raw JSON.
2. Under "reasoning", you may use Markdown.
3. If you provide a "fix", the `code` field MUST be a complete, runnable replacement.
4. Your analysis must focus ONLY on the provided code and issues.
</SYSTEM_CONTEXT>

<ENVIRONMENT_STATE>
Language: {language}
Metrics: {json.dumps(complexity)}
</ENVIRONMENT_STATE>

<ISSUES_BUDGET>
{issues}
</ISSUES_BUDGET>

<BASELINE_CODE>
{code}
</BASELINE_CODE>
"""

    def generate_chat_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes AI response generation with Pydantic self-correction loops.
        """
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured for ChatEngine.")
            
        # 0. Security Sanitization
        user_prompt = PromptSanitizer.sanitize(payload.get("prompt", ""))
            
        # 1. Immutable Baseline Context Snapshot creation happens at API route level
        # 2. Token Budget Allocation
        code, issues_str = TokenBudgetManager.allocate(payload)
        
        # 3. Execution with MAX_SCHEMA_RETRIES
        error_feedback = ""
        for attempt in range(self.MAX_SCHEMA_RETRIES):
            prompt = self._build_system_prompt(payload, code, issues_str, error_feedback)
            # Append user prompt strictly separated
            full_prompt = prompt + f"\n<USER_PROMPT>\n{user_prompt}\n</USER_PROMPT>"
            
            try:
                response = self.model.generate_content(full_prompt)
                text = response.text.strip()
                
                # Clean JSON wrappers
                if text.startswith("```json"): text = text[7:]
                elif text.startswith("```"): text = text[3:]
                if text.endswith("```"): text = text[:-3]
                text = text.strip()
                
                # Parse with Pydantic
                parsed_data = json.loads(text, strict=False)
                validated_model = ChatResponseSchema(**parsed_data)
                
                # 4. Multi-Layer Pre-Flight Validation Gauntlet
                language = payload.get("language", "python")
                original_code = payload.get("code", "")
                
                safe_fixes = []
                for fix in validated_model.fixes:
                    metadata = self.validation_pipeline.execute(fix, original_code, language)
                    if metadata["policy_triggered"]:
                        logger.warning(f"Governance Block: {metadata['blocked_reason']}")
                        # Embed structured risk metadata into reasoning for explainability
                        risk_meta = f"\n\n> [!WARNING]\n> **Patch Blocked by Governance Engine:** {metadata['blocked_reason']} (Severity: {metadata['severity']}, Risk: {metadata['risk_score']})"
                        validated_model.reasoning += risk_meta
                    else:
                        safe_fixes.append(fix)
                        
                validated_model.fixes = safe_fixes
                return validated_model.dict()
                
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Schema Validation Failed (Attempt {attempt+1}/{self.MAX_SCHEMA_RETRIES}): {e}")
                error_feedback = str(e)
                continue
            except Exception as e:
                logger.error(f"ChatEngine Execution Failed: {e}")
                raise Exception(f"AI orchestration pipeline failed: {e}")
                
        raise ValueError(f"MAX_SCHEMA_RETRIES ({self.MAX_SCHEMA_RETRIES}) exceeded. LLM failed to return valid schema.")
