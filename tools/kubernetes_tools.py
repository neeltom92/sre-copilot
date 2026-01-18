"""
Kubernetes API integration tools for SRE Copilot.

Provides tools for:
- Listing available cluster contexts from kubeconfig
- Listing namespaces in a cluster
- Fetching pod logs in real-time
- Accessing previous container logs (for crashed pods)
- Supporting multi-container pods
"""

from dataclasses import dataclass
from typing import Any, Optional
import os


@dataclass
class KubernetesTools:
    """Kubernetes API tools for SRE operations."""

    kubeconfig_path: str = "~/.kube/config"
    _client: Any = None
    _config: Any = None
    _contexts: list[dict] = None

    def __post_init__(self):
        """Initialize Kubernetes client lazily."""
        try:
            from kubernetes import client, config
            from kubernetes.config.config_exception import ConfigException

            # Expand ~ to home directory
            expanded_path = os.path.expanduser(self.kubeconfig_path)

            # Check if kubeconfig exists
            if not os.path.exists(expanded_path):
                return

            try:
                # Load kubeconfig and parse contexts
                self._config = config
                contexts, active_context = config.list_kube_config_contexts(
                    config_file=expanded_path
                )
                self._contexts = contexts

                # Initialize client with default context
                config.load_kube_config(config_file=expanded_path)
                self._client = client.CoreV1Api()
            except ConfigException as e:
                print(f"Failed to load kubeconfig: {e}")
        except ImportError as e:
            print(f"Failed to import kubernetes client: {e}")

    def _ensure_client(self) -> bool:
        """Ensure Kubernetes client is initialized."""
        return self._client is not None

    def _load_context(self, context_name: str) -> bool:
        """Load a specific Kubernetes context."""
        try:
            from kubernetes import client

            expanded_path = os.path.expanduser(self.kubeconfig_path)
            self._config.load_kube_config(
                config_file=expanded_path, context=context_name
            )
            self._client = client.CoreV1Api()
            return True
        except Exception as e:
            print(f"Failed to load context {context_name}: {e}")
            return False

    def get_contexts(self) -> dict:
        """
        List available Kubernetes cluster contexts from kubeconfig.

        Returns:
            Dictionary with contexts list containing name and cluster info
        """
        expanded_path = os.path.expanduser(self.kubeconfig_path)

        if not os.path.exists(expanded_path):
            return {
                "error": f"Kubeconfig not found at {expanded_path}. "
                "Please ensure kubectl is configured with a valid kubeconfig file."
            }

        if self._contexts is None:
            return {
                "error": "Failed to parse kubeconfig. "
                "Please check that your kubeconfig file is valid."
            }

        try:
            contexts_list = []
            for context in self._contexts:
                contexts_list.append(
                    {
                        "name": context["name"],
                        "cluster": context["context"].get("cluster", "unknown"),
                        "user": context["context"].get("user", "unknown"),
                        "namespace": context["context"].get("namespace", "default"),
                    }
                )

            return {"contexts": contexts_list, "count": len(contexts_list)}
        except Exception as e:
            return {"error": f"Failed to list contexts: {str(e)}"}

    def get_namespaces(self, context: str) -> dict:
        """
        List namespaces in the specified Kubernetes cluster.

        Args:
            context: Kubernetes context name

        Returns:
            Dictionary with namespaces list
        """
        expanded_path = os.path.expanduser(self.kubeconfig_path)

        if not os.path.exists(expanded_path):
            return {
                "error": f"Kubeconfig not found at {expanded_path}. "
                "Please ensure kubectl is configured."
            }

        # Load the specified context
        if not self._load_context(context):
            return {"error": f"Failed to load context: {context}"}

        if not self._ensure_client():
            return {"error": "Kubernetes client not configured"}

        try:
            namespaces = self._client.list_namespace()
            namespace_list = [ns.metadata.name for ns in namespaces.items]

            return {
                "namespaces": sorted(namespace_list),
                "count": len(namespace_list),
                "context": context,
            }
        except Exception as e:
            return {"error": f"Failed to list namespaces in context {context}: {str(e)}"}

    def list_pods(
        self,
        context: str,
        namespace: str,
    ) -> dict:
        """
        List all pods in a namespace with their status.

        Args:
            context: Kubernetes context name
            namespace: Namespace name

        Returns:
            Dictionary with pods list and metadata
        """
        expanded_path = os.path.expanduser(self.kubeconfig_path)

        if not os.path.exists(expanded_path):
            return {
                "error": f"Kubeconfig not found at {expanded_path}. "
                "Please ensure kubectl is configured."
            }

        # Load the specified context
        if not self._load_context(context):
            return {"error": f"Failed to load context: {context}"}

        if not self._ensure_client():
            return {"error": "Kubernetes client not configured"}

        try:
            pods = self._client.list_namespaced_pod(namespace=namespace)

            pod_list = []
            for pod in pods.items:
                # Get pod status
                status = pod.status.phase

                # Count restarts
                restart_count = 0
                if pod.status.container_statuses:
                    restart_count = sum(cs.restart_count for cs in pod.status.container_statuses)

                # Get ready status
                ready = "0/0"
                if pod.status.container_statuses:
                    ready_containers = sum(1 for cs in pod.status.container_statuses if cs.ready)
                    total_containers = len(pod.status.container_statuses)
                    ready = f"{ready_containers}/{total_containers}"

                # Get age
                age = ""
                if pod.metadata.creation_timestamp:
                    from datetime import datetime, timezone
                    age_seconds = (datetime.now(timezone.utc) - pod.metadata.creation_timestamp).total_seconds()
                    if age_seconds < 60:
                        age = f"{int(age_seconds)}s"
                    elif age_seconds < 3600:
                        age = f"{int(age_seconds / 60)}m"
                    elif age_seconds < 86400:
                        age = f"{int(age_seconds / 3600)}h"
                    else:
                        age = f"{int(age_seconds / 86400)}d"

                pod_list.append({
                    "name": pod.metadata.name,
                    "ready": ready,
                    "status": status,
                    "restarts": restart_count,
                    "age": age,
                    "node": pod.spec.node_name or "N/A",
                })

            return {
                "pods": pod_list,
                "count": len(pod_list),
                "namespace": namespace,
                "context": context,
            }

        except Exception as e:
            error_msg = str(e)

            # Handle authentication errors
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                return {
                    "error": f"Authentication failed for context '{context}'. "
                    "Please check your kubeconfig credentials."
                }

            # Handle permission errors
            if "403" in error_msg or "forbidden" in error_msg.lower():
                return {
                    "error": f"Permission denied to list pods in namespace '{namespace}'. "
                    "Please check your Kubernetes RBAC permissions."
                }

            # Handle namespace not found
            if "404" in error_msg or "not found" in error_msg.lower():
                return {
                    "error": f"Namespace '{namespace}' not found in context '{context}'."
                }

            # Generic error
            return {
                "error": f"Failed to list pods in namespace '{namespace}': {error_msg}"
            }

    def get_pod_logs(
        self,
        context: str,
        namespace: str,
        pod_name: str,
        container_name: Optional[str] = None,
        tail_lines: int = 100,
        since_seconds: Optional[int] = None,
        previous: bool = False,
    ) -> dict:
        """
        Fetch logs from a pod in the specified cluster and namespace.

        Args:
            context: Kubernetes context name
            namespace: Namespace name
            pod_name: Pod name
            container_name: Container name (required for multi-container pods)
            tail_lines: Number of lines to retrieve (default: 100, max: 10000)
            since_seconds: Only return logs newer than N seconds
            previous: If True, get logs from previous container (for crashed pods)

        Returns:
            Dictionary with logs and metadata
        """
        expanded_path = os.path.expanduser(self.kubeconfig_path)

        if not os.path.exists(expanded_path):
            return {
                "error": f"Kubeconfig not found at {expanded_path}. "
                "Please ensure kubectl is configured."
            }

        # Load the specified context
        if not self._load_context(context):
            return {"error": f"Failed to load context: {context}"}

        if not self._ensure_client():
            return {"error": "Kubernetes client not configured"}

        # Enforce maximum tail lines
        tail_lines = min(tail_lines, 10000)

        try:
            # First, check if pod exists and get container info
            try:
                pod = self._client.read_namespaced_pod(name=pod_name, namespace=namespace)
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    return {
                        "error": f"Pod '{pod_name}' not found in namespace '{namespace}'. "
                        "Please check the pod name and namespace."
                    }
                raise

            # Get list of containers in the pod
            containers = [c.name for c in pod.spec.containers]
            init_containers = [c.name for c in (pod.spec.init_containers or [])]
            all_containers = containers + init_containers

            # If pod has multiple containers and no container specified
            if len(all_containers) > 1 and container_name is None:
                return {
                    "error": f"Pod '{pod_name}' has multiple containers. "
                    f"Please specify one of: {', '.join(all_containers)}",
                    "containers": all_containers,
                }

            # If only one container, use it
            if container_name is None and len(all_containers) == 1:
                container_name = all_containers[0]

            # Verify container exists in pod
            if container_name and container_name not in all_containers:
                return {
                    "error": f"Container '{container_name}' not found in pod '{pod_name}'. "
                    f"Available containers: {', '.join(all_containers)}",
                    "containers": all_containers,
                }

            # Fetch logs
            kwargs = {
                "name": pod_name,
                "namespace": namespace,
                "tail_lines": tail_lines,
                "previous": previous,
            }

            if container_name:
                kwargs["container"] = container_name

            if since_seconds:
                kwargs["since_seconds"] = since_seconds

            logs = self._client.read_namespaced_pod_log(**kwargs)

            # Count lines and check if truncated
            log_lines = logs.split("\n") if logs else []
            line_count = len(log_lines)

            return {
                "logs": logs,
                "metadata": {
                    "pod": pod_name,
                    "namespace": namespace,
                    "context": context,
                    "container": container_name,
                    "lines": line_count,
                    "tail_lines": tail_lines,
                    "previous": previous,
                    "truncated": line_count >= tail_lines,
                },
            }

        except Exception as e:
            error_msg = str(e)

            # Handle authentication errors
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                return {
                    "error": f"Authentication failed for context '{context}'. "
                    "Please check your kubeconfig credentials."
                }

            # Handle permission errors
            if "403" in error_msg or "forbidden" in error_msg.lower():
                return {
                    "error": f"Permission denied to access logs in namespace '{namespace}'. "
                    "Please check your Kubernetes RBAC permissions."
                }

            # Handle connection errors
            if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                return {
                    "error": f"Failed to connect to cluster '{context}'. "
                    "Please check your network connection and cluster availability."
                }

            # Generic error
            return {
                "error": f"Failed to fetch logs from pod '{pod_name}' "
                f"in namespace '{namespace}': {error_msg}"
            }
