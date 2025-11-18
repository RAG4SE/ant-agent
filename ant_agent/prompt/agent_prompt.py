#!/usr/bin/env python3
"""System prompts for Ant Agent."""

import os
from pathlib import Path
from typing import Optional

from ant_agent.prompt.intelligent_workflow_prompt import (
    SMART_WORKFLOW_PROMPT,
    SOURCE_CODE_ANALYSIS_WITH_LSP,
    CODE_REFACTORING,
    DEBUGGING_ASSISTANCE,
    CODE_REVIEW_AND_QUALITY,
    TESTING_AND_VALIDATION
)


def load_skill_from_file(skill_name: str, skills_dir: str = None) -> Optional[str]:
    """
    Load skill text from markdown file.

    Args:
        skill_name: Name of the skill (without .md extension)
        skills_dir: Directory containing skill files (default: ant_agent/skills)

    Returns:
        Skill text content or None if not found
    """
    if skills_dir is None:
        # Default to ant_agent/skills directory
        current_dir = Path(__file__).parent.parent
        skills_dir = current_dir / 'skills'

    skill_file = Path(skills_dir) / f"{skill_name}.md"

    if skill_file.exists():
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading skill {skill_name} from {skill_file}: {e}")
            return None

    return None

def get_agent_skill(skill_name: str) -> str:
    """
    Get the appropriate system prompt based on the selected skill.

    Args:
        skill_name: Name of the skill to use (without .md extension)

    Returns:
        System prompt text
    """

    # Try to load from file
    skill_text = load_skill_from_file(skill_name)
    if skill_text is not None:
        return skill_text

    raise Exception(f"No skill named {skill_name}")

# Default system prompt (for backward compatibility)
AGENT_SYSTEM_PROMPT = SMART_WORKFLOW_PROMPT