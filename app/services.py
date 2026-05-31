"""
Service Layer - Business Logic
Orchestrates analysis engine components and manages data flow
"""

import time
from typing import Dict, Any
from app.analyzer import CodeParser, RuleEngine, ComplexityAnalyzer, AIAnalyzer
from app.models import CodeSubmission
from app.extensions import db


class CodeAnalysisService:
    """
    Main service for code analysis
    Orchestrates parser, rules, complexity, and AI modules
    """
    
    def __init__(self, code: str, language: str = 'python', filename: str = None):
        self.code = code
        self.language = language
        self.filename = filename
        self.results = {}
        
    def analyze(self) -> Dict[str, Any]:
        """
        Execute full analysis pipeline
        Returns comprehensive analysis results
        """
        start_time = time.time()
        
        try:
            # Step 1: Parse code
            parser = CodeParser(self.code)
            parsed_data = parser.parse()
            
            if not parsed_data.get('success'):
                return {
                    'success': False,
                    'error': parsed_data.get('error'),
                    'stage': 'parsing',
                    'time_complexity': 'O(1)',
                    'space_complexity': 'O(1)'
                }
            
            # Step 2: Run rule engine
            rule_engine = RuleEngine(self.code, parsed_data)
            issues = rule_engine.analyze()
            
            # Step 3: Calculate complexity
            complexity_analyzer = ComplexityAnalyzer(self.code, parsed_data)
            complexity_data = complexity_analyzer.calculate()
            
            # Step 4: Generate AI suggestions
            ai_analyzer = AIAnalyzer(self.code, issues, complexity_data)
            ai_suggestions = ai_analyzer.generate_suggestions()
            
            # Calculate analysis duration
            duration = time.time() - start_time
            
            # Compile results
            self.results = {
                'success': True,
                'parsed_data': parsed_data,
                'issues': issues,
                'complexity': complexity_data,
                'time_complexity': complexity_data.get('time_complexity', 'O(1)'),
                'space_complexity': complexity_data.get('space_complexity', 'O(1)'),
                'ai_suggestions': ai_suggestions,
                'analysis_duration': round(duration, 3),
                'summary': self._generate_summary(issues, complexity_data)
            }
            
            return self.results
            
        except Exception as e:
            error_str = str(e).lower()
            code = 'UNKNOWN_ERROR'
            recoverable = False
            severity = 'danger'

            if 'timeout' in error_str or 'deadline' in error_str or 'timed out' in error_str:
                code = 'TIMEOUT'
                recoverable = True
                severity = 'warning'
            elif 'connection' in error_str or 'network' in error_str or 'unreachable' in error_str:
                code = 'NETWORK'
                recoverable = True
                severity = 'warning'
            elif '429' in error_str or 'quota' in error_str or 'rate limit' in error_str:
                code = 'RATE_LIMIT'
                recoverable = True
                severity = 'warning'
            elif 'json' in error_str or 'decode' in error_str or 'parse' in error_str:
                code = 'INVALID_RESPONSE'
                recoverable = True
                severity = 'danger'

            return {
                'success': False,
                'error': {
                    'message': f'Analysis failed: {str(e)}',
                    'code': code,
                    'recoverable': recoverable,
                    'severity': severity
                },
                'stage': 'execution',
                'time_complexity': 'O(1)',
                'space_complexity': 'O(1)'
            }
    
    def _generate_summary(self, issues: list, complexity_data: dict) -> Dict[str, Any]:
        """Generate analysis summary statistics"""
        return {
            'total_issues': len(issues),
            'high_issues': len([i for i in issues if i['severity'] == 'high']),
            'medium_issues': len([i for i in issues if i['severity'] == 'medium']),
            'low_issues': len([i for i in issues if i['severity'] == 'low']),
            'avg_complexity': complexity_data.get('average_complexity', 0),
            'max_complexity': complexity_data.get('max_complexity', 0),
            'overall_risk': complexity_data.get('overall_risk', 'unknown')
        }
    
    def save_to_database(self, user_id: int = None) -> CodeSubmission:
        """
        Persist analysis results to database
        Enables history tracking and reporting
        """
        if not self.results.get('success'):
            raise ValueError("Cannot save failed analysis")
        
        import json
        
        # Serialize dicts/lists to json strings to avoid SQLite parameter binding errors
        issues_json = json.dumps(self.results.get('issues', []))
        complexity_json = json.dumps(self.results.get('complexity', {}))
        ai_suggestions_json = json.dumps(self.results.get('ai_suggestions', {}))

        submission = CodeSubmission(
            code_text=self.code,
            language=self.language,
            filename=self.filename,
            issues=issues_json,
            complexity_score=self.results['complexity'].get('average_complexity', 0),
            complexity_details=complexity_json,
            ai_suggestions=ai_suggestions_json,
            analysis_duration=self.results.get('analysis_duration', 0.0),
            user_id=user_id
        )
        
        db.session.add(submission)
        # Flush to get the ID but don't commit yet (routes.py commits)
        db.session.flush()
        
        return submission
    
    @staticmethod
    def get_history(user_id: int = None, limit: int = 10) -> list:
        """
        Retrieve analysis history
        Optionally filtered by user
        """
        query = CodeSubmission.query
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        submissions = query.order_by(
            CodeSubmission.created_at.desc()
        ).limit(limit).all()
        
        return [s.to_dict() for s in submissions]
    
    @staticmethod
    def get_submission_by_id(submission_id: int) -> CodeSubmission:
        """Retrieve specific submission by ID"""
        return CodeSubmission.query.get_or_404(submission_id)


class CodeValidationService:
    """
    Validation service for code input
    Ensures code meets requirements before analysis
    """
    
    @staticmethod
    def validate_code(code: str, max_length: int = 50000) -> Dict[str, Any]:
        """
        Validate code input
        Returns validation result with any errors
        """
        code_strip = code.strip()
        if not code_strip:
            return {
                'valid': False,
                'error': 'Code cannot be empty'
            }
        
        if len(code) > max_length:
            return {
                'valid': False,
                'error': f'Code exceeds maximum length of {max_length} characters'
            }
        
        # Semantic Input Guard (ignore known placeholders, allow short code)
        placeholders = [
            "// Write your code here...",
            "# Write your code here...",
            "/* Write your code here... */"
        ]
        
        if code_strip in placeholders:
            return {
                'valid': False,
                'error': 'Please enter some code to analyze'
            }
        
        return {
            'valid': True
        }
    
    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
        """Check if file has allowed extension"""
        if not filename:
            return False
        
        extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return extension in allowed_extensions