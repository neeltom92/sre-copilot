"""
LangChain tool wrappers for Datadog and PagerDuty.

Converts the native tools to LangChain-compatible tools for use with LangGraph agents.
"""

from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from tools.datadog_tools import DatadogTools
from tools.pagerduty_tools import PagerDutyTools
from tools.kubernetes_tools import KubernetesTools
from tools.sqs_tools import SQSTools


# =============================================================================
# Datadog Tool Schemas
# =============================================================================

class GetMonitorsInput(BaseModel):
    status_filter: Optional[list[str]] = Field(None, description="Filter by status: 'Alert', 'Warn', 'OK', 'No Data'")
    name_filter: Optional[str] = Field(None, description="Filter monitors by name")
    limit: int = Field(50, description="Maximum monitors to return")


class GetMonitorDetailsInput(BaseModel):
    monitor_id: int = Field(..., description="The Datadog monitor ID")


class QueryMetricsInput(BaseModel):
    query: str = Field(..., description="Datadog metrics query (e.g., 'avg:system.cpu.user{*}')")
    from_time: str = Field("now-1h", description="Start time (e.g., 'now-1h')")
    to_time: str = Field("now", description="End time")


class GetDashboardsInput(BaseModel):
    name_filter: Optional[str] = Field(None, description="Filter dashboards by name")
    limit: int = Field(20, description="Maximum dashboards to return")


class GetAPMServicesInput(BaseModel):
    env: Optional[str] = Field(None, description="Filter by environment (e.g., 'prod')")
    limit: int = Field(50, description="Maximum services to return")


class GetServiceStatsInput(BaseModel):
    service: str = Field(..., description="Service name")
    env: Optional[str] = Field(None, description="Environment filter")
    from_time: str = Field("now-1h", description="Start time")
    to_time: str = Field("now", description="End time")


class SearchTracesInput(BaseModel):
    query: str = Field(..., description="Trace search query (e.g., 'service:api @duration:>1s')")
    from_time: str = Field("now-15m", description="Start time")
    to_time: str = Field("now", description="End time")
    limit: int = Field(50, description="Maximum traces to return")


class GetTraceDetailsInput(BaseModel):
    trace_id: str = Field(..., description="The trace ID")


class GetK8sPodsInput(BaseModel):
    env: Optional[str] = Field(None, description="Environment: prod, stg, or dev (ask user if not specified)")
    cluster: Optional[str] = Field(None, description="Filter by cluster name")
    namespace: Optional[str] = Field(None, description="Filter by namespace")
    app: Optional[str] = Field(None, description="Filter by app/deployment name (e.g., 'mono', 'bumblebee')")
    status: Optional[str] = Field(None, description="Filter by status: Running, Pending, Failed, CrashLoopBackOff")
    limit: int = Field(50, description="Maximum pods to return")


class GetK8sNodesInput(BaseModel):
    env: Optional[str] = Field(None, description="Environment: prod, stg, or dev (ask user if not specified)")
    cluster: Optional[str] = Field(None, description="Filter by cluster name")
    limit: int = Field(50, description="Maximum nodes to return")


class GetK8sDeploymentsInput(BaseModel):
    env: Optional[str] = Field(None, description="Environment: prod, stg, or dev (ask user if not specified)")
    cluster: Optional[str] = Field(None, description="Filter by cluster name")
    namespace: Optional[str] = Field(None, description="Filter by namespace")
    limit: int = Field(50, description="Maximum deployments to return")


class GetK8sContainersInput(BaseModel):
    env: Optional[str] = Field(None, description="Environment: prod, stg, or dev (ask user if not specified)")
    cluster: Optional[str] = Field(None, description="Filter by cluster name")
    namespace: Optional[str] = Field(None, description="Filter by namespace")
    pod: Optional[str] = Field(None, description="Filter by pod name")
    limit: int = Field(50, description="Maximum containers to return")


# =============================================================================
# PagerDuty Tool Schemas
# =============================================================================

class GetPDIncidentsInput(BaseModel):
    statuses: Optional[list[str]] = Field(None, description="Filter by status: 'triggered', 'acknowledged', 'resolved'")
    urgency: Optional[str] = Field(None, description="Filter by urgency: 'high', 'low'")
    limit: int = Field(25, description="Maximum incidents to return")


class GetPDIncidentDetailsInput(BaseModel):
    incident_id: str = Field(..., description="PagerDuty incident ID")


class GetOncallInput(BaseModel):
    schedule_ids: Optional[list[str]] = Field(None, description="Filter by schedule IDs")
    escalation_policy_ids: Optional[list[str]] = Field(None, description="Filter by escalation policy IDs")


class GetPDServicesInput(BaseModel):
    name_filter: Optional[str] = Field(None, description="Filter services by name")
    limit: int = Field(50, description="Maximum services to return")


class AcknowledgeIncidentInput(BaseModel):
    incident_id: str = Field(..., description="PagerDuty incident ID to acknowledge")


class ResolveIncidentInput(BaseModel):
    incident_id: str = Field(..., description="PagerDuty incident ID to resolve")
    resolution: Optional[str] = Field(None, description="Resolution note")


class GetRecentAlertsInput(BaseModel):
    service_id: Optional[str] = Field(None, description="Filter by service ID")
    since_hours: int = Field(24, description="Look back this many hours")
    limit: int = Field(50, description="Maximum alerts to return")


# =============================================================================
# Kubernetes Tool Schemas
# =============================================================================

class GetK8sContextsInput(BaseModel):
    """Get available Kubernetes cluster contexts from kubeconfig."""
    pass


class GetK8sNamespacesInput(BaseModel):
    context: str = Field(..., description="Kubernetes context name")


class ListPodsInput(BaseModel):
    context: str = Field(..., description="Kubernetes context name")
    namespace: str = Field(..., description="Namespace name")


class GetPodLogsInput(BaseModel):
    context: str = Field(..., description="Kubernetes context name")
    namespace: str = Field(..., description="Namespace name")
    pod_name: str = Field(..., description="Pod name")
    container_name: Optional[str] = Field(None, description="Container name (required for multi-container pods)")
    tail_lines: int = Field(100, description="Number of lines to retrieve (default: 100, max: 10000)")
    since_seconds: Optional[int] = Field(None, description="Only return logs newer than N seconds")
    previous: bool = Field(False, description="If True, get logs from previous container (for crashed pods)")


# =============================================================================
# AWS SQS Tool Schemas
# =============================================================================

class SQSListQueuesInput(BaseModel):
    queue_name_prefix: Optional[str] = Field(None, description="Filter queues by name prefix")
    max_results: int = Field(100, description="Maximum queues to return (max: 1000)")


class SQSGetQueueAttributesInput(BaseModel):
    queue_url: str = Field(..., description="SQS queue URL")


class SQSPeekMessagesInput(BaseModel):
    queue_url: str = Field(..., description="SQS queue URL")
    max_messages: int = Field(10, description="Maximum messages to peek at (1-10)")
    wait_time_seconds: int = Field(0, description="Long polling wait time (0-20 seconds)")


class SQSGetQueueUrlInput(BaseModel):
    queue_name: str = Field(..., description="Name of the SQS queue")
    account_id: Optional[str] = Field(None, description="AWS account ID (for cross-account access)")


# =============================================================================
# LangChain Tool Classes
# =============================================================================

def create_datadog_tools(dd: DatadogTools) -> list[BaseTool]:
    """Create LangChain tools for Datadog APM (Application Performance Monitoring) only."""

    class GetAPMServicesTool(BaseTool):
        name: str = "datadog_get_apm_services"
        description: str = "List APM services with request counts. See all instrumented services and traffic levels."
        args_schema: Type[BaseModel] = GetAPMServicesInput

        def _run(self, env: str = None, limit: int = 50) -> str:
            result = dd.get_apm_services(env=env, limit=limit)
            return str(result)

    class GetServiceStatsTool(BaseTool):
        name: str = "datadog_get_service_stats"
        description: str = "Get APM statistics for a service: latency (avg/p95/p99), throughput, error rate. Use for performance investigation."
        args_schema: Type[BaseModel] = GetServiceStatsInput

        def _run(self, service: str, env: str = None, from_time: str = "now-1h", to_time: str = "now") -> str:
            result = dd.get_service_stats(service=service, env=env, from_time=from_time, to_time=to_time)
            return str(result)

    class SearchTracesTool(BaseTool):
        name: str = "datadog_search_traces"
        description: str = "Search APM traces by service, duration, or errors. Find slow requests or investigate endpoints."
        args_schema: Type[BaseModel] = SearchTracesInput

        def _run(self, query: str, from_time: str = "now-15m", to_time: str = "now", limit: int = 50) -> str:
            result = dd.search_traces(query=query, from_time=from_time, to_time=to_time, limit=limit)
            return str(result)

    class GetTraceDetailsTool(BaseTool):
        name: str = "datadog_get_trace_details"
        description: str = "Get detailed trace information including all spans. Drill down to identify bottlenecks."
        args_schema: Type[BaseModel] = GetTraceDetailsInput

        def _run(self, trace_id: str) -> str:
            result = dd.get_trace_details(trace_id=trace_id)
            return str(result)

    # Only APM tools - other Datadog features removed for simplicity
    return [
        GetAPMServicesTool(),
        GetServiceStatsTool(),
        SearchTracesTool(),
        GetTraceDetailsTool(),
    ]


def create_pagerduty_tools(pd: PagerDutyTools) -> list[BaseTool]:
    """Create LangChain tools for PagerDuty."""

    class GetIncidentsTool(BaseTool):
        name: str = "pagerduty_get_incidents"
        description: str = "List PagerDuty incidents. Check active incidents, urgency, and assignments."
        args_schema: Type[BaseModel] = GetPDIncidentsInput

        def _run(self, statuses: list[str] = None, urgency: str = None, limit: int = 25) -> str:
            result = pd.get_incidents(statuses=statuses, urgency=urgency, limit=limit)
            return str(result)

    class GetIncidentDetailsTool(BaseTool):
        name: str = "pagerduty_get_incident_details"
        description: str = "Get detailed PagerDuty incident info including timeline and notes."
        args_schema: Type[BaseModel] = GetPDIncidentDetailsInput

        def _run(self, incident_id: str) -> str:
            result = pd.get_incident_details(incident_id=incident_id)
            return str(result)

    class GetOncallTool(BaseTool):
        name: str = "pagerduty_get_oncall"
        description: str = "Get current on-call users. Find who is responsible for incidents or services."
        args_schema: Type[BaseModel] = GetOncallInput

        def _run(self, schedule_ids: list[str] = None, escalation_policy_ids: list[str] = None) -> str:
            result = pd.get_oncall(schedule_ids=schedule_ids, escalation_policy_ids=escalation_policy_ids)
            return str(result)

    class GetServicesTool(BaseTool):
        name: str = "pagerduty_get_services"
        description: str = "List PagerDuty services and their status."
        args_schema: Type[BaseModel] = GetPDServicesInput

        def _run(self, name_filter: str = None, limit: int = 50) -> str:
            result = pd.get_services(name_filter=name_filter, limit=limit)
            return str(result)

    class AcknowledgeIncidentTool(BaseTool):
        name: str = "pagerduty_acknowledge_incident"
        description: str = "Acknowledge a PagerDuty incident. Use when starting to work on an incident."
        args_schema: Type[BaseModel] = AcknowledgeIncidentInput

        def _run(self, incident_id: str) -> str:
            result = pd.acknowledge_incident(incident_id=incident_id)
            return str(result)

    class ResolveIncidentTool(BaseTool):
        name: str = "pagerduty_resolve_incident"
        description: str = "Resolve a PagerDuty incident. Use when an incident is fixed."
        args_schema: Type[BaseModel] = ResolveIncidentInput

        def _run(self, incident_id: str, resolution: str = None) -> str:
            result = pd.resolve_incident(incident_id=incident_id, resolution=resolution)
            return str(result)

    class GetRecentAlertsTool(BaseTool):
        name: str = "pagerduty_get_recent_alerts"
        description: str = "Get recent alerts/triggers from PagerDuty. See what alerts have fired recently."
        args_schema: Type[BaseModel] = GetRecentAlertsInput

        def _run(self, service_id: str = None, since_hours: int = 24, limit: int = 50) -> str:
            result = pd.get_recent_alerts(service_id=service_id, since_hours=since_hours, limit=limit)
            return str(result)

    return [
        GetIncidentsTool(),
        GetIncidentDetailsTool(),
        GetOncallTool(),
        GetServicesTool(),
        AcknowledgeIncidentTool(),
        ResolveIncidentTool(),
        GetRecentAlertsTool(),
    ]


def create_kubernetes_tools(k8s: KubernetesTools) -> list[BaseTool]:
    """Create LangChain tools for Kubernetes."""

    class GetContextsTool(BaseTool):
        name: str = "k8s_get_contexts"
        description: str = "List available Kubernetes cluster contexts from local kubeconfig. Use to see which clusters are available."
        args_schema: Type[BaseModel] = GetK8sContextsInput

        def _run(self) -> str:
            result = k8s.get_contexts()
            return str(result)

    class GetNamespacesTool(BaseTool):
        name: str = "k8s_get_namespaces"
        description: str = "List namespaces in a Kubernetes cluster. Use after selecting a cluster context to see available namespaces."
        args_schema: Type[BaseModel] = GetK8sNamespacesInput

        def _run(self, context: str) -> str:
            result = k8s.get_namespaces(context=context)
            return str(result)

    class ListPodsTool(BaseTool):
        name: str = "k8s_list_pods"
        description: str = "List all pods in a namespace with their status, restarts, and age. Use this to see what pods are running before fetching logs."
        args_schema: Type[BaseModel] = ListPodsInput

        def _run(self, context: str, namespace: str) -> str:
            result = k8s.list_pods(context=context, namespace=namespace)
            return str(result)

    class GetPodLogsTool(BaseTool):
        name: str = "k8s_get_pod_logs"
        description: str = "Fetch logs from a pod in real-time (no Datadog lag). For crashed pods, use previous=true. For multi-container pods, specify container_name."
        args_schema: Type[BaseModel] = GetPodLogsInput

        def _run(
            self,
            context: str,
            namespace: str,
            pod_name: str,
            container_name: str = None,
            tail_lines: int = 100,
            since_seconds: int = None,
            previous: bool = False,
        ) -> str:
            result = k8s.get_pod_logs(
                context=context,
                namespace=namespace,
                pod_name=pod_name,
                container_name=container_name,
                tail_lines=tail_lines,
                since_seconds=since_seconds,
                previous=previous,
            )
            return str(result)

    return [
        GetContextsTool(),
        GetNamespacesTool(),
        ListPodsTool(),
        GetPodLogsTool(),
    ]


def create_sqs_tools(sqs: SQSTools) -> list[BaseTool]:
    """Create LangChain tools for AWS SQS (read-only)."""

    class ListQueuesTool(BaseTool):
        name: str = "sqs_list_queues"
        description: str = "List AWS SQS queues. Discover available queues or find by name prefix."
        args_schema: Type[BaseModel] = SQSListQueuesInput

        def _run(self, queue_name_prefix: str = None, max_results: int = 100) -> str:
            result = sqs.list_queues(queue_name_prefix=queue_name_prefix, max_results=max_results)
            return str(result)

    class GetQueueAttributesTool(BaseTool):
        name: str = "sqs_get_queue_attributes"
        description: str = "Get queue attributes: message counts, age of oldest message, visibility timeout, DLQ config."
        args_schema: Type[BaseModel] = SQSGetQueueAttributesInput

        def _run(self, queue_url: str) -> str:
            result = sqs.get_queue_attributes(queue_url=queue_url)
            return str(result)

    class PeekMessagesTool(BaseTool):
        name: str = "sqs_peek_messages"
        description: str = "Peek at messages WITHOUT removing them (read-only). Messages stay in queue for other consumers."
        args_schema: Type[BaseModel] = SQSPeekMessagesInput

        def _run(self, queue_url: str, max_messages: int = 10, wait_time_seconds: int = 0) -> str:
            result = sqs.peek_messages(queue_url=queue_url, max_messages=max_messages, wait_time_seconds=wait_time_seconds)
            return str(result)

    class GetQueueUrlTool(BaseTool):
        name: str = "sqs_get_queue_url"
        description: str = "Get the URL of a queue by its name. Useful when you know the name but need the full URL."
        args_schema: Type[BaseModel] = SQSGetQueueUrlInput

        def _run(self, queue_name: str, account_id: str = None) -> str:
            result = sqs.get_queue_url(queue_name=queue_name, account_id=account_id)
            return str(result)

    return [
        ListQueuesTool(),
        GetQueueAttributesTool(),
        PeekMessagesTool(),
        GetQueueUrlTool(),
    ]
