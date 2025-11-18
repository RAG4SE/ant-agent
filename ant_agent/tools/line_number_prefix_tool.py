# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Line number prefix tools for Ant Agent."""

from __future__ import annotations

import os
import tempfile
import time
import shutil
from typing import Any, Optional, Type

from ant_agent.tools.base import AntTool, AntToolResult
from pydantic import BaseModel, Field

temp_dir = tempfile.mkdtemp(prefix="ant_agent_line_numbers_")

class CreateLineNumberedTempFileInput(BaseModel):
    """Input schema for creating numbered temporary file."""
    file_path: str = Field(description="Path to the target file to create a numbered copy of")


class CreateLineNumberedTempFile(AntTool):
    """Tool for creating temporary files with 0-based line numbers."""

    name: str = "create_line_numbered_temp_file"
    description: str = (
        "Create a temporary file copy with 0-based line numbers prefixed to each line. "
        "This tool creates numbered copies of source files to help with line-based analysis. "
        "Use this before position_finder or when you need to reference specific line numbers in code."
    )
    working_dir: str = None
    args_schema: Type[BaseModel] = CreateLineNumberedTempFileInput

    def __init__(self, working_dir: str, **kwargs: Any):
        kwargs['working_dir'] = working_dir
        super().__init__(**kwargs)

    def _run(self, file_path: str) -> AntToolResult:
        """Create a temporary file copy with 0-based line numbers prefixed to each line."""
        if not os.path.exists(self.working_dir):
            return AntToolResult(
                success=False,
                error=f"Working directory not found: {self.working_dir}",
            )
        file_path = os.path.join(self.working_dir, file_path)
        # Check if file exists
        if not os.path.exists(file_path):
            return AntToolResult(
                success=False,
                error=f"File not found: {file_path}",
            )

        # Check if it's a file (not a directory)
        if not os.path.isfile(file_path):
            return AntToolResult(
                success=False,
                error=f"Path is not a file: {file_path}",
            )

        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Try with different encoding for binary files
            with open(file_path, 'r', encoding='latin-1') as f:
                lines = f.readlines()

        global temp_dir

        # Get relative path from working_dir to preserve directory structure
        relative_path = os.path.relpath(file_path, self.working_dir)

        # Create the same directory structure in temp_dir
        temp_relative_dir = os.path.dirname(relative_path)
        if temp_relative_dir and temp_relative_dir != '.':
            temp_target_dir = os.path.join(temp_dir, temp_relative_dir)
            os.makedirs(temp_target_dir, exist_ok=True)
            temp_file_path = os.path.join(temp_target_dir, os.path.basename(relative_path))
        else:
            temp_file_path = os.path.join(temp_dir, os.path.basename(relative_path))

        if os.path.exists(temp_file_path):
            return AntToolResult(
                success=True,
                output=f"Created file: {temp_file_path}, which is the file copy of {file_path} that prefix the original content with 0-based line numbers. This is helpful for you to locate relevant code snippets.",
                metadata={
                    "original_file_path": file_path,
                    "temp_file_path": temp_file_path,
                    "temp_dir": temp_dir,
                    "total_lines": len(lines),
                    "max_lines_applied": False,
                    "original_line_count": len(lines),
                    "relative_path": relative_path
                }
            )

        # Prefix with 0-based line numbers
        numbered_lines = []
        for i, line in enumerate(lines):
            # Remove trailing newline and add back to maintain consistent formatting
            line_content = line.rstrip('\n\r')
            # Format: 000: line content (zero-padded to 3 digits for consistency)
            numbered_line = f"{i:03d}: {line_content}"
            numbered_lines.append(numbered_line)

        # Join lines with newlines
        result_content = '\n'.join(numbered_lines)

        # Write numbered content to temporary file
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(result_content)
        

        return AntToolResult(
            success=True,
            output=f"Created file: {temp_file_path}, which is the file copy of {file_path} that prefix the original content with 0-based line numbers. This is helpful for you to locate relevant code snippets.",
            metadata={
                "original_file_path": file_path,
                "temp_file_path": temp_file_path,
                "temp_dir": temp_dir,
                "total_lines": len(lines),
                "original_line_count": len(lines),
                "relative_path": relative_path
            }
        )


class RemoveAllLineNumberedTempFiles(AntTool):
    """Tool for removing all line-numbered temporary files."""

    name: str = "remove_all_line_numbered_temp_files"
    description: str = (
        "Remove all numbered temporary files created by create_line_numbered_temp_file tool. "
        "This tool cleans up all temporary numbered file copies and removes them from memory. "
        "Use this at the end of analysis to clean up resources."
    )
    args_schema: Type[BaseModel] = None  # No input parameters needed

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def _run(self) -> AntToolResult:
        """Remove all numbered temporary files and clean up memory."""
        if not os.path.exists(temp_dir):
            return AntToolResult(
                    success=True,
                    output="No numbered temporary files found to remove.",
                    metadata={"removed_count": 0, "removed_files": [], "errors": []}
                ) 
        shutil.rmtree(temp_dir) 
        return AntToolResult(
            success=True,
            output="Successfully removed all temporary files, go the the next step",
        )

def remove_line_numbered_temp_file():
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir) 