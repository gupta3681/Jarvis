"""
Gmail Handler Subgraph

A specialized subgraph for handling email management with user approval
for sending/replying to emails.
"""

from typing import Annotated, TypedDict, Literal, Optional, List, Dict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
import os
from datetime import datetime
from langgraph.types import interrupt
from prompts.gmail_handler_prompt import GMAIL_HANDLER_PROMPT
from tools.gmail_tools import (
    search_emails_tool,
    get_email_content_tool,
    send_email_tool,
    reply_to_email_tool
)


# State definition
class GmailHandlerState(TypedDict):
    """State for Gmail handler"""
    messages: Annotated[list, add_messages]
    email_data: Dict  # Store email context
    action_pending: bool  # Waiting for user approval
    iteration_count: int
    is_complete: bool
    needs_main_agent: bool  # Flag to exit and return to main agent


# Wrap tools for LangGraph
@tool
def search_emails(
    query: str = None,
    sender: str = None,
    subject: str = None,
    max_results: int = 10,
    unread_only: bool = False
) -> str:
    """
    Search for emails in Gmail.
    
    Args:
        query: General search query
        sender: Filter by sender email
        subject: Filter by subject
        max_results: Maximum results (default: 10)
        unread_only: Only unread emails
    
    Returns:
        Formatted list of emails
    """
    try:
        emails = search_emails_tool(query, sender, subject, max_results, unread_only)
        
        if not emails:
            return "📧 No emails found matching your criteria."
        
        output = f"📧 Found {len(emails)} email(s):\n\n"
        for idx, email in enumerate(emails, 1):
            output += f"{idx}. **From:** {email['sender']}\n"
            output += f"   **Subject:** {email['subject']}\n"
            output += f"   **Date:** {email['date']}\n"
            output += f"   **Preview:** {email['snippet'][:100]}...\n"
            output += f"   **ID:** {email['id']}\n\n"
        
        return output
    except Exception as e:
        return f"❌ Error searching emails: {str(e)}"


@tool
def read_email(email_id: str) -> str:
    """
    Read full content of an email.
    
    Args:
        email_id: Gmail message ID
    
    Returns:
        Full email content
    """
    try:
        email = get_email_content_tool(email_id)
        
        output = "📧 **Email Details:**\n\n"
        output += f"**From:** {email['sender']}\n"
        output += f"**To:** {email['to']}\n"
        output += f"**Subject:** {email['subject']}\n"
        output += f"**Date:** {email['date']}\n\n"
        output += f"**Body:**\n{email['body']}\n"
        
        return output
    except Exception as e:
        return f"❌ Error reading email: {str(e)}"


@tool
def compose_email(
    to: str,
    subject: str,
    body: str,
    cc: str = None,
    bcc: str = None
) -> str:
    """
    Compose a new email. This will prepare the email but NOT send it yet.
    The user must approve before sending.
    
    Args:
        to: Recipient email
        subject: Email subject
        body: Email body
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
    
    Returns:
        Draft email for user approval
    """
    # Don't actually send yet - just return the draft
    draft = "📝 **Draft Email Ready for Approval:**\n\n"
    draft += f"**To:** {to}\n"
    if cc:
        draft += f"**CC:** {cc}\n"
    if bcc:
        draft += f"**BCC:** {bcc}\n"
    draft += f"**Subject:** {subject}\n\n"
    draft += f"**Body:**\n{body}\n\n"
    draft += "---\n"
    draft += "⚠️ **This email has NOT been sent yet.**\n"
    draft += "Please review and confirm if you want to send it."
    
    return draft


@tool
def compose_reply(
    email_id: str,
    body: str,
    reply_all: bool = False
) -> str:
    """
    Compose a reply to an existing email. This will prepare the reply but NOT send it yet.
    The user must approve before sending.
    
    Args:
        email_id: Gmail message ID to reply to
        body: Reply body
        reply_all: Reply to all recipients
    
    Returns:
        Draft reply for user approval
    """
    try:
        # Get original email to show context
        original = get_email_content_tool(email_id)
        
        draft = "📝 **Draft Reply Ready for Approval:**\n\n"
        draft += f"**Replying to:** {original['sender']}\n"
        draft += f"**Original Subject:** {original['subject']}\n"
        if reply_all:
            draft += f"**CC:** {original['to']}\n"
        draft += f"\n**Your Reply:**\n{body}\n\n"
        draft += "---\n"
        draft += f"**Original Email:**\n{original['body'][:200]}...\n\n"
        draft += "---\n"
        draft += "⚠️ **This reply has NOT been sent yet.**\n"
        draft += "Please review and confirm if you want to send it."
        
        return draft
    except Exception as e:
        return f"❌ Error composing reply: {str(e)}"


def get_gmail_tools():
    """Return list of Gmail tools"""
    return [
        search_emails,
        read_email,
        compose_email,
        compose_reply
    ]


async def gmail_agent_node(state: GmailHandlerState, config: Optional[RunnableConfig] = None) -> GmailHandlerState:
    """
    Gmail agent node that handles email operations with user approval for sending.
    """
    messages = state["messages"]
    email_data = state.get("email_data", {})
    
    # Get Gmail tools
    tools = get_gmail_tools()
    
    # Create LLM with tools bound
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.7,
    )
    llm_with_tools = llm.bind_tools(tools)
    
    # Get core memory from config if available
    configurable = config.get("configurable", {}) if config else {}
    core_memory = configurable.get("core_memory", "No core memory available.")
    
    # Get the system prompt content directly (it doesn't need formatting)
    system_msg = SystemMessage(content=GMAIL_HANDLER_PROMPT.messages[0].prompt.template)
    
    # Get response (may have tool calls or questions)
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
                
                # Store email context if it's a compose or reply
                if tool_name in ["compose_email", "compose_reply"]:
                    email_data["pending_action"] = {
                        "type": tool_name,
                        "args": tool_args
                    }
    
    # Check if we need main agent (for off-topic questions)
    needs_main_agent = (
        not has_tool_calls and 
        response.content and 
        "let me get help from my main assistant" in response.content.lower()
    )
    
    if needs_main_agent:
        return {
            "messages": [response],
            "email_data": email_data,
            "action_pending": False,
            "iteration_count": state.get("iteration_count", 0) + 1,
            "is_complete": True,
            "needs_main_agent": True,
        }
    
    # Check if we have a pending send/reply action
    has_pending_action = "pending_action" in email_data
    
    # If we asked a question (no tool calls), interrupt for user response
    if not has_tool_calls:
        question = response.content
        user_response = interrupt(question)
        
        print("User response:", user_response)
        
        if user_response:
            # If we have a pending action, check if user approved
            if has_pending_action:
                user_lower = user_response.lower().strip()
                # Check for clear approval (must be short and direct)
                is_clear_approval = (
                    user_lower in ["yes", "y", "ok", "sure", "send", "send it", "approve", "confirm"] or
                    (len(user_lower.split()) <= 3 and any(word in user_lower.split() for word in ["yes", "ok", "sure", "send"]))
                )
                if is_clear_approval and "no" not in user_lower and "change" not in user_lower and "modify" not in user_lower:
                    # User approved! Actually send the email
                    pending = email_data["pending_action"]
                    
                    try:
                        if pending["type"] == "compose_email":
                            result = send_email_tool(**pending["args"])
                            confirmation = f"✅ Email sent successfully!\n\nTo: {result['to']}\nSubject: {result['subject']}\nMessage ID: {result['id']}"
                        elif pending["type"] == "compose_reply":
                            result = reply_to_email_tool(**pending["args"])
                            confirmation = f"✅ Reply sent successfully!\n\nTo: {result['to']}\nSubject: {result['subject']}\nMessage ID: {result['id']}"
                        
                        # Clear pending action
                        email_data.pop("pending_action", None)
                        
                        return {
                            "messages": [response, HumanMessage(content=user_response), AIMessage(content=confirmation)],
                            "email_data": email_data,
                            "action_pending": False,
                            "iteration_count": state.get("iteration_count", 0) + 1,
                            "is_complete": True,  # Task complete
                            "needs_main_agent": False,
                        }
                    except Exception as e:
                        error_msg = f"❌ Error sending email: {str(e)}"
                        return {
                            "messages": [response, HumanMessage(content=user_response), AIMessage(content=error_msg)],
                            "email_data": email_data,
                            "action_pending": False,
                            "iteration_count": state.get("iteration_count", 0) + 1,
                            "is_complete": True,
                            "needs_main_agent": False,
                        }
                elif any(word in user_lower for word in ["no", "don't", "cancel", "stop"]) and not any(word in user_lower for word in ["change", "modify", "edit", "update", "revise"]):
                    # User declined without wanting changes
                    email_data.pop("pending_action", None)
                    return {
                        "messages": [response, HumanMessage(content=user_response), AIMessage(content="Okay, I won't send that email. Let me know if you need anything else.")],
                        "email_data": email_data,
                        "action_pending": False,
                        "iteration_count": state.get("iteration_count", 0) + 1,
                        "is_complete": True,
                        "needs_main_agent": False,
                    }
                else:
                    # User wants to modify - clear pending action and continue conversation
                    email_data.pop("pending_action", None)
                    return {
                        "messages": [response, HumanMessage(content=user_response)],
                        "email_data": email_data,
                        "action_pending": False,
                        "iteration_count": state.get("iteration_count", 0) + 1,
                        "is_complete": False,  # Continue to handle modifications
                        "needs_main_agent": False,
                    }
            else:
                # Regular question (not approval), continue conversation
                return {
                    "messages": [response, HumanMessage(content=user_response)],
                    "email_data": email_data,
                    "action_pending": False,
                    "iteration_count": state.get("iteration_count", 0) + 1,
                    "is_complete": False,
                    "needs_main_agent": False,
                }
    
    # Check if task is complete (email sent or search completed)
    is_complete = (
        any(tc["name"] in ["search_emails", "read_email"] for tc in (response.tool_calls if has_tool_calls else [])) and
        not has_pending_action
    )
    
    return {
        "messages": [response] + tool_messages,
        "email_data": email_data,
        "action_pending": has_pending_action,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "is_complete": is_complete,
        "needs_main_agent": False,
    }


def should_continue(state: GmailHandlerState) -> Literal["agent", "end"]:
    """
    Routing function to determine if we should continue or end.
    """
    if state.get("is_complete", False):
        return "end"
    
    # Continue if we need more info or waiting for approval
    return "agent"


# Build the Gmail handler graph
gmail_workflow = StateGraph(GmailHandlerState)

# Add nodes with descriptive names for LangSmith
gmail_workflow.add_node(
    "gmail_agent",
    gmail_agent_node
)

# Set entry point
gmail_workflow.set_entry_point("gmail_agent")

# Add conditional edges
gmail_workflow.add_conditional_edges(
    "gmail_agent",
    should_continue,
    {
        "agent": "gmail_agent",
        "end": END
    }
)

# Compile the graph with proper name for LangSmith
gmail_handler_graph = gmail_workflow.compile()
gmail_handler_graph.name = "Gmail Handler Subgraph"
