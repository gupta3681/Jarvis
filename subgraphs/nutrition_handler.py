"""
Nutrition Logger Subgraph

A specialized subgraph for handling food logging with clarifying questions
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
from prompts.nutrition_handler_prompt import NUTRITION_HANDLER_PROMPT


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


def get_nutrition_sheet(user_id: str = "default_user"):
    """
    Get or create nutrition sheet for user.
    Returns worksheet object.
    """
    try:
        client = get_google_sheets_client()
        if not client:
            return None
        
        # Get spreadsheet name from env or use default
        spreadsheet_name = os.getenv('NUTRITION_SPREADSHEET_NAME', 'Jarvis_Nutrition')
        
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
        print(f"Error getting nutrition sheet: {e}")
        return None


def find_or_create_date_section(worksheet, date_str: str) -> int:
    """
    Find existing date section or create a new one.
    Returns the row number where food entries should be added.
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
                    # Check if this row is empty (no food name in column A)
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
        worksheet.format(f"A{next_row}:H{next_row}", {
            "textFormat": {"bold": True, "fontSize": 12},
            "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
        })
        
        # Add column headers for this date
        next_row += 1
        headers = ['Food', 'Quantity', 'Meal Type', 'Calories', 'Protein (g)', 'Carbs (g)', 'Fats (g)', 'Notes', 'Time']
        for col_idx, header in enumerate(headers, start=1):
            worksheet.update_cell(next_row, col_idx, header)
        
        # Format headers
        worksheet.format(f"A{next_row}:I{next_row}", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95}
        })
        
        return next_row + 1  # Return row for first food entry
        
    except Exception as e:
        print(f"Error finding/creating date section: {e}")
        # Fallback: append at end
        return len(worksheet.get_all_values()) + 1


# State for nutrition logging subgraph
class NutritionHandlerState(TypedDict):
    """State for the nutrition logger subgraph."""
    messages: Annotated[list, add_messages]
    food_data: dict  # Collected food information
    clarification_needed: bool
    iteration_count: int
    is_complete: bool  # Flag to indicate subgraph is done


# Nutrition logger tools
@tool
def read_food_history(user_id: str = "default_user", days: int = 7) -> str:
    """
    Read food history from Google Sheets (date-organized format).
    
    Args:
        user_id: User identifier
        days: Number of days to look back
    
    Returns:
        Food history as formatted string
    """
    try:
        # Get worksheet
        worksheet = get_nutrition_sheet(user_id)
        if not worksheet:
            return "❌ Error: Could not connect to Google Sheets. Check your credentials."
        
        # Get all values from the sheet
        all_values = worksheet.get_all_values()
        
        if not all_values:
            return "No food history found. Start logging your meals!"
        
        # Parse the date-organized format
        cutoff_date = datetime.now() - timedelta(days=days)
        foods_by_date = {}
        current_date = None
        
        for row in all_values:
            if not row or not row[0]:
                continue
            
            # Check if this is a date header
            if row[0] and ',' in row[0] and any(month in row[0] for month in 
                ['January', 'February', 'March', 'April', 'May', 'June', 
                 'July', 'August', 'September', 'October', 'November', 'December']):
                current_date = row[0]
                # Try to parse the date to check if it's within range
                try:
                    date_obj = datetime.strptime(current_date, "%A, %B %d, %Y")
                    if date_obj >= cutoff_date:
                        foods_by_date[current_date] = []
                    else:
                        current_date = None  # Skip old dates
                except ValueError:
                    current_date = None
                continue
            
            # Check if this is a column header row (skip it)
            if row[0] and row[0].lower() == 'food':
                continue
            
            # If we have a current date and this looks like a food row
            if current_date and row[0] and row[0] not in ['Food', '']:
                food_data = {
                    'food': row[0] if len(row) > 0 else '',
                    'quantity': row[1] if len(row) > 1 else '',
                    'meal_type': row[2] if len(row) > 2 else '',
                    'calories': row[3] if len(row) > 3 else '',
                    'protein': row[4] if len(row) > 4 else '',
                    'carbs': row[5] if len(row) > 5 else '',
                    'fats': row[6] if len(row) > 6 else '',
                    'notes': row[7] if len(row) > 7 else '',
                    'time': row[8] if len(row) > 8 else ''
                }
                foods_by_date[current_date].append(food_data)
        
        if not foods_by_date:
            return f"No meals found in the last {days} days."
        
        # Format output
        output = f"🍽️ Food History (Last {days} days):\n\n"
        
        for date, foods in foods_by_date.items():
            output += f"📅 **{date}**\n"
            
            # Calculate daily totals
            total_calories = 0
            total_protein = 0
            total_carbs = 0
            total_fats = 0
            
            for food in foods:
                output += f"   🍴 {food['food']} ({food['meal_type']})\n"
                output += f"      📊 {food['quantity']}"
                
                if food['calories']:
                    output += f" | {food['calories']} cal"
                    try:
                        total_calories += float(food['calories'])
                    except:
                        pass
                
                if food['protein']:
                    output += f" | P: {food['protein']}g"
                    try:
                        total_protein += float(food['protein'])
                    except:
                        pass
                
                if food['carbs']:
                    output += f" | C: {food['carbs']}g"
                    try:
                        total_carbs += float(food['carbs'])
                    except:
                        pass
                
                if food['fats']:
                    output += f" | F: {food['fats']}g"
                    try:
                        total_fats += float(food['fats'])
                    except:
                        pass
                
                if food['time']:
                    output += f" at {food['time']}"
                
                if food['notes']:
                    output += f"\n      📝 {food['notes']}"
                
                output += "\n"
            
            # Add daily totals
            if total_calories > 0:
                output += f"\n   📈 **Daily Total:** {total_calories:.0f} cal | P: {total_protein:.0f}g | C: {total_carbs:.0f}g | F: {total_fats:.0f}g\n"
            
            output += "\n"
        
        return output.strip()
    
    except Exception as e:
        return f"❌ Error reading food history: {str(e)}"


@tool
def write_food_entry(
    food: str,
    quantity: str,
    meal_type: str,
    calories: float = None,
    protein: float = None,
    carbs: float = None,
    fats: float = None,
    notes: str = "",
    user_id: str = "default_user"
) -> str:
    """
    Write food entry to Google Sheets organized by date.
    
    Args:
        food: Food name (e.g., "Chicken Breast")
        quantity: Quantity (e.g., "200g", "1 cup")
        meal_type: Meal type (Breakfast, Lunch, Dinner, Snack)
        calories: Calories (optional)
        protein: Protein in grams (optional)
        carbs: Carbs in grams (optional)
        fats: Fats in grams (optional)
        notes: Additional notes (optional)
        user_id: User identifier
    
    Returns:
        Success message
    """
    try:
        # Get worksheet
        worksheet = get_nutrition_sheet(user_id)
        if not worksheet:
            return "❌ Error: Could not connect to Google Sheets. Check your credentials."
        
        # Get current date and time
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")  # e.g., "Monday, January 15, 2024"
        time_str = now.strftime("%I:%M %p")  # e.g., "02:30 PM"
        
        # Find or create date section
        row_num = find_or_create_date_section(worksheet, date_str)
        
        # Prepare food data
        food_data = [
            food,                           # Food
            quantity,                       # Quantity
            meal_type,                      # Meal Type
            calories if calories else "",   # Calories
            protein if protein else "",     # Protein
            carbs if carbs else "",         # Carbs
            fats if fats else "",           # Fats
            notes,                          # Notes
            time_str                        # Time
        ]
        
        # Write food to the appropriate row
        for col_idx, value in enumerate(food_data, start=1):
            worksheet.update_cell(row_num, col_idx, value)
        
        # Build success message
        food_summary = f"{food} ({quantity}) - {meal_type}"
        if calories:
            food_summary += f" | {calories} cal"
        if protein:
            food_summary += f" | P: {protein}g"
        if carbs:
            food_summary += f" | C: {carbs}g"
        if fats:
            food_summary += f" | F: {fats}g"
        
        return f"✅ Food logged successfully: {food_summary}"
    
    except Exception as e:
        return f"❌ Error logging food: {str(e)}"


@tool
def get_meal_suggestions(meal_type: str = None) -> str:
    """
    Get meal suggestions based on meal type.
    
    Args:
        meal_type: Type of meal (Breakfast, Lunch, Dinner, Snack)
    
    Returns:
        Meal suggestions
    """
    suggestions = {
        "breakfast": [
            "🥚 Scrambled eggs with whole wheat toast",
            "🥣 Oatmeal with berries and nuts",
            "🥤 Protein smoothie with banana and peanut butter",
            "🥞 Greek yogurt with granola and honey",
            "🍳 Veggie omelet with avocado"
        ],
        "lunch": [
            "🍗 Grilled chicken with quinoa and vegetables",
            "🥗 Caesar salad with grilled salmon",
            "🌯 Turkey wrap with hummus and veggies",
            "🍲 Lentil soup with whole grain bread",
            "🍱 Brown rice bowl with tofu and stir-fry vegetables"
        ],
        "dinner": [
            "🥩 Lean steak with sweet potato and broccoli",
            "🐟 Baked salmon with asparagus and wild rice",
            "🍝 Whole wheat pasta with turkey meatballs",
            "🍛 Chicken curry with brown rice",
            "🌮 Fish tacos with cabbage slaw"
        ],
        "snack": [
            "🥜 Handful of almonds",
            "🍎 Apple with peanut butter",
            "🧀 String cheese with whole grain crackers",
            "🥕 Carrots and hummus",
            "🍌 Banana with almond butter"
        ]
    }
    
    if meal_type:
        meal_type_lower = meal_type.lower()
        if meal_type_lower in suggestions:
            return f"💡 {meal_type} Suggestions:\n\n" + "\n".join(suggestions[meal_type_lower])
        else:
            return "Please specify: Breakfast, Lunch, Dinner, or Snack"
    else:
        return "Please specify which meal type you'd like suggestions for: Breakfast, Lunch, Dinner, or Snack"


@tool
def calculate_nutrition_stats(user_id: str = "default_user", days: int = 7) -> str:
    """
    Calculate nutrition statistics over a period.
    
    Args:
        user_id: User identifier
        days: Number of days to analyze
    
    Returns:
        Nutrition statistics
    """
    try:
        # Get worksheet
        worksheet = get_nutrition_sheet(user_id)
        if not worksheet:
            return "❌ Error: Could not connect to Google Sheets."
        
        # Get all values
        all_values = worksheet.get_all_values()
        
        if not all_values:
            return "No nutrition data found."
        
        # Parse and calculate
        cutoff_date = datetime.now() - timedelta(days=days)
        daily_totals = {}
        current_date = None
        
        for row in all_values:
            if not row or not row[0]:
                continue
            
            # Check for date header
            if row[0] and ',' in row[0] and any(month in row[0] for month in 
                ['January', 'February', 'March', 'April', 'May', 'June', 
                 'July', 'August', 'September', 'October', 'November', 'December']):
                current_date = row[0]
                try:
                    date_obj = datetime.strptime(current_date, "%A, %B %d, %Y")
                    if date_obj >= cutoff_date:
                        daily_totals[current_date] = {'calories': 0, 'protein': 0, 'carbs': 0, 'fats': 0}
                    else:
                        current_date = None
                except ValueError:
                    current_date = None
                continue
            
            # Skip headers
            if row[0] and row[0].lower() == 'food':
                continue
            
            # Process food entries
            if current_date and row[0]:
                try:
                    if len(row) > 3 and row[3]:
                        daily_totals[current_date]['calories'] += float(row[3])
                    if len(row) > 4 and row[4]:
                        daily_totals[current_date]['protein'] += float(row[4])
                    if len(row) > 5 and row[5]:
                        daily_totals[current_date]['carbs'] += float(row[5])
                    if len(row) > 6 and row[6]:
                        daily_totals[current_date]['fats'] += float(row[6])
                except (ValueError, IndexError):
                    pass
        
        if not daily_totals:
            return f"No nutrition data found in the last {days} days."
        
        # Calculate averages
        total_days = len(daily_totals)
        avg_calories = sum(d['calories'] for d in daily_totals.values()) / total_days
        avg_protein = sum(d['protein'] for d in daily_totals.values()) / total_days
        avg_carbs = sum(d['carbs'] for d in daily_totals.values()) / total_days
        avg_fats = sum(d['fats'] for d in daily_totals.values()) / total_days
        
        output = f"📊 Nutrition Stats (Last {days} days):\n\n"
        output += f"**Daily Averages:**\n"
        output += f"🔥 Calories: {avg_calories:.0f} cal\n"
        output += f"💪 Protein: {avg_protein:.0f}g\n"
        output += f"🌾 Carbs: {avg_carbs:.0f}g\n"
        output += f"🥑 Fats: {avg_fats:.0f}g\n\n"
        
        output += f"**Total Days Tracked:** {total_days}\n"
        
        return output
    
    except Exception as e:
        return f"❌ Error calculating stats: {str(e)}"


def get_nutrition_tools():
    """Return list of nutrition tools."""
    return [
        read_food_history,
        write_food_entry,
        get_meal_suggestions,
        calculate_nutrition_stats,
    ]




async def nutrition_agent_node(state: NutritionHandlerState, config: Optional[RunnableConfig] = None) -> NutritionHandlerState:
    """
    Single node that handles both clarification questions AND tool execution.
    Uses ReAct pattern - the LLM decides whether to ask questions or use tools.
    """
    messages = state["messages"]
    food_data = state.get("food_data", {})
    
    # Get nutrition tools
    tools = get_nutrition_tools()
    
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
    
    # Format the prompt with current food data
    system_msg = SystemMessage(content=NUTRITION_HANDLER_PROMPT.format(
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
    
    # Check if food was logged (write_food_entry was called)
    food_logged = any(
        tc["name"] == "write_food_entry" 
        for tc in (response.tool_calls if has_tool_calls else [])
    )
    
    # If we asked a question (no tool calls), interrupt and wait for user response
    if not has_tool_calls and not food_logged:
        # Send the question to the user
        question = response.content
        # Interrupt to wait for user input
        user_response = interrupt(question)
        
        # When resumed, add user response to messages
        
        print("User response:", user_response)
        
        if user_response:
            return {
                "messages": [response, HumanMessage(content=user_response)],
                "food_data": food_data,
                "clarification_needed": True,
                "iteration_count": state.get("iteration_count", 0) + 1,
                "is_complete": False,
            }
    
    return {
        "messages": [response] + tool_messages,
        "food_data": food_data,
        "clarification_needed": not food_logged,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "is_complete": food_logged,  # Complete when food is logged
    }


def should_continue(state: NutritionHandlerState) -> Literal["agent", "end"]:
    """
    Routing function to determine if we should continue or end.
    """
    # If food is logged, we're done
    if state.get("is_complete", False):
        return "end"
    
    # Otherwise, continue asking questions
    return "agent"


# Build the nutrition handler graph
nutrition_workflow = StateGraph(NutritionHandlerState)

# Add nodes
nutrition_workflow.add_node("agent", nutrition_agent_node)

# Set entry point
nutrition_workflow.set_entry_point("agent")

# Add conditional edges
nutrition_workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "agent": "agent",
        "end": END
    }
)

# Compile the graph
nutrition_handler_graph = nutrition_workflow.compile()
