"""
Tool schemas for MCP server

Defines Pydantic models for input/output validation of MCP tools.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# ============================================================================
# Input Schemas
# ============================================================================


class ValidateOpenAPIInput(BaseModel):
    """Input schema for validate_openapi tool"""

    spec_path: str = Field(..., description="Path to OpenAPI specification file")
    ruleset: Optional[str] = Field(
        None, description="Optional path to custom Spectral ruleset"
    )


class ValidateArchitectureInput(BaseModel):
    """Input schema for validate_architecture tool"""

    project_path: str = Field(
        ..., description="Path to compiled Java classes directory"
    )
    rule_profile: str = Field(
        "default", description="Rule profile to use (default: 'default')"
    )


class GovernanceSummaryInput(BaseModel):
    """Input schema for governance_summary tool"""

    project_path: str = Field(..., description="Path to project directory")


# ============================================================================
# Output Schemas
# ============================================================================


class Violation(BaseModel):
    """Normalized violation structure"""

    rule_id: str = Field(..., description="Unique identifier for the rule")
    description: str = Field(
        ..., description="Human-readable description of the violation"
    )
    severity: Literal["critical", "warning", "info"] = Field(
        ..., description="Severity level"
    )
    file: str = Field(..., description="File path where violation occurred")
    line: Optional[int] = Field(None, description="Line number (if applicable)")
    fix_hint: str = Field(..., description="Suggested fix or remediation guidance")


class SeveritySummary(BaseModel):
    """Summary of violations by severity"""

    critical: int = Field(0, description="Number of critical violations")
    warning: int = Field(0, description="Number of warnings")
    info: int = Field(0, description="Number of info-level issues")


class ValidateOpenAPIOutput(BaseModel):
    """Output schema for validate_openapi tool"""

    violations: List[Violation] = Field(
        default_factory=list, description="List of violations found"
    )
    severity_summary: SeveritySummary = Field(..., description="Summary by severity")
    suggested_fixes: List[str] = Field(
        default_factory=list, description="High-level suggested fixes"
    )


class ValidateArchitectureOutput(BaseModel):
    """Output schema for validate_architecture tool"""

    violations: List[Violation] = Field(
        default_factory=list, description="List of violations found"
    )
    impacted_layers: List[str] = Field(
        default_factory=list, description="Architectural layers impacted"
    )
    refactoring_guidance: List[str] = Field(
        default_factory=list, description="Refactoring suggestions"
    )


class GovernanceSummaryOutput(BaseModel):
    """Output schema for governance_summary tool"""

    overall_health_score: int = Field(
        ..., ge=0, le=100, description="Overall health score (0-100)"
    )
    critical_violations: int = Field(0, description="Number of critical violations")
    warnings: int = Field(0, description="Number of warnings")
    next_steps: List[str] = Field(
        default_factory=list, description="Recommended next steps"
    )
    scan_types_detected: List[Literal["api_spec", "java_architecture"]] = Field(
        default_factory=list, description="Types of scans detected in project"
    )


# ============================================================================
# Auto-Fix Tool Schemas
# ============================================================================


class ProposeFixesInput(BaseModel):
    """Input schema for propose_fixes tool"""

    report_path: str = Field(..., description="Path to governance report JSON file")
    project_path: str = Field(..., description="Path to project directory")
    output_dir: Optional[str] = Field(
        None, description="Optional directory for output files"
    )
    use_copilot: bool = Field(
        True, description="Use GitHub Copilot for fast fix generation (default: True)"
    )


class ProposedFixInfo(BaseModel):
    """Information about a proposed fix"""

    fix_id: str = Field(..., description="Unique fix identifier")
    rule_id: str = Field(..., description="Rule being fixed")
    file_path: str = Field(..., description="File to be modified")
    line_number: Optional[int] = Field(None, description="Line number of violation")
    complexity: Literal["simple", "moderate", "complex"] = Field(
        ..., description="Fix complexity"
    )
    is_safe_to_auto_apply: bool = Field(
        ..., description="Whether fix can be auto-applied"
    )
    explanation: str = Field(..., description="Explanation of the fix")


class ProposeFixesOutput(BaseModel):
    """Output schema for propose_fixes tool"""

    fixes_proposed: int = Field(..., description="Number of fixes proposed")
    fixes: List[ProposedFixInfo] = Field(
        default_factory=list, description="List of proposed fixes"
    )
    diff_preview_path: Optional[str] = Field(
        None, description="Path to diff preview file"
    )
    safe_to_auto_apply_count: int = Field(
        0, description="Number of safe-to-auto-apply fixes"
    )
    summary_table: Optional[str] = Field(
        None, description="Markdown table summary of fixes"
    )


class ReviewFixesInput(BaseModel):
    """Input schema for review_fixes tool"""

    fix_session_id: str = Field(..., description="Fix session identifier")
    approved_fix_ids: List[str] = Field(
        default_factory=list, description="List of approved fix IDs"
    )
    rejected_fix_ids: List[str] = Field(
        default_factory=list, description="List of rejected fix IDs"
    )
    comments: Optional[dict] = Field(None, description="Optional comments per fix_id")


class ReviewFixesOutput(BaseModel):
    """Output schema for review_fixes tool"""

    approved_count: int = Field(..., description="Number of approved fixes")
    rejected_count: int = Field(..., description="Number of rejected fixes")
    pending_count: int = Field(..., description="Number of pending fixes")
    ready_to_apply: bool = Field(..., description="Whether fixes are ready to apply")


class ApplyFixesInput(BaseModel):
    """Input schema for apply_fixes tool"""

    fix_session_id: str = Field(..., description="Fix session identifier")
    create_branch: bool = Field(True, description="Whether to create a git branch")
    branch_name: Optional[str] = Field(None, description="Optional custom branch name")
    commit_strategy: Literal["by-rule", "single"] = Field(
        "by-rule", description="Commit strategy"
    )


class ApplyFixesOutput(BaseModel):
    """Output schema for apply_fixes tool"""

    fixes_applied: int = Field(..., description="Number of fixes applied")
    branch_name: Optional[str] = Field(None, description="Git branch name")
    commits_created: int = Field(0, description="Number of commits created")
    files_modified: int = Field(0, description="Number of files modified")


class CreateGovernancePRInput(BaseModel):
    """Input schema for create_governance_pr tool"""

    fix_session_id: str = Field(..., description="Fix session identifier")
    push_to_remote: bool = Field(False, description="Whether to push branch to remote")
    remote_name: str = Field("origin", description="Git remote name")


class CreateGovernancePROutput(BaseModel):
    """Output schema for create_governance_pr tool"""

    branch_name: str = Field(..., description="Git branch name")
    pr_title: str = Field(..., description="Pull request title")
    pr_description_path: str = Field(..., description="Path to PR description file")
    commits: int = Field(..., description="Number of commits")
    files_changed: int = Field(..., description="Number of files changed")
    pushed_to_remote: bool = Field(False, description="Whether branch was pushed")
