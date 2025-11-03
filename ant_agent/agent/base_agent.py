#!/usr/bin/env python3
"""New generic Base Agent for Ant Agent - completely rewritten to be general-purpose."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from ant_agent.clients.llm_client import LLMClient
from ant_agent.tools.base import AntTool, AntToolResult
from ant_agent.utils.config import AppConfig
from ant_agent.utils.trajectory_recorder import TrajectoryRecorder


class BaseAgent(ABC):
    """Completely generic base agent class - no hardcoded file names or specific logic."""

    def __init__(
        self,
        app_config: AppConfig,
        trajectory_recorder: Optional[TrajectoryRecorder] = None,
        **kwargs: Any,
    ):
        """Initialize the base agent.

        Args:
            app_config: Application configuration (AppConfig) containing all settings
            trajectory_recorder: Optional trajectory recorder
            **kwargs: Additional keyword arguments
        """
        # Extract configurations from AppConfig
        self.app_config = app_config
        self.llm_client = LLMClient(app_config.model)
        self.trajectory_recorder = trajectory_recorder
        self._kwargs = kwargs
        
        # Initialize basic state first
        self._messages = []
        self._tool_results = []
        self._step_count = 0
        self._task_completed = False
        self._max_steps = app_config.agent.max_steps
        self._tools = self._initialize_tools()

        # Set the initial system prompt
        self._messages = [SystemMessage(content=self._get_system_prompt())]
        


    @property
    def tools(self) -> List[BaseTool]:
        """Get the list of available tools."""
        return self._tools

    @property
    def messages(self) -> List[BaseMessage]:
        """Get the conversation history."""
        return self._messages

    @property
    def task_completed(self) -> bool:
        """Check if the task is completed."""
        return self._task_completed

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation history."""
        self._messages.append(message)
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
            return f"Maximum step limit ({self._max_steps}) reached. Please provide a more specific task."

        self._step_count += 1

        # Get response from LLM with tools
        response = await self.llm_client.ainvoke(
            self.messages,
            tools=self.tools,
        )

        # Handle tool calls if present
        if hasattr(response, 'tool_calls') and response.tool_calls:
            result = await self._handle_tool_calls(response)

            # Continue processing until task is completed or max steps reached
            while not self._task_completed and self._step_count < self._max_steps:
                # Add a gentle prompt to continue if the task seems incomplete
                continuation_prompt = "Continue with the next step of the analysis. If you have completed the full analysis, call task_done with a comprehensive summary."
                self.add_message(HumanMessage(content=continuation_prompt))

                # Continue the conversation
                self._step_count += 1
                continue_response = await self.llm_client.ainvoke(
                    self.messages,
                    tools=self.tools,
                )

                if hasattr(continue_response, 'tool_calls') and continue_response.tool_calls:
                    result = await self._handle_tool_calls(continue_response)
                else:
                    self.add_message(continue_response)
                    if self._task_completed:
                        return continue_response.content
                    # If no tool calls and task not completed, continue the loop
                    continue

            return result
        else:
            # Regular text response
            self.add_message(response)

            # Continue processing until task is completed or max steps reached
            while not self._task_completed and self._step_count < self._max_steps:
                continuation_prompt = "Continue with the analysis. If you have completed the full analysis, call task_done with a comprehensive summary."
                self.add_message(HumanMessage(content=continuation_prompt))

                self._step_count += 1
                continue_response = await self.llm_client.ainvoke(
                    self.messages,
                    tools=self.tools,
                )

                if hasattr(continue_response, 'tool_calls') and continue_response.tool_calls:
                    return await self._handle_tool_calls(continue_response)
                else:
                    self.add_message(continue_response)
                    if self._task_completed:
                        return continue_response.content
                    # If no tool calls and task not completed, continue the loop
                    continue

            return response.content

    def run(self, user_input: str) -> str:
        """Run the agent synchronously with user input."""
        # Add user message
        self.add_message(HumanMessage(content=user_input))

        # Check step limit
        if self._step_count >= self._max_steps:
            return f"Maximum step limit ({self._max_steps}) reached. Please provide a more specific task."

        self._step_count += 1

        # Get response from LLM with tools
        response = self.llm_client.invoke(
            self.messages,
            tools=self.tools,
        )

        # Handle tool calls if present
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return self._handle_tool_calls_sync(response)
        else:
            # Regular text response
            self.add_message(response)
            return response.content

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

            except Exception as e:
                error_content = f"Error executing {tool_name}: {str(e)}"
                final_output.append(f"✗ {tool_name}: {error_content}")
                tool_response_messages.append(
                    ToolMessage(content=error_content, tool_call_id=tool_call_id)
                )

        # Add all tool response messages to conversation
        for tool_msg in tool_response_messages:
            self.add_message(tool_msg)

        # Check if task was completed
        if any(tool_call.get("name") == "task_done" for tool_call in response.tool_calls):
            self._task_completed = True



        # Return formatted output
        return "\n".join(final_output)

    def _handle_tool_calls_sync(self, response: AIMessage) -> str:
        """Handle tool calls in the LLM response synchronously."""
        # For now, just delegate to async version
        # In a real implementation, this would use sync tool execution
        import asyncio
        return asyncio.run(self._handle_tool_calls(response))

    def _initialize_tools(self) -> List[BaseTool]:
        """Initialize the tools for the agent.
        
        This method should be overridden by subclasses to provide specific tools.
        """
        # Default minimal tool set - subclasses should override this
        from ant_agent.tools.bash_tool import BashTool
        from ant_agent.tools.edit_tool import EditTool, CreateFileTool
        from ant_agent.tools.thinking_tool import SequentialThinkingTool
        from ant_agent.tools.task_done_tool import TaskDoneTool
        
        return [
            BashTool(),
            EditTool(),
            CreateFileTool(),
            SequentialThinkingTool(),
            TaskDoneTool(),
        ]

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent.

        This method must be implemented by subclasses.
        """
        pass
    


    def get_tool_by_name(self, name: str) -> Optional[AntTool]:
        """Get a tool by name."""
        return next((tool for tool in self.tools if tool.name == name), None)

    def get_thinking_summary(self) -> str:
        """Get a summary of the thinking process."""
        thinking_tool = self.get_tool_by_name("sequential_thinking")
        if thinking_tool:
            return thinking_tool.get_thinking_summary()
        return "No thinking process recorded."

    def save_trajectory(self, filename: Optional[str] = None) -> Optional[str]:
        """Save the conversation trajectory to a file."""
        if self.trajectory_recorder:
            return self.trajectory_recorder.save(filename)
        return None

    def get_trajectory_summary(self) -> Dict[str, Any]:
        """Get a summary of the trajectory."""
        if self.trajectory_recorder:
            return self.trajectory_recorder.get_summary()
        return {}
    


    @property
    def step_count(self) -> int:
        """Get the current step count."""
        return self._step_count

    @property
    def max_steps(self) -> int:
        """Get the maximum step count."""
        return self._max_steps