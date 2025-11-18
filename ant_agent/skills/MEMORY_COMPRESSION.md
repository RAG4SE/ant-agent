# Memory Compression Skill

This skill is designed to compress conversation history when the token count approaches the context window limit. Instead of storing messages to external memory, it uses intelligent prompt-based compression to maintain conversation continuity while reducing token usage.

## Core Functionality

When token threshold is reached:
1. Analyze the complete conversation history
2. Generate a compressed summary preserving key context, decisions, and important details
3. Clear the message history except for system messages
4. Reconstruct the conversation with system prompt + compressed summary as the new starting point

## Compression Prompt Template

```
You are an expert conversation analyst. Your task is to compress the following conversation history into a concise summary that preserves:

1. **Key Context**: Important background information and setup
2. **Critical Decisions**: Major choices, conclusions, or determinations made
3. **Essential Details**: Specific facts, findings, or data points that are crucial for continuation
4. **Current State**: Where the conversation stands and what needs to happen next
5. **Unresolved Items**: Any outstanding questions, tasks, or issues that still need attention

**Original Conversation History:**
{conversation_history}

**Compression Requirements:**
- Preserve all essential information for task continuation
- Maintain logical flow and dependencies
- Include specific details that influenced decisions
- Note any constraints or requirements that affect future actions
- Keep the summary under {target_tokens} tokens

**Output Format:**
Provide a structured summary in this format:

[CONTEXT]
Key background and setup information

[DECISIONS]
Critical decisions and conclusions made

[DETAILS]
Essential specific details and findings

[STATE]
Current status and next required actions

[UNRESOLVED]
Outstanding items needing attention

[SUMMARY]
Brief overall summary of progress made
```

## Implementation Guidelines

### When to Compress
- Token count exceeds configured threshold (default: 80% of context window)
- Before adding new messages that would exceed limits
- Maintain system messages as anchors

### Compression Strategy
1. **Preserve System Messages**: Always keep system prompts and instructions
2. **Maintain Continuity**: Ensure compressed summary allows seamless continuation
3. **Track Key Information**: Preserve tool results, important findings, and decisions
4. **Optimize for Next Steps**: Focus on information relevant to ongoing tasks

### Quality Assurance
- Verify compressed summary contains all critical information
- Ensure no loss of important context or constraints
- Maintain conversation logical flow
- Preserve specific details that affect future actions

## Usage in BaseAgent

The BaseAgent will:
1. Monitor token count using configured thresholds
2. Load this skill when compression is needed
3. Apply compression to maintain conversation continuity
4. Continue with compressed history as new baseline

## Configuration

The compression behavior is controlled by model configuration:
- `context_window_size`: Maximum context window in tokens
- `token_threshold_ratio`: When to trigger compression (e.g., 0.8 = 80%)
- `enable_token_management`: Enable/disable automatic compression