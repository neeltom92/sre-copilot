# SRE Copilot - Claude Code Configuration

This Streamlit application is an AI-powered SRE assistant that integrates with Datadog and PagerDuty.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run Locally
```bash
streamlit run app.py
```

### 4. Access Your App
Open http://localhost:8501 in your browser

---

## Project Structure

```
sre-copilot/
├── app.py                     # Streamlit UI
├── agent.py                   # LangGraph agent with tool orchestration
├── config.py                  # Configuration management
├── server.py                  # FastAPI backend for React frontend
├── tools/
│   ├── datadog_tools.py       # Datadog API integration
│   ├── pagerduty_tools.py     # PagerDuty API integration
│   └── langchain_tools.py     # LangChain tool wrappers
├── frontend/                  # React frontend (optional)
├── deploy/                    # Kubernetes deployment configs
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container configuration
└── README.md                  # Full documentation
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `DATADOG_API_KEY` | No | Datadog API key |
| `DATADOG_APP_KEY` | No | Datadog application key |
| `PAGERDUTY_API_KEY` | No | PagerDuty API token |

---

## Development Workflow

1. **Make Changes**
   - Edit `app.py` for Streamlit UI changes
   - Edit `agent.py` for agent behavior
   - Edit `tools/` for API integrations

2. **Test Locally**
   ```bash
   streamlit run app.py
   ```

3. **Run Configuration Test**
   ```bash
   python test_config.py
   ```

---

## Architecture

- **LangGraph**: Agent state machine for tool orchestration
- **LangChain**: LLM framework and tool abstractions
- **Claude Sonnet**: AI backbone for natural language understanding
- **Streamlit**: Web UI framework

See `CODE_FLOW.md` for detailed architecture documentation.
