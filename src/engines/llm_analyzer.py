import os
from pathlib import Path
from typing import Optional, List, Dict
import asyncio
import aiohttp
import json
from utils.logger import logger


class LLMAnalyzer:
    """Performs semantic analysis using LLM via Ollama"""

    def __init__(self, api_endpoint: str, api_key: Optional[str] = None):
        self.api_endpoint = api_endpoint
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL", "mistral")

    async def analyze_spec(self, spec_path: Path, spec_content: Dict) -> List[Dict]:
        """Perform semantic analysis on OpenAPI spec"""
        violations = []

        # Analyze paths for semantic issues
        if "paths" in spec_content:
            violations.extend(await self._analyze_paths(spec_content["paths"]))

        # Analyze schemas for leaky abstractions
        if "components" in spec_content and "schemas" in spec_content["components"]:
            violations.extend(
                await self._analyze_schemas(spec_content["components"]["schemas"])
            )

        return violations

    async def _analyze_paths(self, paths: Dict) -> List[Dict]:
        """Analyze API paths for semantic issues"""
        violations = []

        for path, operations in paths.items():
            # Check for verbs in path
            path_segments = [s for s in path.split("/") if s and not s.startswith("{")]

            for segment in path_segments:
                if segment.startswith("v") and segment[1:].isdigit():
                    continue  # Skip version segments

                # Use LLM to detect verbs
                is_verb = await self._is_verb_segment(segment)
                if is_verb:
                    suggestion = await self._suggest_reified_resource(segment)
                    violations.append(
                        {
                            "rule": "semantic-verb-in-path",
                            "severity": 1,  # warning
                            "message": f"Path segment '{segment}' appears to be a verb. Consider reified resource: {suggestion}",
                            "path": path,
                            "line": 0,
                            "source": segment,
                            "engine": "llm",
                            "suggestion": suggestion,
                        }
                    )

            # Analyze operation descriptions
            for method, operation in operations.items():
                if isinstance(operation, dict):
                    if "description" in operation:
                        quality_issues = await self._check_description_quality(
                            operation["description"]
                        )
                        violations.extend(quality_issues)

                # Check for design anomalies
                design_issues = await self._analyze_design_anomalies(path, method)
                violations.extend(design_issues)

        return violations

    async def _analyze_design_anomalies(self, path: str, method: str) -> List[Dict]:
        """Detect broader API design anomalies (granularity, separation of concerns)"""
        violations = []
        path_lower = path.lower()

        # Check for inconsistent granularity (e.g., getUser vs searchUsers where path implies specific access)
        # Detailed logic would require comparing across all paths, here we check specific patterns

        # 1. RPC-style naming in REST paths
        rpc_patterns = [
            "get",
            "search",
            "find",
            "update",
            "delete",
            "create",
            "do",
            "run",
            "execute",
            "process",
        ]
        segments = path_lower.strip("/").split("/")
        for segment in segments:
            # Check for matches, handling separators
            sub_segments = segment.replace("_", " ").replace("-", " ").split()
            if any(s in rpc_patterns for s in sub_segments):
                violations.append(
                    {
                        "rule": "design-rpc-in-rest",
                        "severity": 1,
                        "message": f"Path segment '{segment}' suggests RPC-style 'function call' naming rather than Resource-oriented design.",
                        "path": path,
                        "line": 0,
                        "source": segment,
                        "engine": "llm",  # Heuristic but semantically relevant
                        "suggestion": "Use HTTP methods (GET/POST) on nouns (Resources) instead.",
                    }
                )

        return violations

    async def _analyze_schemas(self, schemas: Dict) -> List[Dict]:
        """Analyze schemas for leaky abstractions"""
        violations = []

        for schema_name, schema in schemas.items():
            if "properties" in schema:
                for prop_name, prop_schema in schema["properties"].items():
                    # Check for 3rd party/legacy terms
                    leaky_terms = [
                        "oracle",
                        "sap",
                        "legacy",
                        "db",
                        "table",
                        "column",
                        "sql",
                    ]
                    if any(term in prop_name.lower() for term in leaky_terms):
                        violations.append(
                            {
                                "rule": "semantic-leaky-abstraction",
                                "severity": 1,  # warning
                                "message": f"Property '{prop_name}' may expose internal implementation details. Consider using domain-specific naming.",
                                "path": f"components.schemas.{schema_name}.properties.{prop_name}",
                                "line": 0,
                                "source": prop_name,
                                "engine": "llm",
                                "suggestion": await self._suggest_domain_name(
                                    prop_name
                                ),
                            }
                        )

        return violations

    async def _is_verb_segment(self, segment: str) -> bool:
        """Use LLM to determine if segment is a verb"""
        # Common verbs for quick detection
        common_verbs = [
            "create",
            "update",
            "delete",
            "get",
            "post",
            "put",
            "patch",
            "activate",
            "deactivate",
            "enable",
            "disable",
            "register",
            "unregister",
            "calculate",
            "process",
            "validate",
            "verify",
            "submit",
            "approve",
            "reject",
            "cancel",
            "execute",
            "run",
        ]
        if segment.lower() in common_verbs:
            return True
        # For complex cases, use LLM with improved prompt
        try:
            prompt = (
                f"Is '{segment}' a verb or action in the context of an API path? "
                f"If yes, suggest a RESTful resource name and show a code snippet for the corrected OpenAPI path. "
                f"Respond with 'yes' or 'no', and if 'yes', provide a markdown code block and explanation."
            )
            response = await self._call_llm(prompt)
            return response.lower().strip().startswith("yes")
        except Exception as e:
            logger.debug(f"LLM verb detection failed: {str(e)}, using heuristic")
            # Fallback heuristic
            if segment.endswith("ing") or segment.endswith("ed"):
                return True
            return False

    async def _call_llm_is_verb(self, segment: str) -> bool:
        """Call LLM API to determine if segment is a verb"""
        prompt = f"""Is '{segment}' a verb or action? Answer with only 'yes' or 'no'."""

        try:
            response = await self._call_llm(prompt)
            return response.lower().strip().startswith("yes")
        except Exception as e:
            logger.debug(f"LLM API call failed: {str(e)}")
            return False

    async def _call_llm(self, prompt: str, timeout: int = 15) -> str:
        """Make an async call to the LLM endpoint with reduced timeout"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_endpoint}/api/generate"
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,
                    "options": {
                        "num_predict": 200,  # Limit response length
                        "top_k": 10,
                        "top_p": 0.9,
                    },
                }

                timeout_config = aiohttp.ClientTimeout(total=timeout)
                async with session.post(
                    url, json=payload, timeout=timeout_config
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "").strip()
                    else:
                        logger.warning(f"LLM API returned status {response.status}")
                        return ""
        except asyncio.TimeoutError:
            logger.warning(
                f"LLM API call timed out after {timeout}s - falling back to heuristics"
            )
            return ""
        except Exception as e:
            logger.warning(
                f"LLM API call failed: {str(e)} - falling back to heuristics"
            )
            return ""

    async def _suggest_reified_resource(self, verb: str) -> str:
        """Suggest a reified resource name"""
        # Use LLM to suggest resource name and code snippet
        prompt = (
            f"Suggest a RESTful resource name to replace the verb '{verb}' in an API path. "
            f"Provide a code snippet showing the corrected OpenAPI path and operation, and a brief explanation. "
            f"Respond in markdown with a code block and explanation."
        )
        try:
            response = await self._call_llm(prompt)
            return response
        except Exception as e:
            logger.debug(f"LLM resource suggestion failed: {str(e)}")
            # Fallback to simple transformation
            transformations = {
                "activate": "activations",
                "register": "registrations",
                "calculate": "calculations",
                "process": "processing-requests",
                "validate": "validations",
                "submit": "submissions",
                "approve": "approvals",
                "cancel": "cancellations",
            }
            return transformations.get(verb.lower(), f"{verb}-requests")

    async def _suggest_domain_name(self, technical_name: str) -> str:
        """Suggest domain-appropriate name"""
        # Placeholder - in production, use LLM for better suggestions
        clean_name = (
            technical_name.lower()
            .replace("oracle", "")
            .replace("sap", "")
            .replace("legacy", "")
        )
        return clean_name or "domainSpecificName"

    async def _check_description_quality(self, description: str) -> List[Dict]:
        """Check if description is meaningful"""
        violations = []

        if len(description) < 10:
            violations.append(
                {
                    "rule": "semantic-poor-description",
                    "severity": 2,  # info
                    "message": "Description is too brief. Consider providing more detail about the operation's purpose and usage.",
                    "path": "description",
                    "line": 0,
                    "source": description,
                    "engine": "llm",
                }
            )

        return violations

    async def enhance_arch_violations(self, violations: List[Dict]) -> List[Dict]:
        """Enhance ArchUnit violations with LLM-generated context and anti-pattern detection"""
        enhanced = []
        for violation in violations:
            try:
                # Copy severity before it might be lost or modified (though python dicts are by ref)
                # Ensure severity is preserved
                severity = violation.get("severity")

                # Generate contextual description
                context_prompt = (
                    f"Explain why this Java architectural violation is a bad practice and suggest a fix:\n"
                    f"Rule: {violation.get('rule', 'Unknown')}\n"
                    f"Message: {violation.get('message', '')}\n"
                    f"Context: ArchUnit test failure.\n\n"
                    f"Include specific refactoring steps (e.g. 'Extract interface', 'Use Dependency Injection')."
                )
                context = await self._call_llm(context_prompt, timeout=25)

                if context:
                    violation["llm_context"] = context
                    violation["enhanced"] = True
                else:
                    violation["enhanced"] = False

                # Explicitly re-set severity if it was somehow lost (defensive)
                if severity is not None:
                    violation["severity"] = int(severity)

            except Exception as e:
                logger.debug(
                    f"LLM enhancement failed for {violation.get('rule')}: {str(e)}"
                )
                violation["enhanced"] = False

            enhanced.append(violation)
        return enhanced

    async def generate_fix(self, file_content: str, violation: Dict) -> str:
        """
        Generate a code fix for a specific violation using the LLM.

        Args:
            file_content: The full content of the file.
            violation: The violation dictionary containing rule and message.

        Returns:
            The fixed file content.
        """
        rule_id = violation.get("rule") or violation.get("rule_id", "unknown")
        message = violation.get("message", "")

        prompt = (
            f"You are an expert Java and API developer. You have been tasked with fixing a code violation.\n"
            f"Here is the file content:\n"
            f"```java\n{file_content}\n```\n\n"
            f"The violation is:\n"
            f"Rule: {rule_id}\n"
            f"Message: {message}\n\n"
            f"Instructions:\n"
            f"1. Specifically fix the violation described above in the provided file.\n"
            f"2. IMPORTANT: Return the COMPLETE fixed file content.\n"
            f"3. Do NOT add markdown formatting (like ```java) in the response, just the raw code.\n"
            f"4. Maintain all other code, imports, and style exactly as is.\n"
            f"5. If you cannot fix it, return the original content exactly.\n"
            f"6. Fix logic: If the rule involves 'paths', 'verbs', or REST conventions, apply standard best practices.\n"
            f"7. Ensure the code is syntactically correct and compiles.\n"
        )

        try:
            # Increase timeout for code generation
            response = await self._call_llm(prompt, timeout=60)

            # Strip potential markdown blocks if the LLM ignores instruction #3
            if response.startswith("```"):
                lines = response.splitlines()
                # Remove first line (```language)
                if lines[0].startswith("```"):
                    lines = lines[1:]
                # Remove last line (```)
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                response = "\n".join(lines)

            return response if response.strip() else file_content

        except Exception as e:
            logger.error(f"LLM fix generation failed: {e}")
            return file_content

    async def generate_batch_fix(
        self, file_content: str, violations: List[Dict]
    ) -> str:
        """
        Generate a single fix for multiple violations in one file.
        """
        violations_text = ""
        categories = set()
        for i, v in enumerate(violations):
            rule_id = v.get("rule") or v.get("rule_id", "unknown")
            category = v.get("engine", "unknown")
            categories.add(category)
            message = v.get("message", "")
            violations_text += f"Violation {i+1} [{category}]:\nRule: {rule_id}\nMessage: {message}\n\n"

        prompt = (
            f"You are an expert developer specializing in {', '.join(categories)} governance.\n"
            f"You need to fix MULTIPLE code violations in the following file.\n"
            f"Here is the file content:\n"
            f"```\n{file_content}\n```\n\n"
            f"VIOLATIONS:\n"
            f"{violations_text}"
            f"INSTRUCTIONS:\n"
            f"1. Fix ALL the violations listed above while maintaining code integrity.\n"
            f"2. Return ONLY the COMPLETE fixed file content.\n"
            f"3. Do NOT add markdown blocks (like ```java) or explanations, just raw code.\n"
            f"4. Focus on fixing paths, naming, and architectural rules as described in the violations.\n"
        )

        try:
            response = await self._call_llm(prompt, timeout=90)

            # Strip markdown blocks
            if response.startswith("```"):
                lines = response.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                response = "\n".join(lines)

            return response if response.strip() else file_content
        except Exception as e:
            logger.error(f"LLM batch fix generation failed: {e}")
            return file_content

    async def generate_cross_file_fix(
        self, files: Dict[str, str], violation: Dict
    ) -> Dict[str, str]:
        """
        Generate fixes for multiple related files.

        Args:
            files: Dictionary of file_path -> file_content
            violation: The violation dictionary.

        Returns:
            Dictionary of file_path -> fixed_content
        """
        rule_id = violation.get("rule") or violation.get("rule_id", "unknown")
        message = violation.get("message", "")

        files_context = ""
        for path, content in files.items():
            ext = Path(path).suffix.lstrip(".")
            files_context += f"File: {path}\n```{ext}\n{content}\n```\n\n"

        prompt = (
            f"You are an expert developer specializing in API governance and clean architecture.\n"
            f"A governance violation was found that might require changes across multiple files.\n\n"
            f"VIOLATION:\n"
            f"Rule: {rule_id}\n"
            f"Message: {message}\n\n"
            f"FILES TO ANALYZE:\n"
            f"{files_context}"
            f"INSTRUCTIONS:\n"
            f"1. Repair the violation while maintaining consistency across all provided files.\n"
            f"2. For example, if an OpenAPI path is renamed, the corresponding Java controller must also be updated.\n"
            f"3. Return the COMPLETE content of EACH file that needs changes.\n"
            f"4. Format the response as a JSON object where keys are the file paths and values are the new contents.\n"
            f'   Example: {{"path/to/file1": "new content", "path/to/file2": "new content"}}\n'
            f"5. Do NOT include markdown blocks around the JSON.\n"
            f"6. If a file does not need changes, you don't have to include it in the JSON.\n"
            f"7. If you cannot fix the violation, return an empty JSON object {{}}.\n"
        )

        try:
            response = await self._call_llm(prompt, timeout=90)

            # Basic cleanup of JSON response
            if "{" in response and "}" in response:
                json_part = response[response.find("{") : response.rfind("}") + 1]
                fixed_files = json.loads(json_part)

                # Verify keys match provided files
                result = {}
                for path, content in fixed_files.items():
                    # Account for various ways LLM might return paths (abs vs rel)
                    matched_path = None
                    for orig_path in files.keys():
                        if orig_path.endswith(path) or path.endswith(orig_path):
                            matched_path = orig_path
                            break

                    if matched_path:
                        result[matched_path] = content
                    else:
                        result[path] = (
                            content  # Trust the LLM if it's a new file or path we didn't expect
                        )

                return result

            return {}

        except Exception as e:
            logger.error(f"LLM cross-file fix generation failed: {e}")
            return {}
