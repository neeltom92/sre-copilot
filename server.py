"""
SRE Copilot API Server - FastAPI backend with A2UI/AG-UI streaming support.

This server wraps the existing LangGraph-based SREAgent with:
- A2UI protocol for rich UI components (tables, alerts, cards)
- AG-UI protocol for SSE streaming
- REST API endpoints for the React frontend
"""

import asyncio
import json
import uuid
import logging
import re
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import Config
from agent import SREAgent, create_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# A2UI Component Generator
# ============================================================================

class A2UIGenerator:
    """Generates A2UI components from agent responses."""

    @staticmethod
    def create_alert(severity: str, title: str, message: str, component_id: str = None) -> dict:
        """Create an A2UI alert component."""
        return {
            "id": component_id or f"alert_{uuid.uuid4().hex[:8]}",
            "type": "alert",
            "props": {
                "severity": severity,
                "title": title,
                "message": message
            },
            "children": []
        }

    @staticmethod
    def create_table(headers: list, rows: list, component_id: str = None) -> tuple:
        """Create an A2UI table component with data binding."""
        table_id = component_id or f"table_{uuid.uuid4().hex[:8]}"
        data_path = f"/tables/{table_id}"

        component = {
            "id": table_id,
            "type": "table",
            "binding": data_path,
            "props": {},
            "children": []
        }

        data = {
            "tables": {
                table_id: {
                    "headers": headers,
                    "rows": rows
                }
            }
        }

        return component, data

    @staticmethod
    def create_card(title: str, children: list, component_id: str = None) -> dict:
        """Create an A2UI card component."""
        card_id = component_id or f"card_{uuid.uuid4().hex[:8]}"
        return {
            "id": card_id,
            "type": "card",
            "props": {},
            "children": children
        }

    @staticmethod
    def create_text(text: str, variant: str = "body1", component_id: str = None) -> dict:
        """Create an A2UI text component."""
        return {
            "id": component_id or f"text_{uuid.uuid4().hex[:8]}",
            "type": "text",
            "props": {"text": text, "variant": variant},
            "children": []
        }

    @staticmethod
    def create_container(children: list, direction: str = "column", component_id: str = None) -> dict:
        """Create an A2UI container component."""
        return {
            "id": component_id or f"container_{uuid.uuid4().hex[:8]}",
            "type": "container",
            "props": {"direction": direction},
            "children": children
        }


class ResponseParser:
    """Parses agent responses to extract structured data for A2UI."""

    @staticmethod
    def extract_table_data(text: str) -> Optional[tuple]:
        """
        Try to extract table data from markdown-style tables in the response.
        Returns (headers, rows) or None if no table found.
        """
        # Look for markdown table pattern
        lines = text.strip().split('\n')
        table_lines = []
        in_table = False

        for line in lines:
            if '|' in line:
                in_table = True
                table_lines.append(line)
            elif in_table and line.strip() == '':
                break

        if len(table_lines) < 2:
            return None

        # Parse headers
        header_line = table_lines[0]
        headers = [cell.strip() for cell in header_line.split('|') if cell.strip()]

        # Skip separator line (if present)
        start_row = 1
        if len(table_lines) > 1 and re.match(r'^[\s\-|:]+$', table_lines[1]):
            start_row = 2

        # Parse rows
        rows = []
        for line in table_lines[start_row:]:
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if cells:
                rows.append(cells)

        return (headers, rows) if rows else None

    @staticmethod
    def detect_alert_type(text: str) -> Optional[dict]:
        """Detect if response should be shown as an alert."""
        text_lower = text.lower()

        if any(word in text_lower for word in ['error', 'failed', 'critical', 'down']):
            return {"severity": "error", "title": "Error Detected"}
        elif any(word in text_lower for word in ['warning', 'high', 'elevated']):
            return {"severity": "warning", "title": "Warning"}
        elif any(word in text_lower for word in ['success', 'healthy', 'resolved', 'completed']):
            return {"severity": "success", "title": "Success"}
        elif any(word in text_lower for word in ['found', 'info', 'status']):
            return {"severity": "info", "title": "Information"}

        return None


# ============================================================================
# FastAPI Application
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting SRE Copilot API Server...")
    config = Config.from_env()
    app.state.config = config
    app.state.agent = create_agent(config)
    logger.info("Agent initialized successfully")

    status = app.state.agent.get_status()
    logger.info(f"Agent status: {status}")

    yield

    # Shutdown
    logger.info("Shutting down SRE Copilot API Server...")


app = FastAPI(
    title="SRE Copilot API",
    description="AI-powered SRE assistant with A2UI/AG-UI streaming",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    thread_id: Optional[str] = None
    extensions: Optional[list[str]] = None


class ChatResponse(BaseModel):
    message: str
    thread_id: str


# ============================================================================
# SSE Event Generators
# ============================================================================

def format_sse_event(event_type: str, data: dict) -> str:
    """Format data as an SSE event."""
    event_data = {"type": event_type, **data}
    return f"data: {json.dumps(event_data)}\n\n"


async def stream_agent_response(
    agent: SREAgent,
    user_message: str,
    thread_id: str,
    use_a2ui: bool = True
) -> AsyncGenerator[str, None]:
    """
    Stream agent response with A2UI/AG-UI protocol support.

    Emits:
    - TEXT_MESSAGE_START: Start of text message
    - TEXT_MESSAGE_CONTENT: Text content chunks
    - TEXT_MESSAGE_END: End of text message
    - TOOL_CALL_START: When a tool is being called
    - TOOL_CALL_END: When tool call completes
    - A2UI_MESSAGE: Rich UI components
    """
    # Emit run start
    yield format_sse_event("RUN_START", {
        "threadId": thread_id,
        "runId": str(uuid.uuid4())
    })

    # Emit text message start
    message_id = str(uuid.uuid4())
    yield format_sse_event("TEXT_MESSAGE_START", {
        "messageId": message_id,
        "threadId": thread_id
    })

    full_response = ""
    tool_detected = False

    try:
        # Stream from the agent
        for chunk in agent.chat_stream(user_message, thread_id):
            if chunk:
                # Check for tool usage indication
                if "*Using " in chunk and "...*" in chunk:
                    tool_name = chunk.replace("*Using ", "").replace("...*", "").strip()
                    tool_call_id = str(uuid.uuid4())
                    yield format_sse_event("TOOL_CALL_START", {
                        "toolCallId": tool_call_id,
                        "toolName": tool_name,
                        "threadId": thread_id
                    })
                    tool_detected = True
                    # Don't add tool indicator to response
                    continue

                # Emit text content
                yield format_sse_event("TEXT_MESSAGE_CONTENT", {
                    "messageId": message_id,
                    "delta": chunk,
                    "threadId": thread_id
                })
                full_response += chunk

                # Small delay for visual effect
                await asyncio.sleep(0.01)

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield format_sse_event("TEXT_MESSAGE_CONTENT", {
            "messageId": message_id,
            "delta": f"\n\nError: {str(e)}",
            "threadId": thread_id
        })

    # Emit text message end
    yield format_sse_event("TEXT_MESSAGE_END", {
        "messageId": message_id,
        "threadId": thread_id
    })

    # Generate A2UI components if enabled
    if use_a2ui and full_response:
        a2ui_components = generate_a2ui_from_response(full_response)
        if a2ui_components:
            for event in a2ui_components:
                yield format_sse_event("A2UI_MESSAGE", {
                    "a2ui": event,
                    "threadId": thread_id
                })

    # Emit run end
    yield format_sse_event("RUN_END", {
        "threadId": thread_id
    })


def generate_a2ui_from_response(response: str) -> list:
    """Generate A2UI components from agent response."""
    events = []
    components = []
    data = {}

    # Try to extract table data
    table_data = ResponseParser.extract_table_data(response)
    if table_data:
        headers, rows = table_data
        table_comp, table_data_binding = A2UIGenerator.create_table(headers, rows)
        components.append(table_comp)
        data.update(table_data_binding)

        # Add title if we can detect what kind of data
        if any(word in response.lower() for word in ['pod', 'kubernetes', 'k8s']):
            title = A2UIGenerator.create_text("Kubernetes Resources", "h6", "title_pods")
            components.insert(0, title)
        elif any(word in response.lower() for word in ['incident', 'pagerduty']):
            title = A2UIGenerator.create_text("Incidents", "h6", "title_incidents")
            components.insert(0, title)

    # Detect if we should show an alert
    alert_info = ResponseParser.detect_alert_type(response)
    if alert_info and not table_data:
        # Extract first sentence as message
        first_sentence = response.split('.')[0] + '.'
        alert = A2UIGenerator.create_alert(
            alert_info["severity"],
            alert_info["title"],
            first_sentence[:200]
        )
        components.append(alert)

    # Build the component tree
    if components:
        child_ids = [c["id"] for c in components]
        root = A2UIGenerator.create_container(child_ids, "column", "root")

        # Surface update event
        all_components = [root] + components
        events.append({
            "type": "surfaceUpdate",
            "components": all_components
        })

        # Data model update event (if we have table data)
        if data:
            events.append({
                "type": "dataModelUpdate",
                "data": data
            })

    return events


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "SRE Copilot API",
        "version": "1.0.0",
        "protocols": ["A2UI", "AG-UI"],
        "endpoints": {
            "stream": "POST /stream - SSE streaming chat",
            "chat": "POST /chat - Simple chat",
            "status": "GET /status - Agent status",
            "health": "GET /health - Health check"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/status")
async def status():
    """Get agent status."""
    agent: SREAgent = app.state.agent
    return agent.get_status()


@app.post("/chat")
async def chat(request: ChatRequest):
    """Simple chat endpoint (non-streaming)."""
    agent: SREAgent = app.state.agent

    # Get the last user message
    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message provided")

    thread_id = request.thread_id or str(uuid.uuid4())
    response = agent.chat(user_message, thread_id)

    return ChatResponse(message=response, thread_id=thread_id)


@app.post("/stream")
async def stream(request: ChatRequest):
    """
    Streaming chat endpoint with A2UI/AG-UI protocol support.

    Returns Server-Sent Events (SSE) with:
    - TEXT_MESSAGE_* events for text streaming
    - TOOL_CALL_* events for tool usage
    - A2UI_MESSAGE events for rich UI components
    """
    agent: SREAgent = app.state.agent

    # Get the last user message
    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message provided")

    thread_id = request.thread_id or str(uuid.uuid4())
    use_a2ui = request.extensions and "a2ui" in request.extensions

    return StreamingResponse(
        stream_agent_response(agent, user_message, thread_id, use_a2ui),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("""
╔══════════════════════════════════════════════════════════════╗
║              SRE Copilot API Server                          ║
╠══════════════════════════════════════════════════════════════╣
║  Protocols: A2UI + AG-UI                                     ║
║  Port: 8000                                                  ║
║                                                              ║
║  Endpoints:                                                  ║
║    GET  /         - API info                                 ║
║    GET  /health   - Health check                             ║
║    GET  /status   - Agent status                             ║
║    POST /chat     - Simple chat                              ║
║    POST /stream   - SSE streaming with A2UI                  ║
║                                                              ║
║  Frontend: http://localhost:3000                             ║
╚══════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(app, host="0.0.0.0", port=8000)
