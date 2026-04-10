from __future__ import annotations

from geo_agent.models.schemas import Confidence, GeoResult

CONFIDENCE_EMOJI = {
    Confidence.HIGH: "🟢",
    Confidence.MEDIUM: "🟡",
    Confidence.LOW: "🔴",
}


def format_geo_result(result: GeoResult, verbose: bool = False) -> str:
    emoji = CONFIDENCE_EMOJI[result.confidence]

    lines = [
        f"📍 *{result.city or 'Unknown'}, {result.region or ''}, {result.country}*",
        f"🌐 `{result.latitude:.4f}, {result.longitude:.4f}`",
        f"{emoji} Confidence: *{result.confidence.value}* ({result.confidence_pct:.0f}%)",
        "",
    ]

    if verbose:
        lines.append("🔍 *Key Clues:*")
        clues = result.clues_used
        if clues.text_and_signage.get("language_detected"):
            lines.append(f"  • Language: {clues.text_and_signage['language_detected']}")
        if clues.infrastructure.get("driving_side") not in (None, "unknown"):
            lines.append(f"  • Driving side: {clues.infrastructure['driving_side']}")
        if clues.architecture.get("style"):
            lines.append(f"  • Architecture: {clues.architecture['style']}")
        if clues.nature.get("vegetation_type"):
            lines.append(f"  • Vegetation: {clues.nature['vegetation_type']}")
        lines.append("")

        lines.append("🧠 *Reasoning:*")
        lines.append(f"_{result.reasoning_trace[:500]}_")
        lines.append("")

        if result.hypotheses:
            lines.append("📊 *All Hypotheses:*")
            for h in result.hypotheses[:3]:
                lines.append(
                    f"  {h.rank}. {h.country} → {h.region} → {h.city} "
                    f"({h.confidence_pct:.0f}%)"
                )

    return "\n".join(lines)
