from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .areas import load_areas
from .classification import ReferenceDataError, validate_builtin_classification_reference
from .llm import LLMClassifier
from .pipeline import run_pipeline
from .settings import DEFAULT_GEOFABRIK_MAX_AGE_DAYS
from .sources.geofabrik import cache_status

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
    key_present = LLMClassifier.is_configured()

    console.print(f"sigma-siphon {__version__}")
    localities = sum(area.kind in {"city", "municipality"} for area in areas.values())
    composites = sum(area.kind == "composite" for area in areas.values())
    console.print(f"Areas: {len(areas)} ({localities} localities + {composites} composites)")
    console.print("OSM source: Geofabrik Philippines PBF")
    console.print(
        "OSM preparation: resumable checkpoints; one national scan per Geofabrik version"
    )
    console.print(
        f"Geofabrik refresh prompt threshold: {DEFAULT_GEOFABRIK_MAX_AGE_DAYS:g} days"
    )
    console.print(
        "Classification reference: built-in PSIC Rev. 5 + PSA 2018 IO16/IO80/IO240 "
        "(run classification-check to validate)"
    )

    if key_present:
        console.print(
            "LLM: API key variable present (not validated) — "
            "LLM is used only when --llm is explicitly requested"
        )
    else:
        console.print(
            "LLM: optional — no API key variable present "
            "(default rules-only mode is ready)"
        )


@app.command("classification-check")
def classification_check() -> None:
    """Validate the built-in PSIC and input-output reference bundle."""
    try:
        report = validate_builtin_classification_reference()
    except ReferenceDataError as exc:
        console.print(f"[red]classification reference error:[/red] {exc}")
        raise typer.Exit(1) from exc

    table = Table(title="Built-in classification reference")
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Details")

    levels = ", ".join(
        f"{level}={count:,}" for level, count in report.taxonomy_level_counts.items()
    )
    table.add_row(
        "PSIC Revision 5",
        "OK",
        f"{report.taxonomy_nodes:,} nodes; {report.taxonomy_roots} roots; {levels}",
    )
    table.add_row(
        "PSIC hierarchy",
        "OK",
        f"fingerprint {report.taxonomy_fingerprint}; "
        f"{report.structural_level_gaps} non-fatal level gap(s)",
    )
    table.add_row(
        "Rev5 → PSIC 2019 bridge",
        "OK",
        f"{report.bridge_rows:,} rows; "
        + ", ".join(f"{k}={v:,}" for k, v in report.bridge_level_counts.items()),
    )
    table.add_row(
        "PSIC 2019 → PSA 2018 I-O",
        "OK",
        f"{report.concordance_rows:,} rows; "
        + ", ".join(f"{k}={v:,}" for k, v in report.concordance_level_counts.items()),
    )
    table.add_row(
        "OSM/Overture crosswalk references",
        "OK",
        f"{len(report.crosswalk_files)} files; {report.crosswalk_rows:,} rows",
    )
    table.add_row(
        "Official PSIC workbook",
        "OK",
        f"sha256 {report.workbook_sha256[:16]}…",
    )
    console.print(table)
    console.print("[green]Classification reference bundle is internally consistent.[/green]")


def _decide_geofabrik_refresh(
    *,
    cache_base: Path,
    max_age_days: float,
    force_refresh: bool,
) -> bool:
    if force_refresh:
        console.print("Geofabrik: refresh explicitly requested.")
        return True

    console.print("Checking cached Geofabrik Philippines extract...")
    status = cache_status(cache_base, max_age_days=max_age_days, check_remote=True)

    if not status.exists:
        console.print("No cached Geofabrik Philippines PBF exists.")
        return typer.confirm(
            "Download it now? It will be reused by later runs.",
            default=True,
            abort=True,
        )

    console.print(f"Geofabrik cache: {status.age_description}.")
    if not status.stale:
        console.print(
            f"Geofabrik cache is within the {max_age_days:g}-day refresh threshold."
        )
        return False

    if status.remote_checked and status.source_gap_days is not None:
        question = (
            f"The cached Geofabrik extract is {status.source_gap_days:.1f} days "
            "behind the current Geofabrik file. Refresh and rebuild all LGU OSM caches?"
        )
    else:
        question = (
            f"The cached Geofabrik extract is {status.cache_age_days:.1f} days old. "
            "Refresh and rebuild all LGU OSM caches?"
        )
    return typer.confirm(question, default=False)


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
    refresh: Annotated[
        bool,
        typer.Option(help="Refresh area-level Overture data and downstream output"),
    ] = False,
    refresh_geofabrik: Annotated[
        bool,
        typer.Option(
            "--refresh-geofabrik",
            help="Force download of current Geofabrik PBF; all LGU OSM caches rebuild",
        ),
    ] = False,
    geofabrik_max_age_days: Annotated[
        float,
        typer.Option(
            "--geofabrik-max-age-days",
            help="Prompt when cached Geofabrik source is this far behind",
        ),
    ] = DEFAULT_GEOFABRIK_MAX_AGE_DAYS,
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
    def show_progress(message: str) -> None:
        console.print(f"[cyan]→[/cyan] {message}")

    cache_base = (cache_dir or root.resolve() / ".sigma-cache").resolve()
    geofabrik_refresh = _decide_geofabrik_refresh(
        cache_base=cache_base,
        max_age_days=geofabrik_max_age_days,
        force_refresh=refresh_geofabrik,
    )

    try:
        target, report = run_pipeline(
            area,
            areas_file=areas_file,
            root=root,
            output_dir=output_dir,
            cache_dir=cache_dir,
            refresh=refresh,
            refresh_geofabrik=geofabrik_refresh,
            clip=clip,
            use_llm=llm,
            progress=show_progress,
        )
    except (KeyError, ValueError, FileNotFoundError, RuntimeError) as exc:
        console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(1) from exc

    counts = report["counts"]
    console.print(
        f"[green]Complete[/green]: {counts['canonical']:,} POIs, "
        f"{counts['tagged']:,} tagged, {counts['unresolved']:,} unresolved"
    )
    console.print(f"Output: [bold]{target}[/bold]")


if __name__ == "__main__":
    app()
