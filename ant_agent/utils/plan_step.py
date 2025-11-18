"""
Structured plan step representation for sequential thinking.

This module provides a dataclass for representing plan steps in a structured format
instead of relying on regex parsing of LLM output.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class PlanStep:
    """Represents a single step in an analysis plan."""

    id: str
    description: str
    status: str = field(default="pending")  # pending, in_progress, completed, blocked
    dependencies: List[str] = field(default_factory=list)
    result: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_in_progress(self) -> None:
        """Mark this step as in progress."""
        self.status = "in_progress"
        if not self.started_at:
            self.started_at = datetime.now()

    def mark_completed(self, result: Optional[str] = None) -> None:
        """Mark this step as completed."""
        self.status = "completed"
        self.result = result
        self.completed_at = datetime.now()

    def mark_blocked(self, reason: str) -> None:
        """Mark this step as blocked."""
        self.status = "blocked"
        self.metadata["blocked_reason"] = reason

    def is_pending(self) -> bool:
        """Check if step is pending."""
        return self.status == "pending"

    def is_in_progress(self) -> bool:
        """Check if step is in progress."""
        return self.status == "in_progress"

    def is_completed(self) -> bool:
        """Check if step is completed."""
        return self.status == "completed"

    def is_blocked(self) -> bool:
        """Check if step is blocked."""
        return self.status == "blocked"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "dependencies": self.dependencies,
            "result": self.result,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_description(cls, description: str, step_id: Optional[str] = None) -> 'PlanStep':
        """Create a PlanStep from a description."""
        if step_id is None:
            import uuid
            step_id = str(uuid.uuid4())[:8]
        return cls(id=step_id, description=description)
