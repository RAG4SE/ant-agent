# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Position finder tool for accurate LSP positioning."""

from __future__ import annotations

import re
import ast
import logging
from typing import Any, Dict, List, Optional, Type
from pathlib import Path

from ant_agent.tools.base import AntTool, AntToolResult
from pydantic import BaseModel, Field

# Set up module-level logger
logger = logging.getLogger(__name__)


class PositionFinderInput(BaseModel):
    """Enhanced input schema for position finder tool with validation capabilities."""
    file_path: str = Field(description="Path to the source file")
    line_number: int = Field(description="0-based line number suggested by LLM")
    line_content: str = Field(description="The content of the line to search in (as suggested by LLM)")
    target: str = Field(description="The target string to find in the line")


class PositionFinderResult(BaseModel):
    """Result schema for position finder."""
    success: bool
    positions: List[Dict[str, Any]] = Field(default_factory=list)
    best_match: Optional[Dict[str, Any]] = None
    alternative_suggestions: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    lsp_coordinates: Optional[Dict[str, Any]] = None  # LSP-ready coordinates


class PositionFinderTool(AntTool):
    """Intelligent position finder for LSP tools.

    This tool helps accurately locate functions, classes, variables, and other identifiers
    in source code, providing precise coordinates for LSP tools like multilspy_python_definition.

    When to use:
    - Before calling multilspy_*_definition (* represents any supported programming language) to get accurate coordinates
    - When you need to find the exact position of a function/class/variable
    - When multilspy tools are failing due to incorrect position data
    - To validate that a target exists before attempting LSP operations

    After using this tool:
    - If failed, use bash tools to explore the file structure instead
    """

    name: str = "position_finder"
    description: str = """Intelligent position finder with LLM suggestion validation for LSP tools. position_finder can find the 0-based line number and the 0-based column number of the target, which is ready for being sent to LSP server. Use this tool when you want to use the multilspy-related tools but do not know the exact position, or when the LLM tells so."""

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
        """Intelligent position finder with LLM suggestion validation and progressive search.

        Args:
            file_path: Path to the source file
            line_number: 0-based line number suggested by LLM
            line_content: The content of the line to search in (as suggested by LLM)
            target: The target string to find in the line

        Returns:
            Validated LSP-compatible coordinates or detailed error for bash fallback
        """
        logger.info(f"PositionFinder: Starting validation for target '{target}' at line {line_number}")
        logger.debug(f"File: {file_path}, Suggested line content: '{line_content}'")

        try:
            # Resolve file path against working directory
            absolute_path = self._get_absolute_path(file_path)
            logger.debug(f"Resolved absolute path: {absolute_path}")

            # Read file content from file_path
            try:
                with open(absolute_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                logger.debug(f"Successfully read file content from {absolute_path}")
            except FileNotFoundError:
                logger.error(f"File not found: {absolute_path}")
                return AntToolResult(
                    success=False,
                    error=f"File not found: {file_path}",
                    metadata={
                        "status": "error",
                        "suggested_action": "check_file_path",
                        "file_path": file_path,
                        "absolute_path": absolute_path
                    }
                )
            except IOError as e:
                logger.error(f"Error reading file {absolute_path}: {str(e)}")
                return AntToolResult(
                    success=False,
                    error=f"Error reading file {file_path}: {str(e)}",
                    metadata={
                        "status": "error",
                        "suggested_action": "check_file_permissions",
                        "file_path": file_path,
                        "absolute_path": absolute_path,
                        "exception": str(e)
                    }
                )

            # Parse file content into lines
            lines = file_content.split('\n')
            logger.debug(f"File has {len(lines)} total lines")

            # Validate line number is within bounds
            if line_number < 0 or line_number >= len(lines):
                logger.warning(f"Invalid line number {line_number}. File has {len(lines)} lines (0-based)")
                return AntToolResult(
                    success=False,
                    error=f"Invalid line number {line_number}. File has {len(lines)} lines (0-based).",
                    metadata={
                        "status": "error",
                        "suggested_action": "use_bash_search",
                        "search_performed": "validation_failed",
                        "line_number_checked": line_number,
                        "total_lines": len(lines)
                    }
                )

            # Step 1: Validate LLM's suggested position
            logger.info(f"Step 1: Validating LLM suggestion at line {line_number}")
            actual_line = lines[line_number].rstrip()  # Remove trailing whitespace
            suggested_line = line_content.rstrip()

            logger.debug(f"Suggested line content: '{suggested_line}'")
            logger.debug(f"Actual line content: '{actual_line}'")

            # Check if the suggested line content matches actual file content
            content_matches = self._lines_match(suggested_line, actual_line)
            target_in_suggested_line = target in suggested_line
            target_in_actual_line = target in actual_line

            logger.debug(f"Content matches: {content_matches}")
            logger.debug(f"Target in suggested line: {target_in_suggested_line}")
            logger.debug(f"Target in actual line: {target_in_actual_line}")

            if content_matches and target_in_actual_line:
                # Perfect match! LLM's suggestion is correct
                logger.info(f"✓ Perfect match found! LLM suggestion validated successfully")
                char_idx = actual_line.find(target)
                if char_idx != -1:
                    return self._create_success_result(
                        absolute_path, line_number, char_idx, actual_line, target,
                        "exact_match", "LLM suggestion validated"
                    )

            # Step 2: Progressive search if initial validation fails
            logger.info(f"Step 2: Initial validation failed, starting progressive search")
            if target_in_actual_line:
                # Content doesn't match but target is in the actual line
                logger.info(f"✓ Target found in actual line despite content mismatch")
                char_idx = actual_line.find(target)
                return self._create_success_result(
                    absolute_path, line_number, char_idx, actual_line, target,
                    "content_mismatch", "target_found_in_actual_line"
                )

            # Step 3: Search ±3 lines around the suggestion
            logger.info(f"Step 3: Searching ±3 lines around line {line_number}")
            result = self._search_in_range(lines, line_number, target, 3, absolute_path)
            if result:
                logger.info(f"✓ Target found within ±3 lines")
                return result

            # Step 4: Expand to ±5 lines if still not found
            logger.info(f"Step 4: Expanding search to ±5 lines around line {line_number}")
            result = self._search_in_range(lines, line_number, target, 5, absolute_path)
            if result:
                logger.info(f"✓ Target found within ±5 lines")
                return result

            # Step 5: Return detailed error for bash fallback
            logger.warning(f"✗ Target '{target}' not found within ±5 lines of line {line_number}")
            logger.info(f"Suggesting bash search as fallback")
            return AntToolResult(
                success=False,
                error=f"Target '{target}' not found within ±5 lines of suggested position (line {line_number}).",
                output=f"Target '{target}' not found within ±5 lines of suggested position (line {line_number}).",
                metadata={
                    "status": "error",
                    "suggested_action": "use_bash_search",
                    "message": f"Target '{target}' not found within ±5 lines of line {line_number}.",
                    "line_number_checked": line_number,
                    "search_performed": "±5 lines",
                    "suggestion": f"Use 'grep -n \"{target}\" {file_path}' to find all occurrences"
                }
            )

        except Exception as e:
            logger.error(f"Position finder validation error: {str(e)}", exc_info=True)
            return AntToolResult(
                output=f"Position finder validation error: {str(e)}",
                success=False,
                error=f"Position finder validation error: {str(e)}",
                metadata={
                    "status": "error",
                    "suggested_action": "use_bash_search",
                    "exception": str(e)
                }
            )

    def _lines_match(self, line1: str, line2: str) -> bool:
        """Check if two lines match, allowing for some whitespace differences."""
        # Remove leading/trailing whitespace and compare
        line1_stripped = line1.strip()
        line2_stripped = line2.strip()
        matches = line1_stripped == line2_stripped
        logger.debug(f"Line comparison: '{line1_stripped}' vs '{line2_stripped}' -> {matches}")
        return matches

    def _search_in_range(self, lines: List[str], center_line: int, target: str, range_size: int, file_path: str) -> Optional[AntToolResult]:
        """Search for target in a range around the center line."""
        start = max(0, center_line - range_size)
        end = min(len(lines), center_line + range_size + 1)

        logger.debug(f"Searching ±{range_size} lines around line {center_line} (range: {start}-{end-1})")

        for i in range(start, end):
            line_content = lines[i].rstrip()
            if target in line_content:
                char_idx = line_content.find(target)
                logger.info(f"✓ Target found at line {i} (0-based) within ±{range_size} search")
                logger.debug(f"Line {i} content: '{line_content}'")
                return self._create_success_result(
                    file_path, i, char_idx, line_content, target,
                    f"range_search_±{range_size}", f"found_in_±{range_size}_lines"
                )

        logger.debug(f"Target not found in ±{range_size} lines search")
        return None

    def _create_success_result(self, file_path: str, line_number: int, char_idx: int,
                             line_content: str, target: str, match_type: str, 
                             validation_method: str) -> AntToolResult:
        """Create a success result with proper formatting."""
        logger.info(f"Creating success result for target '{target}' at line {line_number}, char {char_idx}")
        logger.debug(f"Match type: {match_type}, Validation: {validation_method}")

        lsp_coordinates = {
            "file_path": file_path,
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
                "match_type": match_type,
                "context": line_content.strip(),
                "validation_method": validation_method
            }],
            best_match={
                "line_0_indexed": line_number,
                "line_1_indexed": line_number + 1,
                "character_0_indexed": char_idx,
                "line_content": line_content.strip(),
                "match_type": match_type,
                "context": line_content.strip(),
                "validation_method": validation_method
            },
            lsp_coordinates=lsp_coordinates,
            alternative_suggestions=[]
        )

        output = f"Found '{target}' at line {line_number} (0-based): {line_content}, character {char_idx} (0-based)"
        output += f"\nLSP coordinates: {lsp_coordinates}"
        output += f"\nValidation: {validation_method}"


        return AntToolResult(
            success=True,
            output=output,
            metadata=result_data.dict()
        )

    def _find_positions(self, file_path: str, target: str, search_mode: str, target_type: str, context_line: Optional[int]) -> List[Dict[str, Any]]:
        """Find all positions of the target in file content."""
        positions = []

        # Read file content from file_path
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.split('\n')
        except IOError as e:
            logger.error(f"Error reading file {file_path} for position search: {str(e)}")
            return positions

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
