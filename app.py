"""
SRE Copilot - AI-powered SRE Chat Assistant

An intelligent assistant for Site Reliability Engineers that integrates with
Datadog and PagerDuty to help with on-call duties, incident response, and
observability troubleshooting.

Architecture:
- LangChain + LangGraph for agent orchestration
- Claude Sonnet as the LLM
- Streamlit for the UI
"""

import uuid
import streamlit as st
from config import Config
from agent import SREAgent, get_okta_user


# Page configuration
st.set_page_config(
    page_title="SRE Copilot - AI-Powered Infrastructure Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a Bug": None,
        "About": None,
    },
)

# Modern CSS styling for beautiful chat UI
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global styling */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    }

    .main .block-container {
        color: #e2e8f0;
        max-width: 900px;
        padding-top: 1rem;
        padding-bottom: 100px;
    }

    /* Better layout for larger screens */
    @media (min-width: 1200px) {
        .main .block-container {
            max-width: 1000px;
        }
    }

    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .main-header h1 {
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .main-header p {
        color: #ffffff;
        font-size: 1rem;
        margin: 0.5rem 0 0 0;
        font-weight: 400;
    }

    .coming-soon-badge {
        display: inline-block;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-left: 0.5rem;
        text-transform: uppercase;
    }

    /* Chat input - fixed at bottom */
    .stChatFloatingInputContainer {
        bottom: 0 !important;
        padding: 1rem 2rem 1.5rem 2rem !important;
        background: linear-gradient(180deg, transparent, #0f172a 20%) !important;
        max-width: 900px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        margin-left: 0 !important;
    }

    @media (min-width: 1200px) {
        .stChatFloatingInputContainer {
            max-width: 1000px !important;
        }
    }

    /* Chat messages styling */
    .stChatMessage {
        padding: 1rem 1.2rem;
        border-radius: 16px;
        margin-bottom: 0.8rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }

    [data-testid="stChatMessageContent"] {
        font-size: 0.95rem;
        line-height: 1.7;
    }

    [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessageContent"] li,
    [data-testid="stChatMessageContent"] span {
        color: #ffffff !important;
    }

    /* User message styling */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background: linear-gradient(135deg, #1e40af, #3b82f6) !important;
        border: none;
    }

    /* Assistant message styling */
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background: linear-gradient(135deg, #374151, #4b5563) !important;
        border: none;
    }

    /* Chat input styling */
    .stChatInput {
        border-radius: 25px !important;
        border: 2px solid #e2e8f0 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease;
        background: #ffffff !important;
    }

    .stChatInput:focus-within {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
    }

    /* Sidebar styling - slate dark theme */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }

    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }

    [data-testid="stSidebar"] .stMarkdown h1 {
        color: #ffffff !important;
        font-size: 1.4rem;
        font-weight: 700;
    }

    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #f1f5f9 !important;
        font-weight: 600;
    }

    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] .stCaption p,
    [data-testid="stSidebar"] .stCaption code,
    [data-testid="stSidebar"] code {
        color: #cbd5e1 !important;
    }

    [data-testid="stSidebar"] button {
        background: rgba(255, 255, 255, 0.1) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }

    [data-testid="stSidebar"] button:hover {
        background: rgba(255, 255, 255, 0.2) !important;
    }

    [data-testid="stSidebar"] button p,
    [data-testid="stSidebar"] button span,
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
        color: #ffffff !important;
    }

    /* Sidebar hint text in yellow */
    .sidebar-hint-yellow {
        color: #fef08a !important;
        font-style: italic;
        font-size: 0.85rem;
        margin-top: -0.5rem;
    }

    /* Status badges */
    .status-connected {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
    }

    .status-warning {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }

    .status-error {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }

    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
        border: none;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    /* Example query buttons */
    .example-btn {
        background: #ffffff !important;
        color: #475569 !important;
        border: 1px solid #e2e8f0 !important;
        text-align: left !important;
        font-size: 0.85rem !important;
        transition: all 0.2s ease !important;
    }

    .example-btn:hover {
        background: #f8fafc !important;
        border-color: #6366f1 !important;
        color: #6366f1 !important;
        transform: translateX(4px);
    }

    /* Roadmap section - dark amber theme */
    .roadmap-section {
        background: linear-gradient(135deg, #78350f, #b45309);
        border: none;
        border-radius: 12px;
        padding: 1.2rem;
        margin-top: 1.5rem;
        box-shadow: 0 4px 16px rgba(180, 83, 9, 0.3);
    }

    .roadmap-section h3 {
        color: #fef08a;
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 0.8rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .roadmap-item {
        display: flex;
        align-items: flex-start;
        gap: 0.5rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(254, 240, 138, 0.2);
        color: #fef3c7;
        font-size: 0.85rem;
    }

    .roadmap-item:last-child {
        border-bottom: none;
    }

    .roadmap-icon {
        color: #fbbf24;
        font-size: 1rem;
    }

    /* User info card */
    .user-card {
        background: linear-gradient(135deg, #1e3a8a, #3b82f6);
        border-radius: 8px;
        padding: 0.8rem;
        margin-bottom: 1rem;
    }

    .user-card p {
        margin: 0;
        font-size: 0.85rem;
        color: #ffffff !important;
    }

    .user-card strong {
        color: #fef08a !important;
    }

    /* Metrics styling */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }

    /* Divider styling */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
        margin: 1rem 0;
    }

    /* Spinner/loading */
    .stSpinner > div {
        border-color: #6366f1 !important;
    }

    /* Info/warning boxes */
    .stAlert {
        border-radius: 12px;
        border-width: 2px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }

    /* Welcome info box - dark blue theme */
    [data-testid="stAlert"][data-baseweb="notification"] {
        background: linear-gradient(135deg, #1e3a8a, #3b82f6) !important;
        border: none !important;
    }

    [data-testid="stAlert"] p {
        color: #ffffff !important;
    }

    [data-testid="stAlert"] strong {
        color: #fef08a !important;
    }

    [data-testid="stAlert"] li {
        color: #e0f2fe !important;
    }

    /* Code block styling - prevent strikethrough and ensure proper formatting */
    code, pre, .stCodeBlock, [data-testid="stCodeBlock"] {
        text-decoration: none !important;
    }

    [data-testid="stChatMessageContent"] code {
        text-decoration: none !important;
        background: #1e293b !important;
        color: #e2e8f0 !important;
        padding: 0.2rem 0.4rem !important;
        border-radius: 4px !important;
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace !important;
    }

    [data-testid="stChatMessageContent"] pre {
        text-decoration: none !important;
        background: #1e293b !important;
        color: #e2e8f0 !important;
        padding: 1rem !important;
        border-radius: 8px !important;
        overflow-x: auto !important;
    }

    [data-testid="stChatMessageContent"] pre code {
        background: transparent !important;
        color: #e2e8f0 !important;
        padding: 0 !important;
    }

    /* Integration Badges */
    .integration-badges {
        display: flex;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
        justify-content: center;
    }

    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease;
    }

    .badge:hover {
        transform: translateY(-2px);
    }

    .badge-datadog {
        background: linear-gradient(135deg, #632ca6, #7c3aed);
        color: #ffffff;
    }

    .badge-pagerduty {
        background: linear-gradient(135deg, #059669, #10b981);
        color: #ffffff;
    }

    .badge-k8s {
        background: linear-gradient(135deg, #1e40af, #3b82f6);
        color: #ffffff;
    }

    /* Modern Header Redesign */
    .main-header {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e40af 100%);
        padding: 2.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }

    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: radial-gradient(circle at top right, rgba(99, 102, 241, 0.2), transparent 50%);
        pointer-events: none;
    }

    .header-title {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 0.5rem;
        position: relative;
        z-index: 1;
    }

    .robot-icon {
        font-size: 3rem;
        animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }

    .header-title h1 {
        color: #ffffff;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        background: linear-gradient(135deg, #ffffff, #cbd5e1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .header-subtitle {
        color: #cbd5e1;
        font-size: 1.1rem;
        font-weight: 500;
        margin: 0 0 1.5rem 0;
        position: relative;
        z-index: 1;
        letter-spacing: 0.5px;
    }

    .header-description {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1rem;
        position: relative;
        z-index: 1;
    }

    .capability-item {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        padding: 1rem;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }

    .capability-item:hover {
        background: rgba(255, 255, 255, 0.12);
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
    }

    .cap-icon {
        font-size: 1.5rem;
        line-height: 1;
    }

    .capability-item strong {
        display: block;
        color: #ffffff;
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }

    .cap-detail {
        display: block;
        color: #cbd5e1;
        font-size: 0.85rem;
        line-height: 1.4;
    }

    /* Sidebar Enhancements */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    [data-testid="stSidebar"] .stMarkdown h1 {
        background: linear-gradient(135deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 1.6rem !important;
        font-weight: 800 !important;
        margin-bottom: 0.5rem !important;
    }

    /* Sidebar Buttons - More Modern */
    [data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15)) !important;
        color: #ffffff !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        padding: 0.6rem 1rem !important;
        transition: all 0.3s ease !important;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(139, 92, 246, 0.25)) !important;
        border-color: rgba(99, 102, 241, 0.5) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.3) !important;
    }

    /* Primary Button - More Vibrant */
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4) !important;
    }

    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #7c3aed, #a855f7) !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5) !important;
    }

    /* Capability Cards in Sidebar */
    .capability-card {
        background: linear-gradient(135deg, rgba(30, 58, 138, 0.3), rgba(59, 130, 246, 0.2));
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }

    .capability-card:hover {
        background: linear-gradient(135deg, rgba(30, 58, 138, 0.4), rgba(59, 130, 246, 0.3));
        border-color: rgba(59, 130, 246, 0.5);
        transform: translateX(4px);
    }

    .capability-card-title {
        color: #60a5fa;
        font-weight: 600;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.3rem;
    }

    .capability-card-desc {
        color: #cbd5e1;
        font-size: 0.8rem;
        line-height: 1.4;
    }

    /* Selectbox Improvements */
    [data-testid="stSidebar"] .stSelectbox {
        margin-bottom: 0.75rem;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] {
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
    }

    [data-testid="stSidebar"] [data-baseweb="select"]:hover {
        border-color: rgba(99, 102, 241, 0.5) !important;
        background: rgba(255, 255, 255, 0.12) !important;
    }

    /* Metric Cards */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.08);
        padding: 0.75rem;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    [data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
    }

    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)


def get_agent() -> SREAgent:
    """Create the SRE agent."""
    return SREAgent(config=Config.from_env())


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "agent" not in st.session_state:
        st.session_state.agent = get_agent()
    if "k8s_context" not in st.session_state:
        st.session_state.k8s_context = None
    if "k8s_namespace" not in st.session_state:
        st.session_state.k8s_namespace = None
    if "k8s_namespaces" not in st.session_state:
        st.session_state.k8s_namespaces = []


def render_sidebar():
    """Render the sidebar with status and controls."""
    with st.sidebar:
        # Logo and title
        st.markdown("# 🤖 SRE Copilot")
        st.markdown('<p style="color: #94a3b8; font-size: 0.9rem; margin-top: -1rem; margin-bottom: 1.5rem; font-style: italic;">AI-Powered Infrastructure Assistant</p>', unsafe_allow_html=True)

        # Show logged-in user
        current_user = get_okta_user()
        if current_user != "anonymous":
            st.markdown(f"""
            <div class="user-card">
                <p>👤 <strong>{current_user}</strong></p>
            </div>
            """, unsafe_allow_html=True)

        # Show integration status
        agent_status = st.session_state.agent.get_status()

        # Quick actions
        st.markdown("### ⚡ Quick Actions")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 New Chat", use_container_width=True, type="primary"):
                st.session_state.messages = []
                st.session_state.thread_id = str(uuid.uuid4())
                st.rerun()

        with col2:
            if st.button("🔃 Refresh", use_container_width=True):
                st.cache_resource.clear()
                st.session_state.agent = get_agent()
                st.rerun()

        st.markdown("---")

        # Kubernetes cluster selection
        if agent_status.get("kubernetes_configured", False):
            st.markdown("### ☸️ Kubernetes")

            k8s_tools = st.session_state.agent._kubernetes
            if k8s_tools:
                contexts_result = k8s_tools.get_contexts()

                if "error" not in contexts_result:
                    contexts = contexts_result.get("contexts", [])
                    context_names = [ctx["name"] for ctx in contexts]

                    if context_names:
                        # Cluster dropdown
                        selected_context = st.selectbox(
                            "Cluster Context",
                            options=context_names,
                            key="k8s_context"
                        )

                        # Namespace dropdown
                        if selected_context:
                            ns_result = k8s_tools.get_namespaces(context=selected_context)
                            if "error" not in ns_result:
                                namespaces = ns_result.get("namespaces", [])
                                if namespaces:
                                    selected_namespace = st.selectbox(
                                        "Namespace",
                                        options=namespaces,
                                        key="k8s_namespace"
                                    )
                                    st.markdown(f"""
                                    <div style="background: rgba(59, 130, 246, 0.15); padding: 0.75rem; border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.3); margin-top: 0.5rem;">
                                        <div style="color: #60a5fa; font-weight: 600; font-size: 0.85rem; margin-bottom: 0.25rem;">✅ Context Active</div>
                                        <div style="color: #cbd5e1; font-size: 0.8rem;">📍 <code>{selected_context}</code> → <code>{selected_namespace}</code></div>
                                        <div style="color: #94a3b8; font-size: 0.75rem; margin-top: 0.25rem; font-style: italic;">K8s queries will use this context automatically</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            else:
                                st.error(f"⚠️ {ns_result.get('error')}")
                    else:
                        st.info("No Kubernetes contexts found in kubeconfig")
                else:
                    st.error(f"⚠️ {contexts_result.get('error')}")

            st.markdown("---")

        # Capabilities Section
        st.markdown("### 🎯 Capabilities")

        capabilities = []
        if agent_status.get("kubernetes_configured"):
            capabilities.append(("☸️", "Kubernetes pod monitoring", "Real-time logs and pod status"))
        if agent_status.get("pagerduty_configured"):
            capabilities.append(("🚨", "Incident management", "PagerDuty alerts and on-call"))
        if agent_status.get("datadog_configured"):
            capabilities.append(("📊", "Metric analysis", "Datadog APM traces"))

        # Always show these
        capabilities.append(("🔎", "Log exploration", "Search and analyze logs"))
        capabilities.append(("🔗", "Alert correlation", "Connect related incidents"))

        for icon, title, desc in capabilities:
            st.markdown(f"""
            <div class="capability-card">
                <div class="capability-card-title">{icon} {title}</div>
                <div class="capability-card-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Example queries - Updated with better examples
        st.markdown("### 💡 Example Queries")
        st.markdown("<p class='sidebar-hint-yellow'>Click to try, or type your own question...</p>", unsafe_allow_html=True)

        examples = [
            ("📋", "Show pod logs for nginx-deployment"),
            ("🔄", "Show previous logs for crashed pod"),
            ("👥", "Who's on-call right now?"),
            ("📈", "Show p99 latency for my-service in prod"),
            ("🚨", "Show active PagerDuty incidents"),
            ("🔎", "Search APM traces for slow requests"),
            ("📊", "List all APM services in production"),
        ]

        for icon, example in examples:
            if st.button(f"{icon} {example}", key=f"ex_{example[:20]}", use_container_width=True):
                st.session_state.pending_message = example
                st.rerun()

        st.markdown("---")

        # Roadmap section
        with st.expander("🗺️ Roadmap - Coming Soon"):
            st.markdown("""
            **💬 Mimir / Infra-bot Slack Integration**
            Slack-based ops for seamless team collaboration

            **📚 Confluence Runbook Analysis**
            Automated runbook reviews and incident correlation
            """)

        st.markdown("---")

        # Session info
        st.markdown("### 📊 Session")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Messages", len(st.session_state.messages))
        with col2:
            st.metric("Tools", agent_status["available_tools"])

        st.caption(f"Thread: `{st.session_state.thread_id[:8]}...`")

        st.markdown("---")

        # Footer
        st.caption("🤖 AI SRE to assist in oncall activities")


def render_integration_badges():
    """Render integration status badges at the top."""
    agent_status = st.session_state.agent.get_status()

    badges_html = '<div class="integration-badges">'

    # Datadog badge
    if agent_status.get("datadog_configured"):
        badges_html += '<span class="badge badge-datadog">DATADOG</span>'

    # PagerDuty badge
    if agent_status.get("pagerduty_configured"):
        badges_html += '<span class="badge badge-pagerduty">PAGERDUTY</span>'

    # Kubernetes badge
    if agent_status.get("kubernetes_configured"):
        badges_html += '<span class="badge badge-k8s">KUBERNETES</span>'

    badges_html += '</div>'

    st.markdown(badges_html, unsafe_allow_html=True)


def render_header():
    """Render the main header with welcome message."""
    st.markdown("""
    <div class="main-header">
        <div class="header-title">
            <span class="robot-icon">🤖</span>
            <h1>SRE Copilot</h1>
        </div>
        <p class="header-subtitle">AI-Powered Infrastructure Assistant</p>
        <div class="header-description">
            <div class="capability-item">
                <span class="cap-icon">📊</span>
                <div>
                    <strong>Datadog APM</strong>
                    <span class="cap-detail">Trace issues, analyze latency, search slow requests</span>
                </div>
            </div>
            <div class="capability-item">
                <span class="cap-icon">🚨</span>
                <div>
                    <strong>PagerDuty</strong>
                    <span class="cap-detail">Manage incidents, check on-call schedules</span>
                </div>
            </div>
            <div class="capability-item">
                <span class="cap-icon">☸️</span>
                <div>
                    <strong>Kubernetes</strong>
                    <span class="cap-detail">Real-time pod logs, list pods and namespaces</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_roadmap():
    """Render the roadmap section as a dropdown."""
    with st.expander("🗺️ Roadmap - Coming Soon"):
        st.markdown("""
        **💬 Mimir / Infra-bot Slack Integration**
        Slack-based ops for seamless team collaboration

        **📚 Confluence Runbook Analysis**
        Automated runbook reviews and incident correlation
        """)


def render_chat():
    """Render the main chat interface."""
    # Render integration badges
    render_integration_badges()

    # Render header
    render_header()

    # Check if Claude is configured
    agent_status = st.session_state.agent.get_status()
    if not agent_status["claude_configured"]:
        st.error("""
        **Claude API not configured**

        Please set the `ANTHROPIC_API_KEY` environment variable to use SRE Copilot.
        """)
        return

    if not agent_status["graph_ready"]:
        st.error("Agent graph not ready. Please check your configuration.")
        return

    # Show integration warnings
    if not agent_status["datadog_configured"] and not agent_status["pagerduty_configured"]:
        st.warning("""
        **No integrations configured** - SRE Copilot works best with Datadog and/or PagerDuty.
        """)

    # Create a container for chat messages with some padding at bottom for input
    chat_container = st.container()

    with chat_container:
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar="🧑‍💻" if message["role"] == "user" else "🤖"):
                st.markdown(message["content"])

    # Handle pending message from sidebar buttons
    if "pending_message" in st.session_state:
        user_input = st.session_state.pending_message
        del st.session_state.pending_message
    else:
        user_input = None

    # Chat input
    if prompt := st.chat_input("Ask about incidents, metrics, pods, on-call schedules..."):
        user_input = prompt

    # Process user input
    if user_input:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_input)

        # Prepare message with K8s context if available
        message_to_agent = user_input

        # Add K8s context information if selected and query seems K8s-related
        k8s_keywords = ["pod", "namespace", "cluster", "k8s", "kubernetes", "container", "log"]
        if any(keyword in user_input.lower() for keyword in k8s_keywords):
            if st.session_state.k8s_context and st.session_state.k8s_namespace:
                context_info = f"\n\n[User has selected Kubernetes context: '{st.session_state.k8s_context}' and namespace: '{st.session_state.k8s_namespace}' in the sidebar]"
                message_to_agent = user_input + context_info

        # Get assistant response
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🔍 Analyzing your request..."):
                try:
                    response = st.session_state.agent.chat(
                        message_to_agent,
                        thread_id=st.session_state.thread_id
                    )

                    # Check for conversation limit exceeded
                    if response == "CONVERSATION_LIMIT_EXCEEDED":
                        st.error("⚠️ **Conversation limit reached**")
                        st.info("This conversation has become too long. Please start a new chat to continue.")
                        if st.button("🔄 Start New Chat", type="primary", key="limit_new_chat"):
                            st.session_state.messages = []
                            st.session_state.thread_id = str(uuid.uuid4())
                            st.rerun()
                        response = "This conversation has exceeded the token limit. Please start a new chat to continue."
                    else:
                        st.markdown(response)

                except Exception as e:
                    error_str = str(e)
                    # Also handle token limit error if it bubbles up here
                    if "prompt is too long" in error_str or ("tokens" in error_str and "maximum" in error_str):
                        st.error("⚠️ **Conversation limit reached**")
                        st.info("This conversation has become too long. Please start a new chat to continue.")
                        if st.button("🔄 Start New Chat", type="primary", key="limit_new_chat_err"):
                            st.session_state.messages = []
                            st.session_state.thread_id = str(uuid.uuid4())
                            st.rerun()
                        response = "This conversation has exceeded the token limit. Please start a new chat to continue."
                    else:
                        response = f"Error: {error_str}"
                        st.error(response)

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()



def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
