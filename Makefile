.PHONY: help install setup run run-react test clean first-time-setup check-k8s verify-all

# Default target - show help
help:
	@echo "🤖 SRE Copilot - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "  make first-time-setup  - 🎯 Complete setup for first-time users (recommended!)"
	@echo "  make install           - 📦 Install Python dependencies"
	@echo "  make setup             - 📝 Create .env file from template"
	@echo "  make run               - 🚀 Run Streamlit app (localhost:8501)"
	@echo "  make run-react         - ⚛️  Run React frontend + FastAPI backend"
	@echo "  make test              - 🔍 Test configuration and API keys"
	@echo "  make check-k8s         - ☸️  Check Kubernetes setup"
	@echo "  make verify-all        - ✅ Verify all integrations (Datadog, PagerDuty, K8s)"
	@echo "  make clean             - 🧹 Remove cache and temporary files"
	@echo ""
	@echo "🎯 First Time User? Run this:"
	@echo "   make first-time-setup"
	@echo ""
	@echo "💡 Quick Start (manual steps):"
	@echo "   1. make install"
	@echo "   2. make setup"
	@echo "   3. Edit .env and add your ANTHROPIC_API_KEY"
	@echo "   4. make run"
	@echo ""

# First-time setup - does everything
first-time-setup:
	@echo "🎯 Starting first-time setup for SRE Copilot..."
	@echo ""
	@echo "═══════════════════════════════════════════════"
	@echo "Step 1/5: Checking Python version..."
	@echo "═══════════════════════════════════════════════"
	@python --version || (echo "❌ Python not found! Please install Python 3.9+" && exit 1)
	@echo "✅ Python is installed"
	@echo ""
	@echo "═══════════════════════════════════════════════"
	@echo "Step 2/5: Installing core dependencies..."
	@echo "═══════════════════════════════════════════════"
	@pip install -r requirements.txt
	@echo "✅ Core dependencies installed"
	@echo ""
	@echo "═══════════════════════════════════════════════"
	@echo "Step 3/5: Installing Streamlit (UI framework)..."
	@echo "═══════════════════════════════════════════════"
	@echo "📦 Installing Streamlit - this may take a minute..."
	@pip install streamlit --upgrade
	@echo "✅ Streamlit installed successfully!"
	@echo ""
	@echo "Verifying Streamlit installation..."
	@streamlit --version || (echo "⚠️  Streamlit verification failed" && exit 1)
	@echo "✅ Streamlit verified and ready to use!"
	@echo ""
	@echo "═══════════════════════════════════════════════"
	@echo "Step 4/5: Creating environment configuration..."
	@echo "═══════════════════════════════════════════════"
	@if [ -f .env ]; then \
		echo "⚠️  .env already exists - keeping existing file"; \
		echo "💡 To recreate: rm .env && make setup"; \
	else \
		cp .env.example .env; \
		echo "✅ .env file created from template"; \
	fi
	@echo ""
	@echo "═══════════════════════════════════════════════"
	@echo "Step 5/5: Verifying setup..."
	@echo "═══════════════════════════════════════════════"
	@echo "Checking installed packages..."
	@pip list | grep -E "streamlit|anthropic|langchain|datadog" || true
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "✅ ✅ ✅  SETUP COMPLETE! ✅ ✅ ✅"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "🎉 Your SRE Copilot is ready to run!"
	@echo ""
	@echo "📝 Next Steps:"
	@echo ""
	@echo "   1️⃣  Add your Anthropic API Key:"
	@echo "      Edit .env and add your ANTHROPIC_API_KEY"
	@echo "      Get your key from: https://console.anthropic.com/"
	@echo ""
	@echo "      Quick edit commands:"
	@echo "        vim .env               (terminal editor)"
	@echo "        code .env              (VS Code)"
	@echo "        open -e .env           (Mac TextEdit)"
	@echo ""
	@echo "   2️⃣  Start the application:"
	@echo "        make run"
	@echo ""
	@echo "   3️⃣  Open your browser:"
	@echo "        http://localhost:8501"
	@echo ""
	@echo "💡 Optional integrations (add to .env):"
	@echo "   • Datadog: DATADOG_API_KEY + DATADOG_APP_KEY"
	@echo "   • PagerDuty: PAGERDUTY_API_KEY"
	@echo "   • Kubernetes: Automatically enabled if ~/.kube/config exists"
	@echo ""
	@echo "☸️  Check Kubernetes setup: make check-k8s"
	@echo "❓ Need help? Run: make help"
	@echo ""

# Install dependencies
install:
	@echo "📦 Installing Python dependencies..."
	@echo ""
	@echo "Installing core packages from requirements.txt..."
	@pip install -r requirements.txt
	@echo ""
	@echo "📦 Installing Streamlit (UI framework)..."
	@pip install streamlit --upgrade
	@echo ""
	@echo "Verifying Streamlit installation..."
	@streamlit --version
	@echo ""
	@echo "✅ All dependencies installed successfully!"
	@echo ""
	@echo "📊 Installed packages:"
	@pip list | grep -E "streamlit|anthropic|langchain|datadog|pagerduty|kubernetes" || echo "Core packages ready"
	@echo ""
	@echo "💡 To verify all integrations: make verify-all"
	@echo ""

# Create .env from template
setup:
	@if [ -f .env ]; then \
		echo "⚠️  .env already exists. Skipping setup."; \
		echo "💡 To recreate: rm .env && make setup"; \
	else \
		echo "📝 Creating .env from template..."; \
		cp .env.example .env; \
		echo "✅ .env created!"; \
		echo ""; \
		echo "⚡ Next steps:"; \
		echo "  1. Edit .env and add your ANTHROPIC_API_KEY"; \
		echo "     Get your key from: https://console.anthropic.com/"; \
		echo "  2. (Optional) Add Datadog and PagerDuty keys"; \
		echo "  3. Run: make run"; \
		echo ""; \
	fi

# Run Streamlit app
run:
	@echo "🚀 Starting SRE Copilot (Streamlit)..."
	@echo "📍 Open http://localhost:8501 in your browser"
	@echo ""
	streamlit run app.py

# Run React frontend + FastAPI backend
run-react:
	@echo "🚀 Starting React frontend + FastAPI backend..."
	@echo "📍 Frontend: http://localhost:3000"
	@echo "📍 Backend:  http://localhost:8000"
	@echo ""
	./start.sh

# Test configuration
test:
	@echo "🔍 Testing configuration..."
	@echo ""
	python test_config.py

# Clean up cache and temporary files
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Development: Run with auto-reload
dev:
	@echo "🔧 Starting in development mode..."
	streamlit run app.py --server.runOnSave true

# Check if .env exists
check-env:
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found!"; \
		echo ""; \
		echo "Run: make setup"; \
		echo "Then edit .env and add your API keys"; \
		exit 1; \
	fi

# Check Kubernetes setup
check-k8s:
	@echo "☸️  Checking Kubernetes Configuration"
	@echo "════════════════════════════════════════"
	@echo ""
	@echo "1️⃣  Checking kubernetes Python package..."
	@if pip show kubernetes > /dev/null 2>&1; then \
		echo "✅ kubernetes package installed"; \
		pip show kubernetes | grep -E "Name|Version"; \
	else \
		echo "❌ kubernetes package not installed"; \
		echo ""; \
		echo "Install with: pip install kubernetes>=28.1.0"; \
		echo "Or run: make install"; \
		exit 1; \
	fi
	@echo ""
	@echo "2️⃣  Checking kubeconfig file..."
	@if [ -f ~/.kube/config ]; then \
		echo "✅ Kubeconfig found at ~/.kube/config"; \
		echo ""; \
		echo "📋 Available contexts:"; \
		kubectl config get-contexts --no-headers 2>/dev/null | awk '{print "   • " $$2}' || \
		echo "   (kubectl not installed - contexts will be read by Python client)"; \
	else \
		echo "⚠️  No kubeconfig found at ~/.kube/config"; \
		echo ""; \
		echo "Kubernetes integration will be disabled."; \
		echo ""; \
		echo "To enable:"; \
		echo "  1. Install kubectl"; \
		echo "  2. Configure cluster access (kubectl creates ~/.kube/config)"; \
		echo "  3. Restart the application"; \
	fi
	@echo ""
	@echo "3️⃣  Testing Kubernetes tools..."
	@python3 -c "from tools.kubernetes_tools import KubernetesTools; \
		from config import Config; \
		c = Config.from_env(); \
		print('✅ KubernetesTools initialized successfully'); \
		print(f'   K8s enabled: {c.k8s_enabled}'); \
		print(f'   K8s configured: {c.is_kubernetes_configured()}'); \
		if c.is_kubernetes_configured(): \
			k8s = KubernetesTools(); \
			result = k8s.get_contexts(); \
			if 'error' not in result: \
				print(f\"   Available contexts: {result.get('count', 0)}\"); \
			else: \
				print(f\"   ⚠️  {result.get('error')}\");" 2>/dev/null || \
		echo "⚠️  Could not test Kubernetes tools (this is OK if not configured)"
	@echo ""
	@echo "════════════════════════════════════════"
	@echo "✅ Kubernetes check complete!"
	@echo ""

# Verify all integrations
verify-all:
	@python3 verify_setup.py
