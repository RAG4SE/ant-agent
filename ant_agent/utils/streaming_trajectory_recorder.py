"""
Streaming Trajectory Recorder for Real-time Logging

This module provides a streaming version of trajectory recording that outputs
logs in real-time as the agent executes, rather than waiting until completion.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO
from threading import Lock

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage

from ant_agent.tools.base import AntToolResult
from ant_agent.utils.config import TrajectoryConfig


class StreamingTrajectoryRecorder:
    """Records agent execution trajectories with real-time streaming output."""

    def __init__(self, config: TrajectoryConfig, stream_output: bool = False,
                 stream_file: Optional[TextIO] = None, pretty_print: bool = True,
                 real_time_save: bool = True):
        """Initialize streaming trajectory recorder.

        Args:
            config: Trajectory recording configuration
            stream_output: Whether to stream output to console/file
            stream_file: Optional file stream for output (defaults to stdout)
            pretty_print: Whether to pretty-print JSON output
            real_time_save: Whether to save trajectory file in real-time
        """
        self.config = config
        self.enabled = config.enabled
        self.stream_output = stream_output
        self.pretty_print = pretty_print
        self.stream_file = stream_file or sys.stdout
        self.output_dir = Path(config.output_dir)
        self.real_time_save = real_time_save
        # Thread safety for concurrent access
        self._lock = Lock()

        # Trajectory data storage (still maintained for final save)
        self.trajectory_data: Dict[str, Any] = {
            "session_info": {
                "start_time": self._get_current_time(),
                "version": "0.1.0",
            },
            "messages": [],
            "system_info": {}
            # Removed stream_log and tool_calls completely
        }

        # Current step tracking for context
        self._save_counter = 0  # Counter for periodic saves
        self._save_interval = 1  # Save every xx events

        if self.enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self._log_session_start()

    def _get_current_time(self) -> str:
        """Get current time."""
        return datetime.now().isoformat()

    def _save_trajectory_realtime(self) -> None:
        """Save trajectory data to file in real-time."""
        if not self.real_time_save or not self.enabled:
            return

        try:
            filepath = self.output_dir / self.config.output_file

            # Create a copy of trajectory data with updated end time
            trajectory_copy = self.trajectory_data.copy()
            trajectory_copy["session_info"]["end_time"] = self._get_current_time()

            # Save to temporary file first, then rename for atomic updates
            temp_filepath = filepath.with_suffix('.tmp')
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(trajectory_copy, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_filepath.replace(filepath)

        except Exception as e:
            # Log error but don't interrupt execution
            if self.stream_output:
                error_log = {
                    "timestamp": self._get_current_time(),
                    "type": "save_error",
                    "error": str(e),
                    # Removed icon
                    "level": "error"
                }
                self._stream_log(error_log, save_to_file=False)

    def _should_save(self) -> bool:
        """Check if it's time to save based on the save interval."""
        self._save_counter += 1
        return self._save_counter % self._save_interval == 0

    def _log_session_start(self) -> None:
        """Log session start with streaming output."""
        if not self.stream_output:
            return

        start_log = {
            "timestamp": self._get_current_time(),
            "type": "session_start",
            "message": "Agent session started",  # Removed emoji
            "config": {
                "output_dir": str(self.output_dir),
                "include_llm_calls": self.config.include_llm_calls,
                "include_tool_calls": self.config.include_tool_calls,
                "include_system_info": self.config.include_system_info
            }
        }

        self._stream_log(start_log)

    def _stream_log(self, log_entry: Dict[str, Any], save_to_file: bool = True) -> None:
        """Stream a log entry to output and optionally save to file."""
        if not self.stream_output and not save_to_file:
            return

        with self._lock:
            # Removed: Add to trajectory data (stream_log no longer stored)
            # Stream to output if enabled
            if self.stream_output:
                if self.pretty_print:
                    json_str = json.dumps(log_entry, indent=2, ensure_ascii=False)
                else:
                    json_str = json.dumps(log_entry, ensure_ascii=False)

                # print(f"\n{json_str}", file=self.stream_file, flush=True)

            # Save to file in real-time if enabled
            if save_to_file and self.real_time_save and self._should_save():
                self._save_trajectory_realtime()

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the trajectory with real-time logging."""
        if not self.enabled or not self.config.include_llm_calls:
            return

        message_data = {
            "type": type(message).__name__,
            "content": message.content,
            "timestamp": self._get_current_time(),
        }

        # Add additional metadata based on message type (removed tool_calls)
        if hasattr(message, 'tool_call_id'):
            message_data["tool_call_id"] = message.tool_call_id

        if hasattr(message, 'usage_metadata') and message.usage_metadata:
            message_data["usage"] = message.usage_metadata

        # Extract tool name and args from additional_kwargs for ToolMessage (kept for context)
        if isinstance(message, ToolMessage) and hasattr(message, 'additional_kwargs') and message.additional_kwargs:
            if 'tool_name' in message.additional_kwargs:
                message_data["tool_name"] = message.additional_kwargs['tool_name']
            if 'tool_args' in message.additional_kwargs:
                message_data["tool_args"] = message.additional_kwargs['tool_args']

        # Add to trajectory data
        self.trajectory_data["messages"].append(message_data)

        # Stream log entry (simplified - removed icon and tool calls)
        log_entry = {
            "timestamp": self._get_current_time(),
            "type": "message",
            "message_type": message_data["type"],
            "content_preview": message.content[:200] + "..." if len(message.content) > 200 else message.content,
            "full_content": message.content
        }

        # Minimal handling for different message types (removed icon and tool calls)
        if isinstance(message, HumanMessage):
            log_entry["level"] = "user_input"
        elif isinstance(message, AIMessage):
            log_entry["level"] = "assistant_response"
            # Removed tool calls related fields
        elif isinstance(message, ToolMessage):
            log_entry["level"] = "tool_result"
            # Extract tool name and args from additional_kwargs (keep these as they provide context)
            if hasattr(message, 'additional_kwargs') and message.additional_kwargs:
                if 'tool_name' in message.additional_kwargs:
                    log_entry["tool_name"] = message.additional_kwargs['tool_name']
                if 'tool_args' in message.additional_kwargs:
                    log_entry["tool_args"] = message.additional_kwargs['tool_args']
        elif isinstance(message, SystemMessage):
            log_entry["level"] = "system"

        self._stream_log(log_entry)

    def add_tool_result(self, result: AntToolResult) -> None:
        """Add a tool execution result to the trajectory with real-time logging."""
        if not self.enabled or not self.config.include_tool_calls:
            return
        # tool_data = {
        #     "success": result.success,
        #     "output": result.output,
        #     "error": result.error,
        #     "metadata": result.metadata,
        #     "timestamp": self._get_current_time(),
        # }

        # Removed: Add to trajectory data - no longer storing tool_calls
        # Only stream log entry (removed icon)
        log_entry = {
            "timestamp": self._get_current_time(),
            "type": "tool_execution",
            "tool_name": result.metadata.get("tool_name", "unknown"),
            "success": result.success,
            "output_preview": (result.output[:300] + "..." if result.output and len(result.output) > 300 else result.output) if result.output else "",
            "full_output": result.output if result.output else "",
            "error": result.error if result.error else "",
            "execution_time": result.metadata.get("execution_time", "unknown")
        }

        # Check if there's an error and print it
        if result.error:
            log_entry["error_message"] = result.error

        if result.success:
            log_entry["level"] = "success"
            log_entry["status"] = "Tool executed successfully"
        else:
            log_entry["level"] = "error"
            log_entry["status"] = "Tool execution failed"

        self._stream_log(log_entry)


    def add_system_prompt(self, system_prompt: str) -> None:
        """Add the system prompt to the trajectory with real-time logging."""
        if not self.enabled or not self.config.include_system_info:
            return

        self.trajectory_data["system_info"]["system_prompt"] = system_prompt

        # Stream log entry (removed icon)
        log_entry = {
            "timestamp": self._get_current_time(),
            "type": "system_prompt",
            "prompt_preview": system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt,
            "full_prompt": system_prompt,
            "level": "system"
        }

        self._stream_log(log_entry)


    def save(self, filename: Optional[str] = None) -> str:
        """Save the trajectory to a file (in addition to streaming).

        Args:
            filename: Optional filename. If not provided, uses config.output_file.

        Returns:
            Path to the saved trajectory file
        """
        if not self.enabled:
            return ""

        # Use config output_file if filename not provided
        if not filename:
            filename = self.config.output_file

        filepath = self.output_dir / filename

        # Update end time
        self.trajectory_data["session_info"]["end_time"] = self._get_current_time()

        # Log final save (removed icon and emoji)
        self._stream_log({
            "timestamp": self._get_current_time(),
            "type": "session_end",
            "message": f"Trajectory saved to {filepath}",
            "filepath": str(filepath),
            "level": "system"
        })

        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.trajectory_data, f, indent=2, ensure_ascii=False)

        return str(filepath)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the trajectory."""
        if not self.enabled:
            return {"enabled": False}

        return {
            "enabled": True,
            "message_count": len(self.trajectory_data["messages"]),
            # Removed tool_call_count as tool_calls is no longer stored
            # Removed stream_log_count as stream_log is no longer stored
            "session_duration": self._calculate_duration(),
            # Removed successful_tools and failed_tools as tool_calls is no longer stored
            "output_file": self.config.output_file,
            "output_dir": str(self.output_dir),
            "streaming_enabled": self.stream_output
        }

    def _calculate_duration(self) -> Optional[str]:
        """Calculate session duration."""
        if "start_time" not in self.trajectory_data["session_info"]:
            return None

        start_time = datetime.fromisoformat(self.trajectory_data["session_info"]["start_time"])
        end_time = datetime.fromisoformat(
            self.trajectory_data["session_info"].get("end_time", self._get_current_time())
        )

        duration = end_time - start_time
        return str(duration)

    def reset(self) -> None:
        """Reset the trajectory recorder."""
        self.trajectory_data = {
            "session_info": {
                "start_time": self._get_current_time(),
                "version": "0.1.0",
            },
            "messages": [],
            "system_info": {}
            # Removed stream_log and tool_calls completely
        }


        if self.enabled:
            self._log_session_start()

    def set_stream_file(self, stream_file: TextIO) -> None:
        """Set a new stream file for output."""
        self.stream_file = stream_file

    def enable_streaming(self, enable: bool = True) -> None:
        """Enable or disable streaming output."""
        self.stream_output = enable

    def get_current_context(self) -> Dict[str, Any]:
        """Get current trajectory context for external use."""
        # Get last message timestamp instead of stream_log since stream_log is removed
        last_timestamp = None
        if self.trajectory_data["messages"]:
            last_message = self.trajectory_data["messages"][-1]
            last_timestamp = last_message.get("timestamp")

        return {
            "message_count": len(self.trajectory_data["messages"]),
            # Removed tool_count as tool_calls is no longer stored
            "last_timestamp": last_timestamp
        }

