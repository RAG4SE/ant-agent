---
name: testing-and-validation
description: Assist with testing strategies, test case creation, validation procedures, and test coverage analysis
---

# TESTING_AND_VALIDATION

This skill provides comprehensive testing assistance including test strategy development, test case creation, validation procedures, and coverage analysis.

## Core Capabilities

- **Test Strategy Development**: Design comprehensive testing approaches
- **Test Case Creation**: Write unit, integration, and system tests
- **Test Coverage Analysis**: Identify untested code and coverage gaps
- **Validation Procedures**: Establish validation workflows and criteria
- **Test Debugging**: Assist with failing test investigation and resolution

## Usage Instructions

To assist with testing and validation, follow this systematic testing workflow:

1. **ANALYZE** the code to understand functionality and requirements
2. **ASSESS** current test coverage and identify gaps
3. **DESIGN** appropriate testing strategy for the component
4. **CREATE** comprehensive test cases covering various scenarios
5. **IMPLEMENT** tests using appropriate testing frameworks
6. **VALIDATE** test effectiveness and coverage
7. **DEBUG** failing tests and improve test reliability

## Testing Categories

### Unit Testing
```
Focus Areas:
- Individual function behavior
- Edge cases and boundary conditions
- Error handling and exceptions
- Input validation and data types
- Return value correctness
```

### Integration Testing
```
Focus Areas:
- Component interaction testing
- API endpoint functionality
- Database operation validation
- External service integration
- Data flow between modules
```

### System Testing
```
Focus Areas:
- End-to-end workflow validation
- User scenario testing
- Performance and load testing
- Security vulnerability testing
- Cross-platform compatibility
```

## Technical Requirements

**Required Tools**:
- `Read` - Examine code structure and existing tests
- `Grep` - Search for test files and patterns
- `multilspy_python_definition` - Navigate code definitions
- `Edit` - Create and modify test files
- `Bash` - Run tests and coverage tools
- `task_done` - Complete testing tasks with results

**Testing Frameworks**:
- Python: pytest, unittest, nose
- JavaScript: Jest, Mocha, Jasmine
- Java: JUnit, TestNG
- General: TDD/BDD methodologies

## Examples

**Test Case Creation**:
```
User: "Create unit tests for this function"
→ Analyze function purpose and parameters
→ Identify edge cases and boundary conditions
→ Design test scenarios for normal and error cases
→ Write comprehensive test cases
→ Include setup and teardown if needed
→ Verify test coverage completeness
```

**Test Strategy Development**:
```
User: "What testing approach should I use for this module?"
→ Analyze module complexity and dependencies
→ Assess risk areas and critical functionality
→ Recommend testing pyramid approach
→ Suggest appropriate test types and coverage
→ Provide implementation roadmap
→ Estimate testing effort required
```

**Coverage Analysis**:
```
User: "How can I improve my test coverage?"
→ Run coverage analysis tools
→ Identify untested code sections
→ Analyze coverage gaps by category
→ Suggest priority areas for additional tests
→ Recommend testing techniques for gaps
→ Provide coverage improvement plan
```

## Testing Methodologies

### Test-Driven Development (TDD)
```
Process:
1. Write failing test first
2. Write minimal code to pass test
3. Refactor while keeping tests passing
4. Repeat for next functionality
```

### Behavior-Driven Development (BDD)
```
Process:
1. Define behavior in human-readable format
2. Create automated acceptance tests
3. Implement functionality to satisfy tests
4. Validate against business requirements
```

### Risk-Based Testing
```
Process:
1. Identify high-risk functionality
2. Prioritize testing based on risk
3. Focus resources on critical areas
4. Adjust strategy based on findings
```

## Test Design Techniques

### Equivalence Partitioning
- Divide input data into valid/invalid equivalence classes
- Test representative values from each partition
- Reduce test cases while maintaining coverage

### Boundary Value Analysis
- Test values at partition boundaries
- Include minimum, maximum, and edge values
- Focus on off-by-one and boundary errors

### Decision Table Testing
- Map business rules to test conditions
- Test all combinations of conditions
- Ensure complete business logic coverage

### State Transition Testing
- Test valid and invalid state transitions
- Verify state-dependent behavior
- Check for illegal state changes

## Test Case Structure

### Standard Test Case Format
```python
def test_function_name_scenario():
    """Test [function] with [scenario/condition]"""
    # Arrange: Set up test conditions
    input_data = prepare_test_data()
    expected_result = calculate_expected()

    # Act: Execute the functionality
    actual_result = function_under_test(input_data)

    # Assert: Verify the results
    assert actual_result == expected_result
    assert verify_side_effects()
```

### Test Categories to Include
- **Happy Path**: Normal expected behavior
- **Edge Cases**: Boundary conditions and limits
- **Error Cases**: Invalid inputs and exceptions
- **Performance**: Timing and resource usage
- **Security**: Vulnerability and access testing

## Decision Tree

```
Testing request → What type of testing help?
    ├─ Test creation → Analyze code → Design cases → Write tests → Verify coverage → Done
    ├─ Strategy development → Assess needs → Recommend approach → Create plan → Estimate effort → Done
    ├─ Coverage analysis → Run coverage → Identify gaps → Prioritize areas → Suggest improvements → Done
    └─ Test debugging → Analyze failure → Identify cause → Suggest fix → Verify resolution → Done
```

## Validation Criteria

### Test Quality Metrics
- **Coverage**: Percentage of code executed by tests
- **Effectiveness**: Ability to catch defects
- **Reliability**: Consistent pass/fail results
- **Maintainability**: Ease of updating tests
- **Performance**: Reasonable execution time

### Test Completeness Checklist
- [ ] All functions have corresponding tests
- [ ] Edge cases and boundaries are covered
- [ ] Error conditions are tested
- [ ] Integration points are validated
- [ ] Performance requirements are met
- [ ] Security scenarios are tested

## Key Principles

1. **EARLY TESTING**: Start testing as early as possible in development
2. **AUTOMATION PRIORITY**: Automate repetitive testing tasks
3. **RISK-BASED FOCUS**: Prioritize testing based on risk and impact
4. **CONTINUOUS VALIDATION**: Test throughout development lifecycle
5. **MEASURABLE COVERAGE**: Use metrics to guide testing efforts

**SUCCESS = COMPREHENSIVE TEST COVERAGE + EFFECTIVE DEFECT DETECTION**
**FAILURE = INADEQUATE COVERAGE + UNRELIABLE TESTS**