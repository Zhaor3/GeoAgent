from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional

from geo_agent.extractors.exif import extract_exif
from geo_agent.extractors.visual import extract_visual_clues
from geo_agent.models.schemas import (
    Confidence,
    GeoResult,
    Hypothesis,
    PipelineMode,
    ToolResult,
    VisualClues,
)
from geo_agent.reasoning.final import compute_final_result
from geo_agent.reasoning.hypotheses import generate_hypotheses
from geo_agent.reasoning.verify import verify_hypotheses_with_image
from geo_agent.tools.maps import GoogleGeocodingTool, GoogleMapsPlacesTool
from geo_agent.tools.search import WebSearchTool
from geo_agent.tools.reverse_image import ReverseImageSearchTool

ProgressCallback = Optional[Callable[[str, str], Awaitable[None]]]

VERIFICATION_TOOLS = [
    GoogleMapsPlacesTool(),
    GoogleGeocodingTool(),
    WebSearchTool(),
    ReverseImageSearchTool(),
]


def _build_result_from_exif(exif_data) -> GeoResult:
    return GeoResult(
        latitude=exif_data.latitude,
        longitude=exif_data.longitude,
        country="Unknown",
        confidence=Confidence.HIGH,
        confidence_pct=99.0,
        reasoning_trace="GPS coordinates extracted directly from image EXIF metadata.",
        clues_used=VisualClues(),
    )


async def _verify_single(
    tool, hypothesis: Hypothesis, clues: VisualClues
) -> ToolResult:
    try:
        return await tool.verify(hypothesis, clues)
    except Exception as e:
        return ToolResult(
            tool_name=tool.name,
            hypothesis_rank=hypothesis.rank,
            supports=False,
            confidence_delta=0,
            evidence_summary=f"Error: {e}",
        )


async def _run_tool_verification(
    hypotheses: list[Hypothesis],
    clues: VisualClues,
) -> list[ToolResult]:
    tasks = []
    for h in hypotheses:
        for tool in VERIFICATION_TOOLS:
            tasks.append(_verify_single(tool, h, clues))
    return await asyncio.gather(*tasks)


async def run_pipeline(
    image_bytes: bytes,
    mode: PipelineMode = PipelineMode.FULL,
    progress_callback: ProgressCallback = None,
) -> GeoResult:
    async def emit(stage: str, detail: str = ""):
        if progress_callback:
            await progress_callback(stage, detail)

    # ── Stage 1: EXIF check ──
    await emit("📋 Extracting metadata...")
    exif_data = extract_exif(image_bytes)
    if exif_data.has_gps:
        await emit("✅ GPS found in EXIF!", f"{exif_data.latitude}, {exif_data.longitude}")
        return _build_result_from_exif(exif_data)

    # ── Stage 2: Two-pass visual clue extraction (extended thinking) ──
    await emit("🔍 Pass 1 — Scanning for every visual clue...")
    clues = await extract_visual_clues(image_bytes)
    await emit("🔍 Visual analysis complete", "Two-pass extraction done")

    # ── Stage 3: Hypothesis generation (extended thinking) ──
    await emit("🧠 Generating location hypotheses (deep reasoning)...")
    hypotheses = await generate_hypotheses(clues)

    # ── Stage 4: Self-verification — re-examine image vs hypotheses ──
    await emit("🔎 Re-examining image against hypotheses...")
    try:
        hypotheses = await verify_hypotheses_with_image(image_bytes, hypotheses, clues)
    except Exception:
        pass  # Continue with unverified hypotheses if this fails

    if mode == PipelineMode.FULL:
        # ── Stage 5: External tool verification ──
        await emit("🔧 Verifying with external tools...")
        tool_results = list(await _run_tool_verification(hypotheses, clues))

        # ── Stage 6: Final scoring ──
        await emit("⚖️ Final reasoning...")
        result = compute_final_result(hypotheses, tool_results, clues)
    else:
        result = compute_final_result(hypotheses, [], clues)

    await emit("✅ Done!", f"{result.country}, {result.city or ''}")
    return result
