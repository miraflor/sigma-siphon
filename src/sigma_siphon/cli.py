from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .areas import load_areas
from .classification import (
    PsicClassifier,
    ReferenceDataError,
    validate_builtin_classification_reference,
)
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
    console.print(
        "PSIC-first classifier: standalone `classify` supports deterministic mode, "
        "optional hierarchical model fallback, and built-in I-O mapping; "
        "main `run` path remains unchanged at this checkpoint"
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


@app.command("classify")
def classify_command(
    input_file: Annotated[Path, typer.Argument(help="Canonical POI Parquet to classify")],
    output_file: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output Parquet; default <input>_psic.parquet",
        ),
    ] = None,
    top_n: Annotated[int, typer.Option(help="PSIC retrieval candidates retained per source")] = 5,
    min_score: Annotated[
        float, typer.Option(help="Minimum lexical score for automatic semantic refinement")
    ] = 0.45,
    min_margin: Annotated[
        float, typer.Option(help="Minimum lead over the second candidate for refinement")
    ] = 0.12,
    llm: Annotated[
        bool,
        typer.Option(
            "--llm/--no-llm",
            help="Use hierarchical model traversal only for unresolved deterministic rows",
        ),
    ] = False,
    llm_passes: Annotated[
        int, typer.Option(help="Independent hierarchy traversals per model-assisted row")
    ] = 3,
    llm_temperature: Annotated[
        float, typer.Option(help="Sampling temperature for hierarchical traversal")
    ] = 0.15,
    llm_cache: Annotated[
        Path,
        typer.Option(help="Persistent SQLite cache for model-assisted PSIC decisions"),
    ] = Path(".sigma-cache/psic_llm.sqlite"),
    llm_max_rows: Annotated[
        int | None,
        typer.Option(
            help="Maximum unresolved rows sent to the model; omit for no limit"
        ),
    ] = None,
    with_io: Annotated[
        bool,
        typer.Option(
            "--io/--no-io",
            help="Map final PSIC codes to PSA 2018 IO16/IO80/IO240 candidate sets",
        ),
    ] = True,
    progress_every: Annotated[
        int, typer.Option(help="Report classification progress every N POIs")
    ] = 500,
    verbose: Annotated[
        bool, typer.Option("--verbose/--quiet", help="Show classification progress")
    ] = True,
) -> None:
    """Classify canonical POIs to PSIC Rev. 5 and optionally map them to I-O sectors."""
    import geopandas as gpd
    import pandas as pd

    from .classification import (
        ClassificationDecisionCache,
        HierarchicalPsicTraverser,
        OpenAICompatibleBackend,
        enrich_frame_with_io,
        io_coverage_summary,
        load_builtin_psic_taxonomy,
    )

    source = input_file.resolve()
    if not source.exists():
        console.print(f"[red]error:[/red] input file does not exist: {source}")
        raise typer.Exit(1)
    target = (
        output_file.resolve()
        if output_file is not None
        else source.with_name(f"{source.stem}_psic.parquet")
    )

    if progress_every < 1:
        console.print("[red]error:[/red] --progress-every must be at least 1")
        raise typer.Exit(2)
    if llm_passes < 1:
        console.print("[red]error:[/red] --llm-passes must be at least 1")
        raise typer.Exit(2)
    if llm_temperature < 0:
        console.print("[red]error:[/red] --llm-temperature cannot be negative")
        raise typer.Exit(2)
    if llm_max_rows is not None and llm_max_rows < 1:
        console.print("[red]error:[/red] --llm-max-rows must be at least 1")
        raise typer.Exit(2)

    decision_cache = None
    try:
        # Fail before expensive work if the output destination is malformed/unwritable.
        target.parent.mkdir(parents=True, exist_ok=True)

        if verbose:
            console.print(f"Input: [bold]{source}[/bold]")
            console.print(f"Output: [bold]{target}[/bold]")
            console.print("[cyan]→[/cyan] Reading canonical POIs...")
        started = perf_counter()
        try:
            frame = gpd.read_parquet(source)
        except (ValueError, TypeError):
            frame = pd.read_parquet(source)
        if verbose:
            console.print(
                f"[green]✓[/green] Loaded {len(frame):,} POIs in "
                f"{perf_counter() - started:.1f}s"
            )
            console.print("[cyan]→[/cyan] Loading PSIC taxonomy and semantic index...")

        classifier_started = perf_counter()
        taxonomy = load_builtin_psic_taxonomy()
        traverser = None
        if llm:
            backend = OpenAICompatibleBackend.from_environment()
            decision_cache = ClassificationDecisionCache(llm_cache.resolve())
            traverser = HierarchicalPsicTraverser(
                taxonomy,
                backend,
                passes=llm_passes,
                temperature=llm_temperature,
            )

        classifier = PsicClassifier(
            taxonomy=taxonomy,
            top_n=top_n,
            min_score=min_score,
            min_margin=min_margin,
            traverser=traverser,
            decision_cache=decision_cache,
        )
        if verbose:
            mode = "deterministic + hierarchical model fallback" if llm else "deterministic"
            console.print(
                f"[green]✓[/green] Classifier ready in "
                f"{perf_counter() - classifier_started:.1f}s ({mode})"
            )
            if llm and llm_max_rows is not None:
                console.print(
                    f"[yellow]Model test limit:[/yellow] at most {llm_max_rows:,} "
                    "unresolved rows will be sent to the model"
                )
            console.print(
                f"[cyan]→[/cyan] Classifying {len(frame):,} POIs "
                f"(progress every {progress_every:,})..."
            )

        classification_started = perf_counter()

        def report_progress(done: int, total: int) -> None:
            if not verbose or done == 0:
                return
            elapsed = max(perf_counter() - classification_started, 1e-9)
            rate = done / elapsed
            remaining = max(total - done, 0)
            eta = remaining / rate if rate > 0 else 0.0
            percent = (100.0 * done / total) if total else 100.0
            console.print(
                f"  {done:,}/{total:,} ({percent:5.1f}%) | "
                f"{rate:,.1f} POIs/s | elapsed {elapsed:.0f}s | ETA {eta:.0f}s"
            )

        classified = classifier.classify_frame(
            frame,
            progress=report_progress if verbose else None,
            progress_every=progress_every,
            llm_max_rows=llm_max_rows,
        )
        if decision_cache is not None:
            decision_cache.flush()

        if verbose:
            console.print(
                f"[green]✓[/green] PSIC classification finished in "
                f"{perf_counter() - classification_started:.1f}s"
            )

        coverage = None
        if with_io:
            if verbose:
                console.print(
                    "[cyan]→[/cyan] Mapping PSIC codes through PSIC 2019 to "
                    "PSA 2018 IO16/IO80/IO240..."
                )
            io_started = perf_counter()
            classified = enrich_frame_with_io(classified, taxonomy=taxonomy)
            coverage = io_coverage_summary(classified)
            if verbose:
                console.print(
                    f"[green]✓[/green] I-O mapping finished in "
                    f"{perf_counter() - io_started:.1f}s"
                )

        if verbose:
            console.print("[cyan]→[/cyan] Writing Parquet output...")
        write_started = perf_counter()
        classified.to_parquet(target, index=False)
        if verbose:
            console.print(
                f"[green]✓[/green] Output written in "
                f"{perf_counter() - write_started:.1f}s"
            )
    except (ValueError, FileNotFoundError, RuntimeError, OSError) as exc:
        console.print(f"[red]classification error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        if decision_cache is not None:
            decision_cache.close()

    counts = classified["psic_status"].value_counts(dropna=False).to_dict()
    coded = classified["psic_code"].astype("string").fillna("").str.strip().ne("")
    model_coded = coded & classified["psic_method"].eq("llm")
    deterministic_coded = coded & ~model_coded
    console.print(
        f"[green]Complete[/green]: {len(classified):,} POIs; "
        f"{int(coded.sum()):,} received a PSIC code"
    )
    console.print(f"  deterministic codes: {int(deterministic_coded.sum()):,}")
    if llm:
        console.print(f"  model-assisted codes: {int(model_coded.sum()):,}")
    console.print(f"  without PSIC code: {int((~coded).sum()):,}")
    for status, count in sorted(counts.items(), key=lambda item: (-item[1], str(item[0]))):
        console.print(f"  {status}: {int(count):,}")

    if coverage is not None:
        for resolution in ("io16", "io80", "io240"):
            metrics = coverage["resolutions"][resolution]
            console.print(
                f"  {resolution.upper()} map-ready: {metrics['map_ready_rows']:,} / "
                f"{len(classified):,}"
            )
    console.print(f"Output: [bold]{target}[/bold]")

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
