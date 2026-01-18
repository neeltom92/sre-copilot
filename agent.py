"""
SRE Copilot Agent - LangGraph-powered SRE assistant.

Architecture:
- LangChain for tool abstraction
- LangGraph for agent state management and conversation flow
- Claude Sonnet as the LLM backbone
"""

from typing import Annotated, Optional, TypedDict
from dataclasses import dataclass, field
import uuid
import os
import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from config import Config
from tools.datadog_tools import DatadogTools
from tools.pagerduty_tools import PagerDutyTools
from tools.kubernetes_tools import KubernetesTools
from tools.sqs_tools import SQSTools
from tools.langchain_tools import create_datadog_tools, create_pagerduty_tools, create_kubernetes_tools, create_sqs_tools

logger = logging.getLogger(__name__)

# Try to import jwt for Okta header decoding
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("PyJWT not installed - Okta email extraction will fall back to identity header")


def get_okta_user() -> str:
    """
    Extract user email from Okta headers injected by AWS ALB.

    Priority:
    1. Decode x-amzn-oidc-data JWT to get email
    2. Fall back to x-amzn-oidc-identity header
    3. Fall back to environment variables
    4. Return "anonymous"

    Returns:
        str: User email or "anonymous"
    """
    try:
        import streamlit as st

        # Try to extract from Streamlit context headers
        try:
            headers = st.context.headers

            if headers:
                # Priority 1: Decode x-amzn-oidc-data JWT to get email
                # The x-amzn-oidc-identity header only contains the 'sub' claim (Okta user ID),
                # so we MUST decode the JWT to get the email address for proper user tracking
                oidc_data = headers.get('x-amzn-oidc-data') or headers.get('X-Amzn-Oidc-Data')
                if oidc_data and JWT_AVAILABLE:
                    try:
                        # Decode JWT without signature verification (ALB already verified it)
                        decoded = jwt.decode(oidc_data, options={"verify_signature": False})
                        # Try email first, then preferred_username (which is often email in Okta)
                        email = decoded.get('email') or decoded.get('preferred_username')
                        if email:
                            logger.info(f"Extracted email from Okta JWT: {email}")
                            return email
                    except Exception as jwt_error:
                        logger.debug(f"Failed to decode Okta JWT: {jwt_error}")

                # Priority 2: Try x-forwarded-user header (may contain email)
                # Note: x-amzn-oidc-identity only contains Okta user ID, not email
                forwarded_user = (
                    headers.get('x-forwarded-user') or
                    headers.get('X-Forwarded-User')
                )
                if forwarded_user and '@' in forwarded_user:
                    logger.info(f"Extracted email from x-forwarded-user: {forwarded_user}")
                    return forwarded_user

                # Priority 3: Fall back to x-amzn-oidc-identity (Okta user ID, not email)
                user_identity = (
                    headers.get('x-amzn-oidc-identity') or
                    headers.get('X-Amzn-Oidc-Identity')
                )
                if user_identity:
                    logger.info(f"Extracted Okta user ID from identity header (not email): {user_identity}")
                    return user_identity
        except Exception as header_error:
            logger.debug(f"Could not access headers: {header_error}")

        # Try environment variables (if ALB injects them)
        env_user = os.getenv("OIDC_USER") or os.getenv("REMOTE_USER")
        if env_user:
            logger.info(f"Extracted user from environment: {env_user}")
            return env_user

        return "anonymous"

    except Exception as e:
        logger.warning(f"Error extracting user ID: {e}")
        return "anonymous"


# System prompt for the SRE agent
SYSTEM_PROMPT = """You are an expert SRE (Site Reliability Engineering) assistant helping engineers with on-call duties, incident response, and observability.

You have access to Datadog and PagerDuty tools to help investigate issues, check system health, and manage incidents.

## Your Capabilities:

### Datadog APM (Application Performance Monitoring)
- List APM services and request counts
- Get service statistics (latency, throughput, error rate)
- Search traces by service, duration, or errors
- Get detailed trace information with spans

### PagerDuty
- List active incidents and their status
- Check who is on-call
- View service health
- Acknowledge and resolve incidents
- Review recent alerts

### Kubernetes (Direct Cluster Access)
- List available cluster contexts from local kubeconfig
- List namespaces in a selected cluster
- Fetch pod logs in real-time (no Datadog lag)
- View logs from crashed containers (previous logs)
- Support multi-container pods

### AWS SQS (Read-Only)
- List SQS queues in the account
- Get queue attributes (message counts, age, DLQ config)
- Peek at messages without removing them
- Inspect dead-letter queue contents

## Kubernetes - Two Ways to Access:

### 1. Direct Kubernetes Access (Real-time, No Lag) - USE THIS FOR POD OPERATIONS
**Tools:** k8s_get_contexts, k8s_get_namespaces, k8s_list_pods, k8s_get_pod_logs

When users ask for **pods** or **pod logs**:
- Use the direct K8s tools (k8s_get_*)
- **IMPORTANT**: If the message includes "[User has selected Kubernetes context: '...' and namespace: '...' in the sidebar]", use those values directly - DO NOT ask the user to specify them again
- If no sidebar context is provided and context/namespace not mentioned in the query, then ask the user OR use k8s_get_contexts to list available
- For crashed pods, use previous=true to get previous container logs
- For multi-container pods, specify container_name
- **DO NOT ask for environment (prod/stg/dev)** - use cluster context names instead (e.g., "minikube", "production-eks-cluster")

Workflow:
1. List contexts → k8s_get_contexts
2. List namespaces → k8s_get_namespaces
3. List pods → k8s_list_pods (shows pod status, restarts, age)
4. Get pod logs → k8s_get_pod_logs

Examples:
- "List all pods in kagent namespace" → Use k8s_list_pods with context and namespace
- "Show logs for pod nginx" → Use k8s_get_pod_logs with context and namespace
- "Show previous logs for crashed pod" → Use k8s_get_pod_logs with previous=true


**APM queries**: For APM traces, services, and latency queries, use the service name and environment tag:
- Examples: `env:prod`, `env:stg`, `env:dev` (tags vary by organization)
- Common mappings: production→prod, staging→stg, development→dev
- If the user doesn't specify an environment, ask: "Which environment would you like to check?"

## Common Query Patterns:

**Service latency queries**: When users ask about p99/p95 latency for a service:
- Use `datadog_get_service_stats` tool
- Show latency metrics (avg, p95, p99), throughput, and error rate
- Ask for environment if not specified (e.g., prod, stg, dev)
- Present results clearly with units (ms for latency, req/s for throughput, % for error rate)

**Slow request investigation**: When users ask about slow requests or high latency:
- Use `datadog_search_traces` to find slow traces (e.g., query: "service:api @duration:>1s")
- Use `datadog_get_trace_details` to drill down into specific slow traces
- Identify bottleneck spans and their duration

**APM service overview**: When users want to see all instrumented services:
- Use `datadog_get_apm_services` to list services with request counts
- Filter by environment if specified
- Help identify high-traffic services or services with low activity

## Guidelines:

1. **Be proactive**: When investigating issues, use multiple tools to gather comprehensive information.

2. **Provide context**: Explain what you're checking and why, especially during incident response.

3. **Suggest next steps**: After gathering information, recommend actions the engineer can take.

4. **Be concise but thorough**: Present findings clearly, highlight critical information.

5. **Correlate data**: Connect information across Datadog and PagerDuty to provide a full picture.

6. **Safety first**: For destructive actions (acknowledging/resolving incidents), confirm with the user before proceeding.

7. **Ask for environment**: For Kubernetes queries, always confirm the environment (prod/stg/dev) if not specified.

## Response Format:

When presenting findings:
- Use clear headings and bullet points
- Highlight critical issues with emphasis
- Include relevant links when available
- Summarize key metrics with actual values
- Provide actionable recommendations

Remember: You're helping engineers during potentially stressful on-call situations. Be clear, direct, and helpful."""


# LangGraph State
class AgentState(TypedDict):
    """State for the SRE agent graph."""
    messages: Annotated[list, add_messages]
    thread_id: str


@dataclass
class SREAgent:
    """LangGraph-powered SRE assistant with Datadog and PagerDuty tools."""

    config: Config
    _llm: Optional[ChatAnthropic] = None
    _tools: list = field(default_factory=list)
    _graph: Optional[StateGraph] = None
    _compiled_graph: Optional[any] = None
    _checkpointer: Optional[MemorySaver] = None
    _datadog: Optional[DatadogTools] = None
    _pagerduty: Optional[PagerDutyTools] = None
    _kubernetes: Optional[KubernetesTools] = None
    _sqs: Optional[SQSTools] = None

    def __post_init__(self):
        """Initialize the agent components."""
        self._setup_tools()
        self._setup_llm()
        self._setup_graph()

    def _setup_tools(self):
        """Initialize Datadog and PagerDuty tools."""
        self._tools = []

        if self.config.is_datadog_configured():
            self._datadog = DatadogTools(
                api_key=self.config.datadog_api_key,
                app_key=self.config.datadog_app_key,
                site=self.config.datadog_site,
            )
            self._tools.extend(create_datadog_tools(self._datadog))

        if self.config.is_pagerduty_configured():
            self._pagerduty = PagerDutyTools(api_key=self.config.pagerduty_api_key)
            self._tools.extend(create_pagerduty_tools(self._pagerduty))

        if self.config.is_kubernetes_configured():
            self._kubernetes = KubernetesTools(kubeconfig_path=self.config.kubeconfig_path)
            self._tools.extend(create_kubernetes_tools(self._kubernetes))

        if self.config.is_sqs_configured():
            self._sqs = SQSTools(
                aws_region=self.config.aws_region,
                aws_access_key=self.config.aws_access_key or None,
                aws_secret_key=self.config.aws_secret_key or None,
                aws_profile=self.config.aws_profile or None,
            )
            self._tools.extend(create_sqs_tools(self._sqs))

    def _setup_llm(self):
        """Initialize the Claude LLM with tools."""
        if not self.config.is_anthropic_configured():
            return

        self._llm = ChatAnthropic(
            model=self.config.claude_model,
            api_key=self.config.anthropic_api_key,
            max_tokens=4096,
            temperature=0,
        )

        if self._tools:
            self._llm = self._llm.bind_tools(self._tools)

    def _setup_graph(self):
        """Build the LangGraph agent graph."""
        if not self._llm:
            return

        # Create the graph
        graph_builder = StateGraph(AgentState)

        # Define the agent node
        def agent_node(state: AgentState) -> dict:
            """The main agent node that calls the LLM."""
            messages = state["messages"]

            # Add system message if not present
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

            response = self._llm.invoke(messages)
            return {"messages": [response]}

        # Define the tool condition
        def should_use_tools(state: AgentState) -> str:
            """Determine if we should use tools or end."""
            last_message = state["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        # Add nodes
        graph_builder.add_node("agent", agent_node)

        if self._tools:
            tool_node = ToolNode(tools=self._tools)
            graph_builder.add_node("tools", tool_node)

            # Add edges
            graph_builder.add_edge(START, "agent")
            graph_builder.add_conditional_edges("agent", should_use_tools, {"tools": "tools", END: END})
            graph_builder.add_edge("tools", "agent")
        else:
            graph_builder.add_edge(START, "agent")
            graph_builder.add_edge("agent", END)

        # Setup memory checkpointer for conversation persistence
        self._checkpointer = MemorySaver()

        # Compile the graph
        self._compiled_graph = graph_builder.compile(checkpointer=self._checkpointer)
        self._graph = graph_builder

    def chat(self, user_message: str, thread_id: Optional[str] = None) -> str:
        """
        Send a message and get the response.

        Args:
            user_message: The user's message
            thread_id: Optional thread ID for conversation persistence

        Returns:
            The assistant's response
        """
        if not self._compiled_graph:
            return "Error: Agent not properly configured. Please check your API keys."

        if not thread_id:
            thread_id = str(uuid.uuid4())

        # Prepare input
        input_state = {
            "messages": [HumanMessage(content=user_message)],
            "thread_id": thread_id,
        }

        config = {"configurable": {"thread_id": thread_id}}

        # Run the graph
        try:
            result = self._compiled_graph.invoke(input_state, config)

            # Extract the final response
            messages = result.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    # Handle content that might be a list
                    if isinstance(msg.content, list):
                        text_parts = [
                            block.get("text", "") if isinstance(block, dict) else str(block)
                            for block in msg.content
                        ]
                        return "\n".join(filter(None, text_parts))
                    return msg.content

            return "I apologize, but I couldn't generate a response. Please try again."

        except Exception as e:
            logger.error(f"Chat error: {e}")
            error_str = str(e)
            # Check for token limit exceeded error
            if "prompt is too long" in error_str or ("tokens" in error_str and "maximum" in error_str):
                return "CONVERSATION_LIMIT_EXCEEDED"
            return f"Error: {error_str}"

    def chat_stream(self, user_message: str, thread_id: Optional[str] = None):
        """
        Send a message and stream the response.

        Args:
            user_message: The user's message
            thread_id: Optional thread ID for conversation persistence

        Yields:
            Response chunks as they arrive
        """
        if not self._compiled_graph:
            yield "Error: Agent not properly configured. Please check your API keys."
            return

        if not thread_id:
            thread_id = str(uuid.uuid4())

        input_state = {
            "messages": [HumanMessage(content=user_message)],
            "thread_id": thread_id,
        }

        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Stream events from the graph
            for event in self._compiled_graph.stream(input_state, config, stream_mode="values"):
                messages = event.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, AIMessage):
                        if last_msg.content:
                            if isinstance(last_msg.content, list):
                                for block in last_msg.content:
                                    if isinstance(block, dict) and block.get("text"):
                                        yield block["text"]
                            else:
                                yield last_msg.content
                        # Show tool usage
                        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                            for tool_call in last_msg.tool_calls:
                                yield f"\n\n*Using {tool_call['name']}...*\n"

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield f"Error: {str(e)}"

    def get_conversation_history(self, thread_id: str) -> list[dict]:
        """Get conversation history for a thread."""
        if not self._checkpointer:
            return []

        try:
            state = self._compiled_graph.get_state({"configurable": {"thread_id": thread_id}})
            messages = state.values.get("messages", [])

            history = []
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    history.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage) and msg.content:
                    content = msg.content
                    if isinstance(content, list):
                        content = "\n".join(
                            block.get("text", "") if isinstance(block, dict) else str(block)
                            for block in content
                        )
                    history.append({"role": "assistant", "content": content})

            return history
        except Exception:
            return []

    def clear_history(self, thread_id: str):
        """Clear conversation history for a thread."""
        # MemorySaver doesn't support deletion, so we just start a new thread
        pass

    def get_status(self) -> dict:
        """Get agent status and available integrations."""
        return {
            "claude_configured": self.config.is_anthropic_configured(),
            "claude_model": self.config.claude_model,
            "datadog_configured": self.config.is_datadog_configured(),
            "pagerduty_configured": self.config.is_pagerduty_configured(),
            "kubernetes_configured": self.config.is_kubernetes_configured(),
            "sqs_configured": self.config.is_sqs_configured(),
            "available_tools": len(self._tools),
            "graph_ready": self._compiled_graph is not None,
        }


# Backwards compatibility - keep the old interface working
def create_agent(config: Config) -> SREAgent:
    """Factory function to create an SRE agent."""
    return SREAgent(config=config)
