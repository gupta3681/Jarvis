# LangSmith Tracing Setup

LangSmith provides powerful tracing and monitoring for your LangChain applications.

## What You Get

- 🔍 **Full Trace Visibility**: See every LLM call, tool execution, and chain step
- 📊 **Performance Metrics**: Latency, token usage, costs
- 🐛 **Debugging**: Inspect inputs/outputs at each step
- 📈 **Analytics**: Track usage patterns over time
- 🔄 **Feedback Loop**: Annotate and improve responses

## Setup Steps

### 1. Get Your LangSmith API Key

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Sign up or log in
3. Go to Settings → API Keys
4. Create a new API key

### 2. Configure Your .env

Add these lines to your `.env` file:

```env
# LangSmith Configuration
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_your-actual-key-here
LANGCHAIN_PROJECT=jarvis-assistant
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

### 3. Run Jarvis

That's it! Tracing is automatically enabled when you run:

```bash
uv run python server.py
# or
bash run_jarvis.sh
```

## Viewing Traces

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Select your project: `jarvis-assistant`
3. View traces in real-time as you interact with Jarvis

## What Gets Traced

### Every Conversation:
- User input
- Core memory injection
- LLM reasoning
- Tool calls (add_memory, log_food, etc.)
- Tool results
- Final response

### Example Trace:
```
User: "Remember that I love pizza"
  ├─ Core Memory Loaded
  ├─ LLM Call (gpt-4o)
  │   └─ Tool Call: update_core_memory
  ├─ Tool Execution: update_core_memory
  │   └─ Result: "Updated core memory: preferences.favorite_food = pizza"
  └─ Final Response: "Got it! I'll remember that you love pizza."
```

## Disable Tracing

To disable tracing, set in `.env`:

```env
LANGCHAIN_TRACING_V2=false
```

Or remove the LangSmith configuration entirely.

## Tips

1. **Project Names**: Use different projects for dev/prod
   ```env
   LANGCHAIN_PROJECT=jarvis-dev
   # or
   LANGCHAIN_PROJECT=jarvis-production
   ```

2. **Cost Tracking**: LangSmith shows token usage and estimated costs

3. **Debugging**: Click any trace to see full details of what went wrong

4. **Feedback**: Add thumbs up/down to traces to build evaluation datasets

## Troubleshooting

### Traces Not Showing Up?

1. Check your API key is correct
2. Ensure `LANGCHAIN_TRACING_V2=true`
3. Verify internet connection
4. Check LangSmith status page

### Too Many Traces?

You can filter by:
- Date range
- Status (success/error)
- Latency
- Token count

## Learn More

- [LangSmith Docs](https://docs.smith.langchain.com)
- [LangSmith Cookbook](https://github.com/langchain-ai/langsmith-cookbook)
