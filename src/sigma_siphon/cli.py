from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .areas import load_areas
from .pipeline import run_pipeline

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
    llm_ready = bool(os.getenv("SIGMA_LLM_MODEL") and os.getenv("SIGMA_LLM_API_KEY"))
    osm_ready = bool(os.getenv("SIGMA_OSM_OVERPASS_URL"))
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
    console.print(f"OSM endpoint: {'configured' if osm_ready else 'not configured'}")
    console.print(f"LLM: {'configured' if llm_ready else 'not configured (rules-only fallback)'}")


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
        typer.Option("--llm/--no-llm", help="Use configured LLM for rows not handled by rules"),
    ] = True,
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
    if llm and not report["classification"]["llm_enabled"]:
        console.print(
            "[yellow]LLM credentials are not configured; unresolved rows were left blank. "
            "Set SIGMA_LLM_MODEL and SIGMA_LLM_API_KEY, then rerun.[/yellow]"
        )
    console.print(
        f"[green]Complete[/green]: {counts['canonical']:,} POIs, "
        f"{counts['tagged']:,} tagged, {counts['unresolved']:,} unresolved"
    )
    console.print(f"Output: [bold]{target}[/bold]")


if __name__ == "__main__":
    app()
