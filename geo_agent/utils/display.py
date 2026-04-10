from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from geo_agent.models.schemas import Confidence, GeoResult

console = Console()

CONFIDENCE_COLORS = {
    Confidence.HIGH: "green",
    Confidence.MEDIUM: "yellow",
    Confidence.LOW: "red",
}


def print_header() -> None:
    console.print()
    console.print("[bold cyan]🌍 GeoLocator Agent v1.0[/bold cyan]")
    console.rule(style="cyan")


def print_exif(exif_data) -> None:
    parts = []
    if exif_data.has_gps:
        parts.append(f"[green]GPS found: {exif_data.latitude:.4f}, {exif_data.longitude:.4f}[/green]")
    else:
        parts.append("[dim]No GPS data found[/dim]")
    if exif_data.camera_model:
        parts.append(f"Camera: {exif_data.camera_make or ''} {exif_data.camera_model}".strip())
    if exif_data.datetime_original:
        parts.append(f"Date: {exif_data.datetime_original}")
    console.print(f"📋 EXIF: {' | '.join(parts)}")


def print_clues(clues) -> None:
    console.print("\n[bold]🔍 Extracting visual clues...[/bold]")
    ts = clues.text_and_signage
    if ts.get("language_detected"):
        console.print(f"   ✓ Language detected: {ts['language_detected']}")
    if ts.get("visible_text"):
        texts = ts["visible_text"][:3]
        console.print(f"   ✓ Visible text: {', '.join(texts)}")
    infra = clues.infrastructure
    if infra.get("driving_side") and infra["driving_side"] != "unknown":
        console.print(f"   ✓ Driving side: {infra['driving_side']}")
    arch = clues.architecture
    if arch.get("style"):
        console.print(f"   ✓ Architecture: {arch['style']}")
    nature = clues.nature
    if nature.get("vegetation_type"):
        console.print(f"   ✓ Vegetation: {nature['vegetation_type']}")
    df = clues.distinctive_features
    if df.get("landmarks"):
        console.print(f"   ✓ Landmarks: {', '.join(df['landmarks'][:3])}")
    if df.get("brand_names"):
        console.print(f"   ✓ Brands: {', '.join(df['brand_names'][:3])}")


def print_hypotheses(hypotheses) -> None:
    console.print("\n[bold]🧠 Generating hypotheses...[/bold]")
    for h in hypotheses:
        flag = ""
        location = f"{h.country}"
        if h.region:
            location += f" → {h.region}"
        if h.city:
            location += f" → {h.city}"
        console.print(f"   {h.rank}. {flag}{location}    ({h.confidence_pct:.0f}%)")


def print_tool_results(tool_results) -> None:
    if not tool_results:
        return
    console.print("\n[bold]🔧 Verifying with tools...[/bold]")
    for tr in tool_results:
        symbol = "✓" if tr.supports else "✗"
        sign = "+" if tr.confidence_delta >= 0 else ""
        console.print(
            f"   {symbol} {tr.tool_name}: {tr.evidence_summary} → {sign}{tr.confidence_delta:.0f}%"
        )


def print_result(result: GeoResult, verbose: bool = False) -> None:
    color = CONFIDENCE_COLORS[result.confidence]
    console.rule(style="cyan")

    location_parts = [result.city, result.region, result.country]
    location = ", ".join(p for p in location_parts if p)
    console.print(f"📍 RESULT: [bold]{location}[/bold]")
    console.print(f"🌐 Coordinates: {result.latitude:.4f}° {'N' if result.latitude >= 0 else 'S'}, {result.longitude:.4f}° {'E' if result.longitude >= 0 else 'W'}")
    console.print(f"🎯 Confidence: [bold {color}]{result.confidence.value}[/bold {color}] ({result.confidence_pct:.0f}%)")

    console.rule(style="cyan")

    if verbose and result.reasoning_trace:
        console.print(f"\n[dim]{result.reasoning_trace}[/dim]")
