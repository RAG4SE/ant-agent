---
name: code-refactoring
description: Assist with code refactoring tasks including function extraction, variable renaming, and code structure improvements
---

# CODE_REFACTORING

This skill provides intelligent assistance for code refactoring tasks, helping to improve code structure, readability, and maintainability while preserving functionality.

## Core Capabilities

- **Function Extraction**: Identify and extract reusable code blocks into functions
- **Variable Renaming**: Safely rename variables with LSP-based reference updates
- **Code Structure Improvement**: Suggest and implement structural enhancements
- **Dead Code Elimination**: Identify and remove unused code segments
- **Code Duplication Reduction**: Detect and consolidate repeated patterns

## Usage Instructions

To perform code refactoring, follow this systematic approach:

1. **ANALYZE** the existing code structure using LSP tools
2. **IDENTIFY** refactoring opportunities based on code smells and patterns
3. **PLAN** the refactoring approach preserving existing functionality
4. **EXECUTE** changes using appropriate tools (Edit, multilspy, etc.)
5. **VERIFY** changes didn't break functionality by checking references
6. **DOCUMENT** what was refactored and why

## Refactoring Patterns

### Function Extraction
```
When: Code block is repeated or logically cohesive
Steps:
1. Identify the code block to extract
2. Determine parameters and return value
3. Create new function with appropriate name
4. Replace original code with function call
5. Update all occurrences if duplicated
```

### Variable Renaming
```
When: Variable names are unclear or misleading
Steps:
1. Use multilspy to find all references
2. Rename variable consistently across all occurrences
3. Update comments and documentation
4. Verify no naming conflicts introduced
```

### Code Structure Improvement
```
When: Code organization hinders readability
Steps:
1. Analyze current structure with LSP tools
2. Identify better organization patterns
3. Reorganize while maintaining functionality
4. Update imports and dependencies
```

## Technical Requirements

**Required Tools**:
- `multilspy_python_references` - Find all references to symbols
- `Edit` - Make code changes safely
- `Read` - Analyze existing code structure
- `Grep` - Search for patterns and duplicates
- `task_done` - Complete refactoring tasks

**Safety Checks**:
- Always backup or verify changes can be reverted
- Test that functionality is preserved
- Check for import/dependency issues
- Validate reference updates are complete

## Examples

**Function Extraction**:
```
User: "Extract the validation logic into a separate function"
→ Analyze code block to extract
→ Create new function with proper parameters
→ Replace original code with function call
→ Update function documentation
→ Verify all references are correct
```

**Variable Renaming**:
```
User: "Rename 'temp' variable to something more descriptive"
→ Find all references using multilspy
→ Choose appropriate descriptive name
→ Update all occurrences consistently
→ Update related comments
→ Verify no conflicts
```

**Code Organization**:
```
User: "This class is too large, can we split it?"
→ Analyze class responsibilities
→ Identify cohesive sub-components
→ Extract into separate classes/modules
→ Update imports and dependencies
→ Maintain existing interface if public
```

## Decision Tree

```
Refactoring request → What type of refactoring?
    ├─ Function extraction → Identify block → Extract → Replace → Verify → Done
    ├─ Variable renaming → Find references → Rename all → Update docs → Verify → Done
    ├─ Structure improvement → Analyze → Plan reorganization → Execute → Verify → Done
    └─ General cleanup → Identify issues → Apply fixes → Verify → Document → Done
```

## Safety Guidelines

**Before Refactoring**:
- Understand the complete codebase context
- Identify all affected references and dependencies
- Plan rollback strategy if issues arise

**During Refactoring**:
- Make incremental changes when possible
- Verify each change maintains functionality
- Update documentation and comments

**After Refactoring**:
- Test that functionality is preserved
- Verify no new issues introduced
- Document what was changed and why

## Key Principles

1. **FUNCTIONALITY PRESERVATION**: Never change external behavior during refactoring
2. **INCREMENTAL CHANGES**: Prefer small, verifiable changes over large rewrites
3. **LSP ASSISTANCE**: Use language server tools for safe, accurate changes
4. **DOCUMENTATION**: Always document refactoring decisions and rationale
5. **TESTING MINDSET**: Verify changes don't break existing functionality

**SUCCESS = IMPROVED CODE QUALITY + PRESERVED FUNCTIONALITY**
**FAILURE = BROKEN CODE + LOST FUNCTIONALITY**