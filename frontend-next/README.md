# Jarvis Frontend - Next.js

Modern, component-based chat interface for Jarvis Personal Assistant.

## Features

- ✅ **Persistent WebSocket Connection** - Maintains conversation continuity
- ✅ **Real-time Messaging** - Instant message streaming
- ✅ **Component-Based Architecture** - Reusable, maintainable components
- ✅ **Modern UI** - Clean, responsive design with Tailwind CSS
- ✅ **TypeScript** - Type-safe development
- ✅ **Auto-reconnect** - Handles connection drops gracefully

## Setup

### 1. Install Dependencies

```bash
cd frontend-next
npm install
```

### 2. Run Development Server

```bash
npm run dev
```

The app will be available at [http://localhost:3000](http://localhost:3000)

### 3. Make sure Backend is Running

The backend should be running at `ws://localhost:8000/ws`

```bash
# In the main Jarvis directory
python server.py
```

## Project Structure

```
frontend-next/
├── app/
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Main chat page
│   └── globals.css         # Global styles
├── components/
│   ├── ChatMessage.tsx     # Message bubble component
│   ├── ChatInput.tsx       # Input field component
│   └── Sidebar.tsx         # Sidebar component
├── hooks/
│   └── useWebSocket.ts     # WebSocket connection hook
└── package.json
```

## Components

### ChatMessage
Displays individual messages with different styles for user/assistant/system messages.

### ChatInput
Text input with send button. Supports Enter to send, Shift+Enter for new line.

### Sidebar
Shows connection status and chat controls.

### useWebSocket Hook
Manages WebSocket connection, auto-reconnect, and message state.

## Build for Production

```bash
npm run build
npm start
```

## Technologies

- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **WebSocket API** - Real-time communication
