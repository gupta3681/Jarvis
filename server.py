from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from queue import Queue, Empty
import asyncio
from typing import Dict, Optional
import json
import os
from openai import OpenAI
from config import JarvisConfig
from graph import create_graph
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from memory.core_memory import CoreMemory
import tool_config


app = FastAPI(title="Jarvis Personal Assistant API")

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)
    
    async def monitor_queue(self, session_id: str, message_queue: Queue):
        """Monitor the message queue and send messages to the frontend."""
        while session_id in self.active_connections:
            try:
                # Non-blocking queue check
                message = message_queue.get_nowait()
                await self.send_message(session_id, message)
            except Empty:
                # No messages in queue, wait a bit
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error monitoring queue: {e}")
                break


manager = ConnectionManager()


@app.get("/")
async def root():
    return {"message": "Jarvis Personal Assistant API", "status": "running"}


@app.get("/api/core-memory")
async def get_core_memory(user_id: str = "default_user"):
    """
    Get the current core memory for a user.
    
    Args:
        user_id: User identifier (default: "default_user")
    
    Returns:
        Core memory data as JSON
    """
    try:
        core_memory = CoreMemory(user_id=user_id)
        return {
            "success": True,
            "user_id": user_id,
            "core_memory": core_memory.core
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/tool-config")
async def get_tool_config():
    """
    Get the current tool configuration.
    
    Returns:
        Tool configuration with enabled/disabled status for each tool
    """
    return {
        "success": True,
        "tools": tool_config.load_config(),
        "enabled": tool_config.get_enabled_tools(),
        "disabled": tool_config.get_disabled_tools()
    }


class ToolConfigUpdate(BaseModel):
    tool_name: str
    enabled: bool


@app.post("/api/tool-config")
async def update_tool_config(update: ToolConfigUpdate):
    """
    Update a tool's enabled/disabled status.
    
    Args:
        update: ToolConfigUpdate with tool_name and enabled status
    
    Returns:
        Updated tool configuration
    
    Note: Changes take effect immediately for new conversations.
    Existing WebSocket sessions may need to reconnect.
    """
    try:
        if update.tool_name not in tool_config.DEFAULT_CONFIG:
            return {
                "success": False,
                "error": f"Unknown tool: {update.tool_name}",
                "available_tools": list(tool_config.DEFAULT_CONFIG.keys())
            }
        
        # Update the config (saves to file)
        tool_config.update_tool(update.tool_name, update.enabled)
        
        return {
            "success": True,
            "tool_name": update.tool_name,
            "enabled": update.enabled,
            "message": f"Tool '{update.tool_name}' {'enabled' if update.enabled else 'disabled'}. Reconnect for changes to take effect."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/tool-config/bulk")
async def bulk_update_tool_config(updates: Dict[str, bool]):
    """
    Update multiple tools at once.
    
    Args:
        updates: Dict mapping tool names to enabled status
    
    Returns:
        Updated tool configuration
    """
    try:
        updated = []
        errors = []
        
        for tool_name, enabled in updates.items():
            if tool_name not in tool_config.DEFAULT_CONFIG:
                errors.append(f"Unknown tool: {tool_name}")
                continue
            
            tool_config.update_tool(tool_name, enabled)
            updated.append(tool_name)
        
        return {
            "success": len(errors) == 0,
            "updated": updated,
            "errors": errors if errors else None,
            "current_config": tool_config.load_config()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/tts")
async def text_to_speech(request: dict):
    """
    Convert text to speech using OpenAI TTS.
    
    Args:
        request: JSON with 'text' field
    
    Returns:
        Audio stream (MP3)
    """
    try:
        text = request.get("text", "")
        if not text:
            return {"success": False, "error": "No text provided"}
        
        # Generate speech using OpenAI TTS
        response = openai_client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
            input=text,
            speed=1.0
        )
        
        # Stream the audio response
        return StreamingResponse(
            response.iter_bytes(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3"
            }
        )
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication."""
    print(f"[WS] New connection - session_id: {session_id}")
    await manager.connect(websocket, session_id)
    
    # Create config with message queue and user_id
    config = JarvisConfig(
        session_id=session_id,
        user_id="default_user"  # For now, single user. Later: extract from auth
    )
    message_queue = config.message_queue
    
    # Start queue monitoring task
    monitor_task = asyncio.create_task(
        manager.monitor_queue(session_id, message_queue)
    )
    
    try:
        # Send welcome message
        config.send_message("Connected to Jarvis!", "system")
        
        # Create the graph
        graph = create_graph()
        
        while True:
            # Receive message from client
            print(f"[WS] Waiting for message - session_id: {session_id}")
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_input = message_data.get("message", "")
            
            print(f"[WS] Received message - session_id: {session_id}, message: {user_input[:50]}...")
            
            if not user_input:
                continue
            
            # Send acknowledgment
            config.send_message(f"Processing: {user_input}", "user")
            
            # Add thread_id to config for checkpointer
            runnable_config = config.to_runnable_config()
            runnable_config["configurable"]["thread_id"] = session_id
            
            # Check if there's an active interrupt to resume
            state = graph.get_state(runnable_config)
            has_interrupt = bool(state.next)  # If state.next exists, graph is paused
            
            if has_interrupt:
                # Resume the interrupted graph - pass user input as resume value
                # This will be returned by the interrupt() call in the subgraph
                print(f"[DEBUG] Resuming interrupted graph with: {user_input}")
                result = await graph.ainvoke(
                    Command(resume=user_input),
                    runnable_config
                )
            else:
                # Start fresh with new message
                initial_state = {
                    "messages": [HumanMessage(content=user_input)],
                    "iteration_count": 0
                }
                result = await graph.ainvoke(
                    initial_state,
                    runnable_config
                )
            
            print(f"[DEBUG] Result keys: {result.keys()}")
            
            # Send response to user - either interrupt question or final answer
            if "__interrupt__" in result:
                # Graph was interrupted - send the question to the user
                interrupts = result["__interrupt__"]
                print(f"[DEBUG] Graph interrupted: {interrupts}")
                if interrupts:
                    interrupt_value = interrupts[0].value if hasattr(interrupts[0], 'value') else interrupts[0]
                    config.send_message(str(interrupt_value), "assistant")
            else:
                # Graph completed - send the final AI message
                for msg in reversed(result["messages"]):
                    if type(msg).__name__ == "AIMessage" and hasattr(msg, "content") and msg.content:
                        config.send_message(msg.content, "assistant")
                        break
            
    except WebSocketDisconnect:
        print(f"[WS] Client disconnected - session_id: {session_id}")
        manager.disconnect(session_id)
        monitor_task.cancel()
    except Exception as e:
        import traceback
        print(f"[WS] Error - session_id: {session_id}, error: {e}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        manager.disconnect(session_id)
        monitor_task.cancel()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
