from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from queue import Queue, Empty
import asyncio
from typing import Dict
import json
from config import JarvisConfig
from graph import create_graph
from langchain_core.messages import HumanMessage


app = FastAPI(title="Jarvis Personal Assistant API")

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


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication."""
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
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_input = message_data.get("message", "")
            
            if not user_input:
                continue
            
            # Send acknowledgment
            config.send_message(f"Processing: {user_input}", "user")
            
            # Run the graph with config
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "iteration_count": 0
            }
            
            # Execute graph asynchronously
            result = await graph.ainvoke(
                initial_state,
                config.to_runnable_config()
            )
            
            # Send final response (only the last AI message to user)
            # Skip ToolMessages and intermediate AI messages with tool_calls
            for msg in reversed(result["messages"]):
                if type(msg).__name__ == "AIMessage" and hasattr(msg, "content") and msg.content:
                    # This is the final AI response to the user
                    config.send_message(msg.content, "assistant")
                    break
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        monitor_task.cancel()
    except Exception as e:
        import traceback
        print(f"WebSocket error: {e}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        manager.disconnect(session_id)
        monitor_task.cancel()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
