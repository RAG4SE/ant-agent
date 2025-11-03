#!/usr/bin/env python3
"""TodoList manager for intelligent task tracking and workflow management."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class TodoStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class TodoItem:
    id: str
    title: str
    description: str
    status: TodoStatus
    metadata: Dict[str, Any]
    created_at: float
    completed_at: Optional[float] = None


class TodoManager:
    """Manages a dynamic todo list for workflow tracking."""
    
    def __init__(self):
        self.todos: List[TodoItem] = []
        self.current_todo: Optional[TodoItem] = None
        
    def add_todo(self, title: str, description: str = "", metadata: Dict[str, Any] = None) -> TodoItem:
        """Add a new todo item."""
        import time
        import uuid
        
        todo_id = str(uuid.uuid4())[:8]
        todo = TodoItem(
            id=todo_id,
            title=title,
            description=description,
            status=TodoStatus.PENDING,
            metadata=metadata or {},
            created_at=time.time()
        )
        self.todos.append(todo)
        return todo
    
    def get_pending_todos(self) -> List[TodoItem]:
        """Get all pending todos."""
        return [todo for todo in self.todos if todo.status == TodoStatus.PENDING]
    
    def get_in_progress_todos(self) -> List[TodoItem]:
        """Get all in-progress todos."""
        return [todo for todo in self.todos if todo.status == TodoStatus.IN_PROGRESS]
    
    def start_todo(self, todo_id: str) -> bool:
        """Start working on a todo."""
        for todo in self.todos:
            if todo.id == todo_id and todo.status == TodoStatus.PENDING:
                todo.status = TodoStatus.IN_PROGRESS
                self.current_todo = todo
                return True
        return False
    
    def complete_todo(self, todo_id: str) -> bool:
        """Complete a todo."""
        import time
        
        for todo in self.todos:
            if todo.id == todo_id and todo.status == TodoStatus.IN_PROGRESS:
                todo.status = TodoStatus.COMPLETED
                todo.completed_at = time.time()
                if self.current_todo and self.current_todo.id == todo_id:
                    self.current_todo = None
                return True
        return False
    
    def cancel_todo(self, todo_id: str) -> bool:
        """Cancel a todo."""
        for todo in self.todos:
            if todo.id == todo_id:
                todo.status = TodoStatus.CANCELLED
                if self.current_todo and self.current_todo.id == todo_id:
                    self.current_todo = None
                return True
        return False
    
    def get_todo_summary(self) -> Dict[str, Any]:
        """Get a summary of all todos."""
        pending = len([t for t in self.todos if t.status == TodoStatus.PENDING])
        in_progress = len([t for t in self.todos if t.status == TodoStatus.IN_PROGRESS])
        completed = len([t for t in self.todos if t.status == TodoStatus.COMPLETED])
        cancelled = len([t for t in self.todos if t.status == TodoStatus.CANCELLED])
        
        return {
            "total": len(self.todos),
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "cancelled": cancelled,
            "current_todo": self.current_todo.id if self.current_todo else None
        }
    
    def get_todo_prompt_context(self) -> str:
        """Get todo context for system prompt."""
        pending = self.get_pending_todos()
        in_progress = self.get_in_progress_todos()
        
        if not pending and not in_progress:
            return ""
        
        context = "\n\n**CURRENT TODOS:**"
        
        if in_progress:
            context += f"\n🔄 IN PROGRESS: {in_progress[0].title}"
            if in_progress[0].description:
                context += f" - {in_progress[0].description}"
        
        if pending:
            context += "\n📋 NEXT TODOS:"
            for i, todo in enumerate(pending[:3], 1):  # Show up to 3 next todos
                context += f"\n   {i}. {todo.title}"
                if todo.description:
                    context += f" - {todo.description}"
        
        return context
    
    def is_work_complete(self) -> bool:
        """Check if all work is complete."""
        return len(self.get_pending_todos()) == 0 and len(self.get_in_progress_todos()) == 0
    
    def clear_completed(self) -> None:
        """Clear completed todos."""
        self.todos = [todo for todo in self.todos if todo.status != TodoStatus.COMPLETED]