---
name: code-review-and-quality
description: Perform comprehensive code reviews focusing on code quality, best practices, security vulnerabilities, and performance optimization opportunities
---

# CODE_REVIEW_AND_QUALITY

This skill provides thorough code review capabilities, analyzing code for quality issues, security vulnerabilities, performance problems, and adherence to best practices.

## Core Capabilities

- **Code Quality Analysis**: Identify code smells, complexity issues, and maintainability problems
- **Security Vulnerability Detection**: Find potential security flaws and unsafe practices
- **Performance Optimization**: Identify bottlenecks and inefficient algorithms
- **Best Practices Compliance**: Check adherence to language-specific conventions
- **Documentation Review**: Assess code documentation and comment quality

## Usage Instructions

To perform comprehensive code review, follow this systematic evaluation process:

1. **EXAMINE** the code structure and overall architecture
2. **ANALYZE** for code quality issues and maintainability concerns
3. **SCAN** for security vulnerabilities and unsafe practices
4. **EVALUATE** performance characteristics and optimization opportunities
5. **CHECK** compliance with best practices and conventions
6. **ASSESS** documentation quality and completeness
7. **PROVIDE** actionable recommendations with priority levels

## Review Categories

### Code Quality Analysis
```
Focus Areas:
- Code complexity and readability
- Function and variable naming
- Code duplication and reusability
- Error handling completeness
- Test coverage adequacy
```

### Security Vulnerability Detection
```
Focus Areas:
- Input validation and sanitization
- SQL injection vulnerabilities
- Cross-site scripting (XSS) risks
- Authentication and authorization flaws
- Sensitive data exposure
```

### Performance Optimization
```
Focus Areas:
- Algorithmic efficiency
- Resource usage patterns
- Database query optimization
- Caching opportunities
- Memory management issues
```

### Best Practices Compliance
```
Focus Areas:
- Language-specific conventions
- Design pattern usage
- SOLID principles adherence
- Code organization structure
- Import and dependency management
```

## Technical Requirements

**Required Tools**:
- `Read` - Examine code files and structure
- `Grep` - Search for patterns and anti-patterns
- `multilspy_python_definition` - Navigate code definitions
- `multilspy_python_references` - Analyze code relationships
- `Bash` - Run quality analysis tools when available
- `task_done` - Complete review with structured feedback

**Analysis Techniques**:
- Static code analysis principles
- Security vulnerability patterns
- Performance profiling concepts
- Code quality metrics
- Design pattern recognition

## Examples

**General Code Review**:
```
User: "Review this Python module for code quality issues"
→ Examine overall structure and organization
→ Analyze functions for complexity and clarity
→ Check naming conventions and documentation
→ Identify code duplication and reusability issues
→ Assess error handling and edge cases
→ Provide prioritized recommendations
```

**Security-Focused Review**:
```
User: "Check this code for security vulnerabilities"
→ Scan for input validation issues
→ Check for SQL injection vulnerabilities
→ Analyze authentication/authorization logic
→ Look for sensitive data exposure
→ Review cryptographic implementations
→ Provide security recommendations
```

**Performance Review**:
```
User: "Identify performance bottlenecks in this function"
→ Analyze algorithmic complexity
→ Check for inefficient operations
→ Identify caching opportunities
→ Review database query patterns
→ Suggest optimization strategies
→ Provide performance metrics
```

## Review Framework

### Severity Classification
- **CRITICAL**: Security vulnerabilities, data loss risks
- **HIGH**: Significant performance issues, major maintainability problems
- **MEDIUM**: Code quality issues, minor security concerns
- **LOW**: Style inconsistencies, documentation gaps
- **INFO**: Suggestions for improvement, best practice recommendations

### Review Structure
```
1. Executive Summary
   - Overall code quality assessment
   - Key findings and recommendations
   - Priority action items

2. Detailed Findings
   - Security issues (with severity)
   - Performance concerns (with impact)
   - Code quality problems (with examples)
   - Best practice violations (with rationale)

3. Recommendations
   - Immediate actions (high priority)
   - Improvement opportunities (medium priority)
   - Best practice adoptions (low priority)

4. Positive Aspects
   - Well-implemented solutions
   - Good design decisions
   - Proper documentation
```

## Common Issues and Patterns

### Code Quality Issues
- **Long Functions**: Functions exceeding 20-30 lines
- **Deep Nesting**: More than 3-4 levels of indentation
- **Magic Numbers**: Hard-coded values without explanation
- **Duplicate Code**: Repeated logic across multiple locations
- **Poor Naming**: Unclear variable/function names

### Security Vulnerabilities
- **Input Validation**: Missing or insufficient validation
- **Injection Flaws**: SQL, command, or code injection risks
- **Authentication**: Weak or missing authentication checks
- **Authorization**: Insufficient access control
- **Cryptography**: Weak encryption or improper usage

### Performance Problems
- **Inefficient Algorithms**: O(n²) or worse complexity
- **Database Issues**: N+1 queries, missing indexes
- **Memory Leaks**: Unreleased resources or circular references
- **I/O Bottlenecks**: Synchronous operations in critical paths
- **Caching Misses**: Failure to utilize appropriate caching

## Decision Tree

```
Code review request → What type of review focus?
    ├─ General quality → Comprehensive analysis → All categories → Prioritized recommendations → Done
    ├─ Security focus → Vulnerability scan → Security-specific issues → Risk assessment → Done
    ├─ Performance focus → Bottleneck analysis → Efficiency evaluation → Optimization suggestions → Done
    └─ Specific concern → Targeted analysis → Focused recommendations → Detailed explanation → Done
```

## Key Principles

1. **CONSTRUCTIVE FEEDBACK**: Provide actionable, specific recommendations
2. **PRIORITIZED ISSUES**: Focus on high-impact problems first
3. **BALANCED PERSPECTIVE**: Identify both issues and positive aspects
4. **CONTEXT AWARENESS**: Consider project constraints and requirements
5. **EDUCATIONAL VALUE**: Explain why issues matter and how to fix them

**SUCCESS = IMPROVED CODE QUALITY + ACTIONABLE RECOMMENDATIONS**
**FAILURE = VAGUE CRITICISM WITHOUT CONSTRUCTIVE GUIDANCE**