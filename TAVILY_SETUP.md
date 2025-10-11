# Tavily Web Search Setup

Jarvis now has web search capabilities using Tavily!

## Setup Steps

### 1. Get Tavily API Key
1. Go to https://tavily.com/
2. Sign up for a free account
3. Get your API key from the dashboard
4. Free tier: 1,000 searches/month

### 2. Add to .env file
```bash
TAVILY_API_KEY=tvly-your-api-key-here
```

### 3. Install Package
```bash
uv pip install langchain-community
```

### 4. Restart Backend
```bash
bash run_jarvis.sh
```

## Usage Examples

Now you can ask Jarvis:
- "What's the weather in Boston today?"
- "Latest news about AI"
- "Best restaurants near me"
- "What's the current stock price of Apple?"
- "Tell me about the latest SpaceX launch"

## How It Works

Jarvis will:
1. **Check memory first** for personal information
2. **Search the web** if it needs current/factual information
3. **Return formatted results** with sources

## Tool Details

**Tool Name:** `web_search`

**When Jarvis uses it:**
- Current events and news
- Weather information
- Real-time data (stock prices, sports scores)
- General knowledge and facts
- Definitions and explanations

**When Jarvis uses memory instead:**
- Your personal information
- Past conversations
- Your preferences and habits
- Places you've visited
- People you've mentioned
