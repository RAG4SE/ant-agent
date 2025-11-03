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
    """Input schema for position finder tool."""
    file_path: str = Field(description="Path to the source file")
    target: str = Field(description="Function name, variable name, class name, or other identifier to find")
    search_mode: str = Field(default="exact", description="Search mode: 'exact', 'fuzzy', 'definition', 'reference'")
    context_line: Optional[int] = Field(default=None, description="Optional line number hint (1-indexed)")
    target_type: str = Field(default="any", description="Type of target: 'function', 'class', 'variable', 'import', 'any'")


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
    description: str = """Find accurate positions of functions, classes, and variables for LSP tools.

    This tool intelligently locates code elements and provides LSP-ready coordinates.
    Use it BEFORE calling multilspy_python_definition to ensure accurate positioning.

    Key features:
    - Smart search with multiple modes (exact, fuzzy, definition, reference)
    - Confidence scoring to indicate result reliability
    - LSP-compatible coordinate format (0-indexed line and character)
    - Fallback suggestions when positioning fails

    Best practices:
    1. Use this tool first to find accurate positions
    2. Check the confidence score - >0.8 is reliable for LSP
    3. If confidence is low or fails, switch to bash+grep approach
    4. Always validate results before proceeding with LSP operations"""

    args_schema: Type[BaseModel] = PositionFinderInput

    def _run(self, file_path: str, target: str, search_mode: str = "exact",
             context_line: Optional[int] = None, target_type: str = "any") -> AntToolResult:
        """Find the position of a target in source code."""
        try:
            path = Path(file_path)
            if not path.exists():
                return AntToolResult(
                    success=False,
                    error=f"File not found: {file_path}",
                    metadata={"suggestion": "Check if the file path is correct or use bash to explore the directory"}
                )

            if not path.is_file():
                return AntToolResult(
                    success=False,
                    error=f"Path is not a file: {file_path}",
                    metadata={"suggestion": "Use bash to explore directories"}
                )

            # Read file content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                return AntToolResult(
                    success=False,
                    error=f"Error reading file: {str(e)}",
                    metadata={"suggestion": "Try using bash to read the file instead"}
                )

            # Find positions based on search mode
            positions = self._find_positions(content, target, search_mode, target_type, context_line)

            if not positions:
                return AntToolResult(
                    success=False,
                    error=f"Target '{target}' not found in {file_path}",
                    metadata={
                        "suggestions": [
                            f"Try search_mode='fuzzy' for approximate matching",
                            f"Use bash to search: grep -n '{target}' {file_path}",
                            f"Check if the target name is spelled correctly",
                            f"Try target_type='reference' if looking for usage rather than definition"
                        ]
                    }
                )

            # Calculate confidence and find best match
            best_match, confidence = self._calculate_best_match(positions, context_line, target, content)

            # Convert to LSP coordinates (0-indexed)
            lsp_coordinates = None
            if best_match:
                lsp_coordinates = {
                    "file_path": str(path),
                    "line": best_match["line_0_indexed"],
                    "character": best_match["character_0_indexed"]
                }

            result_data = PositionFinderResult(
                success=True,
                positions=positions,
                best_match=best_match,
                confidence=confidence,
                lsp_coordinates=lsp_coordinates,
                alternative_suggestions=self._generate_suggestions(positions, confidence)
            )

            output = f"Found {len(positions)} position(s) for '{target}'"
            if best_match:
                output += f"\nBest match: Line {best_match['line_1_indexed']}, Character {best_match['character_0_indexed']} (confidence: {confidence:.2f})"
            if lsp_coordinates:
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
                metadata={"suggestion": "Try using bash tools as fallback"}
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