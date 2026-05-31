"""
Analysis Engine - AI Layer
AI-powered code suggestions and recommendations using Anthropic API
"""

import os
import json
import logging
import requests
import difflib
import uuid
from typing import Dict, Any, List
import google.generativeai as genai

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """
    Generates AI-powered code improvement suggestions
    Integrates with Gemini or Anthropic API for intelligent analysis
    """
    
    def __init__(self, code: str, issues: List[Dict], complexity_data: Dict[str, Any], language: str = 'python', api_key: str = None):
        self.code = code
        self.issues = issues
        self.complexity_data = complexity_data
        self.language = language
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel("gemini-flash-latest")
        
    def generate_suggestions(self) -> Dict[str, Any]:
        """
        Generate AI-powered improvement suggestions in pure JSON
        Falls back to rule-based suggestions if API key not available
        """
        if self.gemini_api_key:
            return self._generate_gemini_suggestions()
        elif self.api_key:
            return self._generate_ai_suggestions()
        else:
            return self._generate_fallback_suggestions()
            
    def _get_prompt(self) -> str:
        # Smart Truncation
        code_context = self.code
        if len(code_context) > 3000:
            code_context = self.code[:2000] + '\n\n...[truncated]...\n\n' + self.code[-1000:]
            
        issues_context = self.issues[:10]
        
        return f"""You are a senior software engineer performing a deep code review.
Your job is to analyze logic, detect inefficiencies, and suggest better approaches.

You MUST:
1. Detect inefficient algorithms and patterns
2. Use time and space complexity in reasoning
3. Suggest optimized alternatives when possible
4. Provide at least ONE strong, actionable suggestion

SMART FIX CATEGORIZATION (CRITICAL):
- You must strictly determine if an issue is "fixable" or non-fixable.
- FIXABLE: Set "fixable" to true ONLY for: performance, readability, best practice, or isolated security fixes.
- NON-FIXABLE: Set "fixable" to false for: architectural redesigns, missing business logic, or vague optimization advice. These should remain informational only.

STRICT RULES:
- If time complexity is O(n^2) or worse -> suggest a better approach
- Always explain WHY the current approach is inefficient
- Always provide a clear FIX
- If "fixable" is true, the "example" MUST be the COMPLETE, FULLY RUNNABLE replacement for the ENTIRE provided code. Do NOT return partial snippets if fixable is true.

DO NOT:
- Give generic advice like "improve code"
- Return vague or obvious suggestions

Return ONLY valid JSON.
Do NOT include markdown.
Do NOT include explanations outside JSON.

OUTPUT FORMAT:
{{
  "explanation": "2-4 line summary of code quality",
  "suggestions": [
    {{
      "type": "performance | security | best_practice | readability",
      "problem": "...",
      "solution": "...",
      "fixable": true,
      "example": "...",
      "diff_explanation": {{
        "summary": "...",
        "impact": "...",
        "complexity_before": "O(n²)",
        "complexity_after": "O(n)",
        "change_type": "performance",
        "reasoning": [
          "...",
          "..."
        ]
      }}
    }}
  ]
}}

Code:
{code_context}

Detected Issues:
{issues_context}

Time Complexity:
{self.complexity_data.get('time_complexity', 'O(1)')}

Space Complexity:
{self.complexity_data.get('space_complexity', 'O(1)')}
"""
    
    def _generate_gemini_suggestions(self) -> Dict[str, Any]:
        """
        Use Google Gemini API to generate intelligent suggestions
        """
        prompt = self._get_prompt()
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            try:
                logger.debug("Gemini raw response length: %d", len(text))
            except:
                pass
            
            import re
            parsed = None
            try:
                # Strip markdown json block manually if present
                clean_text = text
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                elif clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                
                # Fix invalid escapes (like \T or \O) that Gemini sometimes generates
                import re
                clean_text = re.sub(r'\\(?=[^"\\/bfnrtu])', r'\\\\', clean_text)
                
                parsed = json.loads(clean_text, strict=False)
            except json.JSONDecodeError as e:
                logger.error(f"First pass JSON parse failed: {e}")
                # Fallback to finding the JSON structure
                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1:
                    try:
                        # Fix invalid escapes here too
                        block_text = text[start:end+1]
                        block_text = re.sub(r'\\(?=[^"\\/bfnrtu])', r'\\\\', block_text)
                        parsed = json.loads(block_text, strict=False)
                    except json.JSONDecodeError as e2:
                        logger.error(f"Second pass JSON parse failed: {e2}")
                        pass
                        
            if not parsed or "suggestions" not in parsed:
                logger.error("Gemini AI Error: Invalid JSON structure or missing 'suggestions'")
                return self._generate_fallback_suggestions()
                
            return self._process_ai_response(parsed)
            
        except Exception as e:
            logger.error("Gemini AI Error: %s", str(e))
            return self._generate_fallback_suggestions()

    def _generate_ai_suggestions(self) -> Dict[str, Any]:
        """
        Use Anthropic API to generate intelligent suggestions natively as JSON
        """
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        prompt = self._get_prompt()

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ]
        }
        
        # 1x Timeout Retry Loop
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code in [429, 529]:
                    logger.warning(f"Anthropic API Rate Limit/Overload: {response.status_code}")
                    return self._generate_fallback_suggestions()
                    
                response.raise_for_status()
                data = response.json()
                
                if "content" not in data:
                    return self._generate_fallback_suggestions()
                    
                text = data["content"][0]["text"]
                
                # Ultimate JSON parsing safety
                parsed = None
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    start = text.find('{')
                    end = text.rfind('}')
                    if start != -1 and end != -1:
                        try:
                            parsed = json.loads(text[start:end+1])
                        except json.JSONDecodeError:
                            return self._generate_fallback_suggestions()
                    else:
                        return self._generate_fallback_suggestions()

                if not parsed or not isinstance(parsed.get("suggestions"), list):
                    return self._generate_fallback_suggestions()

                return self._process_ai_response(parsed)
                
            except requests.exceptions.Timeout:
                if attempt == 0:
                    continue  # Retry once
                return self._generate_fallback_suggestions()
            except requests.exceptions.RequestException as e:
                logger.error("AI Network Error: %s", str(e))
                return self._generate_fallback_suggestions()
            except Exception as e:
                logger.error("AI Error: %s", str(e))
                return self._generate_fallback_suggestions()
        
        return self._generate_fallback_suggestions()

    def _process_ai_response(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        final_suggestions = []
        raw_suggestions = []
        allowed_types = {"performance", "readability", "best_practice", "security"}
        
        # We need to rank suggestions to find the "highest value" one for the escape hatch.
        severity_map = {"security": 4, "performance": 3, "best_practice": 2, "readability": 1}
        
        def calculate_value(sug_obj):
            score = severity_map.get(sug_obj["type"], 0)
            if sug_obj["example"]:
                score += 0.5
            # Tie-break by length
            content_len = len(sug_obj["problem"]) + len(sug_obj["solution"])
            score += (content_len / 10000.0)
            return score

        for sug in parsed.get("suggestions", []):
            if not isinstance(sug, dict):
                continue
                
            problem = str(sug.get("problem", "")).strip()
            solution = str(sug.get("solution", "")).strip()
            
            # 1. Quality / Semantic filter
            action_verbs = ["use", "implement", "refactor", "replace", "add", "remove", "change", "update", "optimize", "avoid", "ensure"]
            tech_keywords = ["loop", "function", "variable", "class", "o(n)", "complexity", "method", "array", "list", "dict", "string", "memory", "time", "cache", "return", "type", "parameter", "algorithm"]
            
            text_lower = (problem + " " + solution).lower()
            has_verb = any(v in text_lower for v in action_verbs)
            has_tech = any(k in text_lower for k in tech_keywords)
            
            # Relaxed AI filtering: Allow if it has deep logic, a code example, or meaningful explanation
            has_example = bool(str(sug.get("example", "")).strip())
            content_len = len(problem) + len(solution)
            
            if not (has_verb and has_tech) and not has_example and content_len < 40:
                continue
                
            # Reject overly vague phrases
            vague_phrases = ["improve code", "fix this", "optimize it", "refactor code", "make it better", "looks bad", "bad code"]
            if problem.lower() in vague_phrases or solution.lower() in vague_phrases:
                continue

            # 3. Type Sanitization & Normalization
            sug_type = str(sug.get("type", "")).strip().lower()
            if sug_type == "bug_risk":
                sug_type = "security"
            elif sug_type not in allowed_types:
                sug_type = "best_practice"
                
            # 4. Example Sanitization
            example = str(sug.get("example", "")).strip()
            fixable = bool(sug.get("fixable", False))
            
            if example:
                if example.startswith("```"):
                    example = "\n".join(example.split("\n")[1:])
                    if example.endswith("```"):
                        example = example[:-3]
                
                # Truncate informational snippets, keep full file for fixes
                if not fixable:
                    example = example[:500].strip()
                
                # PHASE 5 & 8: Safety, Syntax Validation & Semantic Drift (Backend Pre-Flight)
                drift_info = None
                if fixable and self.language == 'python':
                    import ast
                    from app.analyzer.drift_detection import SemanticDriftDetector
                    try:
                        ast.parse(example)
                        
                        # Phase 8: Drift Detection
                        drift_info = SemanticDriftDetector.detect_drift(self.code, example)
                        if drift_info["has_drift"]:
                            logger.warning(f"Semantic Drift Detected: {drift_info['reason']}")
                            fixable = False # Gracefully downgrade to informational only
                            
                    except SyntaxError as e:
                        logger.warning(f"AI Syntax Error Blocked: {e}")
                        fixable = False # Gracefully downgrade to informational only

            line = sug.get("line")
            formatted_sug = {
                "id": str(uuid.uuid4()),
                "type": sug_type,
                "problem": problem,
                "solution": solution,
                "example": example,
                "fixable": fixable,
                "diff_explanation": sug.get("diff_explanation"),
                "drift_info": drift_info,
                "line": line if line else 1,
                "scope": "local" if line else "global",
                "severity": sug.get("severity") or "medium",
                "source": "ai",
                "message": problem
            }
            raw_suggestions.append(formatted_sug)

        # Find the highest value suggestion for the escape hatch
        escape_hatch_sug = None
        if raw_suggestions:
            escape_hatch_sug = max(raw_suggestions, key=calculate_value)

        issues_to_remove = []
        
        for formatted_sug in raw_suggestions:
            problem = formatted_sug["problem"]
            sug_type = formatted_sug["type"]
            
            is_duplicate = False
            
            # Deduplicate against rule-based issues
            for issue in self.issues:
                issue_msg = str(issue.get("message", ""))
                issue_cat = str(issue.get("category", "best_practice"))
                issue_has_example = bool(issue.get("example", ""))
                
                similarity = difflib.SequenceMatcher(None, problem.lower(), issue_msg.lower()).ratio()
                if similarity > 0.85 and sug_type == issue_cat:
                    # 4. Refined Deduplication Bypass
                    if formatted_sug["example"] and not issue_has_example:
                        issues_to_remove.append(issue)
                        continue # Bypass deduplication!
                        
                    is_duplicate = True
                    break
                    
            # Deduplicate against already accepted AI suggestions
            if not is_duplicate:
                for accepted in final_suggestions:
                    similarity = difflib.SequenceMatcher(None, problem.lower(), accepted["problem"].lower()).ratio()
                    if similarity > 0.85:
                        is_duplicate = True
                        break

            # Escape hatch: if this is the highest value suggestion, force it through
            if is_duplicate and formatted_sug is escape_hatch_sug:
                is_duplicate = False
                
            if is_duplicate:
                continue

            final_suggestions.append(formatted_sug)
            
        # Clean up suppressed rules
        for issue in issues_to_remove:
            if issue in self.issues:
                self.issues.remove(issue)

        # Prioritize: Sort by Severity -> Structural richness
        final_suggestions.sort(key=lambda x: calculate_value(x), reverse=True)

        # 5. Suggestion Capping & Fallback Guarantee
        if len(final_suggestions) == 0 and escape_hatch_sug:
            final_suggestions = [escape_hatch_sug]
            
        # Absolute Output Guarantee
        if not final_suggestions:
            fallback_data = self._generate_fallback_suggestions()
            final_suggestions = fallback_data["suggestions"]
            
        final_suggestions = final_suggestions[:5]
            
        return {
            "suggestions": final_suggestions,
            "explanation": str(parsed.get("explanation", "")) or "AI-generated insights"
        }

    
    def _generate_enhanced_suggestions(self) -> str:
        """
        Generate enhanced suggestions based on analysis results
        This simulates AI-like recommendations
        """
        suggestions = []
        
        # Header
        suggestions.append("🤖 AI-Powered Code Improvement Suggestions")
        suggestions.append("=" * 50)
        suggestions.append("")
        
        # Analyze complexity
        avg_complexity = self.complexity_data.get('average_complexity', 0)
        max_complexity = self.complexity_data.get('max_complexity', 0)
        high_risk_funcs = self.complexity_data.get('high_risk_functions', [])
        
        if avg_complexity > 10:
            suggestions.append("⚠️ COMPLEXITY ALERT:")
            suggestions.append(f"Your code has an average complexity of {avg_complexity}.")
            suggestions.append("High complexity makes code harder to test and maintain.")
            suggestions.append("")
            suggestions.append("Recommendations:")
            suggestions.append("• Break down complex functions into smaller, focused functions")
            suggestions.append("• Use early returns to reduce nesting")
            suggestions.append("• Extract conditional logic into well-named helper functions")
            suggestions.append("")
        
        if high_risk_funcs:
            suggestions.append("🔴 HIGH-RISK FUNCTIONS DETECTED:")
            for func in high_risk_funcs[:3]:  # Top 3
                suggestions.append(f"• {func['function']}() - Complexity: {func['complexity']} (Line {func['line']})")
            suggestions.append("")
            suggestions.append("Priority Actions:")
            suggestions.append("1. Refactor these functions immediately")
            suggestions.append("2. Add comprehensive unit tests")
            suggestions.append("3. Consider using design patterns (Strategy, Command)")
            suggestions.append("")
        
        # Analyze issues by severity
        critical = [i for i in self.issues if i['severity'] == 'critical']
        warnings = [i for i in self.issues if i['severity'] == 'warning']
        info = [i for i in self.issues if i['severity'] == 'info']
        
        if critical:
            suggestions.append("🚨 CRITICAL ISSUES:")
            for issue in critical[:3]:
                suggestions.append(f"• {issue['message']} (Line {issue.get('line', '?')})")
            suggestions.append("These require immediate attention!")
            suggestions.append("")
        
        if warnings:
            suggestions.append("⚠️ WARNINGS:")
            suggestions.append(f"Found {len(warnings)} warning(s) that could impact maintainability.")
            
            # Group by rule type
            warning_types = {}
            for w in warnings:
                rule = w['rule']
                warning_types[rule] = warning_types.get(rule, 0) + 1
            
            for rule, count in warning_types.items():
                suggestions.append(f"• {rule.replace('_', ' ').title()}: {count} occurrence(s)")
            suggestions.append("")
        
        # Best practices recommendations
        suggestions.append("💡 BEST PRACTICES RECOMMENDATIONS:")
        
        if not any('docstring' in i['rule'] for i in self.issues):
            suggestions.append("✅ Good: Functions have documentation")
        else:
            suggestions.append("• Add docstrings to all functions and classes")
        
        if not any('naming' in i['rule'] for i in self.issues):
            suggestions.append("✅ Good: Follows naming conventions")
        else:
            suggestions.append("• Follow PEP 8 naming conventions (snake_case for functions, PascalCase for classes)")
        
        if len(self.code.split('\n')) > 500:
            suggestions.append("• Consider splitting into multiple modules")
        
        suggestions.append("• Use type hints for better code clarity")
        suggestions.append("• Add unit tests with at least 80% coverage")
        suggestions.append("• Set up a linter (pylint, flake8) in your CI/CD")
        suggestions.append("")
        
        # Code quality score
        total_issues = len(self.issues)
        quality_score = max(0, 100 - (total_issues * 5) - (avg_complexity * 2))
        
        suggestions.append("📊 CODE QUALITY SCORE:")
        suggestions.append(f"{'█' * int(quality_score / 10)}{' ' * (10 - int(quality_score / 10))} {int(quality_score)}%")
        suggestions.append("")
        
        if quality_score >= 80:
            suggestions.append("🎉 Excellent code quality! Keep up the good work.")
        elif quality_score >= 60:
            suggestions.append("👍 Good code quality. Minor improvements needed.")
        elif quality_score >= 40:
            suggestions.append("⚠️ Fair code quality. Several improvements recommended.")
        else:
            suggestions.append("🔴 Poor code quality. Significant refactoring needed.")
        
        return '\n'.join(suggestions)
    
    def _generate_fallback_suggestions(self) -> Dict[str, Any]:
        """
        Generate dynamic structured fallback dictionary based on code metrics
        """
        suggestions = []
        
        # If high time complexity, suggest optimization
        avg_complexity = self.complexity_data.get('average_complexity', 0)
        max_complexity = self.complexity_data.get('max_complexity', 0)
        
        if avg_complexity > 5 or max_complexity > 10:
            suggestions.append({
                "type": "performance",
                "problem": "High cognitive complexity detected in functions.",
                "solution": "Break down complex functions into smaller, single-responsibility helpers. Extract deeply nested conditional logic into separate, well-named functions.",
                "example": "def handle_user_logic():\n    validate_input()\n    process_data()\n    save_results()"
            })
            
        # If high nesting/issues, suggest refactor
        if len(self.issues) > 3:
            suggestions.append({
                "type": "best_practice",
                "problem": f"The analyzer found {len(self.issues)} structural or stylistic issues.",
                "solution": "Consider setting up an automated linter (like flake8 or pylint) in your CI/CD pipeline to catch these style issues before they are committed.",
                "example": "# .flake8\n[flake8]\nmax-line-length = 88\nextend-ignore = E203"
            })
            
        # If no major issues, suggest advanced best practices
        if not suggestions:
            suggestions.append({
                "type": "best_practice",
                "problem": "Code lacks robust type hinting for better maintainability.",
                "solution": "Add static type hints to your function signatures and variables to improve IDE autocomplete and catch type errors early using tools like mypy.",
                "example": "def process_data(user_id: int, payload: dict) -> bool:\n    pass"
            })
            
        for sug in suggestions:
            sug["source"] = "fallback"
            
        return {
            "suggestions": suggestions,
            "explanation": "Basic analysis (AI unavailable)"
        }