from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from typing import TypedDict, Annotated, Sequence, Optional
from datetime import datetime

from tools.tools import get_tools
from config import JarvisConfig
from memory.core_memory import get_core_memory
from llm import get_conversation_llm
from prompts.main_agent_prompt import AGENT_PROMPT


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[Sequence[HumanMessage | AIMessage | ToolMessage], add_messages]
    iteration_count: int  # Track number of tool calling iterations


def get_config_from_runnable(config: Optional[RunnableConfig]) -> Optional[JarvisConfig]:
    """Extract JarvisConfig from RunnableConfig."""
    if config and "configurable" in config:
        return config["configurable"].get("jarvis_config")
    return None


async def tool_calling_node(state: AgentState, config: RunnableConfig):
    """Node that calls the LLM to decide which tools to use."""
    jarvis_config = get_config_from_runnable(config)
    user_id = jarvis_config.user_id if jarvis_config else "default_user"
    
    # Get current iteration count
    iteration_count = state.get("iteration_count", 0)
    
    if jarvis_config:
        jarvis_config.send_message(f"🤔 Thinking... (iteration {iteration_count + 1})", "node")
    
    # Load core memory and inject into context
    core_memory = get_core_memory(user_id)
    core_context = core_memory.to_context_string()
    
    messages = list(state["messages"])
    
    # Debug: Print message types to diagnose ordering issue
    if jarvis_config and jarvis_config.verbose:
        msg_types = [type(m).__name__ for m in messages]
        print(f"Message types in state: {msg_types}")
    
    llm = get_conversation_llm()
    llm_with_tools = llm.bind_tools(get_tools())
    
    # Use partial to properly inject core memory into the system prompt
    # This ensures core_memory is set once and doesn't interfere with message ordering
    prompt_with_memory = AGENT_PROMPT.partial(
        core_memory=core_context if core_context else "No core memory set yet.", 
        current_date=datetime.now().strftime("%Y-%m-%d"),
        current_time=datetime.now().strftime("%H:%M:%S")
    )
    chain = prompt_with_memory | llm_with_tools
    
    # Use ainvoke for async execution - only pass messages
    response = await chain.ainvoke({"messages": messages})
    
    if jarvis_config and hasattr(response, "tool_calls") and response.tool_calls:
        tool_names = [tc["name"] for tc in response.tool_calls]
        jarvis_config.send_message(f"🔧 Using tools: {', '.join(tool_names)}", "node")
    
    # Increment iteration count
    return {"messages": [response], "iteration_count": iteration_count + 1}


def tool_execution_node(state: AgentState, config: RunnableConfig):
    """Node that executes the tool calls."""
    jarvis_config = get_config_from_runnable(config)
    
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_outputs = []
    task_completed = False
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tools = {tool.name: tool for tool in get_tools()}
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            
            if jarvis_config:
                jarvis_config.send_message(f"⚙️ Executing tool: {tool_name}", "node")
            
            tool = tools[tool_name]
            result = tool.invoke(tool_call["args"])
            
            if jarvis_config:
                jarvis_config.send_message(f"✅ Tool result: {result}", "node")
            
            # Check if this was task_complete
            if tool_name == "task_complete":
                task_completed = True
            
            tool_outputs.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                )
            )
    
    # If task_complete was called, mark iteration count very high to force stop
    if task_completed:
        return {"messages": tool_outputs, "iteration_count": 999}
    
    return {"messages": tool_outputs}


def should_continue(state: AgentState, config: RunnableConfig = None):
    """
    Determine if we should continue to tool execution or end.
    
    Stopping conditions:
    1. No tool calls in last message → END
    2. task_complete tool was called → END
    3. Max iterations reached → END  
    4. Has tool calls and under limit → CONTINUE
    """
    # Get max iterations from config or use default
    jarvis_config = get_config_from_runnable(config)
    max_iterations = jarvis_config.max_iterations if jarvis_config else 10
    
    last_message = state["messages"][-1]
    iteration_count = state.get("iteration_count", 0)
    
    # Check if there are tool calls to execute
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # Check if task_complete was called
        tool_names = [tc["name"] for tc in last_message.tool_calls]
        if "task_complete" in tool_names:
            if jarvis_config:
                jarvis_config.send_message("✅ Agent signaled task completion", "node")
            # Execute the task_complete tool, then end
            return "execute_tools"
        
        # Check if max iterations reached
        if iteration_count >= max_iterations:
            if jarvis_config:
                jarvis_config.send_message(
                    f"⚠️ Max iterations ({max_iterations}) reached. Stopping to prevent infinite loop.",
                    "node"
                )
            return "end"
        
        # Continue with tool execution
        return "execute_tools"
    
    # No tool calls, we're done
    return "end"


def create_graph():
    """Create and compile the agent graph."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("tool_calling", tool_calling_node)
    workflow.add_node("execute_tools", tool_execution_node)
    
    # Set entry point
    workflow.set_entry_point("tool_calling")
    
    # Add edges
    workflow.add_conditional_edges(
        "tool_calling",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "end": END
        }
    )
    workflow.add_edge("execute_tools", "tool_calling")
    
    return workflow.compile()
