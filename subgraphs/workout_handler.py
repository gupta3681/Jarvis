"""
Workout Logger Subgraph

A specialized subgraph for handling workouts with clarifying questions
and structured data storage.
"""

from typing import Annotated, TypedDict, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import os
from datetime import datetime
from langgraph.types import interrupt


# State for workout logging subgraph
class WorkoutHandlerState(TypedDict):
    """State for the workout logger subgraph."""
    messages: Annotated[list, add_messages]
    workout_data: dict  # Collected workout information
    clarification_needed: bool
    iteration_count: int
    is_complete: bool  # Flag to indicate subgraph is done


# Workout logger tools
@tool
def read_workout_history(user_id: str = "default_user", days: int = 7) -> str:
    """
    Read workout history from Excel/database.
    
    Args:
        user_id: User identifier
        days: Number of days to look back
    
    Returns:
        Workout history as formatted string
    """
    # TODO: Implement Excel reading
    return f"Workout history for last {days} days: [To be implemented]"


@tool
def write_workout_entry(
    exercise: str,
    sets: int,
    reps: int,
    weight: float = None,
    duration: int = None,
    notes: str = "",
    user_id: str = "default_user"
) -> str:
    """
    Write workout entry to Excel/database.
    
    Args:
        exercise: Exercise name (e.g., "Bench Press")
        sets: Number of sets
        reps: Number of reps per set
        weight: Weight used in lbs (optional)
        duration: Duration in minutes for cardio (optional)
        notes: Additional notes (optional)
        user_id: User identifier
    
    Returns:
        Success message
    """
    # TODO: Implement Excel writing
    workout_summary = f"{exercise} - {sets} sets x {reps} reps"
    if weight:
        workout_summary += f" @ {weight} lbs"
    if duration:
        workout_summary += f" ({duration} minutes)"
    
    return f"✅ Workout logged successfully: {workout_summary}"


@tool
def get_exercise_suggestions(muscle_group: str = None) -> str:
    """
    Get exercise suggestions based on muscle group.
    
    Args:
        muscle_group: Target muscle group (chest, back, legs, arms, etc.)
    
    Returns:
        List of suggested exercises
    """
    # TODO: Implement exercise database lookup
    suggestions = {
        "chest": ["Bench Press", "Push-ups", "Dumbbell Flyes"],
        "back": ["Pull-ups", "Rows", "Deadlifts"],
        "legs": ["Squats", "Lunges", "Leg Press"],
        "arms": ["Bicep Curls", "Tricep Dips", "Hammer Curls"],
    }
    
    if muscle_group and muscle_group.lower() in suggestions:
        return f"Suggested exercises for {muscle_group}: {', '.join(suggestions[muscle_group.lower()])}"
    return "Popular exercises: Squats, Bench Press, Deadlifts, Pull-ups"


@tool
def calculate_workout_stats(user_id: str = "default_user") -> str:
    """
    Calculate workout statistics and progress.
    
    Args:
        user_id: User identifier
    
    Returns:
        Workout statistics summary
    """
    # TODO: Implement stats calculation
    return "Workout stats: [To be implemented]"


# Get tools for workout logger
def get_workout_tools():
    """Return list of workout logging tools."""
    return [
        read_workout_history,
        write_workout_entry,
        get_exercise_suggestions,
        calculate_workout_stats,
    ]


# System prompt
WORKOUT_HANDLER_PROMPT = """You are a workout logging assistant. Your job is to gather complete workout information and log it.

## Information Needed:
- Exercise name (e.g., "Bench Press", "Squats")
- Number of sets
- Number of reps per set
- Weight used (if applicable)
- Duration (for cardio exercises)
- Any notes or observations

## Your Process:
1. **Ask clarifying questions** ONE AT A TIME to gather missing information
2. **Be conversational and helpful**
3. **When you have all information**, use the `write_workout_entry` tool to log it
4. **Confirm** the workout was logged successfully

## Available Tools:
- `read_workout_history` - View past workouts
- `write_workout_entry` - Save workout to database
- `get_exercise_suggestions` - Suggest exercises
- `calculate_workout_stats` - Show progress

Current date: {current_date}
Current time: {current_time}"""


async def workout_agent_node(state: WorkoutHandlerState) -> WorkoutHandlerState:
    """
    Single node that handles both clarification questions AND tool execution.
    Uses ReAct pattern - the LLM decides whether to ask questions or use tools.
    """
    messages = state["messages"]
    workout_data = state.get("workout_data", {})
    
    # Get workout tools
    tools = get_workout_tools()
    
    # Create LLM with tools bound
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.7,
    )
    llm_with_tools = llm.bind_tools(tools)
    
    # Format the prompt with current workout data
    system_msg = SystemMessage(content=WORKOUT_HANDLER_PROMPT.format(
        current_date=datetime.now().strftime("%Y-%m-%d"),
        current_time=datetime.now().strftime("%H:%M:%S")
    ))
    
    # Get response (may have tool calls or just a question)
    response = await llm_with_tools.ainvoke([system_msg] + messages)
    
    # Execute tool calls if any
    tool_messages = []
    has_tool_calls = hasattr(response, "tool_calls") and response.tool_calls
    
    if has_tool_calls:
        # Create a mapping of tool names to tool objects
        tools_by_name = {tool.name: tool for tool in tools}
        
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            # Get the tool and invoke it
            tool_obj = tools_by_name.get(tool_name)
            
            if tool_obj:
                result = tool_obj.invoke(tool_args)
                tool_messages.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                ))
    
    # Check if workout was logged (write_workout_entry was called)
    workout_logged = any(
        tc["name"] == "write_workout_entry" 
        for tc in (response.tool_calls if has_tool_calls else [])
    )
    
    # If we asked a question (no tool calls), interrupt and wait for user response
    if not has_tool_calls and not workout_logged:
        # Send the question to the user
        question = response.content
        # Interrupt to wait for user input
        user_response = interrupt(question)
        
        # When resumed, add user response to messages
        
        print("User response:", user_response)
        
        if user_response:
            return {
                "messages": [response, HumanMessage(content=user_response)],
                "workout_data": workout_data,
                "clarification_needed": True,
                "iteration_count": state.get("iteration_count", 0) + 1,
                "is_complete": False,
            }
    
    return {
        "messages": [response] + tool_messages,
        "workout_data": workout_data,
        "clarification_needed": not workout_logged,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "is_complete": workout_logged,  # Complete when workout is logged
    }


def should_continue(state: WorkoutHandlerState) -> Literal["agent", "end"]:
    """
    Routing function to determine if we should continue or end.
    """
    # If workout is logged, we're done
    if state.get("is_complete", False):
        return "end"
    
    # Otherwise, continue asking questions
    return "agent"


def create_workout_handler_graph():
    """
    Create the workout logger subgraph with a single ReAct agent node.
    
    Flow:
    1. Start -> Agent (ask questions OR use tools)
    2. Agent decides:
       - Ask clarifying question → Return to main agent (is_complete=False)
       - Call write_workout_entry → Log workout (is_complete=True)
    3. Main agent routes next user message back to subgraph if needed
    4. Repeat until workout is logged
    """
    workflow = StateGraph(WorkoutHandlerState)
    
    # Add single agent node
    workflow.add_node("agent", workout_agent_node)
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add conditional edges - loop until complete
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "agent": "agent",  # Continue asking questions
            "end": END,        # Done when workout is logged
        }
    )
    
    # Compile with checkpointer=True to inherit from parent graph
    # This allows interrupts to bubble up properly
    return workflow.compile(checkpointer=True)


# Create the compiled graph
workout_handler_graph = create_workout_handler_graph()
