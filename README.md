# SRE Copilot

An AI-powered SRE chat assistant that integrates with Datadog APM, PagerDuty, Kubernetes, and AWS SQS to help with application performance monitoring and on-call troubleshooting.

## 🚀 Quick Start (3 Commands!)

```bash
git clone https://github.com/neeltom92/sre-copilot.git
cd sre-copilot
make first-time-setup
vim .env  # Add your API keys
make run
```

**→ Open http://localhost:8501 and start chatting!**

## Demo

![SRE Copilot Demo](demo.gif)

## Features

- **Claude AI Chat**: Natural language interface powered by Claude Sonnet
- **Datadog APM Integration**: Analyze service latency, search traces, investigate slow requests
- **Kubernetes Integration**: Fetch real-time pod logs directly from your clusters
- **PagerDuty Integration**: Manage incidents, check on-call schedules, view services
- **AWS SQS Integration**: Inspect queue attributes, message counts, and peek at messages (read-only)
- **Streamlit UI**: Beautiful web interface with real-time streaming responses
- **Tool Orchestration**: AI automatically uses the right tools to answer your questions
- **Multi-turn Conversations**: Maintains context across your entire session

## Quick Start

### Prerequisites

- **Python 3.9+** - Check with `python --version`
- **[Anthropic API Key](https://console.anthropic.com/)** - Required for Claude AI
- **Streamlit** - Installed automatically by `make first-time-setup`
- **Datadog API keys** - Optional, for APM features (latency, traces, service stats)
- **PagerDuty API token** - Optional, for incident management
- **Kubernetes kubeconfig** - Optional, for real-time pod log access
- **AWS credentials** - Optional, for SQS queue inspection (supports IAM roles, profiles, or explicit keys)

> **Note:** Streamlit is a Python web framework that powers the beautiful chat UI. It will be installed automatically when you run `make first-time-setup` or `make install`.

### Local Setup (Using Make - Easiest!)

**First-time users - just run this:**

```bash
# 1. Clone the repository
git clone https://github.com/neeltom92/sre-copilot.git
cd sre-copilot

# 2. Run one-command setup (installs everything!)
make first-time-setup

# 3. Edit .env and add your API keys
vim .env  # or: code .env, or: open -e .env

# Required:
#   ANTHROPIC_API_KEY=sk-ant-your-key-here
#
# Optional (add for more features):
#   DATADOG_API_KEY=your-datadog-key (for APM traces & latency)
#   DATADOG_APP_KEY=your-datadog-app-key
#   PAGERDUTY_API_KEY=your-pagerduty-key (for incident management)

# 4. Run the app
make run
```

Open http://localhost:8501 in your browser and start chatting!

**That's it!** The `make first-time-setup` command does everything:

1. ✅ **Checks Python version** (ensures Python 3.9+ is installed)
2. ✅ **Installs core dependencies** (from requirements.txt)
3. ✅ **Installs Streamlit UI framework** (with verification)
4. ✅ **Creates .env configuration file** (from template)
5. ✅ **Verifies installation** (shows installed packages)
6. ✅ **Shows clear next steps** (with helpful links and commands)


**Example output:**
```
═══════════════════════════════════════════════
Step 1/5: Checking Python version...
═══════════════════════════════════════════════
✅ Python is installed

═══════════════════════════════════════════════
Step 2/5: Installing core dependencies...
═══════════════════════════════════════════════
✅ Core dependencies installed

═══════════════════════════════════════════════
Step 3/5: Installing Streamlit (UI framework)...
═══════════════════════════════════════════════
📦 Installing Streamlit - this may take a minute...
✅ Streamlit installed successfully!
✅ Streamlit verified and ready to use!

════════════════════════════════════════════════
✅ ✅ ✅  SETUP COMPLETE! ✅ ✅ ✅
════════════════════════════════════════════════
```

**Manual setup (if you prefer step-by-step):**

```bash
make install     # Install dependencies
make setup       # Create .env file
# Edit .env with your API key
make run         # Start the app
```

### Available Make Commands

```bash
make help              # Show all available commands
make first-time-setup  # 🎯 Complete setup for first-time users (recommended!)
make install           # Install Python dependencies + Streamlit
make setup             # Create .env from template
make run               # Run Streamlit app (localhost:8501)
make run-react         # Run React + FastAPI (localhost:3000)
make test              # Test your API key configuration
make clean             # Remove cache and temporary files
make dev               # Run with auto-reload (for development)
```

### Manual Setup (Without Make)

If you prefer not to use Make:

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
vim .env

# Run the app
streamlit run app.py
```

### React Frontend + FastAPI (Advanced)

For the alternative React UI with FastAPI backend:

```bash
# Using Make
make run-react

# Or manually
./start.sh
```

- **Frontend**: http://localhost:3000 (React UI)
- **Backend API**: http://localhost:8000 (FastAPI with SSE streaming)

### What You Need

At minimum, you only need:
- ✅ **ANTHROPIC_API_KEY** - Get from https://console.anthropic.com/

Optional integrations:
- **Datadog APM** - Add `DATADOG_API_KEY` and `DATADOG_APP_KEY` for application performance monitoring (traces, latency, service stats)
- **PagerDuty** - Add `PAGERDUTY_API_KEY` for incident management features
- **Kubernetes** - Automatically enabled if `~/.kube/config` exists for real-time pod log access
- **AWS SQS** - Automatically enabled; uses standard AWS credential chain (IAM roles, `~/.aws/credentials`, or explicit keys)

## Architecture

```
sre-copilot/
├── app.py                     # Streamlit UI (main interface)
├── agent.py                   # LangGraph agent with tool orchestration
├── config.py                  # Configuration management
├── tools/
│   ├── kubernetes_tools.py    # Kubernetes API integration
│   ├── datadog_tools.py       # Datadog APM integration
│   ├── pagerduty_tools.py     # PagerDuty API integration
│   ├── sqs_tools.py           # AWS SQS integration
│   └── langchain_tools.py     # LangChain tool wrappers
├── server.py                  # FastAPI backend (optional React UI)
├── frontend/                  # React frontend (optional)
├── requirements.txt           # Python dependencies
└── Makefile                   # Build and run commands
```

### Tech Stack

- **Streamlit**: Web UI framework for the chat interface
- **LangGraph**: Agent orchestration with tool calling and state management
- **LangChain**: Tool abstraction and LLM framework
- **Claude Sonnet**: AI model for natural language understanding

## Available Tools

### Datadog APM Tools

| Tool | Description |
|------|-------------|
| `datadog_get_apm_services` | List APM services with request counts and traffic levels |
| `datadog_get_service_stats` | Get service latency (avg/p95/p99), throughput, and error rate |
| `datadog_search_traces` | Search APM traces for slow requests or errors |
| `datadog_get_trace_details` | Get detailed trace info with all spans to identify bottlenecks |

### Kubernetes Tools (Direct Access)

| Tool | Description |
|------|-------------|
| `k8s_get_contexts` | List available Kubernetes cluster contexts from kubeconfig |
| `k8s_get_namespaces` | List namespaces in a selected cluster |
| `k8s_list_pods` | List all pods in a namespace with status, restarts, and age |
| `k8s_get_pod_logs` | Fetch real-time pod logs (no Datadog lag) |

### PagerDuty Tools

| Tool | Description |
|------|-------------|
| `pagerduty_get_incidents` | List active incidents |
| `pagerduty_get_incident_details` | Get detailed incident info with timeline |
| `pagerduty_get_oncall` | Check who is currently on-call |
| `pagerduty_get_services` | List services and their status |
| `pagerduty_acknowledge_incident` | Acknowledge an incident |
| `pagerduty_resolve_incident` | Resolve an incident |
| `pagerduty_get_recent_alerts` | View recent alert triggers |

### AWS SQS Tools (Read-Only)

| Tool | Description |
|------|-------------|
| `sqs_list_queues` | List SQS queues in the account, optionally filter by name prefix |
| `sqs_get_queue_attributes` | Get queue stats: message counts, oldest message age, DLQ config |
| `sqs_peek_messages` | Peek at messages without removing them (read-only) |
| `sqs_get_queue_url` | Get queue URL from queue name |

## Example Queries

```
# Datadog APM
"Show p99 latency for my-service in production"
"Search for slow APM traces over 1 second"
"List all APM services in staging environment"
"Show me traces with errors for the api service"

# Kubernetes
"List all pods in kagent namespace in minikube"
"Show logs for pod nginx in namespace default in minikube"
"Show previous logs for crashed pod my-app"
"List all namespaces in minikube cluster"

# PagerDuty
"Show me active PagerDuty incidents"
"Who is on-call right now?"
"Get details for incident P12345"
"Acknowledge incident P12345"

# AWS SQS
"List all SQS queues"
"Show me queues with 'orders' in the name"
"How many messages are in my-queue?"
"What's the age of the oldest message in the DLQ?"
"Peek at messages in the orders-queue"
```

## 💡 Using Kubernetes Features

### Important: Include Cluster Name in Your Messages

The Kubernetes sidebar dropdown is **visual only** - the agent can't see it directly. Always include the cluster context name in your message:

**❌ Won't work:**
```
"list all pods from ns kagent"  (Missing cluster name)
```

**✅ Works:**
```
"list all pods from ns kagent in minikube"
"show logs for pod nginx in namespace default using minikube context"
```

### Kubernetes Query Workflow

1. **List available clusters:**
   ```
   "What Kubernetes clusters are available?"
   "List all contexts"
   ```

2. **List namespaces in a cluster:**
   ```
   "List all namespaces in minikube"
   ```

3. **List pods in a namespace:**
   ```
   "List all pods in kagent namespace in minikube"
   ```

4. **Get pod logs:**
   ```
   "Show logs for pod nginx in namespace default in minikube"
   "Show last 200 lines of logs for pod api-server"
   ```

### Kubernetes Setup

Kubernetes features are **automatically enabled** if `~/.kube/config` exists.

**Check your setup:**
```bash
make check-k8s
```

**If you don't have Kubernetes:**
- The app works fine without it!
- Just use Datadog APM and PagerDuty features

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude (Anthropic) API key (preferred) |
| `CLAUDE_API_KEY` | No | Alias for `ANTHROPIC_API_KEY` |
| `CLAUDE_MODEL` | No | Claude model (default: claude-sonnet-4-20250514) |
| `DATADOG_API_KEY` | No | Datadog API key (preferred) |
| `DD_API_KEY` | No | Alias for `DATADOG_API_KEY` |
| `DATADOG_APP_KEY` | No | Datadog application key (preferred) |
| `DD_APP_KEY` | No | Alias for `DATADOG_APP_KEY` |
| `DATADOG_SITE` | No | Datadog site (default: datadoghq.com) |
| `PAGERDUTY_API_KEY` | No | PagerDuty API token |
| `AWS_REGION` | No | AWS region for SQS (default: us-east-1) |
| `AWS_ACCESS_KEY_ID` | No | AWS access key (optional, can use IAM roles/profiles) |
| `AWS_SECRET_ACCESS_KEY` | No | AWS secret key (optional) |
| `AWS_PROFILE` | No | AWS profile name (optional) |
| `SQS_ENABLED` | No | Enable/disable SQS integration (default: true) |

## Docker

### Using Pre-built Docker Image

The easiest way to run SRE Copilot is with Docker:

```bash
# Pull the latest image (built automatically via GitHub Actions)
docker pull ghcr.io/neeltom92/sre-copilot:latest

# Run with just Claude (minimal setup)
docker run -p 8501:8501 \
  -e ANTHROPIC_API_KEY=your-anthropic-key \
  ghcr.io/neeltom92/sre-copilot:latest

# Run with all integrations (Datadog + PagerDuty)
docker run -p 8501:8501 \
  -e ANTHROPIC_API_KEY=your-anthropic-key \
  -e DATADOG_API_KEY=your-datadog-key \
  -e DATADOG_APP_KEY=your-datadog-app-key \
  -e PAGERDUTY_API_KEY=your-pagerduty-key \
  ghcr.io/neeltom92/sre-copilot:latest
```

**Open:** http://localhost:8501

### Docker Compose (Recommended)

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  sre-copilot:
    image: ghcr.io/neeltom92/sre-copilot:latest
    ports:
      - "8501:8501"
    environment:
      # Required
      - ANTHROPIC_API_KEY=your-anthropic-key

      # Optional - Datadog
      - DATADOG_API_KEY=your-datadog-key
      - DATADOG_APP_KEY=your-datadog-app-key
      - DATADOG_SITE=datadoghq.com

      # Optional - PagerDuty
      - PAGERDUTY_API_KEY=your-pagerduty-key
    restart: unless-stopped
```

Then run:
```bash
docker-compose up -d
```

### Building Docker Image Locally

```bash
# Build the image
docker build -t sre-copilot .

# Run it
docker run -p 8501:8501 \
  -e ANTHROPIC_API_KEY=your-key \
  sre-copilot
```

### Available Image Tags

- `latest` - Latest stable release from main branch
- `main` - Latest commit on main branch
- `main-<sha>` - Specific commit (replace `<sha>` with actual commit hash)

```bash
# Use latest version (recommended)
docker pull ghcr.io/neeltom92/sre-copilot:latest

# Use specific commit (if needed)
docker pull ghcr.io/neeltom92/sre-copilot:main-<commit-sha>
```

## Kubernetes Deployment

Deploy SRE Copilot to Kubernetes using the included Helm chart.

- **Docker Image:** `ghcr.io/neeltom92/sre-copilot:latest` (built via GitHub Actions)
- **Helm Chart:** Available in `deploy/chart/`
- **Access:** ClusterIP + port-forwarding (Ingress optional)

### Quick Deploy to Kubernetes

```bash
# 1. Create namespace
kubectl create namespace sre-copilot

# 2. Create secret with API keys (minimum: ANTHROPIC_API_KEY required)
kubectl create secret generic sre-copilot-secrets \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-your-key-here \
  --from-literal=DATADOG_API_KEY=your-datadog-key \
  --from-literal=DATADOG_APP_KEY=your-datadog-app-key \
  --from-literal=PAGERDUTY_API_KEY=your-pagerduty-key \
  -n sre-copilot

# 3. Install Helm chart
helm install sre-copilot ./deploy/chart \
  --namespace sre-copilot

# 4. Access the application (port-forwarding)
kubectl port-forward svc/sre-copilot 8501:80 -n sre-copilot
```

**→ Open http://localhost:8501 in your browser!**

For production deployment with Ingress, see `deploy/chart/README.md`

## Development

### Testing Configuration

Test if your API keys are configured correctly:

```bash
# Using Make
make test

# Or manually
python test_config.py
```

This will show you which integrations are active.

### Running Locally

```bash
# Streamlit UI (port 8501)
make run

# Development mode with auto-reload
make dev

# React + FastAPI (ports 3000 + 8000)
make run-react

# Manual start (without Make)
streamlit run app.py
streamlit run app.py --server.port 8502  # Custom port
```

### Project Structure

```
tools/
├── datadog_tools.py       # Datadog API client (monitors, metrics, APM, K8s)
├── pagerduty_tools.py     # PagerDuty API client (incidents, on-call)
├── sqs_tools.py           # AWS SQS client (queues, messages)
└── langchain_tools.py     # LangChain tool wrappers for LLM

agent.py                   # LangGraph agent with Claude + tool orchestration
app.py                     # Streamlit UI
server.py                  # FastAPI backend (for React frontend)
config.py                  # Environment configuration
```

## 🗺️ Roadmap

### Upcoming Observability Integrations

We're planning to add support for more observability platforms:

- **Prometheus & Grafana** - Metrics collection and visualization
- **New Relic** - APM and infrastructure monitoring
- **Splunk** - Log aggregation and analysis
- **Elastic (ELK Stack)** - Elasticsearch, Logstash, Kibana
- **Dynatrace** - Full-stack monitoring and AIOps
- **Honeycomb** - Observability for distributed systems

### Other Planned Features

**Kubernetes Enhancements:**
- Enhanced operations (pod exec, scaling, restarts)
- Multi-cluster support improvements
- Resource management and troubleshooting

**Infrastructure & Deployment:**
- Ingress controller support (nginx, ALB, Traefik)
- TLS/HTTPS configuration helpers
- Production-ready Helm chart enhancements

**Integrations:**
- Slack integration for collaborative incident response
- Runbook automation and suggestions
- Alert correlation and root cause analysis
- AWS CloudWatch Logs integration
- AWS SNS integration

**UI/UX:**
- Custom dashboards and saved queries
- Improved visualization and charts
- Query history and favorites

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

If you'd like to add support for a new observability tool, check out the existing integrations in `tools/` as examples.

## License

MIT License - Free to use and modify for your organization's needs.
