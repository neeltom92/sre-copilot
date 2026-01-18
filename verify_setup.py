#!/usr/bin/env python3
"""Verify all SRE Copilot integrations."""

import sys
from agent import SREAgent
from config import Config

def main():
    print("🔍 Verifying All Integrations")
    print("=" * 40)
    print()
    print("Running comprehensive verification...")
    print()

    config = Config.from_env()
    agent = SREAgent(config=config)
    status = agent.get_status()

    print("📊 Integration Status:")
    print("=" * 40)
    print()

    # Claude API (required)
    claude_ok = "✅" if status.get("claude_configured") else "❌"
    print(f"{claude_ok} Claude API: {'Configured' if status.get('claude_configured') else 'Not configured'}")
    if status.get("claude_configured"):
        print(f"   Model: {status.get('claude_model')}")
    print()

    # Datadog (optional)
    dd_ok = "✅" if status.get("datadog_configured") else "⚠️ "
    print(f"{dd_ok} Datadog: {'Configured' if status.get('datadog_configured') else 'Not configured (optional)'}")
    print()

    # PagerDuty (optional)
    pd_ok = "✅" if status.get("pagerduty_configured") else "⚠️ "
    print(f"{pd_ok} PagerDuty: {'Configured' if status.get('pagerduty_configured') else 'Not configured (optional)'}")
    print()

    # Kubernetes (optional)
    k8s_ok = "✅" if status.get("kubernetes_configured") else "⚠️ "
    print(f"{k8s_ok} Kubernetes: {'Configured' if status.get('kubernetes_configured') else 'Not configured (optional)'}")
    print()

    print(f"🛠️  Total tools available: {status.get('available_tools')}")
    print()
    print("=" * 40)

    if not status.get("claude_configured"):
        print()
        print("❌ Claude API is required!")
        print("   Add ANTHROPIC_API_KEY to .env file")
        print("   Get your key: https://console.anthropic.com/")
        print()
        sys.exit(1)
    else:
        print("✅ System is ready to use!")
        if not any([
            status.get("datadog_configured"),
            status.get("pagerduty_configured"),
            status.get("kubernetes_configured")
        ]):
            print()
            print("💡 Tip: Add Datadog, PagerDuty, or Kubernetes for more features")
        print()

if __name__ == "__main__":
    main()
