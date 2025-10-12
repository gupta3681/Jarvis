from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from queue import Queue, Empty
import asyncio
from typing import Dict
import json
import os
from openai import OpenAI
from config import JarvisConfig
from graph import create_graph
from langchain_core.messages import HumanMessage
from memory.core_memory import CoreMemory


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
            
            # Run the graph with config and thread_id for conversation history
            # Use session_id as thread_id to maintain conversation per session
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "iteration_count": 0
            }
            
            # Add thread_id to config for checkpointer
            runnable_config = config.to_runnable_config()
            runnable_config["configurable"]["thread_id"] = session_id
            
            # Execute graph asynchronously
            result = await graph.ainvoke(
                initial_state,
                runnable_config
            )
            
            # Send final response (only the last AI message to user)
            # Skip ToolMessages and intermediate AI messages with tool_calls
            for msg in reversed(result["messages"]):
                if type(msg).__name__ == "AIMessage" and hasattr(msg, "content") and msg.content:
                    # This is the final AI response to the user
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
