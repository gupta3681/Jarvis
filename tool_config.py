"""
Tool Configuration - Enable/disable tools dynamically.

Config is persisted to ~/.jarvis/tool_config.json
Changes from the frontend are saved and read fresh on each request.
"""
import os
import json
from typing import Dict, List
from pathlib import Path

# Config file path
CONFIG_FILE = Path(os.path.expanduser("~/.jarvis/tool_config.json"))

# Default configuration
DEFAULT_CONFIG: Dict[str, bool] = {
    # Core tools (always recommended to keep enabled)
    "core_memory": True,
    "episodic_memory": True,
    "think_tool": True,
    "task_complete": True,
    
    # Optional tools
    "web_search": True,
    "calendar": True,
    
    # Handlers (specialized sub-agents)
    "nutrition_handler": True,
    "workout_handler": True,
    "gmail_handler": True,
}


def _ensure_config_exists():
    """Create config file with defaults if it doesn't exist."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)


def load_config() -> Dict[str, bool]:
    """Load config from file. Always reads fresh."""
    _ensure_config_exists()
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # Merge with defaults to handle new tools
        return {**DEFAULT_CONFIG, **config}
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, bool]):
    """Save config to file."""
    _ensure_config_exists()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def update_tool(tool_name: str, enabled: bool) -> bool:
    """Update a single tool's enabled status. Returns success."""
    if tool_name not in DEFAULT_CONFIG:
        return False
    config = load_config()
    config[tool_name] = enabled
    save_config(config)
    return True


def is_tool_enabled(tool_name: str) -> bool:
    """Check if a tool is enabled. Always reads from file."""
    config = load_config()
    return config.get(tool_name, True)


# For backwards compatibility - but prefer load_config()
def get_tool_config() -> Dict[str, bool]:
    """Get current tool configuration."""
    return load_config()


def get_enabled_tools() -> List[str]:
    """Get list of enabled tool names."""
    config = load_config()
    return [name for name, enabled in config.items() if enabled]


def get_disabled_tools() -> List[str]:
    """Get list of disabled tool names."""
    config = load_config()
    return [name for name, enabled in config.items() if not enabled]


# Tool descriptions for prompt generation
TOOL_DESCRIPTIONS: Dict[str, str] = {
    "core_memory": """- `update_core_memory` - Store important facts about the user (identity, preferences, health info)
- `get_core_memory_info` - Retrieve core memory information""",
    
    "episodic_memory": """- `add_memory` - Store experiences, events, or contextual information
- `search_memory` - Recall past conversations or stored experiences
- `list_all_memories` - View all stored memories
- `delete_memory` - Remove a specific memory by ID
- `update_memory` - Update an existing memory's content""",
    
    "web_search": """- `web_search` - Search the web for real-time information, current events, facts you don't know""",
    
    "calendar": """- `create_calendar_event` - Create new calendar events (meetings, appointments, reminders)
- `list_calendar_events` - View upcoming events on the calendar
- `delete_calendar_event` - Remove events from the calendar
- `update_calendar_event` - Modify existing calendar events""",
    
    "gmail_handler": """- `gmail_handler` - **Use this for ALL email-related tasks**: searching emails, reading emails, sending emails, replying to emails. This is a specialized handler that will ask for user approval before sending any emails.""",
    
    "nutrition_handler": """- `nutrition_handler` - **Use this for ALL nutrition-related tasks**: logging food, viewing meal history, tracking macros/calories, meal suggestions, etc. This is a specialized handler that will guide the user through the food logging process.""",
    
    "workout_handler": """- `workout_handler` - **Use this for ALL workout-related tasks**: logging exercises, viewing workout history, tracking progress, exercise suggestions, etc. This is a specialized handler that will guide the user through the workout logging process.""",
    
    "think_tool": """- `think_tool` - Reason through complex problems step by step""",
    
    "task_complete": """- `task_complete` - Signal that the task is complete""",
}


def get_tool_descriptions_for_prompt() -> str:
    """Generate tool descriptions section for the prompt based on enabled tools."""
    descriptions = []
    for tool_name, description in TOOL_DESCRIPTIONS.items():
        if is_tool_enabled(tool_name):
            descriptions.append(description)
    return "\n".join(descriptions)


def get_handler_context_section() -> str:
    """Generate cross-handler context section based on enabled handlers."""
    enabled_handlers = []
    if is_tool_enabled("nutrition_handler"):
        enabled_handlers.append("nutrition")
    if is_tool_enabled("workout_handler"):
        enabled_handlers.append("workout")
    if is_tool_enabled("gmail_handler"):
        enabled_handlers.append("gmail")
    if is_tool_enabled("calendar"):
        enabled_handlers.append("calendar")
    
    # Only show cross-handler section if multiple handlers are enabled
    if len(enabled_handlers) < 2:
        return ""
    
    section = """
### Cross-Handler Context (IMPORTANT):
**Before calling a handler, fetch relevant context from other handlers if needed.**

The handlers are specialized but isolated—they don't automatically know about each other. When a user's request involves multiple domains, YOU must gather the context first and pass it to the handler.

**When to fetch cross-handler context:**"""
    
    examples = []
    
    if "nutrition" in enabled_handlers and "workout" in enabled_handlers:
        section += "\n- **Nutrition + Workout**: Recovery meals, calorie balance, post-workout nutrition"
        examples.append("""
User: "What should I eat after my workout?"
→ 1. think_tool: "User wants nutrition advice based on their workout. I need workout context first."
→ 2. workout_handler("show today's workout summary")  ← Get context
→ 3. nutrition_handler("suggest recovery meal after: [workout details from step 2]")  ← Pass context""")
    
    if "gmail" in enabled_handlers and "calendar" in enabled_handlers:
        section += "\n- **Email + Calendar**: Scheduling meetings mentioned in emails"
    
    if "gmail" in enabled_handlers and ("workout" in enabled_handlers or "nutrition" in enabled_handlers):
        section += "\n- **Email + Workout/Nutrition**: Sending summaries or updates to trainers/nutritionists"
        if "workout" in enabled_handlers:
            examples.append("""
User: "Email my trainer about today's workout"
→ 1. think_tool: "Need to get workout data first, then compose email."
→ 2. workout_handler("get today's workout summary")
→ 3. gmail_handler("send email to trainer about: [workout summary from step 2]")""")
    
    if examples:
        section += "\n\n**Examples of cross-handler coordination:**"
        section += "".join(examples)
    
    section += """

**When NOT to fetch context (keep it simple):**
- Simple standalone requests that don't involve multiple domains"""
    
    return section
