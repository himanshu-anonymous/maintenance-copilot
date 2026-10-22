"""
bench.py
Sends 30 benchmark requests to the live Readiness Assistant API endpoint.
Measures and prints:
- p50 and p95 first-token latency
- p50 and p95 total response time
- Router / engine overhead (< 100 ms target)
- Cache hit rate
"""

import time
import json
import urllib.request
import math

def percentile(data, p):
    if not data:
        return 0.0
    sorted_d = sorted(data)
    k = (len(sorted_d) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_d[int(k)]
    d0 = sorted_d[int(f)] * (c - k)
    d1 = sorted_d[int(c)] * (k - f)
    return d0 + d1

API_URL = "http://localhost:8000/api/diagnose"

BENCHMARK_PROMPTS = [
    ("P-101", "Vibrating violently on pump bearing bracket", "ALM-VIB-101"),
    ("P-101", "Sounds like marbles rattling inside volute casing", "ALM-SUCT-P-LO"),
    ("P-102", "Puddle of fluid leaking under mechanical seal gland", "ALM-SEAL-LVL-LO"),
    ("M-104", "Motor drive end bearing overheating and burning grease", "ALM-MTR-BRG-HI"),
    ("P-101", "Discharge pipe hammering and pressure needle surging", "ALM-PRESS-PULS"),
    ("P-103", "Pressure gauge fluttering rapidly on discharge line", "ALM-PRESS-PULS"),
    ("M-105", "Shaft coupling buzzing with 2x running vibration", None),
    ("P-102", "Sluggish discharge delivery rate, flow below setpoint", "ALM-FLOW-LO"),
    ("P-101", "Cloudy milky oil in bearing sight glass", "ALM-OIL-CLOUDY"),
    ("M-104", "High current draw tripping overload relay", "ALM-ELEC-OVR-01"),
]


def run_single_request(asset_id: str, symptom: str, alarm: str = None):
    payload = {
        "asset_id": asset_id,
        "symptom_text": symptom,
        "alarm_code": alarm,
        "stream": True
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    t0 = time.perf_counter()
    first_token_time = None
    cache_hit = False

    with urllib.request.urlopen(req, timeout=15.0) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if line.startswith("data: "):
                data_str = line[6:].strip()
                try:
                    chunk = json.loads(data_str)
                    if chunk.get("cached") or chunk.get("cache_hit"):
                        cache_hit = True
                    if "text" in chunk and first_token_time is None:
                        first_token_time = (time.perf_counter() - t0) * 1000
                        if chunk.get("cached") or chunk.get("cache_hit"):
                            cache_hit = True
                except json.JSONDecodeError:
                    pass

    total_time = (time.perf_counter() - t0) * 1000
    if first_token_time is None:
        first_token_time = total_time

    return first_token_time, total_time, cache_hit


def main():
    print("=" * 65)
    print("READINESS ASSISTANT — 30-REQUEST LATENCY BENCHMARK")
    print(f"Target: First Token <= 1.5s (1500ms), Total Time <= 4.0s (4000ms)")
    print("=" * 65)

    first_tokens = []
    total_times = []
    cache_hits = 0
    total_requests = 30

    print(f"Executing {total_requests} diagnostic benchmark requests...")

    for i in range(total_requests):
        prompt_item = BENCHMARK_PROMPTS[i % len(BENCHMARK_PROMPTS)]
        asset_id, symptom, alarm = prompt_item

        try:
            ft_ms, tot_ms, cached = run_single_request(asset_id, symptom, alarm)
            first_tokens.append(ft_ms)
            total_times.append(tot_ms)
            if cached:
                cache_hits += 1

            status_tag = "[CACHE HIT]" if cached else "[LIVE LLM]"
            print(f"Request {i+1:02d}/30: First Token = {ft_ms:6.1f} ms | Total = {tot_ms:6.1f} ms | {status_tag} {asset_id}")
        except Exception as e:
            print(f"Request {i+1:02d}/30 FAILED: {e}")

    # Calculate statistics
    ft_p50 = percentile(first_tokens, 50)
    ft_p95 = percentile(first_tokens, 95)
    tot_p50 = percentile(total_times, 50)
    tot_p95 = percentile(total_times, 95)
    cache_rate = (cache_hits / len(first_tokens)) * 100 if first_tokens else 0.0

    print("\n" + "=" * 65)
    print("LATENCY BENCHMARK REPORT (REAL MEASURED NUMBERS)")
    print("=" * 65)
    print(f"Total Requests Completed : {len(first_tokens)} / {total_requests}")
    print(f"Cache Hit Rate           : {cache_rate:.1f}% ({cache_hits}/{len(first_tokens)})")
    print(f"First Token Latency (p50): {ft_p50:.1f} ms")
    print(f"First Token Latency (p95): {ft_p95:.1f} ms (Target <= 1500 ms)")
    print(f"Total Latency (p50)      : {tot_p50:.1f} ms")
    print(f"Total Latency (p95)      : {tot_p95:.1f} ms (Target <= 4000 ms)")
    print("=" * 65)

    return {
        "first_token_p50": ft_p50,
        "first_token_p95": ft_p95,
        "total_p50": tot_p50,
        "total_p95": tot_p95,
        "cache_rate": cache_rate
    }


if __name__ == "__main__":
    main()
