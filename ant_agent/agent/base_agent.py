# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Base agent class for Ant Agent."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from ant_agent.clients.llm_client import LLMClient
from ant_agent.tools.base import AntTool, AntToolResult
from ant_agent.utils.config import ModelConfig
from ant_agent.utils.trajectory_recorder import TrajectoryRecorder
from omegaconf import DictConfig


class BaseAgent(ABC):
    """Base class for Ant Agent implementations."""

    def __init__(
        self,
        agent_config: DictConfig,
        model_config: ModelConfig,
        trajectory_recorder: Optional[TrajectoryRecorder] = None,
        **kwargs: Any,
    ):
        """Initialize the base agent.

        Args:
            agent_config: Agent configuration (DictConfig from Hydra)
            model_config: Model configuration
            trajectory_recorder: Optional trajectory recorder
            **kwargs: Additional keyword arguments
        """
        self.agent_config = agent_config
        self.model_config = model_config
        self.llm_client = LLMClient(model_config)

        # Initialize trajectory recorder
        self.trajectory_recorder = trajectory_recorder

        # Initialize tools
        self._tools: List[BaseTool] = []
        self._tool_results: List[AntToolResult] = []
        self._messages: List[BaseMessage] = []

        # Add system message
        system_msg = SystemMessage(content=self._get_system_prompt())
        self._messages.append(system_msg)

        # Record system message
        if self.trajectory_recorder:
            self.trajectory_recorder.add_message(system_msg)

        # Execution state
        self._step_count = 0
        self._max_steps = agent_config.get('max_steps', 200)
        self._task_completed = False

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        pass

    @abstractmethod
    def _initialize_tools(self) -> List[AntTool]:
        """Initialize the tools for this agent."""
        pass

    @property
    def tools(self) -> List[BaseTool]:
        """Get the list of available tools."""
        if not self._tools:
            ant_tools = self._initialize_tools()
            tool_list = self.agent_config.get('tools', [])
            self._tools = [tool for tool in ant_tools if tool.name in tool_list]
        return self._tools

    @property
    def messages(self) -> List[BaseMessage]:
        """Get the conversation history."""
        return self._messages.copy()

    @property
    def tool_results(self) -> List[AntToolResult]:
        """Get the history of tool results."""
        return self._tool_results.copy()

    @property
    def step_count(self) -> int:
        """Get the current step count."""
        return self._step_count

    @property
    def is_completed(self) -> bool:
        """Check if the task is completed."""
        return self._task_completed

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation history."""
        self._messages.append(message)
        # Record message in trajectory
        if self.trajectory_recorder:
            self.trajectory_recorder.add_message(message)

    def reset(self) -> None:
        """Reset the agent state."""
        self._messages = [SystemMessage(content=self._get_system_prompt())]
        self._tool_results.clear()
        self._step_count = 0
        self._task_completed = False

    async def arun(self, user_input: str) -> str:
        """Run the agent asynchronously with user input."""
        # Add user message
        self.add_message(HumanMessage(content=user_input))

        # Check step limit
        if self._step_count >= self._max_steps:
            return f"Maximum step limit ({self._max_steps}) reached. Please provide a more specific task or break it down into smaller steps."

        # Get response from LLM with tools
        response = await self.llm_client.ainvoke(
            self.messages,
            tools=self.tools,
        )

        self._step_count += 1

        # Handle tool calls if present
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return await self._handle_tool_calls(response)
        else:
            # Regular text response
            self.add_message(response)
            return response.content

    def run(self, user_input: str) -> str:
        """Run the agent synchronously with user input."""
        # Add user message
        user_msg = HumanMessage(content=user_input)
        self.add_message(user_msg)

        # Check step limit
        if self._step_count >= self._max_steps:
            return f"Maximum step limit ({self._max_steps}) reached. Please provide a more specific task or break it down into smaller steps."

        # Get response from LLM with tools
        response = self.llm_client.invoke(
            self.messages,
            tools=self.tools,
        )

        self._step_count += 1

        # Handle tool calls if present
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return self._handle_tool_calls_sync(response)
        else:
            # Regular text response
            self.add_message(response)
            return response.content

    def _handle_tool_calls_sync(self, response: AIMessage) -> str:
        """Handle tool calls in the LLM response synchronously."""
        self.add_message(response)

        # Process each tool call and create response messages
        tool_response_messages = []
        final_output = []

        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name", "unknown")
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call.get("id", "")

            # Find the tool
            tool = next((t for t in self.tools if t.name == tool_name), None)

            if not tool:
                error_content = f"Tool '{tool_name}' not found"
                final_output.append(f"✗ {tool_name}: {error_content}")
                tool_response_messages.append(
                    ToolMessage(content=error_content, tool_call_id=tool_call_id)
                )
                continue

            try:
                # Execute the tool
                result = tool.run(**tool_args)
                self._tool_results.append(result)

                # Record tool execution in trajectory
                if self.trajectory_recorder:
                    self.trajectory_recorder.add_tool_result(result)

                # Format output
                if result.success:
                    tool_output = result.output or "Success"
                    final_output.append(f"✓ {tool_name}: {tool_output}")
                else:
                    tool_output = result.error or "Tool execution failed"
                    final_output.append(f"✗ {tool_name}: {tool_output}")

                # Create tool response message
                tool_response_messages.append(
                    ToolMessage(content=tool_output, tool_call_id=tool_call_id)
                )

                # Check if task was completed
                if tool_name == "task_done":
                    self._task_completed = True

            except Exception as e:
                error_content = f"Error executing {tool_name}: {str(e)}"
                final_output.append(f"✗ {tool_name}: {error_content}")
                tool_response_messages.append(
                    ToolMessage(content=error_content, tool_call_id=tool_call_id)
                )

        # Add all tool response messages to conversation
        for tool_msg in tool_response_messages:
            self.add_message(tool_msg)

        # Continue conversation only if there are meaningful tool results and not completed
        if not self._task_completed and self._step_count < self._max_steps and len(tool_response_messages) > 0:
            # Check if we should continue based on the context
            # If the last tool was a file creation or successful completion, consider task done
            should_continue = True
            if tool_response_messages:
                last_tool_msg = tool_response_messages[-1]
                if hasattr(last_tool_msg, 'content'):
                    # If the last tool was about creating files successfully, we can stop
                    if "Successfully created file:" in last_tool_msg.content or "Successfully updated file:" in last_tool_msg.content:
                        should_continue = False
                        self._task_completed = True

            if should_continue:
                try:
                    # Get next response from LLM (still provide tools for continued execution)
                    next_response = self.llm_client.invoke(self.messages, tools=self.tools)
                    self._step_count += 1

                    # Check if this is a completion signal or regular response
                    if hasattr(next_response, 'tool_calls') and next_response.tool_calls:
                        # Continue handling tool calls
                        self.add_message(next_response)
                        return self._handle_tool_calls_sync(next_response)
                    else:
                        # Regular text response - add it and finish
                        self.add_message(next_response)
                        final_output.append(next_response.content)
                        return "\n".join(final_output)
                except Exception as e:
                    # Handle API errors gracefully but don't show them to user if tools were successful
                    if any("Successfully" in str(msg.content) for msg in tool_response_messages):
                        final_output.append("Task completed successfully.")
                    return "\n".join(final_output)

        return "\n".join(final_output)

    async def _handle_tool_calls(self, response: AIMessage) -> str:
        """Handle tool calls in the LLM response asynchronously."""
        self.add_message(response)

        # Process each tool call and create response messages
        tool_response_messages = []
        final_output = []

        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name", "unknown")
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call.get("id", "")

            # Find the tool
            tool = next((t for t in self.tools if t.name == tool_name), None)

            if not tool:
                error_content = f"Tool '{tool_name}' not found"
                final_output.append(f"✗ {tool_name}: {error_content}")
                tool_response_messages.append(
                    ToolMessage(content=error_content, tool_call_id=tool_call_id)
                )
                continue

            try:
                # Execute the tool
                if hasattr(tool, 'arun'):
                    result = await tool.arun(**tool_args)
                else:
                    result = tool.run(**tool_args)

                self._tool_results.append(result)

                # Format output
                if result.success:
                    tool_output = result.output or "Success"
                    final_output.append(f"✓ {tool_name}: {tool_output}")
                else:
                    tool_output = result.error or "Tool execution failed"
                    final_output.append(f"✗ {tool_name}: {tool_output}")

                # Create tool response message
                tool_response_messages.append(
                    ToolMessage(content=tool_output, tool_call_id=tool_call_id)
                )

                # Check if task was completed
                if tool_name == "task_done":
                    self._task_completed = True

            except Exception as e:
                error_content = f"Error executing {tool_name}: {str(e)}"
                final_output.append(f"✗ {tool_name}: {error_content}")
                tool_response_messages.append(
                    ToolMessage(content=error_content, tool_call_id=tool_call_id)
                )

        # Add all tool response messages to conversation
        for tool_msg in tool_response_messages:
            self.add_message(tool_msg)

        # Continue conversation only if there are meaningful tool results and not completed
        if not self._task_completed and self._step_count < self._max_steps and len(tool_response_messages) > 0:
            # Check if we should continue based on the context
            # If the last tool was a file creation or successful completion, consider task done
            should_continue = True
            if tool_response_messages:
                last_tool_msg = tool_response_messages[-1]
                if hasattr(last_tool_msg, 'content'):
                    # If the last tool was about creating files successfully, we can stop
                    if "Successfully created file:" in last_tool_msg.content or "Successfully updated file:" in last_tool_msg.content:
                        should_continue = False
                        self._task_completed = True

            if should_continue:
                try:
                    # Get next response from LLM (still provide tools for continued execution)
                    next_response = await self.llm_client.ainvoke(self.messages, tools=self.tools)
                    self._step_count += 1

                    # Check if this is a completion signal or regular response
                    if hasattr(next_response, 'tool_calls') and next_response.tool_calls:
                        # Continue handling tool calls
                        self.add_message(next_response)
                        return await self._handle_tool_calls(next_response)
                    else:
                        # Regular text response - add it and finish
                        self.add_message(next_response)
                        final_output.append(next_response.content)
                        return "\n".join(final_output)
                except Exception as e:
                    # Handle API errors gracefully but don't show them to user if tools were successful
                    if any("Successfully" in str(msg.content) for msg in tool_response_messages):
                        final_output.append("Task completed successfully.")
                    return "\n".join(final_output)

        return "\n".join(final_output)

    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return next((tool for tool in self.tools if tool.name == name), None)

    def list_available_tools(self) -> List[str]:
        """List names of available tools."""
        return [tool.name for tool in self.tools]

    def save_trajectory(self, filename: Optional[str] = None) -> str:
        """Save the trajectory to a file."""
        if self.trajectory_recorder:
            return self.trajectory_recorder.save(filename)
        return ""