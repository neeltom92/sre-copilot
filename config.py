"""
Configuration management for SRE Copilot.

Loads configuration from:
1. Local .env file (for development)
2. Environment variables (for production/EKS)

Environment variables:
- ANTHROPIC_API_KEY: Claude (Anthropic) API key (preferred)
- CLAUDE_API_KEY: Alias for ANTHROPIC_API_KEY
- DATADOG_API_KEY: Datadog API key (preferred)
- DD_API_KEY: Alias for DATADOG_API_KEY
- DATADOG_APP_KEY: Datadog application key (preferred)
- DD_APP_KEY: Alias for DATADOG_APP_KEY
- PAGERDUTY_API_KEY: PagerDuty API token
- DATADOG_SITE: Datadog site (default: datadoghq.com)
- KUBECONFIG: Path to kubeconfig file (default: ~/.kube/config)
- K8S_ENABLED: Enable Kubernetes integration (default: true)
- AWS_REGION: AWS region for SQS (default: us-east-1)
- AWS_ACCESS_KEY_ID: AWS access key (optional, can use IAM roles/profiles)
- AWS_SECRET_ACCESS_KEY: AWS secret key (optional)
- AWS_PROFILE: AWS profile name (optional)
- SQS_ENABLED: Enable AWS SQS integration (default: true)
"""

import os
from dataclasses import dataclass
from pathlib import Path

# Load .env file if it exists (for local development)
def _load_dotenv():
    """Load .env file if present."""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"Loaded config from {env_file}")
        except ImportError:
            # Manual parsing if python-dotenv not installed
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and value:
                            os.environ.setdefault(key, value)
            print(f"Loaded config from {env_file} (manual parse)")

_load_dotenv()

def _first_env(*names: str, default: str = "") -> str:
    """Return the first non-empty environment variable among names."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


@dataclass
class Config:
    """Application configuration."""

    # Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5-20250929"

    # Datadog
    datadog_api_key: str = ""
    datadog_app_key: str = ""
    datadog_site: str = "datadoghq.com"

    # PagerDuty
    pagerduty_api_key: str = ""

    # Kubernetes
    kubeconfig_path: str = "~/.kube/config"
    k8s_enabled: bool = True

    # AWS SQS
    aws_region: str = "us-east-1"
    aws_access_key: str = ""
    aws_secret_key: str = ""
    aws_profile: str = ""
    sqs_enabled: bool = True

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            anthropic_api_key=_first_env("ANTHROPIC_API_KEY", "CLAUDE_API_KEY", default=""),
            claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            datadog_api_key=_first_env("DATADOG_API_KEY", "DD_API_KEY", default=""),
            datadog_app_key=_first_env("DATADOG_APP_KEY", "DD_APP_KEY", default=""),
            datadog_site=os.getenv("DATADOG_SITE", "datadoghq.com"),
            pagerduty_api_key=os.getenv("PAGERDUTY_API_KEY", ""),
            kubeconfig_path=os.getenv("KUBECONFIG", os.path.expanduser("~/.kube/config")),
            k8s_enabled=os.getenv("K8S_ENABLED", "true").lower() == "true",
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            aws_profile=os.getenv("AWS_PROFILE", ""),
            sqs_enabled=os.getenv("SQS_ENABLED", "true").lower() == "true",
        )

    def is_anthropic_configured(self) -> bool:
        """Check if Claude API is configured."""
        return bool(self.anthropic_api_key)

    def is_datadog_configured(self) -> bool:
        """Check if Datadog is configured."""
        return bool(self.datadog_api_key and self.datadog_app_key)

    def is_pagerduty_configured(self) -> bool:
        """Check if PagerDuty is configured."""
        return bool(self.pagerduty_api_key)

    def is_kubernetes_configured(self) -> bool:
        """Check if Kubernetes is configured."""
        return self.k8s_enabled and os.path.exists(os.path.expanduser(self.kubeconfig_path))

    def is_sqs_configured(self) -> bool:
        """Check if AWS SQS is configured (can use IAM roles, profiles, or explicit keys)."""
        return self.sqs_enabled


# Global config instance
config = Config.from_env()
