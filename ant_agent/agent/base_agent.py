#!/usr/bin/env python3
"""New generic Base Agent for Ant Agent - completely rewritten to be general-purpose."""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence
import logging
import os

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from ant_agent.clients.llm_client import LLMClient
from ant_agent.prompt.agent_prompt import get_agent_skill
from ant_agent.clients.enhanced_llm_client import EnhancedLLMClient, create_enhanced_client
from ant_agent.tools.base import AntTool, AntToolResult
from ant_agent.utils.config import AppConfig, LLMProvider
from ant_agent.utils.streaming_trajectory_recorder import StreamingTrajectoryRecorder
from ant_agent.utils.plan_manager import plan_manager, PlanNode
from ant_agent.utils.chat_history import ChatHistory

logger = logging.getLogger(__name__)

class BaseAgent():
    """Completely generic base agent class - no hardcoded file names or specific logic."""

    def __init__(
        self,
        app_config: AppConfig,
        **kwargs: Any,
    ):
        """Initialize the base agent.

        Args:
            app_config: Application configuration (AppConfig) containing all settings
            **kwargs: Additional keyword arguments
        """
        # Handle trajectory recorder selection
        if app_config.trajectory.enabled:
            # New streaming mode
            trajectory_recorder = StreamingTrajectoryRecorder(
                config=app_config.trajectory,
                stream_output=True,
                pretty_print=True,
                real_time_save=True,
            )
        else:
            # No trajectory recording
            trajectory_recorder = None
        # Extract configurations from AppConfig
        self.app_config = app_config

        self.llm_client = create_enhanced_client(
            primary_config=app_config.model,
            retry_strategy="exponential",  # Use exponential backoff
            max_retries=15,  # Increase max retries
            base_delay=2.0,  # Start with 2 second delay
            max_delay=120.0,  # Cap at 2 minutes
            exponential_base=2.0,
            jitter=True,  # Add random jitter
            circuit_breaker_threshold=3,  # Open circuit after 3 failures
            circuit_breaker_timeout=300  # 5 minute timeout
        )

        self._kwargs = kwargs

        system_prompt = SystemMessage(self._get_system_prompt())
        # from ant_agent.utils.chat_history import initialize_chat_history
        # initialize_chat_history(trajectory_recorder)
        # from ant_agent.utils.chat_history import chat_history
        self.chat_history = ChatHistory(trajectory_recorder=trajectory_recorder)
        self.chat_history.add_message(system_prompt)

        # Create LSP manager from LSP config if enabled
        if app_config.lsp.enabled:
            from ant_agent.lsp.multilspy_manager import get_lsp_manager
            self.lsp_manager = get_lsp_manager(app_config.lsp)
        else:
            self.lsp_manager = None

        # Initialize basic state first
        self._step_count = 0
        self._task_completed = False
        self._max_steps = app_config.agent.max_steps
        self._tools = self._initialize_tools()

        # Token management settings from config
        self._context_window_limit = app_config.model.context_window_size
        self._token_threshold = int(self._context_window_limit * app_config.model.token_threshold_ratio)
        self._enable_token_management = app_config.model.enable_token_management
        
    @property
    def tools(self) -> List[BaseTool]:
        """Get the list of available tools."""
        return self._tools

    @property
    def messages(self) -> List[BaseMessage]:
        """Get the conversation history."""
        return self.chat_history.messages

    @property
    def task_completed(self) -> bool:
        """Check if the task is completed."""
        return self._task_completed

    def _generate_intelligent_continuation_prompt(self) -> str:
        """Generate an intelligent continuation prompt based on current plan state with streaming."""
        if not plan_manager.has_active_plans():
            # Fallback to simple prompt if no plans or tracking disabled
            return "Continue with the next step of the analysis. If you have completed the full analysis, call task_done with a comprehensive summary."

        intelligent_prompt = plan_manager.generate_continuation_prompt()
        # if intelligent_prompt.startswith("Now the current plan step is Descend"):
        #     self.chat_history._messages = self.chat_history._messages[:1] # Keep the system message

        return intelligent_prompt

    def _extract_sequential_thinking_plan(self, tool_result: Optional[AntToolResult]) -> Optional[Dict[str, Any]]:
        """Extract plan information from sequential_thinking tool result.

        Args:
            tool_result: The result from sequential_thinking tool execution.

        Returns:
            Optional[Dict[str, Any]]: Plan info with description and steps, or None if no plan found.
        """
        if not tool_result or not tool_result.success:
            return None

        # Try to get structured plan steps from metadata first
        metadata = tool_result.metadata or {}
        if "plan_steps_created" in metadata and metadata.get("plan_steps"):
            # Use structured plan steps from metadata
            plan_steps = metadata["plan_steps"]
            steps = [f"Step {i+1}: {step['description']}" for i, step in enumerate(plan_steps)]

            return {
                "description": "Analysis plan",
                "steps": steps
            }

        if "plan_steps_created" not in metadata:
            raise ValueError(f"plan_steps_created not in metadata: {metadata}")
        
        raise ValueError(f"plan_steps not in metadata: {metadata}")

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation history."""
        self.chat_history.add_message(message)

        # Check token limit every time a message is added
        if self._enable_token_management and hasattr(message, 'usage_metadata') and message.usage_metadata and "total_tokens" in message.usage_metadata:
            if message.usage_metadata["total_tokens"] > self._token_threshold:
                self.compress_memory()


    def reset(self) -> None:
        """Reset the agent state."""
        system_prompt = self._get_system_prompt()
        self.chat_history.clear_all()
        self.chat_history.add_message(system_prompt)
        self._step_count = 0
        self._task_completed = False


    def reset_plan_state(self) -> None:
        """Reset plan tracking state for a new task."""
        plan_manager.clear_all_plans()

    async def arun(self, user_input: str) -> str:
        """Run the agent asynchronously with user input."""
        # Reset plan state for new task
        self.reset_plan_state()

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

        await self._handle_tool_calls(response)

        while not self._task_completed and self._step_count < self._max_steps:
            # Generate intelligent continuation prompt based on plan state
            continuation_prompt = self._generate_intelligent_continuation_prompt()
            self.add_message(HumanMessage(content=continuation_prompt))
            # Continue the conversation
            self._step_count += 1
            continue_response = await self.llm_client.ainvoke(
                self.messages,
                tools=self.tools,
            )
            continue_tool_calls = getattr(continue_response, 'tool_calls', None)
            if continue_tool_calls:
                result = await self._handle_tool_calls(continue_response)
                if self._task_completed:
                    return result
            else:
                self.add_message(continue_response)
                if self._task_completed:
                    return continue_response.content
                continue

        raise RuntimeError("Cannot reach the task_done status after exceeding _max_steps")


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
        tool_calls = getattr(response, 'tool_calls', None)
        if tool_calls:
            return self._handle_tool_calls_sync(response)
        else:
            # Regular text response
            self.add_message(response)
            return response.content

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> AntToolResult:
        """Execute a tool asynchronously."""
        # Find the tool
        tool = next((t for t in self.tools if t.name == tool_name), None)

        if not tool:
            return AntToolResult(
                success=False,
                output="",
                error=f"Tool '{tool_name}' not found"
            )

        try:
            # Execute the tool - pass arguments as kwargs to match AntTool interface
            result = await tool.arun(**tool_args)
            

            # Record tool execution in trajectory
            # if self.trajectory_recorder:
            #     self.trajectory_recorder.add_tool_result(result)

            return result

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise
            return AntToolResult(
                success=False,
                output="",
                error=f"Error executing {tool_name}: {str(e)}"
            )

    async def _handle_tool_calls(self, response: AIMessage) -> str:
        """Handle tool calls in the LLM response asynchronously with plan extraction."""
        # IMPORTANT: Add the assistant message first, before processing tool calls
        self.add_message(response)
        if response.tool_calls is None or response.tool_calls == []:
            return ""

        # Process each tool call and create response messages
        tool_response_messages = []
        final_output = []


        # Required by openai, even if the tool_calls are empty, there must be a tool response.
        # if response.tool_calls == []:
        #     tool_response_messages.append(
        #         ToolMessage(
        #             content="",
        #             tool_call_id = "",
        #         )
        #     )

        # Create a ToolMessage for EVERY tool_call to maintain proper message sequence
        # This ensures that an assistant message with tool_calls is ALWAYS followed by
        # the corresponding number of ToolMessages (even if some are empty/error responses)
        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name", "unknown")
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call.get("id", "")


            try:
                # Execute the tool
                tool_result = await self._execute_tool(tool_name, tool_args)

                # Create tool response message
                tool_response = ToolMessage(
                    content=str(tool_result.output),
                    tool_call_id=tool_call_id,
                    additional_kwargs={
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "tool_result": tool_result.output,
                        "success": tool_result.success,
                        "error": tool_result.error
                    }
                )

                tool_response_messages.append(tool_response)
                final_output.append(str(tool_result.output))

                # Check if task_done was called - but don't break!
                # We must create ToolMessages for all remaining tool_calls
                if tool_name == "task_done":
                    self._task_completed = True
                    break

            except Exception as e:
                import traceback
                traceback.print_exc()
                raise
                error_msg = f"Error executing tool {tool_name}: {str(e)}"
                error_response = ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_call_id,
                    additional_kwargs={"error": str(e), "tool_name": tool_name}
                )
                tool_response_messages.append(error_response)
                final_output.append(error_msg)

        # Add all tool response messages to conversation
        for msg in tool_response_messages:
            self.add_message(msg)

        # Return combined output
        return "\n".join(final_output) if final_output else "Tool execution completed."

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
        from ant_agent.tools.bash_tool import BashTool, TempDirBash, SourceDirBash
        # from ant_agent.tools.edit_tool import EditTool, CreateFileTool
        from ant_agent.tools.thinking_tool import SequentialThinkingTool
        from ant_agent.tools.task_done_tool import TaskDoneTool
        from ant_agent.tools.step_complete_tool import StepCompleteTool
        from ant_agent.tools.plan_complete_tool import PlanCompleteTool
        from ant_agent.tools.memory_tool import MemoryStoreTool, MemorySearchTool
        from ant_agent.tools.line_number_prefix_tool import RemoveAllLineNumberedTempFiles, CreateLineNumberedTempFile, temp_dir
        from ant_agent.tools.position_finder_tool import PositionFinderTool
        # from ant_agent.tools.replan_tool import ReplanTool

        # Get working directory from app_config if available
        working_dir = getattr(self, 'app_config', None) and self.app_config.working_dir or None
        working_dir = os.path.abspath(working_dir)
        logger.debug(f"working_dir is {working_dir}")
        
        tools = [
            TempDirBash(working_dir=temp_dir),
            SourceDirBash(working_dir=working_dir),
            # EditTool(),
            # CreateFileTool(),
            SequentialThinkingTool(),
            TaskDoneTool(),
            StepCompleteTool(),
            # PlanCompleteTool(),
            MemoryStoreTool(),
            # MemorySearchTool(),
            # ReplanTool(),
            # RemoveAllLineNumberedTempFiles(),
            CreateLineNumberedTempFile(working_dir=working_dir),
            PositionFinderTool(working_dir=working_dir)
        ]
        
        if self.lsp_manager:
            lsp_tools = self.lsp_manager.get_available_tools()
            tools.extend(lsp_tools)
        
        return tools

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent.

        This method must be implemented by subclasses.
        """
        """Get the system prompt for Ant Agent based on configured skill."""
        return get_agent_skill(self.app_config.agent.skill) 

    def get_tool_by_name(self, name: str) -> Optional[AntTool]:
        """Get a tool by name."""
        return next((tool for tool in self.tools if tool.name == name), None)

    def compress_memory(self) -> None:
        """Compress conversation history using intelligent prompt-based compression."""
        try:
            # Load compression prompt from skill file
            compression_prompt = get_agent_skill("MEMORY_COMPRESSION")


            ready_to_compressed_contents = "\n".join(self.chat_history.messages[1:-15]) # do not count the first message (system message) or the latest 15 messages
            compress_messages = [
                SystemMessage(compression_prompt),
                HumanMessage(f"Below are the messages that are to be compressed:\n{ready_to_compressed_contents}")
            ]
            compressed_content = self.llm_client.ainvoke(
                messages=compress_messages
            )

            # Keep the latest 15 messages for context
            latest_messages = self.chat_history.messages[-15:] if len(self.chat_history.messages) > 15 else self.chat_history.messages

            # Get system prompt
            system_prompt = self._get_system_prompt()

            # Clear all messages and rebuild with compressed content
            self.chat_history.clear_all()

            # Add system prompt
            self.chat_history.add_message(system_prompt)

            # Add compressed memory as system message
            compressed_content = f"[Previous Conversation Compressed]\n\n{compressed_content.content}[Below are the latest dialogues]"
            self.chat_history.add_message(AIMessage(compressed_content))

            # Add back the latest 15 messages
            for msg in latest_messages:
                self.chat_history.add_message(msg)

            logger.info(f"Compressed {len(self.chat_history.messages[1:-15])} messages, kept latest {len(latest_messages)} messages")

        except Exception as e:
            logger.error(f"Failed to compress history: {e}")
            # Fallback: just clear non-system messages and add notification
            system_messages = self.chat_history.get_message_by_type(SystemMessage)
            self.chat_history.clear_all()
            for sys_msg in system_messages:
                self.chat_history.add_message(sys_msg)
            self.chat_history.add_message("[History compressed - previous conversation archived]")

    @property
    def step_count(self) -> int:
        """Get the current step count."""
        return self._step_count

    @property
    def max_steps(self) -> int:
        """Get the maximum step count."""
        return self._max_steps