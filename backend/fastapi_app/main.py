from __future__ import annotations

import ast
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.analysis import analyze_code
from services.engine import compare_variants
from pydantic import BaseModel


class CodePayload(BaseModel):
    code: str


class MetricsPayload(BaseModel):
    original_code: str | None = None
    code: str | None = None
    variants: list[dict] | None = None


def validate_code(code: str) -> str:
    if not code or not code.strip():
        raise HTTPException(status_code=400, detail="Code is required")
    try:
        ast.parse(code)
    except SyntaxError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Python code: {exc.msg}")
    return code


def extract_original_code(payload: MetricsPayload) -> str:
    original_code = payload.original_code or payload.code
    if not original_code or not original_code.strip():
        raise HTTPException(status_code=400, detail="Original code is required")
    return validate_code(original_code)


def normalize_variants(variants: list[dict]) -> list[dict]:
    valid_variants = []
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        code = str(variant.get("code", "") or "").strip()
        if not code:
            continue
        try:
            ast.parse(code)
        except SyntaxError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid variant code: {exc.msg}")
        valid_variants.append(variant)
    return valid_variants


app = FastAPI(
    title="CodeOptimise FastAPI Backend",
    version="1.0.0",
    description="Python optimizer backend for the React frontend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "CodeOptimise FastAPI backend", "version": "1.0.0"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/analysis")
async def analysis(payload: CodePayload) -> dict:
    code = validate_code(payload.code)
    return analyze_code(code)


@app.post("/optimize")
async def optimize(payload: CodePayload) -> dict:
    code = validate_code(payload.code)
    result = compare_variants(code)
    result["analysis"] = analyze_code(code)
    return result


@app.post("/metrics")
async def metrics(payload: MetricsPayload) -> dict:
    original_code = extract_original_code(payload)
    variants = None if payload.variants is None else normalize_variants(payload.variants)
    return compare_variants(original_code, variants)


# Authentication removed: no auth endpoints in this compact backend


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
