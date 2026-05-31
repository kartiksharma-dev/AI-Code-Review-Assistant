"""
Analysis Engine - Advanced Analyzer
NEW: Function-level risk assessment
"""

import ast
from typing import Dict, List, Any


class AdvancedAnalyzer:
    """Per-function analysis with risk scoring"""
    
    def __init__(self, code: str, complexity_data: Dict, issues: List):
        self.code = code
        self.complexity_data = complexity_data
        self.issues = issues
        
    def analyze_functions(self) -> List[Dict]:
        """Analyze each function with risk assessment"""
        results = []
        
        for func_name, func_data in self.complexity_data.get('function_details', {}).items():
            func_issues = self._get_function_issues(func_name, func_data.get('line', 0))
            risk = self._calculate_risk(func_data, func_issues)
            
            results.append({
                'function_name': func_name,
                'line': func_data.get('line', 0),
                'complexity': {
                    'cyclomatic': func_data.get('complexity', 1),
                    'time': func_data.get('time_complexity', 'O(1)'),
                    'space': func_data.get('space_complexity', 'O(1)'),
                    'reason': func_data.get('big_o_reason', '')
                },
                'issues': func_issues,
                'risk': risk
            })
        
        results.sort(key=lambda x: {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}.get(x['risk'], 0), reverse=True)
        return results
    
    def _get_function_issues(self, func_name: str, func_line: int) -> List:
        """Filter issues for this function"""
        func_issues = []
        func_end = func_line + 50
        
        try:
            tree = ast.parse(self.code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    if hasattr(node, 'end_lineno'):
                        func_end = node.end_lineno
                    break
        except:
            pass
        
        for issue in self.issues:
            if func_line <= issue.get('line', 0) <= func_end:
                func_issues.append(issue)
        
        return func_issues
    
    def _calculate_risk(self, func_data: Dict, func_issues: List) -> str:
        """Calculate HIGH/MEDIUM/LOW risk"""
        cyclomatic = func_data.get('complexity', 1)
        time_comp = func_data.get('time_complexity', 'O(1)')
        
        critical = sum(1 for i in func_issues if i.get('severity') == 'critical')
        warnings = sum(1 for i in func_issues if i.get('severity') == 'warning')
        
        # HIGH risk
        if time_comp in ['O(2^n)', 'O(n!)'] or cyclomatic > 20 or critical > 0:
            return 'HIGH'
        
        # MEDIUM risk
        if time_comp in ['O(n^2)', 'O(n^3)'] or 11 <= cyclomatic <= 20 or warnings >= 3:
            return 'MEDIUM'
        
        return 'LOW'
    
    def get_summary(self) -> Dict:
        """Get analysis summary"""
        funcs = self.analyze_functions()
        
        return {
            'total_functions': len(funcs),
            'high_risk': sum(1 for f in funcs if f['risk'] == 'HIGH'),
            'medium_risk': sum(1 for f in funcs if f['risk'] == 'MEDIUM'),
            'low_risk': sum(1 for f in funcs if f['risk'] == 'LOW'),
            'overall_big_o': self.complexity_data.get('overall_big_o', 'O(1)')
        }