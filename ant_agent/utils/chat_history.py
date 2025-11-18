#!/usr/bin/env python3
"""ChatHistory class for managing conversation messages, decoupled from BaseAgent."""

from typing import List, Optional, Dict, Any
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate

from ant_agent.utils.streaming_trajectory_recorder import StreamingTrajectoryRecorder


# Global instances
chat_history: Optional['ChatHistory'] = None


def initialize_chat_history(trajectory_recorder: Optional[StreamingTrajectoryRecorder] = None) -> None:
    """Initialize global chat_history and trajectory_recorder.
    This function will be called when the module is imported.
    """
    global chat_history

    # This will be configured when BaseAgent is instantiated
    chat_history = ChatHistory(trajectory_recorder=trajectory_recorder)


def reset_chat_history() -> None:
    """Reset global chat history and trajectory recorder."""
    global chat_history, trajectory_recorder

    if chat_history:
        chat_history.clear_all()
    if trajectory_recorder:
        trajectory_recorder.clear()


class ChatHistory:
    """Manages conversation history messages with CRUD operations."""

    def __init__(self, trajectory_recorder: Optional[StreamingTrajectoryRecorder] = None):
        """Initialize ChatHistory.

        Args:
            trajectory_recorder: Optional trajectory recorder for logging messages
        """
        self._messages: List[BaseMessage] = []
        self.trajectory_recorder = trajectory_recorder

    @property
    def messages(self) -> List[BaseMessage]:
        """Get all messages in the conversation history."""
        return self._messages

    @property
    def count(self) -> int:
        """Get the number of messages."""
        return len(self._messages)

    def get_message(self, index: int) -> Optional[BaseMessage]:
        """Get a message at the specified index.

        Args:
            index: The index of the message

        Returns:
            The message at the index, or None if index is out of bounds
        """
        if 0 <= index < len(self._messages):
            return self._messages[index]
        return None

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation history.

        Args:
            message: The message to add
        """
        self._messages.append(message)
        if self.trajectory_recorder:
            self.trajectory_recorder.add_message(message)

    def add_system_message(self, content: str) -> None:
        """Add a system message.

        Args:
            content: The content of the system message
        """
        message = SystemMessage(content=content)
        self.add_message(message)

    def add_human_message(self, content: str) -> None:
        """Add a human/user message.

        Args:
            content: The content of the human message
        """
        message = HumanMessage(content=content)
        self.add_message(message)

    def add_ai_message(self, content: str) -> None:
        """Add an AI/assistant message.

        Args:
            content: The content of the AI message
        """
        message = AIMessage(content=content)
        self.add_message(message)

    def add_tool_message(self, content: str, tool_call_id: str, **additional_kwargs) -> None:
        """Add a tool message.

        Args:
            content: The content of the tool message
            tool_call_id: The ID of the tool call
            **additional_kwargs: Additional keyword arguments
        """
        message = ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            additional_kwargs=additional_kwargs
        )
        self.add_message(message)

    def insert_message(self, index: int, message: BaseMessage) -> None:
        """Insert a message at a specific index.

        Args:
            index: The index to insert at
            message: The message to insert
        """
        if 0 <= index <= len(self._messages):
            self._messages.insert(index, message)
            if self.trajectory_recorder:
                self.trajectory_recorder.add_message(message)

    def update_message(self, index: int, new_content: str) -> bool:
        """Update the content of a message at the specified index.

        Args:
            index: The index of the message to update
            new_content: The new content

        Returns:
            True if the message was updated, False otherwise
        """
        if 0 <= index < len(self._messages):
            message = self._messages[index]
            # Create a new message with updated content
            if isinstance(message, SystemMessage):
                self._messages[index] = SystemMessage(content=new_content)
            elif isinstance(message, HumanMessage):
                self._messages[index] = HumanMessage(content=new_content)
            elif isinstance(message, AIMessage):
                self._messages[index] = AIMessage(content=new_content)
            elif isinstance(message, ToolMessage):
                self._messages[index] = ToolMessage(
                    content=new_content,
                    tool_call_id=message.tool_call_id,
                    additional_kwargs=message.additional_kwargs
                )
            return True
        return False

    def remove_message(self, index: int) -> Optional[BaseMessage]:
        """Remove a message at the specified index.

        Args:
            index: The index of the message to remove

        Returns:
            The removed message, or None if index is out of bounds
        """
        if 0 <= index < len(self._messages):
            return self._messages.pop(index)
        return None

    def remove_last_message(self) -> Optional[BaseMessage]:
        """Remove and return the last message.

        Returns:
            The last message, or None if there are no messages
        """
        if self._messages:
            return self._messages.pop()
        return None

    def remove_last_n_messages(self, n: int) -> List[BaseMessage]:
        """Remove and return the last n messages.

        Args:
            n: Number of messages to remove

        Returns:
            List of removed messages
        """
        removed = []
        for _ in range(min(n, len(self._messages))):
            removed.insert(0, self._messages.pop())
        return removed

    def clear_all(self) -> None:
        """Clear all messages from the conversation history."""
        self._messages.clear()

    def clear_except_system(self) -> None:
        """Clear all messages except system messages."""
        self._messages = [msg for msg in self._messages if isinstance(msg, SystemMessage)]

    def clear_except_last_n(self, n: int) -> None:
        """Clear all messages except the last n messages.

        Args:
            n: Number of messages to keep
        """
        if len(self._messages) > n:
            self._messages = self._messages[-n:]

    def get_system_message(self) -> Optional[SystemMessage]:
        """Get the first system message in the history.

        Returns:
            The first system message, or None if not found
        """
        for msg in self._messages:
            if isinstance(msg, SystemMessage):
                return msg
        return None

    def get_last_message(self) -> Optional[BaseMessage]:
        """Get the last message in the history.

        Returns:
            The last message, or None if there are no messages
        """
        if self._messages:
            return self._messages[-1]
        return None

    def get_last_human_message(self) -> Optional[HumanMessage]:
        """Get the last human message in the history.

        Returns:
            The last human message, or None if not found
        """
        for msg in reversed(self._messages):
            if isinstance(msg, HumanMessage):
                return msg
        return None

    def get_last_ai_message(self) -> Optional[AIMessage]:
        """Get the last AI message in the history.

        Returns:
            The last AI message, or None if not found
        """
        for msg in reversed(self._messages):
            if isinstance(msg, AIMessage):
                return msg
        return None

    def get_message_by_type(self, message_type: type) -> List[BaseMessage]:
        """Get all messages of a specific type.

        Args:
            message_type: The type of message to get (e.g., HumanMessage, AIMessage)

        Returns:
            List of messages of the specified type
        """
        return [msg for msg in self._messages if isinstance(msg, message_type)]

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation history.

        Returns:
            Dictionary containing summary statistics
        """
        total_messages = len(self._messages)
        system_messages = len(self.get_message_by_type(SystemMessage))
        human_messages = len(self.get_message_by_type(HumanMessage))
        ai_messages = len(self.get_message_by_type(AIMessage))
        tool_messages = len(self.get_message_by_type(ToolMessage))

        return {
            "total_messages": total_messages,
            "system_messages": system_messages,
            "human_messages": human_messages,
            "ai_messages": ai_messages,
            "tool_messages": tool_messages
        }

    def search_message_content(self, keyword: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Search for messages containing a keyword.

        Args:
            keyword: The keyword to search for
            case_sensitive: Whether the search should be case sensitive

        Returns:
            List of dictionaries with index and matching messages
        """
        results = []
        for idx, msg in enumerate(self._messages):
            if case_sensitive:
                match = keyword in msg.content
            else:
                match = keyword.lower() in msg.content.lower()
            if match:
                results.append({
                    "index": idx,
                    "message": msg,
                    "type": msg.__class__.__name__
                })
        return results

    def save(self, filename: Optional[str] = None) -> Optional[str]:
        """Save the conversation trajectory to a file."""
        if self.trajectory_recorder:
            return self.trajectory_recorder.save(filename)
        return None

    def to_chat_prompt_template(self) -> ChatPromptTemplate:
        """Convert the message history to a ChatPromptTemplate.

        Returns:
            A ChatPromptTemplate from the messages
        """
        return ChatPromptTemplate.from_messages(self._messages)

    def __len__(self) -> int:
        """Return the number of messages."""
        return len(self._messages)

    def __getitem__(self, index: int) -> BaseMessage:
        """Get a message by index."""
        return self._messages[index]

    def __iter__(self):
        """Iterate over messages."""
        return iter(self._messages)

    def __repr__(self) -> str:
        """String representation of the ChatHistory."""
        summary = self.get_conversation_summary()
        return f"ChatHistory(messages={self.count}, summary={summary})"

