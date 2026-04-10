from __future__ import annotations

import asyncio
import json
import sys

import typer
import httpx

from geo_agent.models.schemas import PipelineMode
from geo_agent.pipeline import run_pipeline
from geo_agent.utils.display import (
    console,
    print_clues,
    print_exif,
    print_header,
    print_hypotheses,
    print_result,
    print_tool_results,
)
from geo_agent.extractors.exif import extract_exif
from geo_agent.utils.image import load_image_bytes

app = typer.Typer(help="GeoLocator Agent — determine where a photo was taken.")


@app.command()
def locate(
    image: str = typer.Argument(None, help="Path to image file"),
    url: str = typer.Option(None, "--url", help="URL to image"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed reasoning"),
    fast: bool = typer.Option(False, "--fast", help="Fast mode (vision only, no tool verification)"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    if not image and not url:
        console.print("[red]Error: Provide an image path or --url[/red]")
        raise typer.Exit(1)

    mode = PipelineMode.FAST if fast else PipelineMode.FULL

    if url:
        console.print(f"📷 Downloading: {url}")
        resp = httpx.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        image_bytes = resp.content
    else:
        console.print(f"📷 Analyzing: {image}")
        image_bytes = load_image_bytes(image)

    if not output_json:
        print_header()
        exif_data = extract_exif(image_bytes)
        print_exif(exif_data)

    result = asyncio.run(run_pipeline(image_bytes=image_bytes, mode=mode))

    if output_json:
        console.print(result.model_dump_json(indent=2))
        return

    print_clues(result.clues_used)
    print_hypotheses(result.hypotheses)
    print_tool_results(result.tool_evidence)
    print_result(result, verbose=verbose)


@app.command()
def bot() -> None:
    from geo_agent.bot.telegram_bot import run_bot

    run_bot()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
