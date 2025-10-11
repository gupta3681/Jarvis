from langchain_core.messages import HumanMessage
from graph import create_graph
from config import JarvisConfig
from queue import Empty


def main():
    print("🤖 Jarvis Personal Assistant (CLI Mode)")
    print("-" * 40)
    
    # Create config with message queue
    config = JarvisConfig(session_id="cli-session", verbose=True)
    
    # Create the graph
    app = create_graph()
    
    # Example usage
    user_input = "Log my breakfast: 2 eggs, toast, and coffee"
    
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "iteration_count": 0
    }
    
    print(f"\nUser: {user_input}\n")
    
    # Run the graph with config
    result = app.invoke(initial_state, config.to_runnable_config())
    
    # Print messages from queue
    print("\n--- Node Messages ---")
    while not config.message_queue.empty():
        try:
            msg = config.message_queue.get_nowait()
            print(f"[{msg['type']}] {msg['content']}")
        except Empty:
            break
    
    # Print the final response
    print("\n--- Final Response ---")
    for message in result["messages"]:
        if hasattr(message, "content") and message.content:
            print(f"Assistant: {message.content}")


if __name__ == "__main__":
    main()
