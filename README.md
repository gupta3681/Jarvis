# 🤖 Jarvis - Personal AI Assistant

A personal AI assistant built with LangGraph, featuring a two-tier memory system and real-time WebSocket communication.

## Features

- 🧠 **Two-Tier Memory System**
  - **Core Memory**: Instant access to identity, work, preferences (like human memory)
  - **Episodic Memory**: Semantic search through experiences using Mem0
  
- 💬 **Conversational AI**: Natural chitchat + task execution
- 🔧 **Tool Calling**: Food logging, workout tracking, calendar management, memory management
- 📅 **Google Calendar Integration**: Create, view, update, and delete calendar events
- 🌐 **Real-time WebSocket**: Live updates from backend to frontend
- 🎨 **Modern UI**: Clean Next.js interface with voice support

## Quick Start

### 1. Install Dependencies
```bash
uv sync
```

### 2. Configure Environment Variables
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your keys:
# OPENAI_API_KEY=your-api-key-here
# OPENAI_MODEL=gpt-4o

# Optional: Enable LangSmith tracing
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=your-langsmith-key
# LANGCHAIN_PROJECT=jarvis-assistant
```

### 3. Setup Your Core Memory (Optional)
```bash
uv run python setup_my_memory.py
```

### 4. Setup Google Calendar (Optional)
See [CALENDAR_SETUP.md](CALENDAR_SETUP.md) for detailed instructions.

```bash
python setup_calendar.py
```

### 5. Run Jarvis

**Option A: Run Both Backend + Frontend**
```bash
bash run_jarvis.sh
```

**Option B: Run Separately**

Terminal 1 (Backend):
```bash
uv run python server.py
```

Terminal 2 (Frontend):
```bash
uv run streamlit run frontend/app.py
```

## Project Structure

```
Jarvis/
├── frontend/           # Streamlit UI
│   └── app.py
├── memory/            # Memory systems
│   └── core_memory.py
├── tools/             # Agent tools
│   └── tools.py
├── prompts/           # LLM prompts
│   └── main_agent_prompt.py
├── graph.py           # LangGraph workflow
├── server.py          # FastAPI WebSocket server
├── config.py          # Configuration
└── main.py            # CLI interface
```

## Memory System

### Core Memory (Instant Access)
Stored in `~/.jarvis/core_memory_*.json`

Categories:
- `identity`: name, age, location
- `work`: company, role, schedule
- `preferences`: workout time, diet type
- `health`: allergies, fitness goals
- `relationships`: important people
- `context`: timezone, language

### Episodic Memory (Semantic Search)
Stored in `~/.mem0/` using Qdrant vector DB

For experiences, conversations, learned facts.

## Tools Available

### Memory Tools
- `update_core_memory()` - Set instant-access facts
- `get_core_memory_info()` - View core memory
- `add_memory()` - Store experiences
- `search_memory()` - Search through memories

### Calendar Tools
- `create_calendar_event()` - Create new events
- `list_calendar_events()` - View upcoming events
- `delete_calendar_event()` - Remove events
- `update_calendar_event()` - Modify events

### Lifestyle Handlers
- `nutrition_handler()` - Food logging and nutrition tracking
- `workout_handler()` - Exercise logging and workout tracking

### Utility Tools
- `web_search()` - Search the web for real-time information
- `think_tool()` - Internal reasoning and planning
- `task_complete()` - Signal task completion

## Development

### Test CLI Mode
```bash
uv run python main.py
```

### Test WebSocket (HTML)
Open `test_client.html` in browser after starting backend.

## Tech Stack

- **LangGraph**: Agent orchestration
- **LangChain**: LLM framework
- **LangSmith**: Tracing and monitoring (optional)
- **FastAPI**: WebSocket backend
- **Streamlit**: Frontend UI
- **Mem0**: Episodic memory
- **OpenAI**: LLM (gpt-4o)
