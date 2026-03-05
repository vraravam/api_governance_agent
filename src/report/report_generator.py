from datetime import datetime
from pathlib import Path
from typing import Dict, List
from utils import FileUtils, ViolationUtils, ReportUtils


class ReportGenerator:
    """Generates markdown reports from scan results"""

    def __init__(self, scan_result):
        """Initialize with scan result"""
        self.scan_result = scan_result

    def generate_markdown(self, output_path: Path):
        """Generate a markdown report from scan results"""
        output_path = Path(output_path)

        # Generate markdown content
        content = self._generate_content()

        # Write to file
        FileUtils.write_text(str(output_path), content)

    def generate_json(self, output_path: Path, include_categories: bool = False):
        """Generate a JSON report from scan results

        Args:
            output_path: Path to save JSON report
            include_categories: Whether to include violation categories
        """
        output_path = Path(output_path)

        all_violations = (
            self.scan_result.spectral_results + self.scan_result.llm_results
        )

        severity_counts = ViolationUtils.count_by_severity(all_violations)

        data = {
            "meta": {
                "scan_type": self.scan_result.scan_type,
                "project_path": self.scan_result.project_path,
                "timestamp": datetime.now().isoformat(),
                "spec_files": self.scan_result.spec_files,
            },
            "summary": {
                "total_violations": self.scan_result.total_violations,
                "critical": severity_counts.get("error", 0),
                "warning": severity_counts.get("warning", 0),
                "info": severity_counts.get("info", 0),
            },
            "violations": all_violations,
        }

        # Add category information if requested
        if include_categories and all_violations:
            from autofix.category_manager import CategoryManager

            category_manager = CategoryManager()

            categorized = category_manager.categorize_violations(all_violations)
            category_summary = category_manager.generate_category_summary(
                all_violations
            )

            data["categories"] = {
                "categorized_violations": {
                    cat_name: [
                        v.get("code", v.get("rule_id", "unknown")) for v in violations
                    ]
                    for cat_name, violations in categorized.items()
                    if violations
                },
                "summary": category_summary,
            }

        FileUtils.write_json(str(output_path), data)

    def _generate_content(self) -> str:
        """Generate markdown content for the report"""
        lines = []

        # Header
        lines.append(
            ReportUtils.create_summary_header(
                "API Governance Scan Report",
                self.scan_result.project_path,
                self.scan_result.scan_type,
            )
        )

        # Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(
            f"- **Specifications Analyzed:** {len(self.scan_result.spec_files)}"
        )
        lines.append(f"- **Total Violations:** {self.scan_result.total_violations}")
        lines.append(f"- **Critical Issues:** {self._count_by_severity(0)}")
        lines.append(f"- **Warnings:** {self._count_by_severity(1)}")
        lines.append(f"- **Info:** {self._count_by_severity(2)}")
        lines.append("")

        # Spec files
        if self.scan_result.spec_files:
            lines.append("## Specification Files")
            lines.append("")
            for spec_file in self.scan_result.spec_files:
                lines.append(f"- `{spec_file}`")
            lines.append("")

        # Automated Rules Results
        if self.scan_result.spectral_results:
            lines.append("## Automated Rules Results")
            lines.append("")
            lines.extend(
                self._format_violations(self.scan_result.spectral_results, "Automated")
            )
            lines.append("")

        # LLM Results
        if self.scan_result.llm_results:
            lines.append("## Semantic Analysis Results (LLM)")
            lines.append("")
            lines.extend(self._format_violations(self.scan_result.llm_results, "LLM"))
            lines.append("")

        # Recommendations
        lines.append("## Recommendations")
        lines.append("")
        lines.append(self._generate_recommendations())
        lines.append("")

        return "\n".join(lines)

    def _count_by_severity(self, severity: int) -> int:
        """Count violations by severity level"""
        count = 0
        for violation in (
            self.scan_result.spectral_results + self.scan_result.llm_results
        ):
            if violation.get("severity") == severity:
                count += 1
        return count

    def _format_violations(self, violations: List[Dict], source: str) -> List[str]:
        """Format violations for markdown output"""
        lines = []

        # Group by severity
        errors = [v for v in violations if v.get("severity") == 0]
        warnings = [v for v in violations if v.get("severity") == 1]
        infos = [v for v in violations if v.get("severity") == 2]

        # Errors
        if errors:
            lines.append(f"### Critical Issues ({len(errors)})")
            lines.append("")
            for violation in errors:
                lines.extend(self._format_violation(violation))
            lines.append("")

        # Warnings
        if warnings:
            lines.append(f"### Warnings ({len(warnings)})")
            lines.append("")
            for violation in warnings:
                lines.extend(self._format_violation(violation))
            lines.append("")

        # Infos
        if infos:
            lines.append(f"### Information ({len(infos)})")
            lines.append("")
            for violation in infos:
                lines.extend(self._format_violation(violation))
            lines.append("")

        return lines

    def _format_violation(self, violation: Dict) -> List[str]:
        """Format a single violation"""
        lines = [ReportUtils.format_violation_markdown(violation)]

        # LLM-generated context (enhanced explanation)
        if violation.get("llm_context"):
            lines.append(f"  - **Why This Matters:** {violation.get('llm_context')}")

        lines.append("")

        return lines

    def _generate_recommendations(self) -> str:
        """Generate recommendations based on violations"""
        error_count = self._count_by_severity(0)
        warning_count = self._count_by_severity(1)

        if error_count == 0 and warning_count == 0:
            return "✅ No issues found! Your API follows all governance rules."

        lines = []

        if error_count > 0:
            lines.append(
                f"1. **Address Critical Issues:** You have {error_count} critical issue(s) that must be resolved to meet governance standards."
            )

        if warning_count > 0:
            lines.append(
                f"2. **Review Warnings:** {warning_count} warning(s) should be addressed to improve API quality and consistency."
            )

        lines.append(
            "3. **Validate Changes:** After making corrections, re-run this scan to verify compliance."
        )
        lines.append(
            "4. **Documentation:** Update your API documentation to reflect any changes made."
        )

        return "\n".join(lines)

    def generate_html(self, output_path: Path):
        """Generate a beautifully formatted HTML report from scan results"""
        output_path = Path(output_path)
        scan = self.scan_result

        # Build HTML
        html = [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            "    <title>API Governance Scan Report</title>",
            "    <style>",
            "        * { margin: 0; padding: 0; box-sizing: border-box; }",
            "        body {",
            '            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;',
            "            line-height: 1.6;",
            "            color: #333;",
            "            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);",
            "            min-height: 100vh;",
            "            padding: 20px;",
            "        }",
            "        .container {",
            "            max-width: 1200px;",
            "            margin: 0 auto;",
            "            background: white;",
            "            border-radius: 12px;",
            "            box-shadow: 0 10px 40px rgba(0,0,0,0.1);",
            "            overflow: hidden;",
            "        }",
            "        .header {",
            "            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);",
            "            color: white;",
            "            padding: 40px;",
            "            text-align: center;",
            "        }",
            "        .header h1 {",
            "            font-size: 2.5em;",
            "            margin-bottom: 10px;",
            "            text-shadow: 0 2px 4px rgba(0,0,0,0.1);",
            "        }",
            "        .header p {",
            "            font-size: 1em;",
            "            opacity: 0.9;",
            "        }",
            "        .score-card {",
            "            display: grid;",
            "            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));",
            "            gap: 20px;",
            "            padding: 40px;",
            "            background: #f8f9fa;",
            "            border-bottom: 1px solid #e9ecef;",
            "        }",
            "        .score-item {",
            "            background: white;",
            "            padding: 20px;",
            "            border-radius: 8px;",
            "            text-align: center;",
            "            box-shadow: 0 2px 8px rgba(0,0,0,0.05);",
            "        }",
            "        .score-item-label {",
            "            font-size: 0.85em;",
            "            color: #666;",
            "            text-transform: uppercase;",
            "            letter-spacing: 1px;",
            "            margin-bottom: 8px;",
            "        }",
            "        .score-item-value {",
            "            font-size: 2em;",
            "            font-weight: bold;",
            "            color: #333;",
            "        }",
            "        .content {",
            "            padding: 40px;",
            "        }",
            "        .section {",
            "            margin-bottom: 40px;",
            "        }",
            "        .section h2 {",
            "            font-size: 1.8em;",
            "            color: #667eea;",
            "            margin-bottom: 20px;",
            "            padding-bottom: 10px;",
            "            border-bottom: 3px solid #667eea;",
            "        }",
            "        .section h3 {",
            "            font-size: 1.3em;",
            "            color: #555;",
            "            margin-top: 25px;",
            "            margin-bottom: 15px;",
            "        }",
            "        .spec-files-list {",
            "            display: grid;",
            "            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));",
            "            gap: 15px;",
            "        }",
            "        .spec-file-item {",
            "            background: #f8f9fa;",
            "            padding: 15px;",
            "            border-radius: 6px;",
            "            border-left: 4px solid #667eea;",
            "            font-family: monospace;",
            "            word-break: break-all;",
            "        }",
            "        .violations-container {",
            "            display: grid;",
            "            grid-template-columns: 1fr;",
            "            gap: 20px;",
            "        }",
            "        .violations-section {",
            "            margin-bottom: 30px;",
            "        }",
            "        .violations-section h3 {",
            "            display: flex;",
            "            align-items: center;",
            "            gap: 10px;",
            "            margin-bottom: 15px;",
            "        }",
            "        .violations-list {",
            "            display: grid;",
            "            grid-template-columns: 1fr;",
            "            gap: 12px;",
            "        }",
            "        .violation-card {",
            "            background: white;",
            "            border: 1px solid #e9ecef;",
            "            border-left: 5px solid #666;",
            "            padding: 20px;",
            "            border-radius: 6px;",
            "            transition: all 0.3s ease;",
            "        }",
            "        .violation-card:hover {",
            "            box-shadow: 0 5px 15px rgba(0,0,0,0.1);",
            "            transform: translateY(-2px);",
            "        }",
            "        .violation-card.error {",
            "            border-left-color: #dc3545;",
            "            background: #fff8f8;",
            "        }",
            "        .violation-card.warning {",
            "            border-left-color: #ffc107;",
            "            background: #fffef8;",
            "        }",
            "        .violation-card.info {",
            "            border-left-color: #17a2b8;",
            "            background: #f8fdfe;",
            "        }",
            "        .violation-header {",
            "            display: flex;",
            "            align-items: center;",
            "            gap: 12px;",
            "            margin-bottom: 12px;",
            "            font-weight: bold;",
            "            font-size: 1.05em;",
            "        }",
            "        .violation-content {",
            "            display: grid;",
            "            grid-template-columns: 1fr;",
            "            gap: 10px;",
            "            font-size: 0.95em;",
            "            color: #555;",
            "        }",
            "        .violation-field {",
            "            display: grid;",
            "            grid-template-columns: 120px 1fr;",
            "            gap: 15px;",
            "        }",
            "        .violation-label {",
            "            font-weight: 600;",
            "            color: #666;",
            "            font-size: 0.9em;",
            "            text-transform: uppercase;",
            "            letter-spacing: 0.5px;",
            "        }",
            "        .violation-value {",
            "            color: #333;",
            "            word-break: break-word;",
            "        }",
            "        .violation-value code {",
            "            background: #f0f0f0;",
            "            padding: 2px 6px;",
            "            border-radius: 3px;",
            "            font-family: monospace;",
            "            font-size: 0.9em;",
            "        }",
            "        .violation-context {",
            "            background: #f0f7ff;",
            "            border-left: 3px solid #667eea;",
            "            padding: 12px;",
            "            border-radius: 4px;",
            "            margin-top: 8px;",
            "            font-style: italic;",
            "            color: #555;",
            "            line-height: 1.5;",
            "        }",
            "        .violation-context strong {",
            "            color: #667eea;",
            "            font-weight: 600;",
            "        }",
            "        .recommendations {",
            "            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);",
            "            color: white;",
            "            padding: 30px;",
            "            border-radius: 8px;",
            "            margin-top: 20px;",
            "        }",
            "        .recommendations h2 {",
            "            color: white;",
            "            border-color: rgba(255,255,255,0.3);",
            "        }",
            "        .recommendations p {",
            "            line-height: 1.8;",
            "            opacity: 0.95;",
            "        }",
            "        .footer {",
            "            background: #f8f9fa;",
            "            padding: 20px;",
            "            text-align: center;",
            "            font-size: 0.85em;",
            "            color: #666;",
            "            border-top: 1px solid #e9ecef;",
            "        }",
            "        @media (max-width: 768px) {",
            "            .header h1 { font-size: 1.8em; }",
            "            .violation-field { grid-template-columns: 1fr; }",
            "        }",
            "    </style>",
            "</head>",
            "<body>",
            '    <div class="container">',
            '        <div class="header">',
            "            <h1>🏛️ API Governance Scan Report</h1>",
            f'            <p>Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")}</p>',
            "        </div>",
            "",
            '        <div class="score-card">',
            f'            <div class="score-item"><div class="score-item-label">📊 Total Violations</div><div class="score-item-value">{scan.total_violations}</div></div>',
            f'            <div class="score-item"><div class="score-item-label">🔴 Critical</div><div class="score-item-value" style="color: #dc3545;">{self._count_by_severity(0)}</div></div>',
            f'            <div class="score-item"><div class="score-item-label">🟡 Warnings</div><div class="score-item-value" style="color: #ffc107;">{self._count_by_severity(1)}</div></div>',
            f'            <div class="score-item"><div class="score-item-label">ℹ️ Info</div><div class="score-item-value" style="color: #17a2b8;">{self._count_by_severity(2)}</div></div>',
            "        </div>",
            "",
        ]

        # Main Content
        html.extend(
            [
                '        <div class="content">',
                "            <!-- Project Info Section -->",
                '            <div class="section">',
                "                <h2>📋 Scan Summary</h2>",
                f"                <p><strong>Scan Type:</strong> {scan.scan_type}</p>",
                f"                <p><strong>Project Path:</strong> <code>{scan.project_path}</code></p>",
                f"                <p><strong>Specifications Analyzed:</strong> {len(scan.spec_files)}</p>",
                "            </div>",
                "",
            ]
        )

        # Spec Files Section
        if scan.spec_files:
            html.extend(
                [
                    '            <div class="section">',
                    "                <h2>📁 Specification Files</h2>",
                    '                <div class="spec-files-list">',
                ]
            )
            for spec_file in scan.spec_files:
                html.append(
                    f'                    <div class="spec-file-item">📄 {spec_file}</div>'
                )
            html.extend(["                </div>", "            </div>", ""])

        # Automated Rules Results
        if scan.spectral_results:
            html.extend(
                [
                    '            <div class="section">',
                    "                <h2>🔍 Automated Rules Results</h2>",
                    '                <div class="violations-container">',
                ]
            )
            html.extend(self._format_html_violations_pretty(scan.spectral_results))
            html.extend(["                </div>", "            </div>", ""])

        # LLM Results
        if scan.llm_results:
            html.extend(
                [
                    '            <div class="section">',
                    "                <h2>🧠 Semantic Analysis Results (LLM)</h2>",
                    '                <div class="violations-container">',
                ]
            )
            html.extend(self._format_html_violations_pretty(scan.llm_results))
            html.extend(["                </div>", "            </div>", ""])

        # Recommendations Section
        html.extend(
            [
                '            <div class="section">',
                '                <div class="recommendations">',
                "                    <h2>✅ Recommendations</h2>",
                f'                    {self._generate_recommendations().replace(chr(10), "<br>")}',
                "                </div>",
                "            </div>",
                "        </div>",
                "",
            ]
        )

        # Footer
        html.extend(
            [
                '        <div class="footer">',
                "            <p>API Governance Scan Report • All violations have been analyzed for compliance with governance standards</p>",
                "        </div>",
                "    </div>",
                "</body>",
                "</html>",
            ]
        )

        output_path.write_text("\n".join(html))

    def _format_html_violations(self, violations: List[Dict], source: str) -> List[str]:
        html = []
        errors = [v for v in violations if v.get("severity") == 0]
        warnings = [v for v in violations if v.get("severity") == 1]
        infos = [v for v in violations if v.get("severity") == 2]
        if errors:
            html.append(
                f'<h3 style="color:red">Critical Issues ({len(errors)})</h3><ul>'
            )
            for v in errors:
                html.append(self._format_html_violation(v))
            html.append("</ul>")
        if warnings:
            html.append(f'<h3 style="color:orange">Warnings ({len(warnings)})</h3><ul>')
            for v in warnings:
                html.append(self._format_html_violation(v))
            html.append("</ul>")
        if infos:
            html.append(f'<h3 style="color:blue">Information ({len(infos)})</h3><ul>')
            for v in infos:
                html.append(self._format_html_violation(v))
            html.append("</ul>")
        return html

    def _format_html_violation(self, violation: Dict) -> str:
        severity_icon = {0: "🔴", 1: "🟡", 2: "🔵"}
        severity_label = {0: "Error", 1: "Warning", 2: "Info"}
        severity = violation.get("severity", 2)
        icon = severity_icon.get(severity, "•")
        label = severity_label.get(severity, "Unknown")
        html = f'<li><strong>{icon} {label}: {violation.get("rule", "Unknown Rule")}</strong>'
        html += f'<br><em>{violation.get("message", "N/A")}</em>'
        if violation.get("path"):
            html += f'<br><span>Path: <code>{violation.get("path")}</code></span>'
        if violation.get("line"):
            html += f'<br><span>Line: {violation.get("line")}</span>'
        # LLM-generated context (enhanced explanation)
        if violation.get("llm_context"):
            html += f'<br><span style="color:#666;font-style:italic"><strong>Why This Matters:</strong> {violation.get("llm_context")}</span>'
        if violation.get("suggestion"):
            html += f'<br><span>Suggestion: {violation.get("suggestion")}</span>'
        html += "</li>"
        return html

    def _format_html_violations_pretty(self, violations: List[Dict]) -> List[str]:
        """Format violations for prettier HTML display with severity grouping"""
        html = []

        # Group by severity
        errors = [v for v in violations if v.get("severity") == 0]
        warnings = [v for v in violations if v.get("severity") == 1]
        infos = [v for v in violations if v.get("severity") == 2]

        # Render errors
        if errors:
            html.extend(
                [
                    '                    <div class="violations-section">',
                    f"                        <h3>🔴 Critical Issues ({len(errors)})</h3>",
                    '                        <div class="violations-list">',
                ]
            )
            for violation in errors:
                html.extend(self._format_violation_card_html(violation, "error"))
            html.extend(
                [
                    "                        </div>",
                    "                    </div>",
                ]
            )

        # Render warnings
        if warnings:
            html.extend(
                [
                    '                    <div class="violations-section">',
                    f"                        <h3>🟡 Warnings ({len(warnings)})</h3>",
                    '                        <div class="violations-list">',
                ]
            )
            for violation in warnings:
                html.extend(self._format_violation_card_html(violation, "warning"))
            html.extend(
                [
                    "                        </div>",
                    "                    </div>",
                ]
            )

        # Render infos
        if infos:
            html.extend(
                [
                    '                    <div class="violations-section">',
                    f"                        <h3>ℹ️ Information ({len(infos)})</h3>",
                    '                        <div class="violations-list">',
                ]
            )
            for violation in infos:
                html.extend(self._format_violation_card_html(violation, "info"))
            html.extend(
                [
                    "                        </div>",
                    "                    </div>",
                ]
            )

        return html

    def _format_violation_card_html(
        self, violation: Dict, severity_class: str
    ) -> List[str]:
        """Format a single violation as an HTML card"""
        severity_icon = {0: "🔴", 1: "🟡", 2: "🔵"}
        severity = violation.get("severity", 2)
        icon = severity_icon.get(severity, "•")
        rule = violation.get("rule", "Unknown Rule")
        message = violation.get("message", "N/A")

        html = [
            f'                            <div class="violation-card {severity_class}">',
            '                                <div class="violation-header">',
            f"                                    <span>{icon}</span>",
            f"                                    <span>{rule}</span>",
            "                                </div>",
            '                                <div class="violation-content">',
            '                                    <div class="violation-field">',
            '                                        <div class="violation-label">Message</div>',
            f'                                        <div class="violation-value">{message}</div>',
            "                                    </div>",
        ]

        # Path
        if violation.get("path"):
            html.extend(
                [
                    '                                    <div class="violation-field">',
                    '                                        <div class="violation-label">Path</div>',
                    f'                                        <div class="violation-value"><code>{violation.get("path")}</code></div>',
                    "                                    </div>",
                ]
            )

        # Line
        if violation.get("line"):
            html.extend(
                [
                    '                                    <div class="violation-field">',
                    '                                        <div class="violation-label">Line</div>',
                    f'                                        <div class="violation-value">{violation.get("line")}</div>',
                    "                                    </div>",
                ]
            )

        html.append("                                </div>")

        # LLM Context (enhanced explanation)
        if violation.get("llm_context"):
            html.extend(
                [
                    '                                <div class="violation-context">',
                    f'                                    <strong>Why This Matters:</strong> {violation.get("llm_context")}',
                    "                                </div>",
                ]
            )

        # Suggestion
        if violation.get("suggestion"):
            html.extend(
                [
                    '                                <div class="violation-context" style="background: #f0fff0; border-left-color: #28a745; margin-top: 12px;">',
                    f'                                    <strong style="color: #28a745;">💡 Suggestion:</strong> {violation.get("suggestion")}',
                    "                                </div>",
                ]
            )

        html.append("                            </div>")

        return html
