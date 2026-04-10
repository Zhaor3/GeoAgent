from __future__ import annotations

from geo_agent.models.schemas import (
    Confidence,
    GeoResult,
    Hypothesis,
    ToolResult,
    VisualClues,
)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_final_result(
    hypotheses: list[Hypothesis],
    tool_results: list[ToolResult],
    clues: VisualClues,
) -> GeoResult:
    scored: list[tuple[float, Hypothesis]] = []
    for h in hypotheses:
        score = h.confidence_pct
        for tr in tool_results:
            if tr.hypothesis_rank == h.rank:
                score += tr.confidence_delta
        scored.append((_clamp(score, 0, 100), h))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best = scored[0]

    if best_score > 80:
        confidence = Confidence.HIGH
    elif best_score > 50:
        confidence = Confidence.MEDIUM
    else:
        confidence = Confidence.LOW

    reasoning_parts = [f"Top hypothesis: {best.country}"]
    if best.region:
        reasoning_parts[0] += f", {best.region}"
    if best.city:
        reasoning_parts[0] += f", {best.city}"
    reasoning_parts.append(f"Reasoning: {best.reasoning}")
    for tr in tool_results:
        if tr.hypothesis_rank == best.rank:
            reasoning_parts.append(f"[{tr.tool_name}] {tr.evidence_summary}")

    return GeoResult(
        latitude=best.latitude,
        longitude=best.longitude,
        country=best.country,
        region=best.region,
        city=best.city,
        confidence=confidence,
        confidence_pct=best_score,
        reasoning_trace="\n".join(reasoning_parts),
        clues_used=clues,
        hypotheses=hypotheses,
        tool_evidence=tool_results,
    )
