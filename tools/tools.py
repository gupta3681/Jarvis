from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from datetime import datetime
import openpyxl
from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage
from memory.core_memory import get_core_memory
from config import JarvisConfig
from tool_config import is_tool_enabled

# Import all subgraphs and tools unconditionally
# Filtering happens dynamically in get_tools() based on current config
from subgraphs.workout_handler import workout_handler_graph
from subgraphs.nutrition_handler import nutrition_handler_graph
from subgraphs.gmail_handler import gmail_handler_graph
from tools.calendar_tools import (
    create_calendar_event,
    list_calendar_events,
    delete_calendar_event,
    update_calendar_event
)

# Load environment variables BEFORE importing Mem0
load_dotenv()

# Now import and initialize Mem0
from mem0 import Memory
import os

# Initialize Mem0 for episodic/experience memory with PERSISTENT storage
# Key: on_disk=True ensures vectors persist across restarts!
qdrant_path = os.path.expanduser("~/.mem0/qdrant_data")
print(f"[INFO] Initializing Mem0 with persistent storage at: {qdrant_path}")

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "jarvis_memories",
            "path": qdrant_path,
            "on_disk": True,  # THIS IS THE KEY! Enables disk persistence
        }
    }
}

memory = Memory.from_config(config)

# Verify the collection is accessible
try:
    test_results = memory.get_all(user_id="__startup_test__")
    print(f"[INFO] Memory system initialized successfully. Collection 'jarvis_memories' is accessible.")
except Exception as e:
    print(f"[WARNING] Memory system initialized but collection check failed: {e}")


def get_user_id_from_config(config: Optional[RunnableConfig]) -> str:
    """Extract user_id from RunnableConfig."""
    if config and "configurable" in config:
        jarvis_config = config["configurable"].get("jarvis_config")
        if jarvis_config and isinstance(jarvis_config, JarvisConfig):
            return jarvis_config.user_id or "default_user"
    return "default_user"


@tool
def add_memory(information: str, config: Optional[RunnableConfig] = None) -> str:
    """
    Store information, experiences, or facts to memory.
    Use this to remember things the user tells you about themselves, their preferences, experiences, etc.
    
    Examples:
    - "I prefer morning workouts"
    - "My favorite food is pizza"
    - "I'm allergic to peanuts"
    - "I work from home on Mondays and Wednesdays"
    """
    user_id = get_user_id_from_config(config)
    print(f"[DEBUG] add_memory - user_id: {user_id}, collection: jarvis_memories, information: {information}")
    result = memory.add(information, user_id=user_id)
    print(f"[DEBUG] add_memory - result: {result}")
    return f"Stored memory: {information}"


@tool
def search_memory(query: str, config: Optional[RunnableConfig] = None) -> str:
    """
    Search through stored memories to find relevant information.
    Use this to recall facts, preferences, or past experiences.
    
    Examples:
    - "What are my workout preferences?"
    - "What foods do I like?"
    - "What am I allergic to?"
    """
    user_id = get_user_id_from_config(config)
    print(f"[DEBUG] search_memory - user_id: {user_id}, collection: jarvis_memories, query: {query}")
    
    results = memory.search(query, user_id=user_id)
    print(f"[DEBUG] search_memory - results type: {type(results)}, count: {len(results.get('results', [])) if isinstance(results, dict) else 0}")
    
    # Mem0 returns a dict with 'results' key containing the actual list
    if isinstance(results, dict) and 'results' in results:
        results = results['results']
    
    if not results or len(results) == 0:
        return "No relevant memories found."
    
    print(f"[DEBUG] Extracted results: {results}")
    
    memories = []
    # Safely iterate through results
    for idx, result in enumerate(results[:5] if len(results) > 5 else results, 1):
        if isinstance(result, dict) and 'memory' in result:
            memories.append(f"{idx}. {result['memory']}")
    
    if not memories:
        return "No relevant memories found."
    
    return "Found memories:\n" + "\n".join(memories)


@tool
def list_all_memories(limit: int = 20, config: Optional[RunnableConfig] = None) -> str:
    """
    List all stored memories for the user.
    Use this to see what has been remembered about the user.
    
    Args:
        limit: Maximum number of memories to return (default 20)
    """
    user_id = get_user_id_from_config(config)
    
    all_mems = memory.get_all(user_id=user_id, limit=limit)
    
    if isinstance(all_mems, dict) and 'results' in all_mems:
        results = all_mems['results']
    else:
        results = []
    
    if not results:
        return "No memories stored yet."
    
    memories = []
    for idx, m in enumerate(results, 1):
        mem_text = m.get('memory', 'Unknown')
        mem_id = m.get('id', '')[:8]
        memories.append(f"{idx}. [{mem_id}] {mem_text}")
    
    return f"Stored memories ({len(results)} total):\n" + "\n".join(memories)


@tool
def delete_memory(memory_id: str, config: Optional[RunnableConfig] = None) -> str:
    """
    Delete a specific memory by its ID.
    Use list_all_memories first to find the memory ID.
    
    Args:
        memory_id: The ID of the memory to delete
    """
    try:
        memory.delete(memory_id)
        return f"Successfully deleted memory: {memory_id}"
    except Exception as e:
        return f"Error deleting memory: {str(e)}"


@tool
def update_memory(memory_id: str, new_content: str, config: Optional[RunnableConfig] = None) -> str:
    """
    Update an existing memory with new content.
    Use list_all_memories first to find the memory ID.
    
    Args:
        memory_id: The ID of the memory to update
        new_content: The new content for the memory
    """
    try:
        memory.update(memory_id, new_content)
        return f"Successfully updated memory {memory_id} to: {new_content}"
    except Exception as e:
        return f"Error updating memory: {str(e)}"


def retrieve_relevant_memories(query: str, user_id: str = "default_user", limit: int = 5) -> str:
    """
    Retrieve relevant memories for a query (non-tool function for auto-injection).
    Returns formatted string of relevant memories or empty string if none found.
    """
    try:
        results = memory.search(query, user_id=user_id, limit=limit)
        
        if isinstance(results, dict) and 'results' in results:
            results = results['results']
        
        if not results:
            return ""
        
        memories = []
        for m in results:
            if isinstance(m, dict) and 'memory' in m:
                memories.append(f"- {m['memory']}")
        
        if not memories:
            return ""
        
        return "\n".join(memories)
    except Exception as e:
        print(f"[WARNING] Error retrieving memories: {e}")
        return ""


@tool
def update_core_memory(category: str, key: str, value: str, config: Optional[RunnableConfig] = None) -> str:
    """
    Update core memory - fundamental facts that are always instantly available.
    
    Categories:
    - identity: name, age, location, etc.
    - work: job, company, work_schedule, etc.
    - preferences: diet_type, workout_style, communication_style, etc.
    - health: allergies, conditions, fitness_goals, etc.
    - relationships: partner, family, friends, etc.
    - context: timezone, language, etc.
    
    Examples:
    - category="identity", key="name", value="John"
    - category="work", key="company", value="Google"
    - category="health", key="allergies", value="peanuts, shellfish"
    """
    user_id = get_user_id_from_config(config)
    core_mem = get_core_memory(user_id)
    core_mem.update(category, key, value)
    return f"Updated core memory: {category}.{key} = {value}"


@tool
def get_core_memory_info(category: str = None, config: Optional[RunnableConfig] = None) -> str:
    """
    Retrieve core memory information.
    If category is provided, returns that category. Otherwise returns all core memory.
    """
    user_id = get_user_id_from_config(config)
    core_mem = get_core_memory(user_id)
    
    if category:
        data = core_mem.get(category)
        if not data:
            return f"No core memory found for category: {category}"
        return f"{category.upper()}:\n" + "\n".join([f"  - {k}: {v}" for k, v in data.items()])
    
    return core_mem.to_context_string()


@tool
async def nutrition_handler(food_description: str, config: Optional[RunnableConfig] = None) -> str:
    """
    Log food intake and handle all nutrition-related tasks. Invokes a specialized subgraph to gather details and log food.
    Example: 'chicken breast 200g for lunch' or 'oatmeal with berries for breakfast'
    
    This tool uses LangGraph interrupts to ask clarifying questions.
    The subgraph will handle the conversation internally.
    """
    
    # Initialize state
    state = {
        "messages": [HumanMessage(content=food_description)],
        "food_data": {},
        "clarification_needed": True,
        "iteration_count": 0,
        "is_complete": False,
    }
    
    # Invoke the nutrition handler subgraph - it will inherit the parent's checkpointer
    # and thread_id automatically through the config
    result = await nutrition_handler_graph.ainvoke(state, config)
    
    print(f"[DEBUG] nutrition_handler result keys: {result.keys()}")
    
    # Check if handler needs main agent to take over
    if result.get("needs_main_agent", False):
        print("[DEBUG] Nutrition handler requesting main agent assistance")
        # Extract the user's last question from messages
        messages = result.get("messages", [])
        user_question = None
        # Find the last HumanMessage (user's question)
        for msg in reversed(messages):
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
                user_question = msg.content
                break
        
        # Return signal with the user's question embedded
        if user_question:
            return f"NEEDS_MAIN_AGENT: {user_question}"
        return "NEEDS_MAIN_AGENT"
    
    ## We don't need to handle interrupts here, the main graph will handle it
    
    # Return the last message content
    if result.get("messages"):
        last_msg = result["messages"][-1]
        return last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
    
    return "Food logging completed."


@tool
async def workout_handler(workout_description: str, config: Optional[RunnableConfig] = None) -> str:
    """
    Log workout activity. Invokes a specialized subgraph to gather details and log the workout.
    Example: 'Running 5km, 30 minutes' or 'Bench press 3x10 @ 60kg'
    
    This tool uses LangGraph interrupts to ask clarifying questions.
    The subgraph will handle the conversation internally.
    """

    
    # Initialize state
    state = {
        "messages": [HumanMessage(content=workout_description)],
        "workout_data": {},
        "clarification_needed": True,
        "iteration_count": 0,
        "is_complete": False,
    }
    
    # Invoke the workout handler subgraph - it will inherit the parent's checkpointer
    # and thread_id automatically through the config
    result = await workout_handler_graph.ainvoke(state, config)
    
    print(f"[DEBUG] log_workout result keys: {result.keys()}")
    
    # Check if handler needs main agent to take over
    if result.get("needs_main_agent", False):
        print("[DEBUG] Workout handler requesting main agent assistance")
        # Extract the user's last question from messages
        messages = result.get("messages", [])
        user_question = None
        # Find the last HumanMessage (user's question)
        for msg in reversed(messages):
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
                user_question = msg.content
                break
        
        # Return signal with the user's question embedded
        if user_question:
            return f"NEEDS_MAIN_AGENT: {user_question}"
        return "NEEDS_MAIN_AGENT"
    
    ## We don't need to handle interrupts here, the main graph will handle it
    
    # Extract the final response
    messages = result.get("messages", [])
    final_message = messages[-1].content if messages else "Workout logged successfully"
    
    return final_message


@tool
async def gmail_handler(email_request: str, config: Optional[RunnableConfig] = None) -> str:
    """
    Manage emails - search, read, send, or reply to emails.
    Invokes a specialized subgraph to handle email operations with user approval.
    
    Examples:
    - 'Show me emails from john@example.com'
    - 'Read my unread emails'
    - 'Send an email to sarah about the meeting'
    - 'Reply to John's email about the project'
    
    This tool uses LangGraph interrupts to ask for user approval before sending emails.
    """
    
    # Initialize state
    state = {
        "messages": [HumanMessage(content=email_request)],
        "email_data": {},
        "action_pending": False,
        "iteration_count": 0,
        "is_complete": False,
        "needs_main_agent": False,
    }
    
    # Invoke the gmail handler subgraph
    result = await gmail_handler_graph.ainvoke(state, config)
    
    print(f"[DEBUG] gmail_handler result keys: {result.keys()}")
    
    # Check if handler needs main agent to take over
    if result.get("needs_main_agent", False):
        print("[DEBUG] Gmail handler requesting main agent assistance")
        # Extract the user's last question from messages
        messages = result.get("messages", [])
        user_question = None
        # Find the last HumanMessage (user's question)
        for msg in reversed(messages):
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
                user_question = msg.content
                break
        
        # Return signal with the user's question embedded
        if user_question:
            return f"NEEDS_MAIN_AGENT: {user_question}"
        return "NEEDS_MAIN_AGENT"
    
    # Return the last message content
    if result.get("messages"):
        last_msg = result["messages"][-1]
        return last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
    
    return "Email operation completed."


@tool 
def think_tool(thought: str, config: Optional[RunnableConfig] = None) -> str:
    """
    Think about the current context, what you are trying to achieve, and how will you achieve it.
    Use this to reason through complex problems step by step.
    """
    return f"Reflection: {thought}"


@tool
def task_complete(summary: str, config: Optional[RunnableConfig] = None) -> str:
    """
    Signal that the task is complete and provide a summary.
    
    Call this when:
    - All requested actions have been completed
    - You have the final answer for the user
    - No more tools need to be executed
    
    Args:
        summary: A brief summary of what was accomplished
    
    Example:
    - "Task complete: Stored allergy information and logged breakfast"
    - "Task complete: Retrieved workout preferences from memory"
    """
    return f"✅ Task Complete: {summary}"


@tool
def web_search(query: str, config: Optional[RunnableConfig] = None) -> str:
    """
    Search the web for real-time information using Tavily.
    Use this when you need current information, news, facts, or anything not in memory.
    
    Examples:
    - "What's the weather in Boston today?"
    - "Latest news about AI"
    - "Best restaurants near me"
    - "Current stock price of Apple"
    
    Args:
        query: The search query
    
    Returns:
        Search results with relevant information
    """
    try:
        # Initialize Tavily search (max 3 results for conciseness)
        tavily = TavilySearchResults(max_results=3)
        results = tavily.invoke(query)
        
        if not results:
            return "No search results found."
        
        # Format results nicely
        formatted_results = []
        for idx, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            content = result.get('content', 'No content')
            url = result.get('url', '')
            formatted_results.append(f"{idx}. {title}\n   {content}\n   Source: {url}")
        
        return "Web search results:\n\n" + "\n\n".join(formatted_results)
    
    except Exception as e:
        return f"Error searching the web: {str(e)}"


def get_tools():
    """Return list of available tools based on tool_config settings."""
    tools = []
    
    # Core memory (instant access)
    if is_tool_enabled("core_memory"):
        tools.extend([update_core_memory, get_core_memory_info])
    
    # Episodic memory (semantic search)
    if is_tool_enabled("episodic_memory"):
        tools.extend([add_memory, search_memory, list_all_memories, delete_memory, update_memory])
    
    # Web search
    if is_tool_enabled("web_search"):
        tools.append(web_search)
    
    # Calendar
    if is_tool_enabled("calendar"):
        tools.extend([
            create_calendar_event,
            list_calendar_events,
            delete_calendar_event,
            update_calendar_event
        ])
    
    # Handlers
    if is_tool_enabled("nutrition_handler"):
        tools.append(nutrition_handler)
    
    if is_tool_enabled("workout_handler"):
        tools.append(workout_handler)
    
    if is_tool_enabled("gmail_handler"):
        tools.append(gmail_handler)
    
    # Agent control
    if is_tool_enabled("think_tool"):
        tools.append(think_tool)
    
    if is_tool_enabled("task_complete"):
        tools.append(task_complete)
    
    return tools



