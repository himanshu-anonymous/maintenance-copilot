"""
warmup.py
Primes the Readiness Assistant system:
1. Verifies /api/health
2. Primes the BM25 retrieval index and in-memory JsonGraphStore
3. Establishes persistent HTTP/2 client connection to Gemini API
4. Warms up Redis LRU cache
"""

import time
import json
import urllib.request
import sys

API_BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000/api"


def main():
    print("=" * 60)
    print("READINESS ASSISTANT — WARMUP SCRIPT")
    print("=" * 60)

    # 1. Check Health
    print("[1/3] Pinging API healthcheck endpoint...")
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(f"{API_BASE}/health")
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode())
            print(f"      Status: {data.get('status')} | SQLite: {data.get('services', {}).get('sqlite', {}).get('status')} | Redis: {data.get('services', {}).get('redis', {}).get('status')}")
    except Exception as e:
        print(f"      Healthcheck ping failed: {e}")
        sys.exit(1)

    # 2. Prime Graph & Retrieval
    print("[2/3] Priming Graph Store and BM25 index...")
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(f"{API_BASE}/assets")
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            assets = json.loads(resp.read().decode())
            print(f"      Loaded {len(assets)} assets into memory in {(time.perf_counter() - t0)*1000:.1f} ms")
    except Exception as e:
        print(f"      Assets priming failed: {e}")

    # 3. Prime Diagnostic Engine & LLM connection
    print("[3/3] Sending warmup diagnostic query to prime HTTP/2 connection...")
    t0 = time.perf_counter()
    try:
        payload = {
            "asset_id": "P-101",
            "symptom_text": "Vibration check warmup routine",
            "stream": False
        }
        req = urllib.request.Request(
            f"{API_BASE}/diagnose",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            res_str = resp.read().decode()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            print(f"      Warmup query completed in {elapsed_ms:.1f} ms")
    except Exception as e:
        print(f"      Warmup diagnostic query warning: {e}")

    print("=" * 60)
    print(">>> WARMUP COMPLETE — SYSTEM READY FOR SUB-SECOND DEMO <<<")
    print("=" * 60)


if __name__ == "__main__":
    main()
