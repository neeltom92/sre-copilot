#!/usr/bin/env python3
"""Test Datadog API connection and K8s queries."""

from config import Config
from tools.datadog_tools import DatadogTools

def test_datadog():
    config = Config.from_env()

    print("=" * 60)
    print("Datadog API Connection Test")
    print("=" * 60)

    print(f"\nAPI Key: {config.datadog_api_key[:8]}...{config.datadog_api_key[-4:]}" if config.datadog_api_key else "NOT SET")
    print(f"App Key: {config.datadog_app_key[:8]}...{config.datadog_app_key[-4:]}" if config.datadog_app_key else "NOT SET")
    print(f"Site: {config.datadog_site}")

    if not config.is_datadog_configured():
        print("\n❌ Datadog not configured!")
        return

    print("\n--- Initializing Datadog Tools ---")
    dd = DatadogTools(
        api_key=config.datadog_api_key,
        app_key=config.datadog_app_key,
        site=config.datadog_site,
    )

    print(f"V1 Client initialized: {dd._v1_client is not None}")
    print(f"V2 Client initialized: {dd._v2_client is not None}")

    # Test 1: Basic monitors query
    print("\n--- Test 1: Get Monitors ---")
    try:
        result = dd.get_monitors(limit=3)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Found {result.get('total_count', 0)} monitors")
            print(f"   Status summary: {result.get('status_summary', {})}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 2: K8s pods query
    print("\n--- Test 2: Get K8s Pods (env=dev) ---")
    try:
        result = dd.get_k8s_pods(env="dev", limit=5)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Found {result.get('total_count', 0)} pods")
            print(f"   Phase summary: {result.get('phase_summary', {})}")
            if result.get('pods'):
                print(f"   Sample pods: {[p.get('pod', 'unknown')[:30] for p in result['pods'][:3]]}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Raw metrics query to verify API works
    print("\n--- Test 3: Raw Metrics Query ---")
    try:
        result = dd.query_metrics(query="avg:system.cpu.user{*}", from_time="now-5m", to_time="now")
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            series_count = len(result.get('series', []))
            print(f"✅ Query returned {series_count} series")
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

    # Test 4: K8s specific metrics
    print("\n--- Test 4: K8s Metrics Query (kubernetes_state.pod.status_phase) ---")
    try:
        from datadog_api_client.v1.api.metrics_api import MetricsApi
        import time

        api = MetricsApi(dd._v1_client)
        now = int(time.time())
        from_ts = now - 900

        # Try different query patterns
        queries = [
            "sum:kubernetes_state.pod.status_phase{env:dev} by {pod_name,phase}",
            "sum:kubernetes_state.pod.status_phase{*} by {pod_name,phase}",
            "avg:kubernetes.pods.running{env:dev}",
            "avg:kubernetes.pods.running{*}",
        ]

        for query in queries:
            print(f"\n   Trying: {query[:60]}...")
            try:
                response = api.query_metrics(_from=from_ts, to=now, query=query)
                series_count = len(response.series) if response.series else 0
                print(f"   → Got {series_count} series")
                if series_count > 0 and response.series[0].pointlist:
                    print(f"   → Sample scope: {response.series[0].scope[:50] if response.series[0].scope else 'N/A'}...")
            except Exception as e:
                print(f"   → Error: {str(e)[:80]}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_datadog()
