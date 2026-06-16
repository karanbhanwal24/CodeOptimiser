import ast
import contextlib
import io
import timeit
import tracemalloc

from services.optimization import generate_variants


REPETITIONS = 5


def _safe_exec(compiled):
    namespace = {"__name__": "__benchmark__"}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compiled, namespace, namespace)


def _measure_code(code):
    try:
        compiled = compile(code, "<optimizer-variant>", "exec")
    except Exception as exc:
        return {"error": str(exc), "time_ms": None, "memory_mb": None}

    timer = timeit.Timer(lambda: _safe_exec(compiled))
    try:
        timings = timer.repeat(repeat=REPETITIONS, number=1)
        best_time_ms = min(timings) * 1000
    except Exception as exc:
        return {"error": str(exc), "time_ms": None, "memory_mb": None}

    try:
        tracemalloc.start()
        tracemalloc.clear_traces()
        _safe_exec(compiled)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    except Exception as exc:
        with contextlib.suppress(Exception):
            tracemalloc.stop()
        return {"error": str(exc), "time_ms": round(best_time_ms, 4), "memory_mb": None}

    return {
        "error": None,
        "time_ms": round(best_time_ms, 4),
        "memory_mb": round(peak / (1024 * 1024), 6),
    }


def _improvement(original_value, variant_value):
    if original_value in (None, 0) or variant_value is None:
        return 0.0
    return round(((original_value - variant_value) / original_value) * 100, 2)


def _confidence(improvement_pct):
    if improvement_pct > 20:
        return "high"
    if improvement_pct >= 5:
        return "medium"
    return "low"


def _count_non_empty_lines(code):
    return sum(1 for line in code.splitlines() if line.strip())


def _cyclomatic_complexity(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While)):
            complexity += 1
        elif isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            complexity += max(len(node.values) - 1, 1)
    return complexity


def _prepare_variants(original_code, variants):
    if variants is not None:
        return {"variants": variants}
    return generate_variants(original_code)


def _select_output_variant(comparison_variants):
    combined_variant = next(
        (
            variant
            for variant in comparison_variants
            if variant.get("name") == "combined"
            and not variant.get("error")
            and variant.get("code")
        ),
        None,
    )
    if combined_variant:
        return combined_variant

    valid_variants = [variant for variant in comparison_variants if not variant["error"] and variant["time_ms"] is not None]
    if not valid_variants:
        return None
    return min(valid_variants, key=lambda item: (item["time_ms"], item["memory_mb"] or float("inf")))


def compare_variants(original_code: str, variants=None) -> dict:
    generated = _prepare_variants(original_code, variants)
    original_metrics = _measure_code(original_code)

    comparison_variants = []
    combined_summary = {}

    for variant in generated["variants"]:
        variant_code = variant.get("code", original_code)
        metrics = _measure_code(variant_code)
        time_gain = _improvement(original_metrics["time_ms"], metrics["time_ms"])
        memory_gain = _improvement(original_metrics["memory_mb"], metrics["memory_mb"])
        entry = {
            **variant,
            "time_ms": metrics["time_ms"],
            "memory_mb": metrics["memory_mb"],
            "time_improvement_pct": time_gain,
            "memory_improvement_pct": memory_gain,
            "confidence": _confidence(time_gain),
            "error": metrics["error"],
        }

        if variant.get("name") == "combined":
            entry["lines_of_code_before"] = _count_non_empty_lines(original_code)
            entry["lines_of_code_after"] = _count_non_empty_lines(variant_code)
            entry["cyclomatic_complexity_before"] = _cyclomatic_complexity(original_code)
            entry["cyclomatic_complexity_after"] = _cyclomatic_complexity(variant_code)
            combined_summary = {
                "lines_of_code_before": entry["lines_of_code_before"],
                "lines_of_code_after": entry["lines_of_code_after"],
                "cyclomatic_complexity_before": entry["cyclomatic_complexity_before"],
                "cyclomatic_complexity_after": entry["cyclomatic_complexity_after"],
            }

        comparison_variants.append(entry)

    best_variant = _select_output_variant(comparison_variants)

    optimized_code = best_variant["code"] if best_variant else original_code
    optimized_time_ms = best_variant["time_ms"] if best_variant else original_metrics["time_ms"]
    optimized_memory_mb = best_variant["memory_mb"] if best_variant else original_metrics["memory_mb"]

    improvements = [f"{variant['name']}: {variant['description']}" for variant in comparison_variants if variant["name"] != "no-op"]
    explanation = (
        f"Selected '{best_variant['name']}' as the final output after applying safe rewrites until the optimizer reached a fixed point."
        if best_variant
        else "No executable optimization variant outperformed the original code, so the original was preserved."
    )

    return {
        "optimized_code": optimized_code,
        "original_time_ms": original_metrics["time_ms"],
        "optimized_time_ms": optimized_time_ms,
        "original_memory_mb": original_metrics["memory_mb"],
        "optimized_memory_mb": optimized_memory_mb,
        "time_improvement_pct": _improvement(original_metrics["time_ms"], optimized_time_ms),
        "memory_improvement_pct": _improvement(original_metrics["memory_mb"], optimized_memory_mb),
        "variants": comparison_variants,
        "explanation": explanation,
        "improvements": improvements,
        **combined_summary,
    }
