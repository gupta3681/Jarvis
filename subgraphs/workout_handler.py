"""
Workout Logger Subgraph

A specialized subgraph for handling workouts with clarifying questions
and structured data storage.
"""

from typing import Annotated, TypedDict, Literal, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
import os
from datetime import datetime, timedelta
from langgraph.types import interrupt
import gspread
from google.oauth2.service_account import Credentials
from prompts.workout_handler_prompt import WORKOUT_HANDLER_PROMPT


# Google Sheets setup
def get_google_sheets_client():
    """
    Initialize and return Google Sheets client.
    Requires GOOGLE_SHEETS_CREDENTIALS_PATH in .env
    """
    try:
        # Define the scope
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Get credentials path from environment
        creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
        if not creds_path:
            raise ValueError("GOOGLE_SHEETS_CREDENTIALS_PATH not set in .env")
        
        # Authenticate
        creds = Credentials.from_service_account_file(creds_path, scopes=scope)
        client = gspread.authorize(creds)
        
        return client
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        return None


def get_workout_sheet(user_id: str = "default_user"):
    """
    Get or create workout sheet for user.
    Returns worksheet object.
    """
    try:
        client = get_google_sheets_client()
        if not client:
            return None
        
        # Get spreadsheet name from env or use default
        spreadsheet_name = os.getenv('WORKOUT_SPREADSHEET_NAME', 'Jarvis_Workouts')
        
        try:
            # Try to open existing spreadsheet
            spreadsheet = client.open(spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            # Create new spreadsheet if it doesn't exist
            spreadsheet = client.create(spreadsheet_name)
            # Share with your email (optional)
            user_email = os.getenv('USER_EMAIL')
            if user_email:
                spreadsheet.share(user_email, perm_type='user', role='writer')
        
        # Get or create worksheet for user
        try:
            worksheet = spreadsheet.worksheet(user_id)
        except gspread.WorksheetNotFound:
            # Create new worksheet - no headers needed for date-organized format
            worksheet = spreadsheet.add_worksheet(title=user_id, rows=1000, cols=10)
        
        return worksheet
    except Exception as e:
        print(f"Error getting workout sheet: {e}")
        return None


def find_or_create_date_section(worksheet, date_str: str) -> int:
    """
    Find existing date section or create a new one.
    Returns the row number where exercises should be added.
    """
    try:
        # Get all values from the sheet
        all_values = worksheet.get_all_values()
        
        # Look for existing date header
        for idx, row in enumerate(all_values):
            if row and row[0] == date_str:
                # Found the date! Now find the next empty row in this section
                # Start checking from the row after the column headers
                check_row = idx + 2  # Date row + header row
                
                # Find the next empty row (where column A is empty)
                while check_row < len(all_values):
                    # Check if this row is empty (no exercise name in column A)
                    if not all_values[check_row][0]:
                        return check_row + 1  # +1 because sheets are 1-indexed
                    
                    # Check if we hit another date section (column A has a date-like string)
                    if ',' in all_values[check_row][0] and any(month in all_values[check_row][0] for month in 
                        ['January', 'February', 'March', 'April', 'May', 'June', 
                         'July', 'August', 'September', 'October', 'November', 'December']):
                        # Hit another date section, insert before it
                        return check_row + 1
                    
                    check_row += 1
                
                # Reached end of sheet, return next row
                return check_row + 1
        
        # Date not found, create new section at the end
        next_row = len(all_values) + 1
        if next_row > 1:  # Add spacing if not first entry
            next_row += 1
        
        # Add date header (bold, larger)
        worksheet.update_cell(next_row, 1, date_str)
        worksheet.format(f"A{next_row}:F{next_row}", {
            "textFormat": {"bold": True, "fontSize": 12},
            "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
        })
        
        # Add column headers for this date
        next_row += 1
        headers = ['Exercise', 'Sets', 'Reps', 'Weight (lbs)', 'Notes', 'Time']
        for col_idx, header in enumerate(headers, start=1):
            worksheet.update_cell(next_row, col_idx, header)
        
        # Format headers
        worksheet.format(f"A{next_row}:F{next_row}", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95}
        })
        
        return next_row + 1  # Return row for first exercise
        
    except Exception as e:
        print(f"Error finding/creating date section: {e}")
        # Fallback: append at end
        return len(worksheet.get_all_values()) + 1


# State for workout logging subgraph
class WorkoutHandlerState(TypedDict):
    """State for the workout logger subgraph."""
    messages: Annotated[list, add_messages]
    workout_data: dict  # Collected workout information
    clarification_needed: bool
    iteration_count: int
    is_complete: bool  # Flag to indicate subgraph is done
    needs_main_agent: bool  # Flag to exit and let main agent handle


# Workout logger tools
@tool
def read_workout_history(user_id: str = "default_user", days: int = 7) -> str:
    """
    Read workout history from Google Sheets (date-organized format).
    
    Args:
        user_id: User identifier
        days: Number of days to look back
    
    Returns:
        Workout history as formatted string
    """
    try:
        # Get worksheet
        worksheet = get_workout_sheet(user_id)
        if not worksheet:
            return "❌ Error: Could not connect to Google Sheets. Check your credentials."
        
        # Get all values from the sheet
        all_values = worksheet.get_all_values()
        
        if not all_values:
            return "No workout history found. Start logging your workouts!"
        
        # Parse the date-organized format
        cutoff_date = datetime.now() - timedelta(days=days)
        workouts_by_date = {}
        current_date = None
        
        for row in all_values:
            if not row or not row[0]:
                continue
            
            # Check if this is a date header (first column has text, looks like a date)
            if row[0] and ',' in row[0] and any(month in row[0] for month in 
                ['January', 'February', 'March', 'April', 'May', 'June', 
                 'July', 'August', 'September', 'October', 'November', 'December']):
                current_date = row[0]
                # Try to parse the date to check if it's within range
                try:
                    # Parse "Monday, January 15, 2024" format
                    date_obj = datetime.strptime(current_date, "%A, %B %d, %Y")
                    if date_obj >= cutoff_date:
                        workouts_by_date[current_date] = []
                    else:
                        current_date = None  # Skip old dates
                except ValueError:
                    current_date = None
                continue
            
            # Check if this is a column header row (skip it)
            if row[0] and row[0].lower() == 'exercise':
                continue
            
            # If we have a current date and this looks like an exercise row
            if current_date and row[0] and row[0] not in ['Exercise', '']:
                exercise_data = {
                    'exercise': row[0] if len(row) > 0 else '',
                    'sets': row[1] if len(row) > 1 else '',
                    'reps': row[2] if len(row) > 2 else '',
                    'weight': row[3] if len(row) > 3 else '',
                    'notes': row[4] if len(row) > 4 else '',
                    'time': row[5] if len(row) > 5 else ''
                }
                workouts_by_date[current_date].append(exercise_data)
        
        if not workouts_by_date:
            return f"No workouts found in the last {days} days."
        
        # Format output
        output = f"📊 Workout History (Last {days} days):\n\n"
        
        for date, exercises in workouts_by_date.items():
            output += f"📅 **{date}**\n"
            for ex in exercises:
                output += f"   💪 {ex['exercise']}\n"
                output += f"      📈 {ex['sets']} sets x {ex['reps']} reps"
                
                if ex['weight']:
                    output += f" @ {ex['weight']} lbs"
                
                if ex['time']:
                    output += f" at {ex['time']}"
                
                if ex['notes']:
                    output += f"\n      📝 {ex['notes']}"
                
                output += "\n"
            output += "\n"
        
        return output.strip()
    
    except Exception as e:
        return f"❌ Error reading workout history: {str(e)}"


@tool
def write_workout_entry(
    exercise: str,
    sets: int,
    reps: int,
    weight: float = None,
    notes: str = "",
    user_id: str = "default_user"
) -> str:
    """
    Write workout entry to Google Sheets organized by date.
    
    Args:
        exercise: Exercise name (e.g., "Bench Press")
        sets: Number of sets
        reps: Number of reps per set
        weight: Weight used in lbs (optional)
        notes: Additional notes (optional)
        user_id: User identifier
    
    Returns:
        Success message
    """
    try:
        # Get worksheet
        worksheet = get_workout_sheet(user_id)
        if not worksheet:
            return "❌ Error: Could not connect to Google Sheets. Check your credentials."
        
        # Get current date and time
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")  # e.g., "Monday, January 15, 2024"
        time_str = now.strftime("%I:%M %p")  # e.g., "02:30 PM"
        
        # Find or create date section
        row_num = find_or_create_date_section(worksheet, date_str)
        
        # Prepare exercise data
        exercise_data = [
            exercise,                    # Exercise
            sets,                        # Sets
            reps,                        # Reps
            weight if weight else "",   # Weight
            notes,                       # Notes
            time_str                     # Time
        ]
        
        # Write exercise to the appropriate row
        for col_idx, value in enumerate(exercise_data, start=1):
            worksheet.update_cell(row_num, col_idx, value)
        
        # Build success message
        workout_summary = f"{exercise} - {sets} sets x {reps} reps"
        if weight:
            workout_summary += f" @ {weight} lbs"
        
        return f"✅ Workout logged successfully: {workout_summary}"
    
    except Exception as e:
        return f"❌ Error logging workout: {str(e)}"


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





async def workout_agent_node(state: WorkoutHandlerState, config: Optional[RunnableConfig] = None) -> WorkoutHandlerState:
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
    
    # Get core memory from config if available
    configurable = config.get("configurable", {}) if config else {}
    core_memory = configurable.get("core_memory", "No core memory available.")
    user_weight = configurable.get("user_weight", "Not specified")
    user_height = configurable.get("user_height", "Not specified")
    
    # Format the prompt with current workout data
    system_msg = SystemMessage(content=WORKOUT_HANDLER_PROMPT.format(
        current_date=datetime.now().strftime("%Y-%m-%d"),
        current_time=datetime.now().strftime("%H:%M:%S"),
        core_memory=core_memory,
        user_weight=user_weight,
        user_height=user_height
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
    
    # Check if the response indicates we need the main agent
    needs_main_agent = (
        not has_tool_calls and 
        response.content and 
        "let me get help from my main assistant" in response.content.lower()
    )
    
    if needs_main_agent:
        # Exit and let main agent handle
        return {
            "messages": [response],
            "workout_data": workout_data,
            "clarification_needed": False,
            "iteration_count": state.get("iteration_count", 0) + 1,
            "is_complete": True,  # Mark complete to exit
            "needs_main_agent": True,  # Signal to main agent
        }
    
    # If we asked a question (no tool calls), interrupt and wait for user response
    if not has_tool_calls:
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
                "needs_main_agent": False,
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
    
    # Add single agent node with descriptive name for LangSmith
    workflow.add_node(
        "workout_agent", 
        workout_agent_node,
        metadata={"name": "Workout Agent (Exercise Logging)"}
    )
    
    # Set entry point
    workflow.set_entry_point("workout_agent")
    
    # Add conditional edges - loop until complete
    workflow.add_conditional_edges(
        "workout_agent",
        should_continue,
        {
            "agent": "workout_agent",  # Continue asking questions
            "end": END,                # Done when workout is logged
        }
    )
    
    # Compile with checkpointer=True to inherit from parent graph
    # This allows interrupts to bubble up properly
    return workflow.compile(checkpointer=True, name="Workout Handler Subgraph")


# Create the compiled graph
workout_handler_graph = create_workout_handler_graph()
