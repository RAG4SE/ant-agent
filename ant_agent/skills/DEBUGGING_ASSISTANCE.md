---
name: debugging-assistance
description: Provide comprehensive debugging assistance including error analysis, breakpoint suggestions, and step-by-step debugging workflows
---

# DEBUGGING_ASSISTANCE

This skill provides systematic debugging assistance for identifying, analyzing, and resolving code issues using various debugging tools and techniques.

## Core Capabilities

- **Error Analysis**: Parse and interpret error messages, stack traces, and exceptions
- **Breakpoint Suggestions**: Recommend strategic breakpoint locations
- **Variable Inspection**: Help examine variable states and data flow
- **Code Tracing**: Assist with step-by-step execution analysis
- **Root Cause Identification**: Systematically narrow down issue sources

## Usage Instructions

To provide debugging assistance, follow this systematic debugging workflow:

1. **GATHER** error information, stack traces, and context
2. **ANALYZE** the error type, location, and potential causes
3. **LOCATE** the problematic code using LSP tools
4. **INSPECT** variable states and execution flow
5. **SUGGEST** debugging strategies and breakpoint locations
6. **VERIFY** potential fixes and test solutions

## Debugging Methodology

### Error Analysis Process
```
When: User encounters error messages or exceptions
Steps:
1. Parse error message for type, location, and details
2. Identify the failing code section using LSP
3. Analyze potential causes based on error type
4. Suggest investigation strategies
5. Recommend debugging tools and techniques
```

### Breakpoint Strategy
```
When: User needs to debug execution flow
Steps:
1. Analyze code structure and execution paths
2. Identify key variables and state changes
3. Suggest strategic breakpoint locations
4. Recommend variable inspection points
5. Provide step-through debugging guidance
```

### Variable Inspection
```
When: User needs to understand data state
Steps:
1. Identify relevant variables and data structures
2. Suggest inspection points in execution
3. Recommend data formatters and viewers
4. Help trace data flow and modifications
```

## Technical Requirements

**Required Tools**:
- `multilspy_python_definition` - Navigate to error locations
- `multilspy_python_references` - Find related code sections
- `Read` - Examine code and variable declarations
- `Bash` - Execute debugging commands and scripts
- `Grep` - Search for error patterns and related code
- `task_done` - Complete debugging assistance

**Debugging Tools Integration**:
- Python debugger (pdb) integration
- Logging analysis and interpretation
- Stack trace parsing and explanation
- Variable state examination techniques

## Examples

**Error Message Analysis**:
```
User: "I'm getting AttributeError: 'NoneType' object has no attribute 'process'"
→ Parse error type and attribute details
→ Find the problematic line using LSP
→ Analyze why object might be None
→ Suggest null checks or initialization fixes
→ Recommend debugging prints or breakpoints
```

**Stack Trace Interpretation**:
```
User: "Help me understand this stack trace"
→ Parse stack trace for call sequence
→ Identify the root failure point
→ Navigate to each frame in the trace
→ Explain the execution path that led to error
→ Suggest where to add debugging information
```

**Debugging Strategy**:
```
User: "My function is returning unexpected results"
→ Analyze function logic and expected behavior
→ Suggest breakpoint locations at key decisions
→ Recommend variable inspection points
→ Help trace execution path
→ Suggest test cases to isolate the issue
```

## Decision Tree

```
Debugging request → What type of debugging help?
    ├─ Error analysis → Parse error → Locate code → Analyze cause → Suggest fix → Done
    ├─ Breakpoint help → Analyze code → Suggest locations → Explain strategy → Done
    ├─ Variable inspection → Identify variables → Suggest inspection points → Help interpret → Done
    └─ General debugging → Understand issue → Recommend approach → Guide through process → Done
```

## Debugging Strategies

### Systematic Approach
1. **Reproduce the Issue**: Ensure consistent reproduction
2. **Isolate the Problem**: Narrow down to minimal failing case
3. **Examine State**: Inspect variables and execution context
4. **Trace Execution**: Follow code path to understand behavior
5. **Test Hypotheses**: Verify potential causes and solutions

### Common Debugging Techniques
- **Print Debugging**: Strategic logging and output
- **Breakpoint Debugging**: Step-through execution analysis
- **Binary Search**: Divide and conquer approach
- **Rubber Ducking**: Explain code to identify issues
- **Logging Analysis**: Interpret application logs

## Error Categories and Approaches

**Syntax Errors**:
- Parse error messages for line numbers
- Check for typos and missing symbols
- Verify indentation and structure

**Runtime Errors**:
- Analyze stack traces for call sequences
- Check variable initialization and state
- Examine exception handling

**Logic Errors**:
- Compare expected vs actual behavior
- Trace execution paths
- Verify algorithm correctness

**Performance Issues**:
- Identify bottlenecks using profiling
- Analyze algorithmic complexity
- Check for inefficient operations

## Key Principles

1. **SYSTEMATIC APPROACH**: Follow structured debugging methodology
2. **EVIDENCE-BASED**: Make hypotheses based on observed behavior
3. **ISOLATION**: Narrow down to minimal reproducible cases
4. **VERIFICATION**: Test assumptions and potential fixes
5. **DOCUMENTATION**: Keep track of debugging process and findings

**SUCCESS = IDENTIFIED ROOT CAUSE + CLEAR SOLUTION PATH**
**FAILURE = RANDOM TRIAL AND ERROR WITHOUT PROGRESS**