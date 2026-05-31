import ast
from typing import Dict, Any

class SemanticDriftDetector:
    """
    Analyzes Python AST to detect dangerous semantic drift between original code and AI-optimized code.
    Detects removed conditions, loops, exception handlers, and returns.
    """
    
    @staticmethod
    def detect_drift(original_code: str, new_code: str) -> Dict[str, Any]:
        result = {
            "has_drift": False,
            "risk_level": "low",
            "reason": ""
        }
        
        try:
            original_ast = ast.parse(original_code)
            new_ast = ast.parse(new_code)
        except SyntaxError:
            # SyntaxError should already be caught by validation, but handle gracefully
            return {"has_drift": True, "risk_level": "high", "reason": "Invalid syntax in new code"}
            
        def get_ast_counts(tree):
            counts = {
                "if_statements": 0,
                "loops": 0,
                "try_blocks": 0,
                "returns": 0,
                "function_calls": set()
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    counts["if_statements"] += 1
                elif isinstance(node, (ast.For, ast.While)):
                    counts["loops"] += 1
                elif isinstance(node, ast.Try):
                    counts["try_blocks"] += 1
                elif isinstance(node, ast.Return):
                    counts["returns"] += 1
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        counts["function_calls"].add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        counts["function_calls"].add(node.func.attr)
                        
            return counts

        orig_counts = get_ast_counts(original_ast)
        new_counts = get_ast_counts(new_ast)
        
        reasons = []
        risk = "low"
        
        # High Risk: Removing authentication, try/except, or returns
        if new_counts["try_blocks"] < orig_counts["try_blocks"]:
            reasons.append("Removed exception handling (try/except block)")
            risk = "high"
            
        if new_counts["returns"] < orig_counts["returns"]:
            reasons.append("Changed return paths (fewer return statements)")
            risk = "high"
            
        # Medium Risk: Removing loops or conditions
        if new_counts["if_statements"] < orig_counts["if_statements"]:
            reasons.append("Removed condition (if statement)")
            if risk != "high": risk = "medium"
            
        if new_counts["loops"] < orig_counts["loops"]:
            reasons.append("Removed or restructured loop")
            if risk != "high": risk = "medium"
            
        # Check specific function calls missing (Security/Validation proxies)
        missing_calls = orig_counts["function_calls"] - new_counts["function_calls"]
        dangerous_missing = [c for c in missing_calls if any(x in c.lower() for x in ['auth', 'validate', 'check', 'verify', 'secure'])]
        if dangerous_missing:
            reasons.append(f"Removed critical function call(s): {', '.join(dangerous_missing)}")
            risk = "high"

        if reasons:
            result["has_drift"] = True
            result["risk_level"] = risk
            result["reason"] = " | ".join(reasons)
            
        return result
