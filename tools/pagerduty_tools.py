"""
PagerDuty API integration tools for SRE Copilot.

Provides tools for:
- Listing active incidents
- Getting on-call schedules
- Acknowledging/resolving incidents
- Getting service status
- Listing recent alerts
"""

from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime, timedelta


@dataclass
class PagerDutyTools:
    """PagerDuty API tools for SRE operations."""

    api_key: str
    _session: Any = None

    def __post_init__(self):
        """Initialize PagerDuty API session lazily."""
        if not self.api_key:
            return

        try:
            from pdpyras import APISession

            self._session = APISession(self.api_key, default_from="sre-copilot@example.com")
        except ImportError:
            pass

    def _ensure_session(self) -> bool:
        """Ensure API session is initialized."""
        return self._session is not None

    def get_incidents(
        self,
        statuses: Optional[list[str]] = None,
        urgency: Optional[str] = None,
        service_ids: Optional[list[str]] = None,
        limit: int = 25,
    ) -> dict:
        """
        List PagerDuty incidents.

        Args:
            statuses: Filter by status (triggered, acknowledged, resolved)
            urgency: Filter by urgency (high, low)
            service_ids: Filter by service IDs
            limit: Maximum incidents to return

        Returns:
            List of incidents with details
        """
        if not self._ensure_session():
            return {"error": "PagerDuty client not configured"}

        try:
            params = {"limit": limit}

            if statuses:
                params["statuses[]"] = statuses
            else:
                # Default to active incidents
                params["statuses[]"] = ["triggered", "acknowledged"]

            if urgency:
                params["urgencies[]"] = [urgency]

            if service_ids:
                params["service_ids[]"] = service_ids

            incidents = self._session.list_all("incidents", params=params)

            results = []
            status_counts = {"triggered": 0, "acknowledged": 0, "resolved": 0}

            for incident in incidents[:limit]:
                status = incident.get("status", "unknown")
                if status in status_counts:
                    status_counts[status] += 1

                results.append({
                    "id": incident.get("id"),
                    "incident_number": incident.get("incident_number"),
                    "title": incident.get("title"),
                    "status": status,
                    "urgency": incident.get("urgency"),
                    "created_at": incident.get("created_at"),
                    "service": {
                        "id": incident.get("service", {}).get("id"),
                        "name": incident.get("service", {}).get("summary"),
                    },
                    "assigned_to": [
                        a.get("assignee", {}).get("summary")
                        for a in incident.get("assignments", [])
                    ],
                    "escalation_policy": incident.get("escalation_policy", {}).get("summary"),
                    "html_url": incident.get("html_url"),
                })

            return {
                "incidents": results,
                "total_count": len(results),
                "status_summary": status_counts,
            }

        except Exception as e:
            return {"error": f"Failed to fetch incidents: {str(e)}"}

    def get_incident_details(self, incident_id: str) -> dict:
        """
        Get detailed information about a specific incident.

        Args:
            incident_id: PagerDuty incident ID

        Returns:
            Incident details including timeline and notes
        """
        if not self._ensure_session():
            return {"error": "PagerDuty client not configured"}

        try:
            incident = self._session.rget(f"incidents/{incident_id}")

            # Get incident notes
            notes = []
            try:
                notes_response = self._session.rget(f"incidents/{incident_id}/notes")
                notes = [
                    {
                        "content": n.get("content"),
                        "created_at": n.get("created_at"),
                        "user": n.get("user", {}).get("summary"),
                    }
                    for n in notes_response.get("notes", [])[:10]
                ]
            except Exception:
                pass

            # Get log entries (timeline)
            timeline = []
            try:
                log_entries = self._session.list_all(
                    f"incidents/{incident_id}/log_entries",
                    params={"limit": 20}
                )
                timeline = [
                    {
                        "type": entry.get("type"),
                        "created_at": entry.get("created_at"),
                        "summary": entry.get("summary"),
                        "agent": entry.get("agent", {}).get("summary"),
                    }
                    for entry in log_entries[:20]
                ]
            except Exception:
                pass

            return {
                "id": incident.get("id"),
                "incident_number": incident.get("incident_number"),
                "title": incident.get("title"),
                "status": incident.get("status"),
                "urgency": incident.get("urgency"),
                "created_at": incident.get("created_at"),
                "resolved_at": incident.get("resolved_at"),
                "description": incident.get("description"),
                "service": {
                    "id": incident.get("service", {}).get("id"),
                    "name": incident.get("service", {}).get("summary"),
                },
                "assigned_to": [
                    a.get("assignee", {}).get("summary")
                    for a in incident.get("assignments", [])
                ],
                "escalation_policy": incident.get("escalation_policy", {}).get("summary"),
                "html_url": incident.get("html_url"),
                "notes": notes,
                "timeline": timeline,
            }

        except Exception as e:
            return {"error": f"Failed to fetch incident details: {str(e)}"}

    def get_oncall(
        self,
        schedule_ids: Optional[list[str]] = None,
        escalation_policy_ids: Optional[list[str]] = None,
    ) -> dict:
        """
        Get current on-call users.

        Args:
            schedule_ids: Filter by schedule IDs
            escalation_policy_ids: Filter by escalation policy IDs

        Returns:
            Current on-call users and their schedules
        """
        if not self._ensure_session():
            return {"error": "PagerDuty client not configured"}

        try:
            params = {}
            if schedule_ids:
                params["schedule_ids[]"] = schedule_ids
            if escalation_policy_ids:
                params["escalation_policy_ids[]"] = escalation_policy_ids

            oncalls = self._session.list_all("oncalls", params=params)

            results = []
            seen = set()

            for oncall in oncalls:
                user = oncall.get("user") or {}
                schedule = oncall.get("schedule") or {}
                escalation_policy = oncall.get("escalation_policy") or {}

                key = f"{user.get('id')}:{schedule.get('id')}:{oncall.get('escalation_level')}"
                if key in seen:
                    continue
                seen.add(key)

                results.append({
                    "user": {
                        "id": user.get("id"),
                        "name": user.get("summary"),
                        "email": user.get("email"),
                    },
                    "schedule": {
                        "id": schedule.get("id"),
                        "name": schedule.get("summary"),
                    } if schedule else None,
                    "escalation_policy": {
                        "id": escalation_policy.get("id"),
                        "name": escalation_policy.get("summary"),
                    } if escalation_policy else None,
                    "escalation_level": oncall.get("escalation_level"),
                    "start": oncall.get("start"),
                    "end": oncall.get("end"),
                })

            return {
                "oncalls": results,
                "count": len(results),
            }

        except Exception as e:
            return {"error": f"Failed to fetch on-call information: {str(e)}"}

    def get_services(
        self,
        name_filter: Optional[str] = None,
        include_status: bool = True,
        limit: int = 50,
    ) -> dict:
        """
        List PagerDuty services and their status.

        Args:
            name_filter: Filter services by name
            include_status: Include current status information
            limit: Maximum services to return

        Returns:
            List of services with status
        """
        if not self._ensure_session():
            return {"error": "PagerDuty client not configured"}

        try:
            params = {"limit": limit}
            if name_filter:
                params["query"] = name_filter

            services = self._session.list_all("services", params=params)

            results = []
            status_counts = {"active": 0, "warning": 0, "critical": 0, "maintenance": 0, "disabled": 0}

            for service in services[:limit]:
                status = service.get("status", "unknown")
                if status in status_counts:
                    status_counts[status] += 1

                results.append({
                    "id": service.get("id"),
                    "name": service.get("name"),
                    "description": service.get("description", "")[:200] if service.get("description") else None,
                    "status": status,
                    "escalation_policy": service.get("escalation_policy", {}).get("summary"),
                    "created_at": service.get("created_at"),
                    "html_url": service.get("html_url"),
                    "incident_urgency_rule": service.get("incident_urgency_rule", {}).get("type"),
                })

            return {
                "services": results,
                "total_count": len(results),
                "status_summary": status_counts,
            }

        except Exception as e:
            return {"error": f"Failed to fetch services: {str(e)}"}

    def acknowledge_incident(self, incident_id: str) -> dict:
        """
        Acknowledge a PagerDuty incident.

        Args:
            incident_id: PagerDuty incident ID

        Returns:
            Updated incident status
        """
        if not self._ensure_session():
            return {"error": "PagerDuty client not configured"}

        try:
            payload = {
                "incident": {
                    "type": "incident_reference",
                    "status": "acknowledged",
                }
            }

            result = self._session.rput(f"incidents/{incident_id}", json=payload)

            return {
                "success": True,
                "incident_id": incident_id,
                "new_status": result.get("status", "acknowledged"),
                "message": f"Incident {incident_id} acknowledged",
            }

        except Exception as e:
            return {"error": f"Failed to acknowledge incident: {str(e)}"}

    def resolve_incident(self, incident_id: str, resolution: Optional[str] = None) -> dict:
        """
        Resolve a PagerDuty incident.

        Args:
            incident_id: PagerDuty incident ID
            resolution: Optional resolution note

        Returns:
            Updated incident status
        """
        if not self._ensure_session():
            return {"error": "PagerDuty client not configured"}

        try:
            payload = {
                "incident": {
                    "type": "incident_reference",
                    "status": "resolved",
                }
            }

            if resolution:
                payload["incident"]["resolution"] = resolution

            result = self._session.rput(f"incidents/{incident_id}", json=payload)

            return {
                "success": True,
                "incident_id": incident_id,
                "new_status": result.get("status", "resolved"),
                "message": f"Incident {incident_id} resolved",
            }

        except Exception as e:
            return {"error": f"Failed to resolve incident: {str(e)}"}

    def get_recent_alerts(
        self,
        service_id: Optional[str] = None,
        since_hours: int = 24,
        limit: int = 50,
    ) -> dict:
        """
        Get recent alerts/triggers.

        Args:
            service_id: Filter by service ID
            since_hours: Look back this many hours (default: 24)
            limit: Maximum alerts to return

        Returns:
            List of recent alerts
        """
        if not self._ensure_session():
            return {"error": "PagerDuty client not configured"}

        try:
            since = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat() + "Z"

            params = {
                "since": since,
                "limit": limit,
            }

            if service_id:
                path = f"services/{service_id}/log_entries"
            else:
                path = "log_entries"
                params["is_overview"] = True

            log_entries = self._session.list_all(path, params=params)

            # Filter to trigger events
            alerts = []
            for entry in log_entries:
                if entry.get("type") not in ["trigger_log_entry", "alert_log_entry"]:
                    continue

                alerts.append({
                    "id": entry.get("id"),
                    "type": entry.get("type"),
                    "created_at": entry.get("created_at"),
                    "summary": entry.get("summary"),
                    "service": entry.get("service", {}).get("summary"),
                    "incident": {
                        "id": entry.get("incident", {}).get("id"),
                        "summary": entry.get("incident", {}).get("summary"),
                    } if entry.get("incident") else None,
                })

                if len(alerts) >= limit:
                    break

            return {
                "alerts": alerts,
                "count": len(alerts),
                "since": since,
            }

        except Exception as e:
            return {"error": f"Failed to fetch alerts: {str(e)}"}


# Tool definitions for Claude
PAGERDUTY_TOOLS = [
    {
        "name": "pagerduty_get_incidents",
        "description": "List PagerDuty incidents. Use this to check active incidents, their urgency, and assignments.",
        "input_schema": {
            "type": "object",
            "properties": {
                "statuses": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by status: 'triggered', 'acknowledged', 'resolved'. Default: ['triggered', 'acknowledged']",
                },
                "urgency": {
                    "type": "string",
                    "enum": ["high", "low"],
                    "description": "Filter by urgency level",
                },
                "service_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by service IDs",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum incidents to return (default: 25)",
                    "default": 25,
                },
            },
        },
    },
    {
        "name": "pagerduty_get_incident_details",
        "description": "Get detailed information about a specific PagerDuty incident including timeline and notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "PagerDuty incident ID",
                },
            },
            "required": ["incident_id"],
        },
    },
    {
        "name": "pagerduty_get_oncall",
        "description": "Get current on-call users. Use this to find who is responsible for incidents or services.",
        "input_schema": {
            "type": "object",
            "properties": {
                "schedule_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by schedule IDs",
                },
                "escalation_policy_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by escalation policy IDs",
                },
            },
        },
    },
    {
        "name": "pagerduty_get_services",
        "description": "List PagerDuty services and their current status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name_filter": {
                    "type": "string",
                    "description": "Filter services by name (substring match)",
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
        "name": "pagerduty_acknowledge_incident",
        "description": "Acknowledge a PagerDuty incident. Use this when starting to work on an incident.",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "PagerDuty incident ID to acknowledge",
                },
            },
            "required": ["incident_id"],
        },
    },
    {
        "name": "pagerduty_resolve_incident",
        "description": "Resolve a PagerDuty incident. Use this when an incident is fixed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "PagerDuty incident ID to resolve",
                },
                "resolution": {
                    "type": "string",
                    "description": "Optional resolution note describing the fix",
                },
            },
            "required": ["incident_id"],
        },
    },
    {
        "name": "pagerduty_get_recent_alerts",
        "description": "Get recent alerts/triggers from PagerDuty. Use this to see what alerts have fired recently.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service_id": {
                    "type": "string",
                    "description": "Filter by service ID",
                },
                "since_hours": {
                    "type": "integer",
                    "description": "Look back this many hours (default: 24)",
                    "default": 24,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum alerts to return (default: 50)",
                    "default": 50,
                },
            },
        },
    },
]
