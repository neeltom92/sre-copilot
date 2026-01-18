#!/usr/bin/env python3
"""Test APM metrics to verify span type discovery and service stats work correctly."""

from config import Config
from tools.datadog_tools import DatadogTools
import json


def test_apm():
    config = Config.from_env()

    print("=" * 70)
    print("APM Metrics Test")
    print("=" * 70)

    if not config.is_datadog_configured():
        print("\n❌ Datadog not configured!")
        return

    print("\n--- Initializing Datadog Tools ---")
    dd = DatadogTools(
        api_key=config.datadog_api_key,
        app_key=config.datadog_app_key,
        site=config.datadog_site,
    )

    # Test 1: List APM services (no env filter)
    print("\n--- Test 1: List APM Services (all envs) ---")
    try:
        result = dd.get_apm_services(limit=10)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Found {result.get('count', 0)} services (total discovered: {result.get('total_discovered', 0)})")
            for svc in result.get('services', [])[:5]:
                print(f"   - {svc.get('service')}: {svc.get('requests_last_hour')} requests, span_types: {svc.get('span_types', [])}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: List APM services in dev
    print("\n--- Test 2: List APM Services (env=dev) ---")
    try:
        result = dd.get_apm_services(env="dev", limit=10)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Found {result.get('count', 0)} services in dev")
            for svc in result.get('services', [])[:5]:
                print(f"   - {svc.get('service')}: {svc.get('requests_last_hour')} requests, span_types: {svc.get('span_types', [])}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 3: Get service stats for a specific service in dev (using "weather" which exists)
    print("\n--- Test 3: Get Service Stats (weather in dev) ---")
    try:
        result = dd.get_service_stats(service="weather", env="dev", from_time="now-1h")
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Service: {result.get('service')}, Env: {result.get('env')}")
            if result.get('warning'):
                print(f"⚠️  Warning: {result.get('warning')}")
                print(f"   Tried span types: {result.get('tried_span_types', [])}")
            else:
                print(f"   Span type: {result.get('span_type')}")
                latency = result.get('latency', {})
                print(f"   Latency: avg={latency.get('avg_ms')}ms, p95={latency.get('p95_ms')}ms, p99={latency.get('p99_ms')}ms")
                throughput = result.get('throughput', {})
                print(f"   Throughput: {throughput.get('requests_per_sec')} req/s")
                errors = result.get('errors', {})
                print(f"   Errors: {errors.get('errors_per_sec')} err/s, rate={errors.get('error_rate_percent')}%")
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

    # Test 3b: Test with "mono" in dev (which likely doesn't exist - to show warning message)
    print("\n--- Test 3b: Get Service Stats (mono in dev - likely no data) ---")
    try:
        result = dd.get_service_stats(service="mono", env="dev", from_time="now-1h")
        if result.get('warning'):
            print(f"⚠️  As expected: {result.get('warning')[:80]}...")
        else:
            print(f"✅ Unexpected: Found data for mono! Span type: {result.get('span_type')}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 4: Get service stats for a service that might use different span type
    print("\n--- Test 4: Test Span Type Discovery ---")
    try:
        # First discover what span type mono uses
        span_name = dd._discover_service_span_name("mono", "dev")
        print(f"   Discovered span name for 'mono' in dev: {span_name or 'None (no data found)'}")

        # Try with prod
        span_name_prod = dd._discover_service_span_name("mono", "prod")
        print(f"   Discovered span name for 'mono' in prod: {span_name_prod or 'None (no data found)'}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 5: Get service stats with different time windows
    print("\n--- Test 5: Service Stats with Different Time Windows ---")
    service_to_test = "bumblebee"  # Using a service we know exists from Test 1
    env_to_test = "prod"

    for time_window in ["now-15m", "now-30m", "now-1h"]:
        try:
            result = dd.get_service_stats(service=service_to_test, env=env_to_test, from_time=time_window)
            if "warning" in result:
                print(f"   {time_window}: No data")
            else:
                latency = result.get('latency', {})
                p99 = latency.get('p99_ms')
                if p99 is not None:
                    print(f"   {time_window}: p99={p99:.2f}ms (span_type={result.get('span_type')})")
                else:
                    print(f"   {time_window}: No latency data")
        except Exception as e:
            print(f"   {time_window}: Error - {e}")

    # Test 6: Try WITHOUT env filter to see if it's an env issue
    print("\n--- Test 6: Service Stats WITHOUT env filter ---")
    try:
        result = dd.get_service_stats(service="bumblebee", env=None, from_time="now-1h")
        if "warning" in result:
            print(f"⚠️  Warning: {result.get('warning')}")
        else:
            latency = result.get('latency', {})
            print(f"✅ Service: bumblebee (no env filter)")
            print(f"   Span type: {result.get('span_type')}")
            print(f"   Latency: avg={latency.get('avg_ms')}, p95={latency.get('p95_ms')}, p99={latency.get('p99_ms')}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 7: Debug span discovery for bumblebee
    print("\n--- Test 7: Debug Span Discovery for bumblebee ---")
    try:
        span_name = dd._discover_service_span_name("bumblebee", None)
        print(f"   bumblebee (no env): {span_name or 'None'}")
        span_name = dd._discover_service_span_name("bumblebee", "prod")
        print(f"   bumblebee (env=prod): {span_name or 'None'}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 8: Direct query to see raw metrics
    print("\n--- Test 8: Direct metrics query for bumblebee ---")
    try:
        from datadog_api_client.v1.api.metrics_api import MetricsApi
        import time

        api = MetricsApi(dd._v1_client)
        now = int(time.time())
        from_ts = now - 3600  # Last hour for more data

        # Try different query patterns
        queries = [
            "sum:trace.servlet.request.hits{service:bumblebee} by {env}.as_count()",
            "avg:trace.servlet.request.duration{service:bumblebee}",
            "p99:trace.servlet.request.duration{service:bumblebee}",  # No env filter
            "percentile:trace.servlet.request.duration{service:bumblebee}[p99]",  # Alternative syntax
            "trace.servlet.request.duration.by.service.99p{service:bumblebee}",  # Try APM summary metric
        ]

        for query in queries:
            try:
                response = api.query_metrics(_from=from_ts, to=now, query=query)
                series_count = len(response.series) if response.series else 0
                if series_count > 0:
                    sample = response.series[0]
                    scope = sample.scope or "N/A"
                    points = len(sample.pointlist) if sample.pointlist else 0
                    latest = sample.pointlist[-1].value[1] if sample.pointlist and sample.pointlist[-1].value else None
                    print(f"   ✅ {query[:55]}... → {series_count} series, scope={scope[:30]}, latest={latest}")
                else:
                    print(f"   ❌ {query[:55]}... → No data")
            except Exception as e:
                print(f"   ❌ {query[:55]}... → Error: {str(e)[:50]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 9: Find actual environment names
    print("\n--- Test 9: What environments exist for bumblebee? ---")
    try:
        from datadog_api_client.v1.api.metrics_api import MetricsApi
        import time

        api = MetricsApi(dd._v1_client)
        now = int(time.time())
        from_ts = now - 3600

        query = "sum:trace.servlet.request.hits{service:bumblebee} by {env}.as_count()"
        response = api.query_metrics(_from=from_ts, to=now, query=query)

        print("   Available environments for bumblebee:")
        for series in response.series or []:
            scope = series.scope or ""
            env = "unknown"
            for part in scope.split(","):
                if part.startswith("env:"):
                    env = part.replace("env:", "")
                    break
            hits = sum(p.value[1] for p in series.pointlist if p.value[1]) if series.pointlist else 0
            print(f"   - {env}: {int(hits)} requests")
    except Exception as e:
        print(f"❌ Exception: {e}")

    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)


if __name__ == "__main__":
    test_apm()
