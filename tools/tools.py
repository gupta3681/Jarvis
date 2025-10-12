from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from datetime import datetime
import openpyxl
from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from subgraphs.workout_handler import workout_handler_graph
from langchain_core.messages import HumanMessage
from memory.core_memory import get_core_memory
from config import JarvisConfig

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
def log_food(food_description: str, config: Optional[RunnableConfig] = None) -> str:
    """
    Log food intake. Takes a description of what was eaten.
    Example: 'chicken breast 200g, rice 150g, broccoli 100g'
    """
    # user_id = get_user_id_from_config(config)
    # file_path = Path(f"food_log_{user_id}.xlsx")
    
    # # Create or load workbook
    # if file_path.exists():
    #     wb = openpyxl.load_workbook(file_path)
    #     ws = wb.active
    # else:
    #     wb = openpyxl.Workbook()
    #     ws = wb.active
    #     ws.append(["Timestamp", "Food Description", "Notes"])
    
    # # Add entry
    # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # ws.append([timestamp, food_description, "Auto-logged"])
    
    # wb.save(file_path)
    print("Pass through for now ")

    return f"Logged food: {food_description}"


@tool
async def log_workout(workout_description: str, config: Optional[RunnableConfig] = None) -> str:
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
    
    ## We don't need to handle interrupts here, the main graph will handle it
    
    # Extract the final response
    messages = result.get("messages", [])
    final_message = messages[-1].content if messages else "Workout logged successfully"
    
    return final_message


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
    """Return list of all available tools."""
    return [
        # Core memory (instant access)
        update_core_memory,
        get_core_memory_info,
        # Episodic memory (semantic search)
        add_memory,
        search_memory,
        # Web search
        web_search,
        # Health tracking
        log_food,
        log_workout,
        # Agent control
        think_tool,
        task_complete
    ]



