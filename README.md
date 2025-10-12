# 🤖 Jarvis (I know, I am super innovative with names; ) - Personal AI Assistant

An **agentic AI assistant** built with LangGraph that autonomously manages your daily life through specialized handlers, persistent memory, and real-time communication. Jarvis doesn't just answer questions— makes decisions and most importantly takes action.

## 🎯 Why Is This Agentic?

Unlike traditional chatbots that simply respond to queries, Jarvis is almost a **true autonomous agent**:

- **🎭 Multi-Agent Architecture**: Main orchestrator delegates to specialized sub-agents (Currently - Gmail, Nutrition, Workout handlers)
- **🔄 Autonomous Decision-Making**: Plans multi-step tasks, chains tools, and adapts based on results
- **🧠 Persistent Memory**: Remembers context across conversations and learns from interactions
- **✅ Human-in-the-Loop**: Seeks approval for critical actions (sending emails, deleting events)
- **🔧 Tool Use**: Dynamically selects and executes tools based on user intent
- **🎯 Goal-Oriented**: Breaks down complex requests into actionable steps

## ✨ Key Features

### 🧠 **Two-Tier Memory System**
- **Core Memory**: Instant access to identity, work, preferences (like human working memory)
- **Episodic Memory**: Semantic search through past experiences using Mem0
- **Memory Persistence**: All memories stored locally (for now) and survive restarts 

### 🤖 **Specialized Handler System**
- **Gmail Handler**: Search, read, compose, and send emails with approval workflow
- **Nutrition Handler**: Log meals, track macros, get dietary suggestions. All meals are logged to a google sheet.
- **Workout Handler**: Log exercises, track progress, analyze workout history. All workouts are logged to a google sheet. 
- **Calendar Integration**: Create, view, update, and delete Google Calendar events. 

### 🔄 **Agentic Capabilities**
- **Autonomous Planning**: Uses `think_tool` for complex reasoning
- **Multi-Step Execution**: Chains multiple tools to complete tasks
- **Context Awareness**: Maintains conversation state across interactions

### 🌐 **Overall Architecture**
- **WebSocket Communication**: Live bidirectional updates
- **Next.js Frontend**: Modern, responsive UI with voice support
- **FastAPI Backend**: High-performance async server
- **Streaming Responses**: Real-time token streaming for natural conversations

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

## 🏗️ Architecture

### **Multi-Agent System**
```
User Request
    ↓
Main Agent (Orchestrator)
    ├─→ Gmail Handler (Email management)
    ├─→ Nutrition Handler (Food tracking)
    ├─→ Workout Handler (Exercise logging)
    ├─→ Calendar Tools (Event management)
    └─→ Memory Tools (Context persistence)
```

### **Project Structure**
```
Jarvis/
├── frontend/              # Next.js UI
│   ├── app/              # App router pages
│   ├── components/       # React components
│   └── lib/              # Utilities
├── subgraphs/            # Specialized agent handlers
│   ├── gmail_handler.py  # Email management agent
│   ├── nutrition_handler.py
│   └── workout_handler.py
├── tools/                # Tool implementations
│   ├── gmail_tools.py    # Gmail API integration
│   ├── calendar_tools.py # Google Calendar API
│   ├── memory_tools.py   # Memory operations
│   └── web_search.py     # Web search capability
├── prompts/              # Agent system prompts
│   ├── main_agent_prompt.py
│   └── gmail_handler_prompt.py
├── memory/               # Memory systems
│   └── core_memory.py    # Core memory management
├── graph.py              # Main LangGraph workflow
├── server.py             # FastAPI WebSocket server
└── main.py               # CLI interface
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


## 🛠️ Tech Stack

### **AI & Agent Framework**
- **LangGraph**: Multi-agent orchestration and workflow management
- **OpenAI GPT-4.1**: Primary language model
- **LangSmith**: Tracing and debugging (optional)

### **Backend**
- **FastAPI**: High-performance async WebSocket server
- **Python 3.11+**: Core runtime
- **UV**: Fast Python package manager

### **Frontend**
- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **WebSocket**: Real-time bidirectional communication

### **Memory & Storage**
- **Mem0**: Episodic memory with semantic search
- 
### **Integrations**
- **Gmail API**: Email management
- **Google Calendar API**: Event scheduling
- **Tavily API**: Web search capability

## 🎓 Key Concepts

### **Handler Pattern**
Specialized sub-agents handle domain-specific tasks:
- Each handler has its own prompt, tools, and state
- Handlers can interrupt for user input (approval workflows)
- Main agent orchestrates between handlers

### **Memory Architecture**
- **Core Memory**: Fast key-value store for essential facts
- **Episodic Memory**: Vector-based semantic search for experiences
- **Conversation State**: Maintained across interactions

### **Human-in-the-Loop**
Critical actions require explicit approval:
- Email sending (shows draft first)
- Calendar event deletion
- Sensitive data modifications

### **Tool Composition**
Tools are composable and chainable:
```python
search_memory("workouts") → compose_email(data) → send_email()
```

## 💡 Example Use Cases

### **Email Management**
```
You: "Send an email to john@example.com about our meeting"
Jarvis: [Composes draft] → Shows preview → Waits for approval → Sends
```

### **Nutrition Tracking**
```
You: "I had chicken and rice for lunch"
Jarvis: Logs meal → Estimates macros → Updates daily totals → Suggests dinner
```

### **Workout Logging**
```
You: "Log my workout: bench press 3x10 at 185lbs"
Jarvis: Records exercise → Tracks progress → Compares to previous sessions
```

### **Calendar Management**
```
You: "Schedule a meeting with Sarah tomorrow at 2pm"
Jarvis: Creates event → Adds to Google Calendar → Confirms creation
```

### **Complex Multi-Step Tasks** (Coming Soon)
```
You: "Email my trainer about today's workout"
Jarvis: Retrieves workout data → Composes email → Shows draft → Sends
```

## 🚀 Roadmap

### **Current Features** ✅
- [x] Multi-agent architecture with specialized handlers
- [x] Gmail integration with approval workflow
- [x] Nutrition and workout tracking
- [x] Google Calendar integration
- [x] Two-tier memory system
- [x] Real-time WebSocket communication
- [x] Voice input support

### **In Progress** 🔄
- [ ] Multi-step task orchestration (handler chaining)
- [ ] Cross-handler data sharing
- [ ] Enhanced context awareness

### **Planned Features** 📋
- [ ] Proactive suggestions and reminders
- [ ] Slack/Discord integration
- [ ] Multi-user support


## 🤝 Contributing

Contributions are welcome! This project is a personal AI assistant but can serve as a template for building your own agentic systems.

### **Areas for Contribution**
- New handlers (e.g., finance, travel, shopping)
- Additional integrations (Notion, Spotify, etc.)
- UI/UX improvements
- Performance optimizations
- Documentation

## 📄 License

MIT License - feel free to use this as a foundation for your own AI assistant!

---

**Built with ❤️ using LangGraph and modern AI frameworks**
