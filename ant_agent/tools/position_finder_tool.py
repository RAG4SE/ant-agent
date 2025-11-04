# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Position finder tool for accurate LSP positioning."""

from __future__ import annotations

import re
import ast
from typing import Any, Dict, List, Optional, Type
from pathlib import Path

from ant_agent.tools.base import AntTool, AntToolResult
from pydantic import BaseModel, Field


class PositionFinderInput(BaseModel):
    """Simplified input schema for position finder tool."""
    file_path: str = Field(description="Path to the source file")
    line_number: int = Field(description="0-based line number where to search")
    line_content: str = Field(description="The content of the line to search in")
    target: str = Field(description="The target string to find in the line")


class PositionFinderResult(BaseModel):
    """Result schema for position finder."""
    success: bool
    positions: List[Dict[str, Any]] = Field(default_factory=list)
    best_match: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    alternative_suggestions: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    lsp_coordinates: Optional[Dict[str, Any]] = None  # LSP-ready coordinates


class PositionFinderTool(AntTool):
    """Intelligent position finder for LSP tools.

    This tool helps accurately locate functions, classes, variables, and other identifiers
    in source code, providing precise coordinates for LSP tools like multilspy_python_definition.

    When to use:
    - Before calling multilspy_python_definition to get accurate coordinates
    - When you need to find the exact position of a function/class/variable
    - When multilspy tools are failing due to incorrect position data
    - To validate that a target exists before attempting LSP operations

    After using this tool:
    - If success and confidence > 0.8, use the lsp_coordinates with multilspy tools
    - If success but confidence < 0.8, consider using bash+grep as fallback
    - If failed, use bash tools to explore the file structure instead
    """

    name: str = "position_finder"
    description: str = """Find the exact position of a target string in a specific line of code for LSP tools.

    This simplified tool takes a specific line of code and finds the position of a target string within it.
    Use it BEFORE calling multilspy_python_definition to get precise coordinates.

    Key features:
    - Simple and precise: specify exact line and target
    - LSP-compatible coordinate format (0-indexed line and character)
    - Working directory support for relative path resolution
    - High confidence exact matching

    Best practices:
    1. Use this tool when you know the exact line containing the target
    2. Provide the full line content for accurate matching
    3. Use 0-based line numbers as per LSP specification
    4. The tool returns the first occurrence of the target in the line"""

    args_schema: Type[BaseModel] = PositionFinderInput
    working_dir: str

    def __init__(self, working_dir: str, **kwargs):
        """Initialize PositionFinderTool with working directory.

        Args:
            working_dir: Working directory for resolving relative paths.
            **kwargs: Additional keyword arguments for parent class.
        """
        # Set working_dir before calling super().__init__ to pass Pydantic validation
        kwargs['working_dir'] = working_dir
        super().__init__(**kwargs)
        self.working_dir = working_dir

    def _get_absolute_path(self, file_path: str) -> str:
        """Get absolute path for file, resolving relative paths against working directory."""
        path = Path(file_path)
        if path.is_absolute():
            return str(path)
        else:
            return str(Path(self.working_dir) / path)

    def _run(self, file_path: str, line_number: int, line_content: str, target: str) -> AntToolResult:
        """Find the position of a target in the specified line of code.

        Args:
            file_path: Path to the source file
            line_number: 0-based line number where to search
            line_content: The content of the line to search in
            target: The target string to find in the line

        Returns:
            LSP-compatible coordinates with the target position
        """
        try:
            # Resolve file path against working directory
            absolute_path = self._get_absolute_path(file_path)
            path = Path(absolute_path)

            # 验证文件存在（可选，因为我们要找的是指定行的内容）
            if not path.exists():
                return AntToolResult(
                    success=False,
                    error=f"File not found: {file_path} (resolved to: {absolute_path})",
                    metadata={"suggestion": "Check if the file path is correct"}
                )

            if not path.is_file():
                return AntToolResult(
                    success=False,
                    error=f"Path is not a file: {file_path} (resolved to: {absolute_path})",
                    metadata={"suggestion": "Use bash to explore directories"}
                )

            # 在指定的行内容中查找目标
            char_idx = line_content.find(target)

            if char_idx == -1:
                return AntToolResult(
                    success=False,
                    error=f"Target '{target}' not found in line {line_number}: {line_content}",
                    metadata={"suggestion": "Check if the target string is correct or try a different line"}
                )

            # 返回LSP兼容的坐标
            lsp_coordinates = {
                "file_path": absolute_path,
                "line": line_number,  # 0-based
                "character": char_idx  # 0-based
            }

            result_data = PositionFinderResult(
                success=True,
                positions=[{
                    "line_0_indexed": line_number,
                    "line_1_indexed": line_number + 1,
                    "character_0_indexed": char_idx,
                    "line_content": line_content.strip(),
                    "match_type": "exact",
                    "context": line_content.strip()
                }],
                best_match={
                    "line_0_indexed": line_number,
                    "line_1_indexed": line_number + 1,
                    "character_0_indexed": char_idx,
                    "line_content": line_content.strip(),
                    "match_type": "exact",
                    "context": line_content.strip()
                },
                confidence=1.0,  # 精确匹配，置信度为1.0
                lsp_coordinates=lsp_coordinates,
                alternative_suggestions=[]
            )

            output = f"Found '{target}' at line {line_number} (0-based): {line_content}, character {char_idx} (0-based)"
            output += f"\nLSP coordinates: {lsp_coordinates}"

            return AntToolResult(
                success=True,
                output=output,
                metadata=result_data.dict()
            )

        except Exception as e:
            return AntToolResult(
                success=False,
                error=f"Position finder error: {str(e)}",
                metadata={"suggestion": "Check input parameters"}
            )

    def _find_positions(self, content: str, target: str, search_mode: str, target_type: str, context_line: Optional[int]) -> List[Dict[str, Any]]:
        """Find all positions of the target in content."""
        positions = []
        lines = content.split('\n')

        # Try different search strategies based on mode and target type
        if search_mode == "exact":
            positions = self._exact_search(lines, target, target_type)
        elif search_mode == "fuzzy":
            positions = self._fuzzy_search(lines, target, target_type)
        elif search_mode == "definition":
            positions = self._definition_search(lines, target, target_type)
        elif search_mode == "reference":
            positions = self._reference_search(lines, target, target_type)
        else:
            # Default to exact search
            positions = self._exact_search(lines, target, target_type)

        # If context line is provided, prioritize positions near that line
        if context_line and positions:
            positions = self._prioritize_by_context(positions, context_line)

        return positions

    def _exact_search(self, lines: List[str], target: str, target_type: str) -> List[Dict[str, Any]]:
        """Exact string matching search."""
        positions = []
        for line_idx, line in enumerate(lines):
            # Skip comments and strings for function/class definitions
            if target_type in ["function", "class", "any"]:
                stripped_line = line.strip()
                if stripped_line.startswith('#') or stripped_line.startswith('"""'):
                    continue

            # Find all occurrences of target in this line
            char_idx = line.find(target)
            while char_idx != -1:
                # Validate this is a valid occurrence (not part of another word)
                if self._is_valid_occurrence(line, char_idx, len(target)):
                    positions.append({
                        "line_0_indexed": line_idx,
                        "line_1_indexed": line_idx + 1,
                        "character_0_indexed": char_idx,
                        "line_content": line.strip(),
                        "match_type": "exact",
                        "context": self._get_context(lines, line_idx)
                    })
                char_idx = line.find(target, char_idx + 1)
        return positions

    def _fuzzy_search(self, lines: List[str], target: str, target_type: str) -> List[Dict[str, Any]]:
        """Fuzzy matching for similar names."""
        positions = []
        target_lower = target.lower()

        for line_idx, line in enumerate(lines):
            line_lower = line.lower()
            # Simple fuzzy matching - contains target as substring
            char_idx = line_lower.find(target_lower)
            while char_idx != -1:
                positions.append({
                    "line_0_indexed": line_idx,
                    "line_1_indexed": line_idx + 1,
                    "character_0_indexed": char_idx,
                    "line_content": line.strip(),
                    "match_type": "fuzzy",
                    "context": self._get_context(lines, line_idx)
                })
                char_idx = line_lower.find(target_lower, char_idx + 1)
        return positions

    def _definition_search(self, lines: List[str], target: str, target_type: str) -> List[Dict[str, Any]]:
        """Search for definitions (functions, classes, etc.)."""
        positions = []

        for line_idx, line in enumerate(lines):
            stripped_line = line.strip()

            # Look for function definitions
            if target_type in ["function", "any"]:
                if f"def {target}(" in stripped_line or f"def {target} (" in stripped_line:
                    char_idx = line.find(f"def {target}")
                    if char_idx != -1:
                        positions.append({
                            "line_0_indexed": line_idx,
                            "line_1_indexed": line_idx + 1,
                            "character_0_indexed": char_idx,
                            "line_content": line.strip(),
                            "match_type": "function_definition",
                            "context": self._get_context(lines, line_idx)
                        })

            # Look for class definitions
            if target_type in ["class", "any"]:
                if f"class {target}(" in stripped_line or f"class {target}:" in stripped_line:
                    char_idx = line.find(f"class {target}")
                    if char_idx != -1:
                        positions.append({
                            "line_0_indexed": line_idx,
                            "line_1_indexed": line_idx + 1,
                            "character_0_indexed": char_idx,
                            "line_content": line.strip(),
                            "match_type": "class_definition",
                            "context": self._get_context(lines, line_idx)
                        })

            # Look for variable assignments
            if target_type in ["variable", "any"]:
                if f"{target} =" in stripped_line or f"{target}:" in stripped_line:
                    char_idx = line.find(target)
                    if char_idx != -1:
                        positions.append({
                            "line_0_indexed": line_idx,
                            "line_1_indexed": line_idx + 1,
                            "character_0_indexed": char_idx,
                            "line_content": line.strip(),
                            "match_type": "variable_definition",
                            "context": self._get_context(lines, line_idx)
                        })

        return positions

    def _reference_search(self, lines: List[str], target: str, target_type: str) -> List[Dict[str, Any]]:
        """Search for references/usage."""
        positions = []

        for line_idx, line in enumerate(lines):
            # Skip definition lines
            stripped_line = line.strip()
            if stripped_line.startswith('def ') or stripped_line.startswith('class '):
                continue

            # Find usage of the target
            char_idx = line.find(target)
            while char_idx != -1:
                if self._is_valid_occurrence(line, char_idx, len(target)):
                    positions.append({
                        "line_0_indexed": line_idx,
                        "line_1_indexed": line_idx + 1,
                        "character_0_indexed": char_idx,
                        "line_content": line.strip(),
                        "match_type": "reference",
                        "context": self._get_context(lines, line_idx)
                    })
                char_idx = line.find(target, char_idx + 1)

        return positions

    def _is_valid_occurrence(self, line: str, start_idx: int, length: int) -> bool:
        """Check if this is a valid word occurrence, not part of another word."""
        # Check character before
        if start_idx > 0:
            prev_char = line[start_idx - 1]
            if prev_char.isalnum() or prev_char == '_':
                return False

        # Check character after
        if start_idx + length < len(line):
            next_char = line[start_idx + length]
            if next_char.isalnum() or next_char == '_':
                return False

        return True

    def _get_context(self, lines: List[str], line_idx: int, context_size: int = 2) -> str:
        """Get context around a line."""
        start = max(0, line_idx - context_size)
        end = min(len(lines), line_idx + context_size + 1)

        context_lines = []
        for i in range(start, end):
            prefix = ">>> " if i == line_idx else "    "
            context_lines.append(f"{prefix}{i+1}: {lines[i]}")

        return "\n".join(context_lines)

    def _prioritize_by_context(self, positions: List[Dict[str, Any]], context_line: int) -> List[Dict[str, Any]]:
        """Prioritize positions based on proximity to context line."""
        if not positions:
            return positions

        # Calculate distances and sort by proximity
        for pos in positions:
            distance = abs(pos["line_1_indexed"] - context_line)
            pos["context_distance"] = distance

        return sorted(positions, key=lambda x: x["context_distance"])

    def _calculate_best_match(self, positions: List[Dict[str, Any]], context_line: Optional[int], target: str, content: str) -> tuple:
        """Calculate the best match and confidence score."""
        if not positions:
            return None, 0.0

        # Score each position
        for pos in positions:
            score = 0.0

            # Base score for being a valid match
            score += 0.5

            # Bonus for definition types
            if "definition" in pos.get("match_type", ""):
                score += 0.3

            # Bonus for exact matches
            if pos.get("match_type") == "exact":
                score += 0.2

            # Context proximity bonus
            if context_line:
                distance = abs(pos["line_1_indexed"] - context_line)
                if distance <= 3:
                    score += 0.2 * (1 - distance / 10)

            # Content analysis bonus
            line_content = pos.get("line_content", "")
            if "def " in line_content and "(" in line_content:
                score += 0.1
            if line_content.strip().startswith(("def ", "class ")):
                score += 0.1

            pos["score"] = min(score, 1.0)  # Cap at 1.0

        # Find best match
        best_match = max(positions, key=lambda x: x.get("score", 0.0))
        confidence = best_match.get("score", 0.0)

        return best_match, confidence

    def _generate_suggestions(self, positions: List[Dict[str, Any]], confidence: float) -> List[str]:
        """Generate alternative suggestions based on results."""
        suggestions = []

        if confidence < 0.6:
            suggestions.append("Low confidence - consider using bash+grep for manual verification")

        if len(positions) > 1:
            suggestions.append(f"Multiple matches found ({len(positions)}) - verify the correct one")

        if confidence > 0.8:
            suggestions.append("High confidence match - safe to use with LSP tools")

        suggestions.extend([
            "Use the lsp_coordinates with multilspy_python_definition for precise definition lookup",
            "If LSP tools fail, fall back to bash tools for file exploration"
        ])

        return suggestions