# Agent Loop Control

## Overview

Jarvis uses a **ReAct-style agent** with tool calling and execution nodes that can loop multiple times to complete complex tasks.

## Graph Structure

```
User Input
    ↓
[tool_calling_node] ← Loop back if more tools needed
    ↓
[should_continue] - Decision point
    ↓
[tool_execution_node]
    ↓
[should_continue] - Check again
    ↓
End (final response)
```

## Stopping Conditions

The agent stops when **any** of these conditions are met:

### 1. **task_complete Tool Called** ✅ (Recommended)
- Agent explicitly signals completion
- Calls `task_complete("summary of what was done")`
- Cleanest way to end the loop
- Prevents unnecessary iterations

### 2. **No Tool Calls** ✅
- LLM decides no more tools are needed
- Returns final response to user
- Fallback if agent forgets to call task_complete

### 3. **Max Iterations Reached** 🛑
- Default: **10 iterations**
- Configurable via `JarvisConfig.max_iterations`
- Prevents infinite loops
- User gets warning message

## Iteration Tracking

Each loop through the graph increments `iteration_count`:

```python
initial_state = {
    "messages": [HumanMessage(content=user_input)],
    "iteration_count": 0  # Starts at 0
}
```

Each time `tool_calling_node` runs:
- `iteration_count` increments by 1
- Displayed to user: "🤔 Thinking... (iteration 2)"

## Example Flows

### Simple Task (1 iteration)
```
User: "Log my breakfast: eggs and toast"
→ Iteration 1: 
   - think_tool("User wants to log food...")
   - log_food("eggs and toast")
   - think_tool("Food logged successfully")
   - task_complete("Logged breakfast") ← STOPS HERE
→ Final response
→ Total: 1 iteration
```

### Complex Task (Multiple iterations)
```
User: "Remember I'm allergic to peanuts and log my lunch"
→ Iteration 1: 
   - think_tool("User wants to store allergy and log food...")
   - update_core_memory(health, allergies, peanuts)
→ Iteration 2: 
   - think_tool("Allergy stored, now logging food...")
   - log_food("lunch")
→ Iteration 3:
   - think_tool("Both tasks complete")
   - task_complete("Stored allergy and logged lunch") ← STOPS HERE
→ Final response
→ Total: 3 iterations
```

### Max Iterations Hit (Edge case)
```
User: [Complex request that causes loop]
→ Iterations 1-9: Various tool calls
→ Iteration 10: Max reached
→ ⚠️ Warning: "Max iterations (10) reached. Stopping to prevent infinite loop."
→ Forced end with partial response
```

## Configuration

### Default Settings
```python
config = JarvisConfig(
    max_iterations=10,  # Default
    session_id="user-123"
)
```

### Custom Settings
```python
# For complex tasks, increase limit
config = JarvisConfig(
    max_iterations=20,  # Allow more iterations
    session_id="user-123"
)

# For simple tasks, decrease limit
config = JarvisConfig(
    max_iterations=5,  # Faster timeout
    session_id="user-123"
)
```

## Why This Matters

### Prevents Infinite Loops
Without limits, the agent could:
- Get stuck in tool calling loops
- Waste API credits
- Hang the application

### Allows Multi-Step Reasoning
With proper limits, the agent can:
- Use think_tool before and after actions
- Chain multiple tools together
- Handle complex, multi-step requests

### Provides Visibility
Users see:
- Current iteration number
- Which tools are being used
- When max iterations are hit

## Best Practices

1. **Default (10) is good for most cases**
   - Allows reflection (think_tool)
   - Handles multi-step tasks
   - Prevents runaway loops

2. **Increase for complex workflows**
   - Data analysis tasks
   - Multi-step planning
   - Research queries

3. **Decrease for simple chatbots**
   - Quick Q&A
   - Single-action tasks
   - Cost optimization

## Monitoring

Track iterations in LangSmith:
- See exact iteration count per request
- Identify patterns causing high iterations
- Optimize prompts to reduce unnecessary loops

## Future Enhancements

Potential improvements:
- [ ] Dynamic iteration limits based on task complexity
- [ ] Early stopping if agent detects completion
- [ ] Token budget limits (in addition to iterations)
- [ ] User-configurable limits via frontend
