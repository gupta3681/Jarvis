from typing import Optional
from dataclasses import dataclass, field
from queue import Queue


@dataclass
class JarvisConfig:
    """Configuration object passed through all graph nodes."""
    
    # Message queue for WebSocket communication
    message_queue: Queue = field(default_factory=Queue)
    
    # Optional user context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Agent behavior
    max_iterations: int = 10  # Maximum tool calling iterations
    verbose: bool = True
    
    def send_message(self, message: str, message_type: str = "info"):
        """Send a message to the frontend via the queue."""
        self.message_queue.put({
            "type": message_type,
            "content": message,
            "user_id": self.user_id,
            "session_id": self.session_id
        })
    
    def to_runnable_config(self) -> dict:
        """Convert to LangChain RunnableConfig format."""
        return {
            "configurable": {
                "jarvis_config": self
            }
        }
