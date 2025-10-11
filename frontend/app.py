"""
Streamlit frontend for Jarvis Personal Assistant.
"""
import streamlit as st
import asyncio
import websockets
import json
from datetime import datetime

from memory.core_memory import get_core_memory


# Page config
st.set_page_config(
    page_title="Jarvis - Personal Assistant",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = f"streamlit-{datetime.now().timestamp()}"
if "ws_url" not in st.session_state:
    st.session_state.ws_url = "ws://localhost:8000/ws"


async def send_message_to_backend(message: str, session_id: str, status_callback=None):
    """Send message to backend via WebSocket and receive responses."""
    uri = f"{st.session_state.ws_url}/{session_id}"
    responses = []
    
    try:
        async with websockets.connect(uri) as websocket:
            # Send message
            await websocket.send(json.dumps({"message": message}))
            
            # Receive responses
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)
                    responses.append(data)
                    
                    # Call status callback for real-time updates
                    if status_callback and data.get("type") == "node":
                        status_callback(data.get("content", ""))
                    
                    # Check if this is the final assistant response
                    if data.get("type") == "assistant":
                        break
                except asyncio.TimeoutError:
                    break
                except websockets.exceptions.ConnectionClosed:
                    break
    except Exception as e:
        st.error(f"Connection error: {e}")
        return [{"type": "error", "content": str(e)}]
    
    return responses


def display_core_memory():
    """Display core memory in sidebar."""
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        st.title("🧠 Core Memory")
    with col2:
        if st.button("🔄", help="Refresh core memory"):
            st.rerun()
    
    core_mem = get_core_memory("default_user")
    core_data = core_mem.get_all()
    
    for category, data in core_data.items():
        if data:  # Only show non-empty categories
            with st.sidebar.expander(f"📋 {category.title()}", expanded=False):
                for key, value in data.items():
                    st.write(f"**{key}:** {value}")
    
    if st.sidebar.button("⚙️ Setup Core Memory"):
        st.sidebar.info("Run: `uv run python setup_my_memory.py`")


def main():
    """Main Streamlit app."""
    
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Backend URL
        backend_url = st.text_input(
            "Backend URL",
            value=st.session_state.ws_url,
            help="WebSocket URL of the backend"
        )
        if backend_url != st.session_state.ws_url:
            st.session_state.ws_url = backend_url
        
        st.divider()
        
        # Core memory viewer
        display_core_memory()
        
        st.divider()
        
        # Clear chat
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            # Generate new session ID to reset backend state
            st.session_state.session_id = f"streamlit-{datetime.now().timestamp()}"
            st.rerun()
    
    # Main chat interface
    st.title("🤖 Jarvis - Personal Assistant")
    st.caption("Your AI-powered personal assistant with memory")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show node messages if available (only when tools were used)
            if "node_messages" in message and message["node_messages"]:
                with st.expander("🔧 Processing Details", expanded=False):
                    for node_msg in message["node_messages"]:
                        st.caption(f"_{node_msg}_")
    
    # Chat input
    if prompt := st.chat_input("Message Jarvis..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response from backend
        with st.chat_message("assistant"):
            # Create a placeholder for live status updates
            status_placeholder = st.empty()
            
            # Callback to update status in real-time
            def update_status(status_msg):
                status_placeholder.caption(f"_{status_msg}_")
            
            # Run async function with status callback
            responses = asyncio.run(
                send_message_to_backend(prompt, st.session_state.session_id, update_status)
            )
            
            # Clear status after completion
            status_placeholder.empty()
            
            # Separate node messages and assistant response
            node_messages = []
            assistant_response = ""
            tools_used = False
            
            for resp in responses:
                if resp["type"] == "node":
                    node_messages.append(resp["content"])
                    # Check if any tools were actually executed
                    if "Using tools:" in resp["content"] or "Executing tool:" in resp["content"]:
                        tools_used = True
                elif resp["type"] == "assistant":
                    assistant_response = resp["content"]
            
            # Display assistant response (after collecting all responses)
            if assistant_response:
                st.markdown(assistant_response)
                
                # Only show processing details if tools were used
                if node_messages and tools_used:
                    with st.expander("🔧 Processing Details", expanded=False):
                        for node_msg in node_messages:
                            st.caption(f"_{node_msg}_")
                
                # Add to session state
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response,
                    "node_messages": node_messages if tools_used else []
                })
            else:
                error_msg = "No response received from backend."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "node_messages": []
                })


if __name__ == "__main__":
    main()
