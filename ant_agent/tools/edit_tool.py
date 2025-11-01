# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""File editing tool for Ant Agent."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, Type

from ant_agent.tools.base import AntTool, AntToolResult
from pydantic import BaseModel


class EditInput(BaseModel):
    """Input schema for edit tool."""
    file_path: str
    old_str: str
    new_str: str


class EditTool(AntTool):
    """Tool for editing files using string replacement."""

    name: str = "edit_tool"
    description: str = "Edit a file by replacing exact string matches"
    args_schema: Type[BaseModel] = EditInput

    def _run(self, file_path: str, old_str: str, new_str: str) -> AntToolResult:
        """Edit file by replacing old_str with new_str."""
        try:
            path = Path(file_path)

            # Check if file exists
            if not path.exists():
                return AntToolResult(
                    success=False,
                    error=f"File not found: {file_path}"
                )

            # Read file content
            content = path.read_text(encoding='utf-8')

            # Check if old string exists
            if old_str not in content:
                return AntToolResult(
                    success=False,
                    error=f"String not found in file: {old_str[:100]}..."
                )

            # Replace content
            new_content = content.replace(old_str, new_str)

            # Write back to file
            path.write_text(new_content, encoding='utf-8')

            return AntToolResult(
                success=True,
                output=f"Successfully replaced string in {file_path}",
                metadata={
                    "file_path": file_path,
                    "replacements": content.count(old_str),
                    "file_size": len(new_content)
                }
            )

        except PermissionError:
            return AntToolResult(
                success=False,
                error=f"Permission denied: {file_path}"
            )
        except Exception as e:
            return AntToolResult(
                success=False,
                error=f"File edit failed: {str(e)}"
            )


class CreateFileInput(BaseModel):
    """Input schema for create file tool."""
    file_path: str
    content: str


class CreateFileTool(AntTool):
    """Tool for creating new files."""

    name: str = "create_file"
    description: str = "Create a new file or overwrite an existing file with the specified content"
    args_schema: Type[BaseModel] = CreateFileInput

    def _run(self, file_path: str, content: str) -> AntToolResult:
        """Create a new file or overwrite existing file with the given content."""
        try:
            path = Path(file_path)

            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file already exists
            if path.exists():
                # If file exists, overwrite it with new content
                existing_content = path.read_text(encoding='utf-8')
                path.write_text(content, encoding='utf-8')

                return AntToolResult(
                    success=True,
                    output=f"Successfully updated file: {file_path}",
                    metadata={
                        "file_path": file_path,
                        "file_size": len(content),
                        "action": "overwrite"
                    }
                )
            else:
                # Create new file
                path.write_text(content, encoding='utf-8')

                return AntToolResult(
                    success=True,
                    output=f"Successfully created file: {file_path}",
                    metadata={
                        "file_path": file_path,
                        "file_size": len(content),
                        "action": "create"
                    }
                )

        except PermissionError:
            return AntToolResult(
                success=False,
                error=f"Permission denied: {file_path}"
            )
        except Exception as e:
            return AntToolResult(
                success=False,
                error=f"File operation failed: {str(e)}"
            )