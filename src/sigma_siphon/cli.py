from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .areas import load_areas
from .llm import LLMClassifier
from .pipeline import run_pipeline
from .settings import DEFAULT_LLM_MODEL, DEFAULT_OSM_OVERPASS_URL

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Acquire, reconcile, clip and IO-tag Philippine POIs.",
)
console = Console()


@app.command("areas")
def areas_command(
    search: Annotated[str | None, typer.Option(help="Filter area names/slugs")] = None,
    areas_file: Annotated[Path | None, typer.Option(help="Alternate areas YAML")] = None,
) -> None:
    areas = load_areas(areas_file)
    query = (search or "").casefold().strip()
    table = Table(title="Configured areas")
    table.add_column("Slug")
    table.add_column("Name")
    table.add_column("Kind")
    table.add_column("PSGC")
    table.add_column("Boundary")
    for area in areas.values():
        haystack = f"{area.slug} {area.name} {' '.join(area.aliases)}".casefold()
        if query and query not in haystack:
            continue
        table.add_row(
            area.slug,
            area.name,
            area.kind,
            area.psgc_code or "—",
            "GPKG" if area.boundary else "bbox",
        )
    console.print(table)


@app.command("doctor")
def doctor(
    areas_file: Annotated[Path | None, typer.Option(help="Alternate areas YAML")] = None,
) -> None:
    areas = load_areas(areas_file)
    llm_ready = LLMClassifier.is_configured()
    osm_override = bool(os.getenv("SIGMA_OSM_OVERPASS_URL", "").strip())

    console.print(f"sigma-siphon {__version__}")
    localities = sum(area.kind in {"city", "municipality"} for area in areas.values())
    composites = sum(area.kind == "composite" for area in areas.values())
    console.print(f"Areas: {len(areas)} ({localities} localities + {composites} composites)")

    boundary_files = {
        area.boundary.gpkg
        for area in areas.values()
        if area.boundary is not None
    }
    missing_boundaries = sorted(path for path in boundary_files if not path.exists())
    console.print(
        "Exact boundaries: "
        + ("available" if boundary_files and not missing_boundaries else "MISSING")
    )
    if missing_boundaries:
        for path in missing_boundaries:
            console.print(f"  missing: {path}")

    endpoint_label = (
        "deployment override"
        if osm_override
        else f"built-in default ({DEFAULT_OSM_OVERPASS_URL})"
    )
    console.print(f"OSM endpoint: ready — {endpoint_label}")

    if llm_ready:
        model = os.getenv("SIGMA_LLM_MODEL", DEFAULT_LLM_MODEL).strip() or DEFAULT_LLM_MODEL
        console.print(f"LLM: configured — {model}")
    else:
        console.print(
            "LLM: optional — API key not configured "
            "(default rules-only mode is ready)"
        )


@app.command("run")
def run_command(
    area: Annotated[str, typer.Argument(help="Area slug, exact name, or 10-digit PSGC")],
    areas_file: Annotated[Path | None, typer.Option(help="Alternate areas YAML")] = None,
    root: Annotated[Path, typer.Option(help="Working root")] = Path("."),
    output_dir: Annotated[
        Path | None, typer.Option(help="Output root; default <root>/output")
    ] = None,
    cache_dir: Annotated[
        Path | None, typer.Option(help="Cache root; default <root>/.sigma-cache")
    ] = None,
    refresh: Annotated[bool, typer.Option(help="Redownload source data for this area")] = False,
    clip: Annotated[
        bool,
        typer.Option("--clip/--no-clip", help="Clip source points to configured boundary"),
    ] = True,
    llm: Annotated[
        bool,
        typer.Option(
            "--llm/--no-llm",
            help="Optionally use the LLM for rows not handled by deterministic rules",
        ),
    ] = False,
) -> None:
    try:
        target, report = run_pipeline(
            area,
            areas_file=areas_file,
            root=root,
            output_dir=output_dir,
            cache_dir=cache_dir,
            refresh=refresh,
            clip=clip,
            use_llm=llm,
        )
    except (KeyError, ValueError, FileNotFoundError, RuntimeError) as exc:
        console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(1) from exc

    counts = report["counts"]
    classification = report["classification"]
    console.print(
        f"[green]Complete[/green]: {counts['canonical']:,} POIs, "
        f"{counts['tagged']:,} tagged, {counts['unresolved']:,} unresolved"
    )
    if classification["llm_enabled"]:
        console.print(
            "Classification: "
            f"{classification['tagged_by_rule']:,} rules + "
            f"{classification['tagged_by_llm']:,} LLM"
        )
    else:
        console.print(
            f"Classification: {classification['tagged_by_rule']:,} rules "
            "(default rules-only mode)"
        )
    console.print(f"Output: [bold]{target}[/bold]")


if __name__ == "__main__":
    app()
