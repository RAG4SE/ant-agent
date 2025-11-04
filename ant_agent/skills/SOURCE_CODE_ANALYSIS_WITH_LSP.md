---
name: source-code-analysis-with-lsp
description: Use LSP tools to analyze code structure, find definitions, and show complete source code of functions/classes
---

# SOURCE_CODE_ANALYSIS_WITH_LSP

Intelligent code analysis using Language Server Protocol (LSP) tools to locate and display complete source code.

## Core Capabilities

- **Definition Lookup**: Use LSP tools to find exact function/class definitions
- **Source Code Display**: Show complete implementations, not just locations
- **Intelligent Validation**: position_finder validates LLM suggestions automatically
- **Progressive Search**: ±3 lines → ±5 lines when initial position is wrong

## Quick Workflow

1. **Check JSON format**: If user requests JSON, prepare exact JSON output
2. **Read file**: Get complete content with bash
3. **Validate position**: Use position_finder with intelligent validation
4. **Find definition**: Use multilspy with validated coordinates
5. **Show code**: Display complete source implementation
6. **Format output**: Return JSON first (if requested), then call task_done

**CRITICAL: JSON format must be returned IMMEDIATELY if requested, before any analysis!**

**JSON Output Enforcement:**
- **Before any analysis text** → Output requested JSON format
- **No "Analysis:", "Result:", "Finding:"** before JSON
- **Direct JSON output** → `{"answer": "no"}`
- **Then task_done with same JSON** → `task_done:0 {"summary": "{"answer": "no"}"}`

**STEP 6A: JSON Output (if requested)**
```
# If user requested JSON format:
→ Output EXACT JSON: {"answer": "no"}
→ Then call task_done: task_done:1 {"summary": "{"answer": "no"}"}

# If user did NOT request JSON:
→ Proceed with standard analysis and task_done
```

## position_finder Usage

**New intelligent position_finder:**
```bash
# 1. Read file content
bash:0 {"command": "cat contracts/DataManager.sol"}

# 2. Use position_finder with validation
position_finder:1 {"file_path": "contracts/DataManager.sol", "file_content": "<complete_content>", "line_number": 24, "line_content": "mapping(uint256 => StorageInfo) private storages;", "target": "StorageInfo"}

# 3. Handle results:
# SUCCESS → Use lsp_coordinates directly
# ERROR → Follow suggested_action, use bash grep
```

## Success Criteria

**MANDATORY:**
- ✓ Show COMPLETE source code (multiple lines)
- ✗ Never stop after just finding position

**Format Rules:**
- **JSON requests**: Return EXACT JSON first, then task_done with same JSON
- **Standard requests**: Call task_done after showing source code

**CRITICAL JSON FORMAT ENFORCEMENT:**
When user requests JSON format (e.g., "Return in JSON: {"answer": "yes or no"}"):
1. **IMMEDIATELY** return the exact JSON structure - NO text before it
2. **NO analysis or explanation** before the JSON output
3. **Use the SAME JSON** in task_done summary parameter
4. **Example**: User says "Return JSON: {"answer": "yes"}" → You output: `{"answer": "yes"}` then `task_done:0 {"summary": "{"answer": "yes"}"}`

## Technical Requirements

**Tools:**
- `multilspy*_definition` - LSP definition lookup
- `position_finder` - Intelligent position validation
- `bash` - File operations and code display
- `task_done` - Complete analysis
- `sequential_thinking` - Complex problem solving

**position_finder features:**
- Validates LLM suggestions against file content
- Auto-search ±3 → ±5 lines when wrong
- Guaranteed accurate 0-based coordinates
- Clear error messages with bash fallback

## JSON Format Checklist

**Before returning any result, check if JSON format was requested:**

- [ ] **Did user mention "JSON"?** Look for: "JSON", "json", "{" in request
- [ ] **If YES** → Return EXACT JSON first, no text before it
- [ ] **Use same JSON** in task_done summary parameter
- [ ] **If NO** → Proceed with standard analysis format

**Example JSON detection:**
```
User: "Return in JSON: {"answer": "yes or no"}"
→ IMMEDIATELY output: {"answer": "no"}
→ Then call: task_done:0 {"summary": "{"answer": "no"}"}
```

**CRITICAL EXECUTION STEPS:**
1. **Before any analysis** → Check if JSON requested
2. **If JSON requested** → Output EXACT JSON immediately
3. **No text before JSON** → No "Analysis:", "Result:", etc.
4. **Use same JSON in task_done** → Copy exact structure to summary parameter

## Error Handling

When position_finder returns ERROR:
1. Follow `suggested_action` immediately
2. Use provided bash grep command
3. Analyze all occurrences
4. Continue with bash-found location

## Key Principles

1. **JSON FIRST**: When JSON format requested, output it immediately before any analysis
2. **TRUST position_finder**: Use validated coordinates directly
3. **FOLLOW ERRORS**: Use suggested bash commands when it fails
4. **SHOW COMPLETE CODE**: Always display full implementations
5. **PROVIDE INSIGHTS**: Give meaningful code analysis

## CRITICAL REMINDERS

**FOR JSON FORMAT REQUESTS:**
- **NEVER** call task_done without first outputting the JSON
- **ALWAYS** output JSON before any analysis text
- **COPY EXACT** JSON structure to task_done summary
- **NO EXCEPTIONS** - This is mandatory for all JSON requests
