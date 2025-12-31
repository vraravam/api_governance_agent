"""
Auto-Fix Module for API Governance Agent

Provides IDE-integrated auto-fix capabilities for governance violations.
"""

from .engine import AutoFixEngine
from .proposer import FixProposer
from .diff_generator import DiffGenerator
from .review_gate import ReviewGate
from .pr_creator import PRCreator
from .category_manager import CategoryManager
from .subcategory_manager import SubcategoryManager

__all__ = [
    "AutoFixEngine",
    "FixProposer",
    "DiffGenerator",
    "ReviewGate",
    "PRCreator",
    "CategoryManager",
    "SubcategoryManager",
]
