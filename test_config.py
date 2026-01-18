#!/usr/bin/env python3
"""Quick test to verify .env configuration is loaded correctly."""

from config import Config

def test_config():
    """Test that all configuration values are loaded properly."""
    config = Config.from_env()

    print("=" * 60)
    print("SRE Copilot Configuration Test")
    print("=" * 60)

    # Check Anthropic
    print("\n[Claude API]")
    if config.is_anthropic_configured():
        # Show first/last 4 chars for verification
        key = config.anthropic_api_key
        masked = f"{key[:12]}...{key[-4:]}" if len(key) > 16 else "***"
        print(f"  ✅ API Key: {masked}")
        print(f"  Model: {config.claude_model}")
    else:
        print("  ❌ Not configured (set ANTHROPIC_API_KEY)")

    # Check Datadog
    print("\n[Datadog]")
    if config.is_datadog_configured():
        api_key = config.datadog_api_key
        app_key = config.datadog_app_key
        print(f"  ✅ API Key: {api_key[:8]}...{api_key[-4:]}")
        print(f"  ✅ App Key: {app_key[:8]}...{app_key[-4:]}")
        print(f"  Site: {config.datadog_site}")
    else:
        print("  ❌ Not configured (set DD_API_KEY and DD_APP_KEY)")

    # Check PagerDuty
    print("\n[PagerDuty]")
    if config.is_pagerduty_configured():
        key = config.pagerduty_api_key
        masked = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
        print(f"  ✅ API Key: {masked}")
    else:
        print("  ❌ Not configured (set PAGERDUTY_API_KEY)")

    print("\n" + "=" * 60)

    # Summary
    all_configured = all([
        config.is_anthropic_configured(),
        config.is_datadog_configured(),
        config.is_pagerduty_configured(),
    ])

    if all_configured:
        print("✅ All integrations configured! Ready to run.")
    else:
        print("⚠️  Some integrations not configured (see above)")

    print("=" * 60)

    return config


if __name__ == "__main__":
    test_config()
