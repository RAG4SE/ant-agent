# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Bash execution tool for Ant Agent."""

from __future__ import annotations

import asyncio
import os
import shlex
import subprocess
from typing import Any, Dict, Optional, Type

from ant_agent.tools.base import AntTool, AntToolResult
from pydantic import BaseModel


class BashInput(BaseModel):
    """Input schema for bash tool."""
    command: str


class BashTool(AntTool):
    """Tool for executing bash commands."""

    name: str = "bash"
    description: str = "Execute bash commands in the terminal"
    args_schema: Type[BaseModel] = BashInput
    working_dir: str

    def __init__(self, working_dir: str, **kwargs):
        """Initialize BashTool with working directory.

        Args:
            working_dir: Working directory for command execution.
            **kwargs: Additional keyword arguments for parent class.
        """
        # Set working_dir before calling super().__init__ to pass Pydantic validation
        kwargs['working_dir'] = working_dir
        super().__init__(**kwargs)

    def _run(self, command: str) -> AntToolResult:
        """Execute bash command synchronously."""
        # Check if working directory exists
        if not os.path.exists(self.working_dir):
            raise FileNotFoundError(f"Working directory does not exist: {self.working_dir}")

        original_cwd = None
        try:
            # Change to working directory
            original_cwd = os.getcwd()
            os.chdir(self.working_dir)

            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )

            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"

            return AntToolResult(
                success=result.returncode == 0,
                output=output,
                metadata={
                    "return_code": result.returncode,
                    "command": command,
                    "working_dir": self.working_dir
                }
            )

        except subprocess.TimeoutExpired:
            return AntToolResult(
                success=False,
                error="Command timed out after 30 seconds"
            )
        except Exception as e:
            return AntToolResult(
                success=False,
                error=f"Command execution failed: {str(e)}"
            )
        finally:
            # Restore original working directory
            if original_cwd:
                os.chdir(original_cwd)

    async def _arun(self, command: str) -> AntToolResult:
        """Execute bash command asynchronously."""
        # Check if working directory exists
        if not os.path.exists(self.working_dir):
            raise FileNotFoundError(f"Working directory does not exist: {self.working_dir}")

        original_cwd = None
        try:
            # Change to working directory
            original_cwd = os.getcwd()
            os.chdir(self.working_dir)

            # Execute command asynchronously
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return AntToolResult(
                    success=False,
                    error="Command timed out after 30 seconds"
                )

            output = stdout.decode() if stdout else ""
            if stderr:
                output += f"\nSTDERR:\n{stderr.decode()}"

            return AntToolResult(
                success=process.returncode == 0,
                output=output,
                metadata={
                    "return_code": process.returncode,
                    "command": command,
                    "working_dir": self.working_dir
                }
            )

        except Exception as e:
            return AntToolResult(
                success=False,
                error=f"Command execution failed: {str(e)}"
            )
        finally:
            # Restore original working directory
            if original_cwd:
                os.chdir(original_cwd)