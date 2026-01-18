# SRE Copilot - Code Flow Documentation

This document explains the architecture and code flow of the SRE Copilot application.

## High-Level Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Streamlit UI  │────▶│   LangGraph      │────▶│  Claude (LLM)   │
│   (app.py)      │     │   Agent Loop     │     │                 │
└─────────────────┘     │   (agent.py)     │     └────────┬────────┘
                        └────────┬─────────┘              │
                                 │                        │ tool calls
                        ┌────────▼─────────┐              │
                        │     Tools        │◀─────────────┘
                        │ - Datadog APIs   │
                        │ - PagerDuty APIs │
                        └──────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit web UI, chat interface, session management |
| `agent.py` | LangGraph agent with tool orchestration |
| `config.py` | Environment variable configuration |
| `tools/datadog_tools.py` | Datadog API wrapper (metrics, logs, APM, K8s) |
| `tools/pagerduty_tools.py` | PagerDuty API wrapper (incidents, on-call) |
| `tools/langchain_tools.py` | Converts native tools to LangChain format |

---

## Request Flow

```
1. User types in chat
        ↓
2. app.py: render_chat() captures input
        ↓
3. agent.chat(user_message, thread_id)
        ↓
4. LangGraph State Machine:
   ┌──────────────────────────────────────┐
   │  START                               │
   │    ↓                                 │
   │  [agent_node] → Call Claude          │
   │    ↓                                 │
   │  [should_use_tools?]                 │
   │    │                                 │
   │    ├─ YES → [tools_node] ───┐        │
   │    │         execute tools  │        │
   │    │                        │        │
   │    │        ┌───────────────┘        │
   │    │        ↓                        │
   │    │   back to agent_node            │
   │    │                                 │
   │    └─ NO → END (final response)      │
   └──────────────────────────────────────┘
        ↓
5. Response displayed in Streamlit
```

---

## Component Details

### 1. Streamlit UI (`app.py`)

The entry point for the application. Handles:

- **Page Configuration**: Sets up the Streamlit page with title, icon, and layout
- **Session State**: Maintains conversation history, thread ID, and agent instance
- **Chat Interface**: Renders messages and captures user input
- **Sidebar**: Shows user info, example queries, and quick actions

```python
# Session state initialization
st.session_state.messages = []           # Chat history
st.session_state.thread_id = str(uuid4()) # Conversation ID
st.session_state.agent = get_agent()      # Agent instance
```

### 2. Agent State Machine (`agent.py`)

The core orchestration layer using **LangGraph**:

```python
class AgentState(TypedDict):
    messages: list      # Conversation history (system, user, AI, tool messages)
    thread_id: str      # For memory persistence across reruns
```

#### Graph Construction

```python
graph_builder = StateGraph(AgentState)
graph_builder.add_node("agent", agent_node)      # Calls Claude LLM
graph_builder.add_node("tools", ToolNode(tools)) # Executes tool calls
graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", should_use_tools)
graph_builder.add_edge("tools", "agent")

# Compile with memory checkpointer
checkpointer = MemorySaver()
compiled_graph = graph_builder.compile(checkpointer=checkpointer)
```

#### Key Functions

| Function | Purpose |
|----------|---------|
| `agent_node()` | Sends messages to Claude, receives response (may include tool calls) |
| `should_use_tools()` | Routes to tools node if Claude wants to call tools, else ends |
| `tools_node` | Executes requested tools via LangChain ToolNode |

#### SREAgent Class

```python
@dataclass
class SREAgent:
    _llm: ChatAnthropic           # Claude model
    _tools: list[BaseTool]        # Datadog + PagerDuty tools
    _compiled_graph: CompiledGraph
    _checkpointer: MemorySaver
    _datadog: DatadogTools
    _pagerduty: PagerDutyTools
```

**Initialization flow:**
1. `_setup_tools()` - Create Datadog and PagerDuty tool instances
2. `_setup_llm()` - Create Claude LLM with bound tools
3. `_setup_graph()` - Build and compile LangGraph state machine

### 3. Tool Architecture

Native Python tools are wrapped for LangChain compatibility:

```
Native Tools                    LangChain Wrappers
┌─────────────────────┐        ┌──────────────────────────┐
│ DatadogTools        │        │ class GetMonitorsTool    │
│ - get_monitors()    │───────▶│   name: str              │
│ - get_service_stats()│       │   description: str       │
│ - search_traces()   │        │   args_schema: BaseModel │
│ - get_k8s_pods()    │        │   _run(): executes tool  │
└─────────────────────┘        └──────────────────────────┘
```

#### Datadog Tools (`tools/datadog_tools.py`)

| Tool | Description |
|------|-------------|
| `get_monitors()` | Fetch monitors and their current status |
| `get_monitor_details()` | Detailed monitor config and thresholds |
| `query_metrics()` | Raw metrics queries with time parsing |
| `get_incidents()` | Datadog incident listing |
| `get_apm_services()` | Discover all instrumented services |
| `get_service_stats()` | Latency (avg/p95/p99), throughput, error rate |
| `search_traces()` | Find traces by service/duration/error |
| `get_k8s_pods()` | Pod status, restarts, phases |
| `get_k8s_nodes()` | Node status, capacity, CPU/memory |
| `get_k8s_deployments()` | Deployment replica health |

#### PagerDuty Tools (`tools/pagerduty_tools.py`)

| Tool | Description |
|------|-------------|
| `get_incidents()` | Active incidents (triggered/acknowledged) |
| `get_incident_details()` | Full incident with timeline and notes |
| `acknowledge_incident()` | Mark incident as acknowledged |
| `resolve_incident()` | Close incident with optional note |
| `get_oncall()` | Current on-call users by schedule |
| `get_services()` | PagerDuty services and status |

### 4. Configuration (`config.py`)

Centralized configuration from environment variables:

```python
@dataclass
class Config:
    # Claude
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-5-20250929"

    # Datadog
    datadog_api_key: str
    datadog_app_key: str
    datadog_site: str = "datadoghq.com"

    # PagerDuty
    pagerduty_api_key: str
```

---

## Example Query Flow

**User asks:** "What's the latency for the bumblebee service in prod?"

```
1. app.py captures input
   └── user_input = "What's the latency for bumblebee in prod?"

2. agent.chat(user_input, thread_id) called
   └── Creates input_state with HumanMessage

3. Graph invoked: agent_node
   └── System prompt + messages sent to Claude
   └── Claude analyzes and decides to call a tool

4. Claude returns tool_calls:
   └── datadog_get_service_stats(service="bumblebee", env="prod")

5. should_use_tools() returns "tools"
   └── Routes to tools_node

6. tools_node executes:
   └── Calls DatadogTools.get_service_stats()
   └── Queries Datadog APM API
   └── Returns ToolMessage with latency data

7. Back to agent_node:
   └── Claude receives tool results
   └── Formulates human-readable response

8. should_use_tools() returns "end"
   └── No more tool calls needed

9. Response returned to app.py
   └── Displayed in Streamlit chat
   └── Added to session messages
```

---

## Environment Mappings

The system prompt includes mappings for environment names:

| User Input | APM env |
|------------|---------|
| prod, production | `env:prod` |
| stg, stage, staging | `env:stg` |
| dev, development | `env:dev` |

---

## Dependencies

### Core Stack
- **streamlit** - Web UI framework
- **langchain** / **langchain-anthropic** - LLM framework
- **langgraph** - State machine and agentic loops

### API Clients
- **datadog-api-client** - Datadog API
- **pdpyras** - PagerDuty API

### Utilities
- **python-dotenv** - Environment file loading
- **pyjwt** - JWT decoding for user context

---

## Key Design Decisions

1. **LangGraph for Agentic Loops**: Handles tool use orchestration automatically with conditional routing

2. **Multiple Span Type Discovery**: APM tools try different span types (web.request, servlet.request, etc.) to find data

3. **Environment Auto-Mapping**: System prompt and tools automatically map user-friendly env names to Datadog identifiers

4. **Memory via MemorySaver**: Persists conversation context across Streamlit reruns using thread_id

5. **Modular Tool Architecture**: Native tools → LangChain wrappers → Agent usage for clean separation of concerns
