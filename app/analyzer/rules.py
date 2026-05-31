"""
Analysis Engine - Rules Module
UPGRADED: Enhanced code smell detection + new detectors
Maintains backward compatibility
"""

import ast
import re
import copy
import hashlib
import builtins
import uuid
from typing import List, Dict, Any, Set

BUILTINS = set(dir(builtins))


class ScopeTracker(ast.NodeVisitor):
    """
    Intelligent AST scope tracker for identifying variables in the global namespace.
    Handles nested scoping, tuple unpacking, and deduplication safely.
    """
    def __init__(self):
        self.scope_stack = ["module"]
        self.global_vars = []
        self.seen_vars = set()

    def _extract_names(self, node):
        names = []
        if isinstance(node, ast.Name):
            names.append((node.id, getattr(node, 'lineno', 0)))
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                names.extend(self._extract_names(elt))
        elif isinstance(node, ast.Starred):
            names.extend(self._extract_names(node.value))
        return names

    def _add_global(self, target):
        if self.scope_stack[-1] == "module":
            names = self._extract_names(target)
            for name, lineno in names:
                if name not in self.seen_vars and not name.startswith('_'):
                    self.seen_vars.add(name)
                    self.global_vars.append({'name': name, 'line': lineno})

    def visit_FunctionDef(self, node):
        self.scope_stack.append("function")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.scope_stack.append("function")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_ClassDef(self, node):
        self.scope_stack.append("class")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Assign(self, node):
        for target in node.targets:
            self._add_global(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        self._add_global(node.target)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self._add_global(node.target)
        self.generic_visit(node)


class ASTNormalizer(ast.NodeTransformer):
    """
    Normalizes AST functions by safely stripping formatting, docstrings,
    and uniformly mapping variables to generic tokens while preserving built-ins.
    """
    def __init__(self):
        self.var_map = {}
        self.var_counter = 0

    def _get_var(self, name: str) -> str:
        if name not in self.var_map:
            self.var_map[name] = f"var_{self.var_counter}"
            self.var_counter += 1
        return self.var_map[name]

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in BUILTINS:
            pass  # Preserve built-in name
        else:
            node.func = self.visit(node.func)
        node.args = [self.visit(arg) for arg in node.args]
        node.keywords = [self.visit(k) for k in node.keywords]
        return node

    def visit_Name(self, node):
        node.id = self._get_var(node.id)
        return node

    def visit_arg(self, node):
        node.arg = self._get_var(node.arg)
        return self.generic_visit(node)
        
    def visit_arguments(self, node):
        self.generic_visit(node)
        return node

    def visit_Attribute(self, node):
        node.value = self.visit(node.value)
        return node

    def visit_keyword(self, node):
        node.value = self.visit(node.value)
        return node


class RuleEngine:
    """
    Enhanced code quality detector
    EXISTING rules + NEW rules:
    - Unused variables (NEW)
    - Dead code after return/break (NEW)
    - Infinite loops (NEW)
    - All existing rules preserved
    """
    
    SEVERITY_LEVELS = {'high': 3, 'medium': 2, 'low': 1}
    
    def __init__(self, code: str, parsed_data: Dict[str, Any]):
        self.code = code
        self.parsed_data = parsed_data
        self.issues = []
        self.assigned_vars = {}
        self.used_vars = set()
        self._tree = None
        self._tree_parsed = False
        
    def _get_tree(self):
        """Optimized syntax-safe AST parsing with caching"""
        if not self._tree_parsed:
            try:
                self._tree = ast.parse(self.code)
            except SyntaxError:
                self._tree = None
            self._tree_parsed = True
        return self._tree
        
    def analyze(self) -> List[Dict[str, Any]]:
        """Run all rule checks (existing + new)"""
        # EXISTING RULES
        self._check_long_functions()
        self._check_too_many_arguments()
        self._check_deep_nesting()
        self._check_unused_imports()
        self._check_naming_conventions()
        self._check_missing_docstrings()
        self._check_magic_numbers()
        self._check_duplicate_code()
        self._check_global_variables()
        self._check_exception_handling()
        
        # NEW RULES
        self._check_unused_variables()
        self._check_dead_code()
        self._check_infinite_loops()
        self._check_security_risks()
        
        self.issues.sort(key=lambda x: self.SEVERITY_LEVELS.get(x['severity'], 0), reverse=True)
        return self.issues
    
    def _add_issue(self, rule: str, severity: str, message: str, line: int = None, suggestion: str = None, category: str = "best_practice"):
        """Helper to add an issue"""
        self.issues.append({
            'id': str(uuid.uuid4()),
            'rule': rule,
            'severity': severity,
            'type': category,
            'category': category, # Keep for backward compatibility internally
            'message': message,
            'line': line if line else 1,
            'scope': "local" if line else "global",
            'suggestion': suggestion,
            'source': 'fallback'
        })
    
    # ==================== EXISTING RULES (UNCHANGED) ====================
    
    def _check_long_functions(self):
        """Detect functions that are too long (>50 lines)"""
        for func in self.parsed_data.get('functions', []):
            if func['num_statements'] > 50:
                self._add_issue(
                    'long_function', 'low',
                    f"Function '{func['name']}' is too long ({func['num_statements']} statements)",
                    func['line'],
                    'Consider breaking into smaller functions',
                    'readability'
                )
    
    def _check_too_many_arguments(self):
        """Detect functions with too many parameters (>5)"""
        for func in self.parsed_data.get('functions', []):
            if len(func['args']) > 5:
                self._add_issue(
                    'too_many_arguments', 'low',
                    f"Function '{func['name']}' has {len(func['args'])} parameters",
                    func['line'],
                    'Consider using a configuration object',
                    'readability'
                )
    
    def _check_deep_nesting(self):
        """Detect deeply nested code (>4 levels)"""
        tree = self._get_tree()
        if not tree: return
        try:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    depth = self._calculate_nesting_depth(node)
                    if depth > 4:
                        self._add_issue(
                            'deep_nesting', 'low',
                            f"Function '{node.name}' has deep nesting (level {depth})",
                            node.lineno,
                            'Extract nested logic into separate functions',
                            'readability'
                        )
        except:
            pass
    
    def _calculate_nesting_depth(self, node, current_depth=0):
        """Calculate maximum nesting depth"""
        max_depth = current_depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        return max_depth
    
    def _check_unused_imports(self):
        """Detect potentially unused imports"""
        imports = self.parsed_data.get('imports', [])
        code_lines = self.code.split('\n')
        
        for imp in imports:
            module_name = imp.get('name') or imp.get('module')
            if module_name:
                used = any(module_name in line for i, line in enumerate(code_lines) if i + 1 != imp['line'])
                
                if not used:
                    self._add_issue(
                        'unused_import', 'low',
                        f"Import '{module_name}' appears unused",
                        imp['line'],
                        'Remove unused imports',
                        'best_practice'
                    )
    
    def _check_naming_conventions(self):
        """Check PEP 8 naming conventions"""
        for func in self.parsed_data.get('functions', []):
            if not re.match(r'^[a-z_][a-z0-9_]*$', func['name']) and not func['name'].startswith('__'):
                self._add_issue(
                    'naming_convention', 'low',
                    f"Function '{func['name']}' should use snake_case",
                    func['line'],
                    'Rename function using snake_case convention',
                    'readability'
                )
        
        for cls in self.parsed_data.get('classes', []):
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', cls['name']):
                self._add_issue(
                    'naming_convention', 'low',
                    f"Class '{cls['name']}' should use PascalCase",
                    cls['line'],
                    'Use PascalCase for class names (PEP 8)',
                    'readability'
                )
    
    def _check_missing_docstrings(self):
        """Check for missing docstrings"""
        tree = self._get_tree()
        if not tree: return
        try:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    has_docstring = (len(node.body) > 0 and isinstance(node.body[0], ast.Expr) 
                                   and isinstance(node.body[0].value, ast.Constant))
                    if not has_docstring:
                        node_type = 'Function' if isinstance(node, ast.FunctionDef) else 'Class'
                        self._add_issue(
                            'missing_docstring', 'low',
                            f"{node_type} '{node.name}' is missing a docstring",
                            node.lineno,
                            'Add docstring to document purpose',
                            'readability'
                        )
        except:
            pass
    
    def _check_magic_numbers(self):
        """Detect magic numbers"""
        tree = self._get_tree()
        if not tree: return
        try:
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    if node.value not in [0, 1, -1, 2, 10, 100] and hasattr(node, 'lineno'):
                        self._add_issue(
                            'magic_number', 'low',
                            f"Magic number '{node.value}' found",
                            node.lineno,
                            'Define as a named constant',
                            'readability'
                        )
        except:
            pass
    
    def _check_duplicate_code(self):
        """Advanced AST-based duplicate code detection"""
        tree = self._get_tree()
        if not tree: return
        
        try:
            hash_map = {}
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    node_count = len(list(ast.walk(node)))
                    if node_count < 10:
                        continue
                        
                    if len(node.body) == 1:
                        stmt = node.body[0]
                        if isinstance(stmt, ast.Pass):
                            continue
                        if isinstance(stmt, ast.Return) and stmt.value is None:
                            continue
                            
                    func_copy = copy.deepcopy(node)
                    
                    if (func_copy.body and isinstance(func_copy.body[0], ast.Expr) and 
                        isinstance(func_copy.body[0].value, ast.Constant) and 
                        isinstance(func_copy.body[0].value.value, str)):
                        func_copy.body = func_copy.body[1:]
                        
                    func_copy.name = "generic_func"
                    
                    normalizer = ASTNormalizer()
                    normalized_func = normalizer.visit(func_copy)
                    
                    dump_str = ast.dump(normalized_func, annotate_fields=False, include_attributes=False)
                    func_hash = hashlib.md5(dump_str.encode()).hexdigest()
                    
                    if func_hash not in hash_map:
                        hash_map[func_hash] = []
                    hash_map[func_hash].append((node.name, node.lineno))
            
            for func_hash, duplicates in hash_map.items():
                if len(duplicates) > 1:
                    names = [f"'{d[0]}'" for d in duplicates]
                    first_line = duplicates[0][1]
                    
                    self._add_issue(
                        'duplicate_code', 'medium',
                        f"{', '.join(names[:-1])} and {names[-1]} share identical logic structure",
                        first_line,
                        'Extract identical logic into a shared reusable function',
                        'best_practice'
                    )
        except Exception:
            pass
    
    def _check_global_variables(self):
        """Warn about global variables with accurate scoping and destructuring"""
        tree = self._get_tree()
        if not tree: return
        try:
            tracker = ScopeTracker()
            tracker.visit(tree)
            
            for var in tracker.global_vars:
                self._add_issue(
                    'global_variable', 'low',
                    f"Global variable '{var['name']}' detected",
                    var['line'],
                    'Consider function parameters or class attributes',
                    'best_practice'
                )
        except Exception as e:
            pass
    
    def _check_exception_handling(self):
        """Check for bare except clauses"""
        tree = self._get_tree()
        if not tree: return
        try:
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    self._add_issue(
                        'bare_except', 'high',
                        'Bare except clause detected',
                        node.lineno,
                        'Catch specific exceptions',
                        'security'
                    )
        except:
            pass
    
    # ==================== NEW RULES ====================
    
    def _check_unused_variables(self):
        """NEW: Detect variables assigned but never used"""
        tree = self._get_tree()
        if not tree: return
        try:
            
            # Collect assigned and used variables
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.assigned_vars[target.id] = getattr(node, 'lineno', 0)
                            
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    self.used_vars.add(node.id)
            
            # Find unused (not starting with _)
            for var_name, line_no in self.assigned_vars.items():
                if var_name not in self.used_vars and not var_name.startswith('_'):
                    self._add_issue(
                        'unused_variable', 'low',
                        f"Unused variable '{var_name}'",
                        line_no,
                        "Remove or prefix with _ if intentionally unused",
                        'best_practice'
                    )
        except:
            pass
    
    def _check_dead_code(self):
        """NEW: Detect code after return/break/continue"""
        tree = self._get_tree()
        if not tree: return
        try:
            
            for node in ast.walk(tree):
                if hasattr(node, 'body') and isinstance(node.body, list):
                    for i, stmt in enumerate(node.body):
                        if isinstance(stmt, (ast.Return, ast.Break, ast.Continue)):
                            if i < len(node.body) - 1:
                                next_stmt = node.body[i + 1]
                                self._add_issue(
                                    'dead_code', 'low',
                                    f"Dead code after {stmt.__class__.__name__.lower()}",
                                    getattr(next_stmt, 'lineno', 0),
                                    "Remove unreachable code",
                                    'best_practice'
                                )
        except:
            pass
    
    def _check_infinite_loops(self):
        """NEW: Detect while True without break"""
        tree = self._get_tree()
        if not tree: return
        try:
            
            for node in ast.walk(tree):
                if isinstance(node, ast.While):
                    # Check if condition is True
                    if isinstance(node.test, ast.Constant) and node.test.value is True:
                        # Check for break statement
                        has_break = any(isinstance(child, ast.Break) for child in ast.walk(node))
                        
                        if not has_break:
                            self._add_issue(
                                'infinite_loop', 'high',
                                'Potential infinite loop (while True without break)',
                                getattr(node, 'lineno', 0),
                                'Add break condition or exit mechanism',
                                'performance'
                            )
        except:
            pass

    def _check_security_risks(self):
        """NEW: Detect dangerous functions like eval, exec, and subprocess"""
        tree = self._get_tree()
        if not tree: return
        try:
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Direct call: eval() or exec()
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ['eval', 'exec']:
                            self._add_issue(
                                'security_risk', 'high',
                                f"Dangerous built-in function '{node.func.id}' used",
                                getattr(node, 'lineno', 0),
                                f"Avoid using {node.func.id}() with untrusted input",
                                'security'
                            )
                    
                    # Attribute call: os.system(), pickle.load(), subprocess.run()
                    elif isinstance(node.func, ast.Attribute):
                        func_name = getattr(node.func, 'attr', '')
                        obj_name = ''
                        
                        if isinstance(node.func.value, ast.Name):
                            obj_name = node.func.value.id
                            
                        # Detect os.system, pickle.load, etc
                        if obj_name == 'os' and func_name == 'system':
                            self._add_issue(
                                'security_risk', 'high',
                                "Use of 'os.system' detected",
                                getattr(node, 'lineno', 0),
                                "Use subprocess module with shell=False instead",
                                'security'
                            )
                        elif obj_name == 'pickle' and func_name in ['load', 'loads']:
                            self._add_issue(
                                'security_risk', 'high',
                                "Use of 'pickle.load' detected",
                                getattr(node, 'lineno', 0),
                                "Pickle is unsafe. Use json module instead",
                                'security'
                            )
                        elif obj_name == 'subprocess' and func_name in ['call', 'run', 'Popen']:
                            self._add_issue(
                                'security_risk', 'high',
                                f"Use of 'subprocess.{func_name}' detected",
                                getattr(node, 'lineno', 0),
                                "Ensure shell=False and input is sanitized",
                                'security'
                            )
                        # Also catch obj.eval() if somebody aliases
                        elif func_name in ['eval', 'exec']:
                            self._add_issue(
                                'security_risk', 'high',
                                f"Dangerous function call '{func_name}' used via attribute",
                                getattr(node, 'lineno', 0),
                                f"Avoid using {func_name}() with untrusted input",
                                'security'
                            )
        except Exception:
            pass