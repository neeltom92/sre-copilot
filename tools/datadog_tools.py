"""
Datadog API integration tools for SRE Copilot.

Provides tools for:
- Fetching monitors and their status
- Querying metrics
- Listing incidents
- Getting dashboards
- APM services and statistics
- Trace search and analysis
- Kubernetes cluster metrics (pods, nodes, deployments, containers)
"""

from dataclasses import dataclass
from typing import Any, Optional
import json


@dataclass
class DatadogTools:
    """Datadog API tools for SRE operations."""

    api_key: str
    app_key: str
    site: str = "datadoghq.com"
    _api_client: Any = None
    _v1_client: Any = None
    _v2_client: Any = None

    def __post_init__(self):
        """Initialize Datadog API clients lazily."""
        if not self.api_key or not self.app_key:
            return

        try:
            from datadog_api_client import ApiClient, Configuration

            self._configuration = Configuration()
            self._configuration.api_key["apiKeyAuth"] = self.api_key
            self._configuration.api_key["appKeyAuth"] = self.app_key
            self._configuration.server_variables["site"] = self.site

            # In datadog-api-client v2.x, use single ApiClient for both v1 and v2 APIs
            # Must enter context to initialize properly
            self._api_client = ApiClient(self._configuration)
            self._api_client.__enter__()
            self._v1_client = self._api_client
            self._v2_client = self._api_client
        except ImportError as e:
            print(f"Failed to import datadog_api_client: {e}")

    def _ensure_client(self) -> bool:
        """Ensure API client is initialized."""
        return self._v1_client is not None

    def get_monitors(
        self,
        status_filter: Optional[list[str]] = None,
        name_filter: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        Fetch monitors and their status.

        Args:
            status_filter: Filter by status (e.g., ["Alert", "Warn", "OK"])
            name_filter: Filter by name (substring match)
            limit: Maximum number of monitors to return

        Returns:
            Dictionary with monitors list and summary
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v1.api.monitors_api import MonitorsApi

            api = MonitorsApi(self._v1_client)

            kwargs = {"page_size": limit}
            if name_filter:
                kwargs["name"] = name_filter

            monitors = api.list_monitors(**kwargs)

            results = []
            status_counts = {"Alert": 0, "Warn": 0, "OK": 0, "No Data": 0, "Other": 0}

            for monitor in monitors:
                status = str(monitor.overall_state) if monitor.overall_state else "Unknown"

                # Apply status filter if provided
                if status_filter and status not in status_filter:
                    continue

                # Count statuses
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts["Other"] += 1

                results.append({
                    "id": monitor.id,
                    "name": monitor.name,
                    "type": str(monitor.type) if monitor.type else None,
                    "status": status,
                    "message": monitor.message[:200] if monitor.message else None,
                    "tags": list(monitor.tags) if monitor.tags else [],
                    "query": monitor.query[:200] if monitor.query else None,
                })

            return {
                "monitors": results[:limit],
                "total_count": len(results),
                "status_summary": status_counts,
            }

        except Exception as e:
            return {"error": f"Failed to fetch monitors: {str(e)}"}

    def get_monitor_details(self, monitor_id: int) -> dict:
        """
        Get detailed information about a specific monitor.

        Args:
            monitor_id: The monitor ID

        Returns:
            Monitor details including query, thresholds, and recent status
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v1.api.monitors_api import MonitorsApi

            api = MonitorsApi(self._v1_client)
            monitor = api.get_monitor(monitor_id=monitor_id)

            return {
                "id": monitor.id,
                "name": monitor.name,
                "type": str(monitor.type) if monitor.type else None,
                "status": str(monitor.overall_state) if monitor.overall_state else None,
                "query": monitor.query,
                "message": monitor.message,
                "tags": list(monitor.tags) if monitor.tags else [],
                "created": str(monitor.created) if monitor.created else None,
                "modified": str(monitor.modified) if monitor.modified else None,
                "options": {
                    "thresholds": monitor.options.thresholds._data_store if monitor.options and monitor.options.thresholds else None,
                    "notify_no_data": monitor.options.notify_no_data if monitor.options else None,
                    "evaluation_delay": monitor.options.evaluation_delay if monitor.options else None,
                } if monitor.options else None,
            }

        except Exception as e:
            return {"error": f"Failed to fetch monitor details: {str(e)}"}

    def query_metrics(
        self,
        query: str,
        from_time: str = "now-1h",
        to_time: str = "now",
    ) -> dict:
        """
        Query metrics from Datadog.

        Args:
            query: Datadog metrics query (e.g., "avg:system.cpu.user{*}")
            from_time: Start time (e.g., "now-1h", "now-4h", epoch timestamp)
            to_time: End time (e.g., "now", epoch timestamp)

        Returns:
            Metrics data with series and values
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v1.api.metrics_api import MetricsApi
            import time

            api = MetricsApi(self._v1_client)

            # Parse relative time strings
            now = int(time.time())

            def parse_time(t: str) -> int:
                if t == "now":
                    return now
                if t.startswith("now-"):
                    delta = t[4:]
                    if delta.endswith("h"):
                        return now - int(delta[:-1]) * 3600
                    if delta.endswith("m"):
                        return now - int(delta[:-1]) * 60
                    if delta.endswith("d"):
                        return now - int(delta[:-1]) * 86400
                return int(t)

            from_ts = parse_time(from_time)
            to_ts = parse_time(to_time)

            response = api.query_metrics(
                _from=from_ts,
                to=to_ts,
                query=query,
            )

            series_data = []
            for series in response.series or []:
                points = []
                if series.pointlist:
                    # Sample points if too many
                    step = max(1, len(series.pointlist) // 20)
                    for i, point in enumerate(series.pointlist):
                        if i % step == 0:
                            points.append({
                                "timestamp": point.value[0],
                                "value": point.value[1],
                            })

                series_data.append({
                    "metric": series.metric,
                    "scope": series.scope,
                    "points": points,
                    "unit": series.unit[0].name if series.unit else None,
                    "avg": sum(p["value"] for p in points if p["value"]) / len(points) if points else None,
                })

            return {
                "query": query,
                "from": from_time,
                "to": to_time,
                "series": series_data,
            }

        except Exception as e:
            return {"error": f"Failed to query metrics: {str(e)}"}

    def get_incidents(
        self,
        status: Optional[list[str]] = None,
        limit: int = 20,
    ) -> dict:
        """
        Get Datadog incidents.

        Args:
            status: Filter by status (e.g., ["active", "stable", "resolved"])
            limit: Maximum number of incidents to return

        Returns:
            List of incidents with details
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v2.api.incidents_api import IncidentsApi

            api = IncidentsApi(self._v2_client)

            # Note: list_incidents may require additional setup
            incidents_response = api.list_incidents()

            results = []
            for incident in incidents_response.data or []:
                attrs = incident.attributes
                inc_status = attrs.fields.get("state", {}).get("value", "unknown") if attrs.fields else "unknown"

                if status and inc_status not in status:
                    continue

                results.append({
                    "id": incident.id,
                    "title": attrs.title,
                    "status": inc_status,
                    "severity": attrs.fields.get("severity", {}).get("value") if attrs.fields else None,
                    "created": str(attrs.created) if attrs.created else None,
                    "customer_impact": attrs.customer_impact_scope,
                    "commander": attrs.commander.data.attributes.name if attrs.commander and attrs.commander.data else None,
                })

                if len(results) >= limit:
                    break

            return {
                "incidents": results,
                "total_count": len(results),
            }

        except Exception as e:
            return {"error": f"Failed to fetch incidents: {str(e)}"}

    def get_dashboards(self, name_filter: Optional[str] = None, limit: int = 20) -> dict:
        """
        List Datadog dashboards.

        Args:
            name_filter: Filter by name (substring match)
            limit: Maximum dashboards to return

        Returns:
            List of dashboards with URLs
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v1.api.dashboards_api import DashboardsApi

            api = DashboardsApi(self._v1_client)
            response = api.list_dashboards()

            dashboards = []
            for dash in response.dashboards or []:
                if name_filter and name_filter.lower() not in (dash.title or "").lower():
                    continue

                dashboards.append({
                    "id": dash.id,
                    "title": dash.title,
                    "url": f"https://app.{self.site}/dashboard/{dash.id}",
                    "author": dash.author_handle,
                    "created": str(dash.created_at) if dash.created_at else None,
                    "modified": str(dash.modified_at) if dash.modified_at else None,
                })

                if len(dashboards) >= limit:
                    break

            return {
                "dashboards": dashboards,
                "count": len(dashboards),
            }

        except Exception as e:
            return {"error": f"Failed to fetch dashboards: {str(e)}"}

    def get_apm_services(
        self,
        env: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        List APM services with their statistics.

        Args:
            env: Filter by environment (e.g., "prod", "staging")
            limit: Maximum services to return

        Returns:
            List of APM services with stats
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v1.api.metrics_api import MetricsApi
            import time

            api = MetricsApi(self._v1_client)

            # Query APM service metrics to discover services
            now = int(time.time())
            from_ts = now - 3600  # Last hour

            # Map common environment aliases to actual Datadog env tags
            env_mapping = {
                "prod": "production",
                "prd": "production",
                "stage": "stg",
                "staging": "stg",
                "development": "dev",
            }
            actual_env = env_mapping.get(env.lower(), env) if env else None
            env_filter = f",env:{actual_env}" if actual_env else ""

            # Try multiple span types to discover all services
            span_types = [
                "web.request",
                "servlet.request",
                "http.request",
                "flask.request",
                "grpc.request",
                "graphql.request",
            ]

            # Collect services from all span types
            services_map = {}  # service_name -> {total_hits, span_types}

            for span_type in span_types:
                query = f"sum:trace.{span_type}.hits{{*{env_filter}}} by {{service}}.as_count()"

                try:
                    response = api.query_metrics(_from=from_ts, to=now, query=query)

                    for series in response.series or []:
                        # Parse scope to extract service name
                        # Scope format: "service:name,env:prod" or "service:name"
                        service_name = "unknown"
                        if series.scope:
                            for part in series.scope.split(","):
                                if part.startswith("service:"):
                                    service_name = part.replace("service:", "")
                                    break

                        # Calculate total requests
                        total_hits = sum(p.value[1] for p in series.pointlist if p.value[1]) if series.pointlist else 0

                        if total_hits > 0 and service_name != "unknown":
                            if service_name not in services_map:
                                services_map[service_name] = {
                                    "requests_last_hour": 0,
                                    "span_types": [],
                                }
                            services_map[service_name]["requests_last_hour"] += int(total_hits)
                            if span_type not in services_map[service_name]["span_types"]:
                                services_map[service_name]["span_types"].append(span_type)
                except Exception:
                    continue

            # Convert to list
            services = []
            for service_name, data in services_map.items():
                services.append({
                    "service": service_name,
                    "requests_last_hour": data["requests_last_hour"],
                    "span_types": data["span_types"],
                })

            # Sort by requests descending
            services.sort(key=lambda x: x["requests_last_hour"], reverse=True)

            return {
                "services": services[:limit],
                "count": len(services[:limit]),
                "total_discovered": len(services),
                "env_filter": env,
            }

        except Exception as e:
            return {"error": f"Failed to fetch APM services: {str(e)}"}

    def _discover_service_span_name(
        self,
        service: str,
        env: Optional[str] = None,
    ) -> Optional[str]:
        """
        Discover the actual span name used by a service in APM.

        Datadog APM metrics use different span names depending on the framework:
        - trace.web.request (generic web)
        - trace.servlet.request (Java)
        - trace.flask.request (Flask)
        - trace.express.request (Express.js)
        - trace.grpc.request (gRPC)
        - trace.<operation_name> (custom)

        Args:
            service: Service name
            env: Environment filter (will be mapped: prod->production, stage->stg)

        Returns:
            The span name that has data, or None if not found
        """
        if not self._ensure_client():
            return None

        try:
            from datadog_api_client.v1.api.metrics_api import MetricsApi
            import time

            api = MetricsApi(self._v1_client)
            now = int(time.time())
            from_ts = now - 900  # Last 15 minutes for faster discovery

            # Map common environment aliases to actual Datadog env tags
            env_mapping = {
                "prod": "production",
                "prd": "production",
                "stage": "stg",
                "staging": "stg",
                "development": "dev",
            }
            actual_env = env_mapping.get(env.lower(), env) if env else None
            env_filter = f",env:{actual_env}" if actual_env else ""

            # Common span types to try, ordered by likelihood
            span_types = [
                "web.request",
                "servlet.request",
                "http.request",
                "flask.request",
                "django.request",
                "express.request",
                "fastapi.request",
                "grpc.request",
                "graphql.request",
                "aws.lambda",
            ]

            for span_type in span_types:
                query = f"sum:trace.{span_type}.hits{{service:{service}{env_filter}}}.as_count()"
                try:
                    response = api.query_metrics(_from=from_ts, to=now, query=query)
                    if response.series:
                        points = response.series[0].pointlist or []
                        if points and any(p.value[1] and p.value[1] > 0 for p in points):
                            return span_type
                except Exception:
                    continue

            return None

        except Exception:
            return None

    def get_service_stats(
        self,
        service: str,
        env: Optional[str] = None,
        from_time: str = "now-1h",
        to_time: str = "now",
    ) -> dict:
        """
        Get APM statistics for a specific service.

        Args:
            service: Service name
            env: Environment filter (e.g., "prod")
            from_time: Start time
            to_time: End time

        Returns:
            Service stats including latency, error rate, throughput
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v1.api.metrics_api import MetricsApi
            import time

            api = MetricsApi(self._v1_client)

            now = int(time.time())

            def parse_time(t: str) -> int:
                if t == "now":
                    return now
                if t.startswith("now-"):
                    delta = t[4:]
                    if delta.endswith("h"):
                        return now - int(delta[:-1]) * 3600
                    if delta.endswith("m"):
                        return now - int(delta[:-1]) * 60
                    if delta.endswith("d"):
                        return now - int(delta[:-1]) * 86400
                return int(t)

            from_ts = parse_time(from_time)
            to_ts = parse_time(to_time)

            # Map common environment aliases to actual Datadog env tags
            env_mapping = {
                "prod": "production",
                "prd": "production",
                "stage": "stg",
                "staging": "stg",
                "development": "dev",
            }
            actual_env = env_mapping.get(env.lower(), env) if env else None
            env_filter = f",env:{actual_env}" if actual_env else ""

            # Discover the actual span name used by this service
            span_name = self._discover_service_span_name(service, actual_env)

            # Common span types to try if discovery fails
            span_types_to_try = [span_name] if span_name else []
            span_types_to_try.extend([
                "web.request",
                "servlet.request",
                "http.request",
                "flask.request",
                "grpc.request",
            ])
            # Remove duplicates while preserving order
            seen = set()
            span_types_to_try = [x for x in span_types_to_try if x and not (x in seen or seen.add(x))]

            results = {}
            successful_span_type = None

            # Try each span type until we find one with data
            for span_type in span_types_to_try:
                # Note: Percentile metrics use a different format:
                # trace.<span_type>.duration.by.service.99p instead of p99:trace.<span_type>.duration
                metrics = {
                    "latency_avg": f"avg:trace.{span_type}.duration{{service:{service}{env_filter}}}",
                    "latency_p95": f"avg:trace.{span_type}.duration.by.service.95p{{service:{service}{env_filter}}}",
                    "latency_p99": f"avg:trace.{span_type}.duration.by.service.99p{{service:{service}{env_filter}}}",
                    "requests": f"sum:trace.{span_type}.hits{{service:{service}{env_filter}}}.as_rate()",
                    "errors": f"sum:trace.{span_type}.errors{{service:{service}{env_filter}}}.as_rate()",
                }

                temp_results = {}
                has_data = False

                for metric_name, query in metrics.items():
                    try:
                        response = api.query_metrics(_from=from_ts, to=to_ts, query=query)
                        if response.series:
                            points = response.series[0].pointlist or []
                            values = [p.value[1] for p in points if p.value[1] is not None]
                            if values:
                                has_data = True
                                temp_results[metric_name] = {
                                    "avg": sum(values) / len(values),
                                    "min": min(values),
                                    "max": max(values),
                                    "latest": values[-1] if values else None,
                                }
                    except Exception:
                        pass

                if has_data:
                    results = temp_results
                    successful_span_type = span_type
                    break

            # Calculate error rate
            error_rate = None
            if "requests" in results and "errors" in results:
                req_avg = results["requests"].get("avg", 0)
                err_avg = results["errors"].get("avg", 0)
                if req_avg > 0:
                    error_rate = (err_avg / req_avg) * 100

            # Unit conversions for latency:
            # - trace.*.duration metrics return values in milliseconds
            # - trace.*.duration.by.service.*p metrics return values in seconds
            latency_avg_raw = results.get("latency_avg", {}).get("avg")
            latency_p95_sec = results.get("latency_p95", {}).get("avg")
            latency_p99_sec = results.get("latency_p99", {}).get("avg")

            # Convert to milliseconds
            # avg:trace.*.duration is already in milliseconds
            latency_avg_ms = latency_avg_raw if latency_avg_raw is not None else None
            # trace.*.duration.by.service.*p metrics are in seconds, convert to ms
            latency_p95_ms = latency_p95_sec * 1_000 if latency_p95_sec is not None else None
            latency_p99_ms = latency_p99_sec * 1_000 if latency_p99_sec is not None else None

            # Build response
            response_data = {
                "service": service,
                "env": actual_env if actual_env else env,
                "env_requested": env,  # Original env requested by user
                "from": from_time,
                "to": to_time,
                "latency": {
                    "avg_ms": round(latency_avg_ms, 3) if latency_avg_ms is not None else None,
                    "p95_ms": round(latency_p95_ms, 3) if latency_p95_ms is not None else None,
                    "p99_ms": round(latency_p99_ms, 3) if latency_p99_ms is not None else None,
                },
                "throughput": {
                    "requests_per_sec": results.get("requests", {}).get("avg"),
                    "peak_requests_per_sec": results.get("requests", {}).get("max"),
                },
                "errors": {
                    "errors_per_sec": results.get("errors", {}).get("avg"),
                    "error_rate_percent": error_rate,
                },
                "url": f"https://app.{self.site}/apm/service/{service}",
            }

            # Add metadata about the query
            if successful_span_type:
                response_data["span_type"] = successful_span_type
                response_data["metric_prefix"] = f"trace.{successful_span_type}"
            else:
                response_data["warning"] = (
                    f"No APM data found for service '{service}'"
                    + (f" in env '{env}'" if env else "")
                    + ". The service may not be instrumented, may use a different name in Datadog, "
                    + "or there may be no recent traffic. Try checking the service name in Datadog APM UI."
                )
                response_data["tried_span_types"] = span_types_to_try

            return response_data

        except Exception as e:
            return {"error": f"Failed to fetch service stats: {str(e)}"}

    def search_traces(
        self,
        query: str,
        from_time: str = "now-15m",
        to_time: str = "now",
        limit: int = 50,
    ) -> dict:
        """
        Search APM traces.

        Args:
            query: Trace search query (e.g., "service:api @duration:>1s")
            from_time: Start time
            to_time: End time
            limit: Maximum traces to return

        Returns:
            List of traces matching the query
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v2.api.spans_api import SpansApi
            from datadog_api_client.v2.model.spans_list_request import SpansListRequest
            from datadog_api_client.v2.model.spans_list_request_data import SpansListRequestData
            from datadog_api_client.v2.model.spans_list_request_attributes import SpansListRequestAttributes
            from datadog_api_client.v2.model.spans_query_filter import SpansQueryFilter
            from datadog_api_client.v2.model.spans_sort import SpansSort
            from datadog_api_client.v2.model.spans_list_request_page import SpansListRequestPage

            api = SpansApi(self._v2_client)

            body = SpansListRequest(
                data=SpansListRequestData(
                    attributes=SpansListRequestAttributes(
                        filter=SpansQueryFilter(
                            query=query,
                            _from=from_time,
                            to=to_time,
                        ),
                        sort=SpansSort.TIMESTAMP_DESCENDING,
                        page=SpansListRequestPage(limit=limit),
                    ),
                    type="search_request",
                ),
            )

            response = api.list_spans(body=body)

            traces = []
            seen_trace_ids = set()

            for span in response.data or []:
                attrs = span.attributes
                trace_id = attrs.attributes.get("trace_id") if attrs.attributes else None

                # Deduplicate by trace_id
                if trace_id and trace_id in seen_trace_ids:
                    continue
                if trace_id:
                    seen_trace_ids.add(trace_id)

                traces.append({
                    "span_id": span.id,
                    "trace_id": trace_id,
                    "service": attrs.service,
                    "resource": attrs.resource,
                    "operation": attrs.attributes.get("operation_name") if attrs.attributes else None,
                    "duration_ns": attrs.attributes.get("duration") if attrs.attributes else None,
                    "duration_ms": attrs.attributes.get("duration", 0) / 1_000_000 if attrs.attributes and attrs.attributes.get("duration") else None,
                    "status": attrs.attributes.get("status") if attrs.attributes else None,
                    "error": attrs.attributes.get("error") if attrs.attributes else None,
                    "timestamp": str(attrs.timestamp) if attrs.timestamp else None,
                    "host": attrs.host,
                })

            return {
                "query": query,
                "from": from_time,
                "to": to_time,
                "traces": traces,
                "count": len(traces),
            }

        except Exception as e:
            return {"error": f"Failed to search traces: {str(e)}"}

    def get_trace_details(
        self,
        trace_id: str,
    ) -> dict:
        """
        Get detailed information about a specific trace.

        Args:
            trace_id: The trace ID

        Returns:
            Trace details including all spans
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v2.api.spans_api import SpansApi
            from datadog_api_client.v2.model.spans_list_request import SpansListRequest
            from datadog_api_client.v2.model.spans_list_request_data import SpansListRequestData
            from datadog_api_client.v2.model.spans_list_request_attributes import SpansListRequestAttributes
            from datadog_api_client.v2.model.spans_query_filter import SpansQueryFilter
            from datadog_api_client.v2.model.spans_list_request_page import SpansListRequestPage

            api = SpansApi(self._v2_client)

            # Search for all spans with this trace_id
            body = SpansListRequest(
                data=SpansListRequestData(
                    attributes=SpansListRequestAttributes(
                        filter=SpansQueryFilter(
                            query=f"trace_id:{trace_id}",
                            _from="now-24h",
                            to="now",
                        ),
                        page=SpansListRequestPage(limit=100),
                    ),
                    type="search_request",
                ),
            )

            response = api.list_spans(body=body)

            spans = []
            total_duration = 0
            services = set()
            has_error = False

            for span in response.data or []:
                attrs = span.attributes
                duration = attrs.attributes.get("duration", 0) if attrs.attributes else 0

                if attrs.service:
                    services.add(attrs.service)

                if attrs.attributes and attrs.attributes.get("error"):
                    has_error = True

                spans.append({
                    "span_id": span.id,
                    "parent_id": attrs.attributes.get("parent_id") if attrs.attributes else None,
                    "service": attrs.service,
                    "resource": attrs.resource,
                    "operation": attrs.attributes.get("operation_name") if attrs.attributes else None,
                    "duration_ms": duration / 1_000_000 if duration else None,
                    "status": attrs.attributes.get("status") if attrs.attributes else None,
                    "error": attrs.attributes.get("error") if attrs.attributes else None,
                    "error_message": attrs.attributes.get("error.message") if attrs.attributes else None,
                    "http_method": attrs.attributes.get("http.method") if attrs.attributes else None,
                    "http_url": attrs.attributes.get("http.url") if attrs.attributes else None,
                    "http_status": attrs.attributes.get("http.status_code") if attrs.attributes else None,
                })

                if duration > total_duration:
                    total_duration = duration

            # Sort spans by duration descending to show slowest first
            spans.sort(key=lambda x: x.get("duration_ms") or 0, reverse=True)

            return {
                "trace_id": trace_id,
                "total_duration_ms": total_duration / 1_000_000 if total_duration else None,
                "span_count": len(spans),
                "services": list(services),
                "has_error": has_error,
                "spans": spans,
                "url": f"https://app.{self.site}/apm/trace/{trace_id}",
            }

        except Exception as e:
            return {"error": f"Failed to fetch trace details: {str(e)}"}

    def get_k8s_pods(
        self,
        env: Optional[str] = None,
        cluster: Optional[str] = None,
        namespace: Optional[str] = None,
        status: Optional[str] = None,
        app: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        Get Kubernetes pod status and metrics.

        Args:
            env: Environment filter (prod, stg, dev)
            cluster: Filter by cluster name
            namespace: Filter by namespace
            status: Filter by status (Running, Pending, Failed, Succeeded, CrashLoopBackOff)
            app: Filter by app/deployment name (e.g., 'mono', 'bumblebee')
            limit: Maximum pods to return

        Returns:
            Pod status, restarts, and resource usage
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v1.api.metrics_api import MetricsApi
            import time

            api = MetricsApi(self._v1_client)
            now = int(time.time())
            from_ts = now - 300  # Last 5 minutes for fresher data

            # Build filter
            filters = []
            if env:
                filters.append(f"env:{env}")
            if cluster:
                filters.append(f"kube_cluster_name:{cluster}")
            if namespace:
                filters.append(f"kube_namespace:{namespace}")
            if app:
                # App name can be in kube_deployment or pod_name prefix
                filters.append(f"kube_deployment:{app}")
            filter_str = ",".join(filters) if filters else "*"

            pods = {}

            # Query pod phase counts
            phase_query = f"sum:kubernetes_state.pod.status_phase{{{filter_str}}} by {{kube_namespace,pod_name,phase}}"
            phase_response = api.query_metrics(_from=from_ts, to=now, query=phase_query)

            for series in phase_response.series or []:
                scope_parts = series.scope.split(",") if series.scope else []
                pod_name = None
                ns = None
                phase = None

                for part in scope_parts:
                    if part.startswith("pod_name:"):
                        pod_name = part.replace("pod_name:", "")
                    elif part.startswith("kube_namespace:"):
                        ns = part.replace("kube_namespace:", "")
                    elif part.startswith("phase:"):
                        phase = part.replace("phase:", "")

                # Only set phase when metric value > 0 (pod is actually in this phase)
                if pod_name and phase and series.pointlist:
                    last_value = series.pointlist[-1].value[1] if series.pointlist[-1].value else 0
                    if last_value and last_value > 0:
                        key = f"{ns}/{pod_name}"
                        # Capitalize phase for display (running -> Running)
                        display_phase = phase.capitalize() if phase else "Unknown"
                        pods[key] = {"namespace": ns, "pod": pod_name, "phase": display_phase, "status": display_phase}

            # Query container restarts
            restart_query = f"sum:kubernetes_state.container.restarts{{{filter_str}}} by {{kube_namespace,pod_name}}"
            restart_response = api.query_metrics(_from=from_ts, to=now, query=restart_query)

            for series in restart_response.series or []:
                scope_parts = series.scope.split(",") if series.scope else []
                pod_name = None
                ns = None

                for part in scope_parts:
                    if part.startswith("pod_name:"):
                        pod_name = part.replace("pod_name:", "")
                    elif part.startswith("kube_namespace:"):
                        ns = part.replace("kube_namespace:", "")

                if pod_name and series.pointlist:
                    key = f"{ns}/{pod_name}"
                    restart_count = int(series.pointlist[-1].value[1] or 0)
                    if key in pods:
                        pods[key]["restarts"] = restart_count
                    else:
                        # Create pod entry if we have restart data but no phase data
                        pods[key] = {"namespace": ns, "pod": pod_name, "phase": "Unknown", "status": "Unknown", "restarts": restart_count}

            # Query for CrashLoopBackOff containers (waiting state with reason)
            crashloop_query = f"sum:kubernetes_state.container.status_report.count.waiting{{{filter_str},reason:crashloopbackoff}} by {{kube_namespace,pod_name}}"
            try:
                crashloop_response = api.query_metrics(_from=from_ts, to=now, query=crashloop_query)
                for series in crashloop_response.series or []:
                    scope_parts = series.scope.split(",") if series.scope else []
                    pod_name = None
                    ns = None

                    for part in scope_parts:
                        if part.startswith("pod_name:"):
                            pod_name = part.replace("pod_name:", "")
                        elif part.startswith("kube_namespace:"):
                            ns = part.replace("kube_namespace:", "")

                    if pod_name:
                        key = f"{ns}/{pod_name}"
                        if key in pods and series.pointlist and series.pointlist[-1].value[1] and series.pointlist[-1].value[1] > 0:
                            pods[key]["status"] = "CrashLoopBackOff"
            except Exception:
                pass  # CrashLoopBackOff query may fail if metric doesn't exist

            # Also mark pods with high recent restarts as potentially CrashLoopBackOff
            for key, pod in pods.items():
                restarts = pod.get("restarts", 0)
                if restarts > 5 and pod.get("status") == "Running":
                    pod["status"] = "Running (High Restarts)"

            # Filter by status if specified
            result_list = list(pods.values())
            if status:
                status_lower = status.lower()
                result_list = [p for p in result_list if
                    status_lower in p.get("status", "").lower() or
                    status_lower in p.get("phase", "").lower()]

            # Sort by restarts descending (problematic pods first)
            result_list.sort(key=lambda x: x.get("restarts", 0), reverse=True)

            # Count by status
            status_counts = {}
            for pod in result_list:
                s = pod.get("status", "Unknown")
                status_counts[s] = status_counts.get(s, 0) + 1

            return {
                "pods": result_list[:limit],
                "total_count": len(result_list),
                "status_summary": status_counts,
                "filters": {"cluster": cluster, "namespace": namespace, "status": status, "app": app},
                "note": "Data from Datadog metrics (may have 1-2 min lag vs kubectl). For real-time status, use kubectl directly.",
            }

        except Exception as e:
            return {"error": f"Failed to fetch K8s pods: {str(e)}"}

    def get_k8s_nodes(
        self,
        env: Optional[str] = None,
        cluster: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        Get Kubernetes node status and capacity.

        Args:
            env: Environment filter (prod, stg, dev)
            cluster: Filter by cluster name
            limit: Maximum nodes to return

        Returns:
            Node status, capacity, and resource usage
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v1.api.metrics_api import MetricsApi
            import time

            api = MetricsApi(self._v1_client)
            now = int(time.time())
            from_ts = now - 900  # Last 15 minutes

            # Map env to cluster name if cluster not specified
            env_to_cluster = {
                "prod": "services-prod-use1-mz-5",
                "production": "services-prod-use1-mz-5",
                "stg": "services-stg-use1-mz-1",
                "stage": "services-stg-use1-mz-1",
                "staging": "services-stg-use1-mz-1",
                "dev": "services-dev-use1-mz-3",
                "development": "services-dev-use1-mz-3",
            }

            filters = []
            # Use cluster if provided, otherwise map env to cluster
            if cluster:
                filters.append(f"kube_cluster_name:{cluster}")
            elif env and env.lower() in env_to_cluster:
                filters.append(f"kube_cluster_name:{env_to_cluster[env.lower()]}")
            filter_str = ",".join(filters) if filters else "*"

            nodes = {}

            # Query node status
            status_query = f"sum:kubernetes_state.node.status{{{filter_str}}} by {{host,status}}"
            status_response = api.query_metrics(_from=from_ts, to=now, query=status_query)

            for series in status_response.series or []:
                scope_parts = series.scope.split(",") if series.scope else []
                host = None
                node_status = None

                for part in scope_parts:
                    if part.startswith("host:"):
                        host = part.replace("host:", "")
                    elif part.startswith("status:"):
                        node_status = part.replace("status:", "")

                if host:
                    if host not in nodes:
                        nodes[host] = {"node": host, "status": "Unknown"}
                    if series.pointlist and series.pointlist[-1].value[1] and series.pointlist[-1].value[1] > 0:
                        nodes[host]["status"] = node_status

            # Query CPU capacity
            cpu_cap_query = f"avg:kubernetes.cpu.capacity{{{filter_str}}} by {{host}}"
            cpu_cap_response = api.query_metrics(_from=from_ts, to=now, query=cpu_cap_query)

            for series in cpu_cap_response.series or []:
                host = series.scope.replace("host:", "") if series.scope else None
                if host and host in nodes and series.pointlist:
                    nodes[host]["cpu_capacity_cores"] = round(series.pointlist[-1].value[1] or 0, 2)

            # Query memory capacity
            mem_cap_query = f"avg:kubernetes.memory.capacity{{{filter_str}}} by {{host}}"
            mem_cap_response = api.query_metrics(_from=from_ts, to=now, query=mem_cap_query)

            for series in mem_cap_response.series or []:
                host = series.scope.replace("host:", "") if series.scope else None
                if host and host in nodes and series.pointlist:
                    bytes_val = series.pointlist[-1].value[1] or 0
                    nodes[host]["memory_capacity_gb"] = round(bytes_val / (1024**3), 2)

            # Query CPU usage
            cpu_usage_query = f"avg:kubernetes.cpu.usage.total{{{filter_str}}} by {{host}}"
            cpu_usage_response = api.query_metrics(_from=from_ts, to=now, query=cpu_usage_query)

            for series in cpu_usage_response.series or []:
                host = series.scope.replace("host:", "") if series.scope else None
                if host and host in nodes and series.pointlist:
                    # CPU usage is in nanocores, convert to cores
                    nanocores = series.pointlist[-1].value[1] or 0
                    nodes[host]["cpu_usage_cores"] = round(nanocores / 1e9, 2)
                    if nodes[host].get("cpu_capacity_cores"):
                        nodes[host]["cpu_percent"] = round(
                            (nodes[host]["cpu_usage_cores"] / nodes[host]["cpu_capacity_cores"]) * 100, 1
                        )

            # Query memory usage
            mem_usage_query = f"avg:kubernetes.memory.usage{{{filter_str}}} by {{host}}"
            mem_usage_response = api.query_metrics(_from=from_ts, to=now, query=mem_usage_query)

            for series in mem_usage_response.series or []:
                host = series.scope.replace("host:", "") if series.scope else None
                if host and host in nodes and series.pointlist:
                    bytes_val = series.pointlist[-1].value[1] or 0
                    nodes[host]["memory_usage_gb"] = round(bytes_val / (1024**3), 2)
                    if nodes[host].get("memory_capacity_gb"):
                        nodes[host]["memory_percent"] = round(
                            (nodes[host]["memory_usage_gb"] / nodes[host]["memory_capacity_gb"]) * 100, 1
                        )

            result_list = list(nodes.values())
            # Sort by CPU usage descending
            result_list.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)

            # Count by status
            status_counts = {}
            for node in result_list:
                status = node.get("status", "Unknown")
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                "nodes": result_list[:limit],
                "total_count": len(result_list),
                "status_summary": status_counts,
                "cluster": cluster,
            }

        except Exception as e:
            return {"error": f"Failed to fetch K8s nodes: {str(e)}"}

    def get_k8s_deployments(
        self,
        env: Optional[str] = None,
        cluster: Optional[str] = None,
        namespace: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        Get Kubernetes deployment status and replica counts.

        Args:
            env: Environment filter (prod, stg, dev)
            cluster: Filter by cluster name
            namespace: Filter by namespace
            limit: Maximum deployments to return

        Returns:
            Deployment replica status (desired, available, unavailable)
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v1.api.metrics_api import MetricsApi
            import time

            api = MetricsApi(self._v1_client)
            now = int(time.time())
            from_ts = now - 900  # Last 15 minutes

            filters = []
            if env:
                filters.append(f"env:{env}")
            if cluster:
                filters.append(f"kube_cluster_name:{cluster}")
            if namespace:
                filters.append(f"kube_namespace:{namespace}")
            filter_str = ",".join(filters) if filters else "*"

            deployments = {}

            # Query desired replicas
            desired_query = f"avg:kubernetes_state.deployment.replicas_desired{{{filter_str}}} by {{kube_namespace,kube_deployment}}"
            desired_response = api.query_metrics(_from=from_ts, to=now, query=desired_query)

            for series in desired_response.series or []:
                scope_parts = series.scope.split(",") if series.scope else []
                deployment = None
                ns = None

                for part in scope_parts:
                    if part.startswith("kube_deployment:"):
                        deployment = part.replace("kube_deployment:", "")
                    elif part.startswith("kube_namespace:"):
                        ns = part.replace("kube_namespace:", "")

                if deployment:
                    key = f"{ns}/{deployment}"
                    if key not in deployments:
                        deployments[key] = {"namespace": ns, "deployment": deployment}
                    if series.pointlist:
                        deployments[key]["desired"] = int(series.pointlist[-1].value[1] or 0)

            # Query available replicas
            available_query = f"avg:kubernetes_state.deployment.replicas_available{{{filter_str}}} by {{kube_namespace,kube_deployment}}"
            available_response = api.query_metrics(_from=from_ts, to=now, query=available_query)

            for series in available_response.series or []:
                scope_parts = series.scope.split(",") if series.scope else []
                deployment = None
                ns = None

                for part in scope_parts:
                    if part.startswith("kube_deployment:"):
                        deployment = part.replace("kube_deployment:", "")
                    elif part.startswith("kube_namespace:"):
                        ns = part.replace("kube_namespace:", "")

                if deployment:
                    key = f"{ns}/{deployment}"
                    if key in deployments and series.pointlist:
                        deployments[key]["available"] = int(series.pointlist[-1].value[1] or 0)

            # Query unavailable replicas
            unavailable_query = f"avg:kubernetes_state.deployment.replicas_unavailable{{{filter_str}}} by {{kube_namespace,kube_deployment}}"
            unavailable_response = api.query_metrics(_from=from_ts, to=now, query=unavailable_query)

            for series in unavailable_response.series or []:
                scope_parts = series.scope.split(",") if series.scope else []
                deployment = None
                ns = None

                for part in scope_parts:
                    if part.startswith("kube_deployment:"):
                        deployment = part.replace("kube_deployment:", "")
                    elif part.startswith("kube_namespace:"):
                        ns = part.replace("kube_namespace:", "")

                if deployment:
                    key = f"{ns}/{deployment}"
                    if key in deployments and series.pointlist:
                        deployments[key]["unavailable"] = int(series.pointlist[-1].value[1] or 0)

            # Calculate health status
            result_list = []
            unhealthy_count = 0
            for dep in deployments.values():
                desired = dep.get("desired", 0)
                available = dep.get("available", 0)
                unavailable = dep.get("unavailable", 0)

                if desired > 0 and available < desired:
                    dep["status"] = "Degraded"
                    unhealthy_count += 1
                elif desired == 0:
                    dep["status"] = "Scaled to Zero"
                else:
                    dep["status"] = "Healthy"

                result_list.append(dep)

            # Sort unhealthy first
            result_list.sort(key=lambda x: (x.get("status") != "Degraded", x.get("deployment", "")))

            return {
                "deployments": result_list[:limit],
                "total_count": len(result_list),
                "unhealthy_count": unhealthy_count,
                "filters": {"cluster": cluster, "namespace": namespace},
            }

        except Exception as e:
            return {"error": f"Failed to fetch K8s deployments: {str(e)}"}

    def get_k8s_containers(
        self,
        env: Optional[str] = None,
        cluster: Optional[str] = None,
        namespace: Optional[str] = None,
        pod: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        Get Kubernetes container resource usage (CPU, memory).

        Args:
            env: Environment filter (prod, stg, dev)
            cluster: Filter by cluster name
            namespace: Filter by namespace
            pod: Filter by pod name
            limit: Maximum containers to return

        Returns:
            Container CPU and memory usage with limits
        """
        if not self._ensure_client():
            return {"error": "Datadog client not configured"}

        try:
            from datadog_api_client.v1.api.metrics_api import MetricsApi
            import time

            api = MetricsApi(self._v1_client)
            now = int(time.time())
            from_ts = now - 900  # Last 15 minutes

            filters = []
            if env:
                filters.append(f"env:{env}")
            if cluster:
                filters.append(f"kube_cluster_name:{cluster}")
            if namespace:
                filters.append(f"kube_namespace:{namespace}")
            if pod:
                filters.append(f"pod_name:{pod}")
            filter_str = ",".join(filters) if filters else "*"

            containers = {}

            # Query CPU usage
            cpu_query = f"avg:kubernetes.cpu.usage.total{{{filter_str}}} by {{kube_namespace,pod_name,kube_container_name}}"
            cpu_response = api.query_metrics(_from=from_ts, to=now, query=cpu_query)

            for series in cpu_response.series or []:
                scope_parts = series.scope.split(",") if series.scope else []
                container = None
                pod_name = None
                ns = None

                for part in scope_parts:
                    if part.startswith("kube_container_name:"):
                        container = part.replace("kube_container_name:", "")
                    elif part.startswith("pod_name:"):
                        pod_name = part.replace("pod_name:", "")
                    elif part.startswith("kube_namespace:"):
                        ns = part.replace("kube_namespace:", "")

                if container and pod_name:
                    key = f"{ns}/{pod_name}/{container}"
                    if key not in containers:
                        containers[key] = {
                            "namespace": ns,
                            "pod": pod_name,
                            "container": container,
                        }
                    if series.pointlist:
                        # CPU in nanocores, convert to millicores
                        nanocores = series.pointlist[-1].value[1] or 0
                        containers[key]["cpu_millicores"] = round(nanocores / 1e6, 2)

            # Query memory usage
            mem_query = f"avg:kubernetes.memory.usage{{{filter_str}}} by {{kube_namespace,pod_name,kube_container_name}}"
            mem_response = api.query_metrics(_from=from_ts, to=now, query=mem_query)

            for series in mem_response.series or []:
                scope_parts = series.scope.split(",") if series.scope else []
                container = None
                pod_name = None
                ns = None

                for part in scope_parts:
                    if part.startswith("kube_container_name:"):
                        container = part.replace("kube_container_name:", "")
                    elif part.startswith("pod_name:"):
                        pod_name = part.replace("pod_name:", "")
                    elif part.startswith("kube_namespace:"):
                        ns = part.replace("kube_namespace:", "")

                if container and pod_name:
                    key = f"{ns}/{pod_name}/{container}"
                    if key in containers and series.pointlist:
                        bytes_val = series.pointlist[-1].value[1] or 0
                        containers[key]["memory_mb"] = round(bytes_val / (1024**2), 2)

            # Query memory limits
            mem_limit_query = f"avg:kubernetes.memory.limits{{{filter_str}}} by {{kube_namespace,pod_name,kube_container_name}}"
            mem_limit_response = api.query_metrics(_from=from_ts, to=now, query=mem_limit_query)

            for series in mem_limit_response.series or []:
                scope_parts = series.scope.split(",") if series.scope else []
                container = None
                pod_name = None
                ns = None

                for part in scope_parts:
                    if part.startswith("kube_container_name:"):
                        container = part.replace("kube_container_name:", "")
                    elif part.startswith("pod_name:"):
                        pod_name = part.replace("pod_name:", "")
                    elif part.startswith("kube_namespace:"):
                        ns = part.replace("kube_namespace:", "")

                if container and pod_name:
                    key = f"{ns}/{pod_name}/{container}"
                    if key in containers and series.pointlist:
                        bytes_val = series.pointlist[-1].value[1] or 0
                        containers[key]["memory_limit_mb"] = round(bytes_val / (1024**2), 2)
                        if containers[key].get("memory_mb") and bytes_val > 0:
                            containers[key]["memory_percent"] = round(
                                (containers[key]["memory_mb"] / containers[key]["memory_limit_mb"]) * 100, 1
                            )

            result_list = list(containers.values())
            # Sort by memory percent descending (high usage first)
            result_list.sort(key=lambda x: x.get("memory_percent", 0), reverse=True)

            return {
                "containers": result_list[:limit],
                "total_count": len(result_list),
                "filters": {"cluster": cluster, "namespace": namespace, "pod": pod},
            }

        except Exception as e:
            return {"error": f"Failed to fetch K8s containers: {str(e)}"}


# Tool definitions for Claude
DATADOG_TOOLS = [
    {
        "name": "datadog_get_monitors",
        "description": "Fetch Datadog monitors and their current status. Use this to check alerting monitors, find monitors in specific states, or get an overview of monitoring health.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by status: 'Alert', 'Warn', 'OK', 'No Data'. Leave empty for all.",
                },
                "name_filter": {
                    "type": "string",
                    "description": "Filter monitors by name (substring match)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of monitors to return (default: 50)",
                    "default": 50,
                },
            },
        },
    },
    {
        "name": "datadog_get_monitor_details",
        "description": "Get detailed information about a specific Datadog monitor including its query, thresholds, and configuration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "monitor_id": {
                    "type": "integer",
                    "description": "The Datadog monitor ID",
                },
            },
            "required": ["monitor_id"],
        },
    },
    {
        "name": "datadog_query_metrics",
        "description": "Query Datadog metrics. Use this to check system metrics, application performance, or custom metrics. Supports aggregations like avg, sum, max, min.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Datadog metrics query (e.g., 'avg:system.cpu.user{*}', 'sum:requests.count{service:api}')",
                },
                "from_time": {
                    "type": "string",
                    "description": "Start time (e.g., 'now-1h', 'now-4h', 'now-1d'). Default: 'now-1h'",
                    "default": "now-1h",
                },
                "to_time": {
                    "type": "string",
                    "description": "End time (e.g., 'now'). Default: 'now'",
                    "default": "now",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "datadog_get_incidents",
        "description": "Get Datadog incidents. Use this to check active incidents, their severity, and who is handling them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by status: 'active', 'stable', 'resolved'. Leave empty for all.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of incidents to return (default: 20)",
                    "default": 20,
                },
            },
        },
    },
    {
        "name": "datadog_get_dashboards",
        "description": "List Datadog dashboards. Use this to find relevant dashboards for investigation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name_filter": {
                    "type": "string",
                    "description": "Filter dashboards by name (substring match)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum dashboards to return (default: 20)",
                    "default": 20,
                },
            },
        },
    },
    {
        "name": "datadog_get_apm_services",
        "description": "List APM services with request counts. Use this to see all instrumented services and their traffic levels.",
        "input_schema": {
            "type": "object",
            "properties": {
                "env": {
                    "type": "string",
                    "description": "Filter by environment (e.g., 'prod', 'staging')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum services to return (default: 50)",
                    "default": 50,
                },
            },
        },
    },
    {
        "name": "datadog_get_service_stats",
        "description": "Get APM statistics for a specific service including latency (avg, p95, p99), throughput, and error rate. Use this to investigate service performance or diagnose latency issues.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name to get stats for",
                },
                "env": {
                    "type": "string",
                    "description": "Environment filter (e.g., 'prod')",
                },
                "from_time": {
                    "type": "string",
                    "description": "Start time (e.g., 'now-1h', 'now-4h'). Default: 'now-1h'",
                    "default": "now-1h",
                },
                "to_time": {
                    "type": "string",
                    "description": "End time. Default: 'now'",
                    "default": "now",
                },
            },
            "required": ["service"],
        },
    },
    {
        "name": "datadog_search_traces",
        "description": "Search APM traces by service, duration, status, or errors. Use this to find slow requests, errors, or investigate specific endpoints.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Trace search query (e.g., 'service:api', 'service:api @duration:>1s', 'service:api status:error', 'service:api resource_name:/api/users')",
                },
                "from_time": {
                    "type": "string",
                    "description": "Start time (e.g., 'now-15m', 'now-1h'). Default: 'now-15m'",
                    "default": "now-15m",
                },
                "to_time": {
                    "type": "string",
                    "description": "End time. Default: 'now'",
                    "default": "now",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum traces to return (default: 50)",
                    "default": 50,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "datadog_get_trace_details",
        "description": "Get detailed information about a specific trace including all spans, durations, and errors. Use this to drill down into a specific request to identify bottlenecks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trace_id": {
                    "type": "string",
                    "description": "The trace ID to get details for",
                },
            },
            "required": ["trace_id"],
        },
    },
    {
        "name": "datadog_get_k8s_pods",
        "description": "Get Kubernetes pod status, restarts, and health. Use this to check pod status, find crashing pods, or investigate restart loops. IMPORTANT: Always ask user for environment (prod/stg/dev) if not specified. Note: Datadog metrics may have 1-2 min lag vs kubectl for real-time status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "env": {
                    "type": "string",
                    "description": "Environment: prod, stg, or dev (REQUIRED - ask user if not specified)",
                    "enum": ["prod", "stg", "dev"],
                },
                "cluster": {
                    "type": "string",
                    "description": "Filter by cluster name",
                },
                "namespace": {
                    "type": "string",
                    "description": "Filter by namespace",
                },
                "app": {
                    "type": "string",
                    "description": "Filter by app/deployment name (e.g., 'mono', 'bumblebee')",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status: Running, Pending, Failed, Succeeded, CrashLoopBackOff",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum pods to return (default: 50)",
                    "default": 50,
                },
            },
        },
    },
    {
        "name": "datadog_get_k8s_nodes",
        "description": "Get Kubernetes node status, capacity, and resource usage. Use this to check node health, find overloaded nodes, or investigate capacity issues. IMPORTANT: Always ask user for environment (prod/stg/dev) if not specified.",
        "input_schema": {
            "type": "object",
            "properties": {
                "env": {
                    "type": "string",
                    "description": "Environment: prod, stg, or dev (REQUIRED - ask user if not specified)",
                    "enum": ["prod", "stg", "dev"],
                },
                "cluster": {
                    "type": "string",
                    "description": "Filter by cluster name",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum nodes to return (default: 50)",
                    "default": 50,
                },
            },
        },
    },
    {
        "name": "datadog_get_k8s_deployments",
        "description": "Get Kubernetes deployment status and replica counts. Use this to check deployment health, find degraded deployments, or verify rollouts. IMPORTANT: Always ask user for environment (prod/stg/dev) if not specified.",
        "input_schema": {
            "type": "object",
            "properties": {
                "env": {
                    "type": "string",
                    "description": "Environment: prod, stg, or dev (REQUIRED - ask user if not specified)",
                    "enum": ["prod", "stg", "dev"],
                },
                "cluster": {
                    "type": "string",
                    "description": "Filter by cluster name",
                },
                "namespace": {
                    "type": "string",
                    "description": "Filter by namespace",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum deployments to return (default: 50)",
                    "default": 50,
                },
            },
        },
    },
    {
        "name": "datadog_get_k8s_containers",
        "description": "Get Kubernetes container CPU and memory usage. Use this to find resource-hungry containers, investigate OOM issues, or check resource utilization. IMPORTANT: Always ask user for environment (prod/stg/dev) if not specified.",
        "input_schema": {
            "type": "object",
            "properties": {
                "env": {
                    "type": "string",
                    "description": "Environment: prod, stg, or dev (REQUIRED - ask user if not specified)",
                    "enum": ["prod", "stg", "dev"],
                },
                "cluster": {
                    "type": "string",
                    "description": "Filter by cluster name",
                },
                "namespace": {
                    "type": "string",
                    "description": "Filter by namespace",
                },
                "pod": {
                    "type": "string",
                    "description": "Filter by pod name",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum containers to return (default: 50)",
                    "default": 50,
                },
            },
        },
    },
]
