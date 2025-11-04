---
name: source-code-analysis-with-lsp
description: Use LSP tools to analyze code structure, find definitions, and show complete source code of functions/classes
---

# SOURCE_CODE_ANALYSIS_WITH_LSP

This skill enables intelligent code analysis using Language Server Protocol (LSP) tools to locate and display complete source code of functions, classes, and identifiers.

## Core Capabilities

- **Code Structure Analysis**: Understand natural language requests about code
- **Definition Lookup**: Use LSP tools to find exact function/class definitions
- **Source Code Display**: Show complete implementations, not just locations
- **Intelligent Extraction**: Parse natural language to extract file names, line numbers, and function names

## Usage Instructions

To analyze code and show function/class definitions, follow this workflow:

1. **UNDERSTAND** the user's request - identify the target function/class and file
2. **LOCATE** the exact position using parsing, analysis, or position_finder tools, remind that position_finder takes in 0-based line number.
3. **INSPECT AND RELOCATE** check if the target really lies in the position suggested by position_finder, if not, search around the position to fetch for the true position.
4. **FIND** the definition using multilspy_python_definition with precise coordinates
5. **SHOW** the complete source code using bash to display the actual function
6. **COMPLETE** by calling task_done only after showing the actual code

## Critical Requirements

**MANDATORY SUCCESS CRITERIA**:
- ✓ Show the COMPLETE source code of the function
- ✓ Display multiple lines to show the full implementation
- ✗ NEVER stop after just finding position/location

**FAILURE = INCOMPLETE**: Only showing location without source code
**SUCCESS = COMPLETE**: Showing the actual function implementation

## Output Format Rules

**CRITICAL FORMAT CHECK**:
- If user explicitly requested JSON format (e.g., "Return in JSON: {"source code": <source_code>}"), FIRST return the exact JSON format they requested
- Only AFTER returning the requested format, call task_done to complete the task
- **IMPORTANT**: When calling task_done after returning JSON, use the SAME JSON format in the task_done summary - do not create a new plain text summary
- If no specific format requested, call task_done after showing the source code

## Technical Requirements

**Required Tools**:
- `multilspy*_definition` - Find definitions using LSP of different languages
- `position_finder` - Get precise coordinates for LSP tools
- `bash` - Display source code files
- `task_done` - Complete the analysis task
- `sequential_thinking` - Think step-by-step to solve complex problems 

**Position Accuracy**:
- LSP tools require 0-based line and character positions
- If you cannot determine accurate coordinates, use position_finder to get precise location data

## Key Principles

1. **AUTONOMOUS EXECUTION**: Analyze requests and execute all necessary steps independently
2. **MULTI-STEP WORKFLOW**: Continue taking actions until analysis is complete
3. **COMPLETION CRITERIA**: Only call task_done when fully answering the user's question
4. **POSITION ACCURACY**: Use position_finder when LSP coordinates are unclear
5. **REPOSITORY ANALYSIS**: Provide meaningful insights about codebase purpose and structure
