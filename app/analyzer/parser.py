"""
Analysis Engine - Parser Module
AST-based code parsing and extraction using Python's ast module
"""

import ast
from typing import List, Dict, Any


class CodeParser:
    """
    Parses Python code into Abstract Syntax Tree (AST)
    Extracts functions, classes, imports, and code structure
    """
    
    def __init__(self, code: str):
        self.code = code
        self.tree = None
        self.functions = []
        self.classes = []
        self.imports = []
        self.variables = []
        
    def parse(self) -> Dict[str, Any]:
        """
        Main parsing method
        Returns structured data about the code
        """
        try:
            self.tree = ast.parse(self.code)
            self._extract_functions()
            self._extract_classes()
            self._extract_imports()
            self._extract_variables()
            
            return {
                'success': True,
                'functions': self.functions,
                'classes': self.classes,
                'imports': self.imports,
                'variables': self.variables,
                'total_lines': len(self.code.split('\n'))
            }
        except SyntaxError as e:
            return {
                'success': False,
                'error': f'Syntax Error: {str(e)}',
                'line': e.lineno,
                'offset': e.offset
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Parsing Error: {str(e)}'
            }
    
    def _extract_functions(self):
        """Extract all function definitions"""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                self.functions.append({
                    'name': node.name,
                    'line': node.lineno,
                    'args': [arg.arg for arg in node.args.args],
                    'num_statements': len(node.body),
                    'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
                    'is_async': isinstance(node, ast.AsyncFunctionDef),
                    'returns': self._get_return_type(node)
                })
    
    def _extract_classes(self):
        """Extract all class definitions"""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                self.classes.append({
                    'name': node.name,
                    'line': node.lineno,
                    'methods': methods,
                    'num_methods': len(methods),
                    'bases': [self._get_name(base) for base in node.bases],
                    'decorators': [self._get_decorator_name(d) for d in node.decorator_list]
                })
    
    def _extract_imports(self):
        """Extract all import statements"""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    self.imports.append({
                        'type': 'from_import',
                        'module': node.module,
                        'name': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno
                    })
    
    def _extract_variables(self):
        """Extract global variable assignments"""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.variables.append({
                            'name': target.id,
                            'line': node.lineno,
                            'scope': 'global'
                        })
    
    def _get_decorator_name(self, decorator) -> str:
        """Get decorator name from AST node"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id
        return 'unknown'
    
    def _get_return_type(self, node) -> str:
        """Extract return type annotation if present"""
        if node.returns:
            return ast.unparse(node.returns) if hasattr(ast, 'unparse') else 'annotated'
        return None
    
    def _get_name(self, node) -> str:
        """Get name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return 'unknown'
    
    def get_function_body(self, func_name: str) -> str:
        """Get the source code of a specific function"""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                # Get line numbers
                start = node.lineno - 1
                end = node.end_lineno if hasattr(node, 'end_lineno') else start + len(node.body)
                lines = self.code.split('\n')[start:end]
                return '\n'.join(lines)
        return None