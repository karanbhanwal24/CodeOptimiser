import json
import statistics
import subprocess
import sys

BENCHMARK_RUNS = 7
BENCHMARK_WARMUPS = 2
BENCHMARK_TARGET_MS = 25.0
MAX_BATCH_ITERATIONS = 1024
MAX_EXECUTION_SECONDS = 2
HEAVY_CODE_THRESHOLD_MS = 200.0
HEAVY_CODE_RUNS = 3


PYTHON_BENCHMARK_SCRIPT = f"""
import contextlib
import io
import json
import statistics
import sys
import time
import tracemalloc

RUNS = {BENCHMARK_RUNS}
WARMUPS = {BENCHMARK_WARMUPS}
TARGET_MS = {BENCHMARK_TARGET_MS}
MAX_BATCH_ITERATIONS = {MAX_BATCH_ITERATIONS}
HEAVY_CODE_THRESHOLD_MS = {HEAVY_CODE_THRESHOLD_MS}
HEAVY_CODE_RUNS = {HEAVY_CODE_RUNS}

code = sys.stdin.read()
compiled = compile(code, "<optimizer-benchmark>", "exec")

def execute_once():
    namespace = {{}}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compiled, namespace)

def run_batch(iterations):
    started = time.perf_counter()
    for _ in range(iterations):
        execute_once()
    ended = time.perf_counter()
    return (ended - started) * 1000

tracemalloc.start()
started = time.perf_counter()
execute_once()
first_run_ms = (time.perf_counter() - started) * 1000
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

if first_run_ms >= HEAVY_CODE_THRESHOLD_MS:
    iterations = 1
    run_count = HEAVY_CODE_RUNS
else:
    iterations = 1
    for _ in range(WARMUPS):
        run_batch(1)
    while iterations < MAX_BATCH_ITERATIONS:
        if run_batch(iterations) >= TARGET_MS:
            break
        iterations *= 2
    run_count = RUNS

series = [run_batch(iterations) / iterations for _ in range(run_count)]
average = sum(series) / len(series)
median = statistics.median(series)

payload = {{
    "execution_time": round(average, 4),
    "average_time": round(average, 4),
    "median_time": round(median, 4),
    "memory_usage": round(peak / 1024, 4),
    "runs": len(series),
    "series": [round(value, 4) for value in series],
    "fastest_time": round(min(series), 4),
    "slowest_time": round(max(series), 4),
    "stability": round(statistics.pstdev(series) if len(series) > 1 else 0, 4),
    "iterations_per_run": iterations,
}}

sys.stdout.write(json.dumps(payload))
"""


def benchmark_code(code):
    try:
        compile(code, "<optimizer-benchmark>", "exec")
    except Exception as exc:
        return {"error": str(exc)}

    try:
        result = subprocess.run(
            [sys.executable, "-c", PYTHON_BENCHMARK_SCRIPT],
            input=code,
            capture_output=True,
            text=True,
            timeout=MAX_EXECUTION_SECONDS + 1,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Execution exceeded {MAX_EXECUTION_SECONDS} seconds"}

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "Benchmark execution failed"
        return {"error": stderr.splitlines()[-1]}

    try:
        return json.loads(result.stdout)
    except Exception as exc:
        return {"error": f"Benchmark parser failure: {exc}"}


def compute_gain(original_value, optimized_value):
    if original_value in (None, 0) or optimized_value is None:
        return 0
    return round(((original_value - optimized_value) / original_value) * 100, 2)


def compare_metrics(original_code, optimized_code):
    original = benchmark_code(original_code)
    if original.get("error"):
        return {
            "original": original,
            "optimized": original,
            "gain": {"time_gain_percent": 0, "memory_gain_percent": 0},
            "benchmark": {
                "runs": BENCHMARK_RUNS,
                "warmups": BENCHMARK_WARMUPS,
                "timeout_seconds": MAX_EXECUTION_SECONDS,
            },
        }

    if optimized_code == original_code:
        optimized = original
    else:
        optimized = benchmark_code(optimized_code)
        if optimized.get("error"):
            optimized = original

    return {
        "original": original,
        "optimized": optimized,
        "gain": {
            "time_gain_percent": compute_gain(original.get("execution_time"), optimized.get("execution_time")),
            "memory_gain_percent": compute_gain(original.get("memory_usage"), optimized.get("memory_usage")),
        },
        "benchmark": {
            "runs": BENCHMARK_RUNS,
            "warmups": BENCHMARK_WARMUPS,
            "timeout_seconds": MAX_EXECUTION_SECONDS,
        },
    }
