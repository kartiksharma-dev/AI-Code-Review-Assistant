"""
Analysis Engine Package
UPDATED: Added AdvancedAnalyzer export
Maintains backward compatibility
"""

from .parser import CodeParser
from .rules import RuleEngine
from .complexity import ComplexityAnalyzer
from .ai_layer import AIAnalyzer
from .advanced_analyzer import AdvancedAnalyzer  # NEW

__all__ = [
    'CodeParser', 
    'RuleEngine', 
    'ComplexityAnalyzer', 
    'AIAnalyzer',
    'AdvancedAnalyzer'  # NEW
]