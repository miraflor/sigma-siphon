from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
import yaml
from shapely import union_all
from shapely.geometry import shape

PSGC_EXPECTED = 1642
COMPOSITES = {
    "metro_manila": {
        "name": "Metro Manila",
        "aliases": ["NCR", "National Capital Region"],
        "members": [
            "1380100000", "1380200000", "1380300000", "1380400000",
            "1380500000", "1380600000", "1380700000", "1380800000",
            "1380900000", "1381000000", "1381100000", "1381200000",
            "1381300000", "1381400000", "1381500000", "1381600000",
            "1381701000",
        ],
    },
    "metro_cebu": {
        "name": "Metro Cebu",
        "aliases": [],
        "members": [
            "0730600000", "0731300000", "0731100000", "0702250000",
            "0702223000", "0702214000", "0702218000", "0702219000",
            "0702227000", "0702220000", "0702232000", "0702234000",
            "0702241000",
        ],
    },
    "metro_davao": {
        "name": "Metro Davao",
        "aliases": ["Metropolitan Davao"],
        "members": [
            "1130700000", "1102315000", "1102319000", "1102317000",
            "1102403000", "1102509000", "1102412000", "1102404000",
            "1102411000", "1102408000", "1102414000", "1102303000",
            "1108204000", "1108603000", "1108604000",
        ],
    },
}
REF_REPO = "faeldon/philippines-json-maps"
REF_COMMIT = "8eeead560246863c8c820c31ca6fbca81a279477"
REF_DIR = "2023/geojson/provdists/lowres"
REF_API = f"https://api.github.com/repos/{REF_REPO}/contents/{REF_DIR}?ref={REF_COMMIT}"
REF_RAW = f"https://raw.githubusercontent.com/{REF_REPO}/{REF_COMMIT}"
LEGACY_BGY_SOURCES = (
    ("lowres", "2019/geojson/barangays/lowres", "0.001"),
    ("medres", "2019/geojson/barangays/medres", "0.01"),
    ("hires", "2019/geojson/barangays/hires", "0.1"),
)


def text_norm(value: object) -> str:
    s = "" if value is None else str(value)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.casefold().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def header_norm(value: object) -> str:
    return text_norm(value).replace(" ", "")


def slugify_name(name: str) -> str:
    s = text_norm(name)
    if s.startswith("city of "):
        s = s[8:]
    if s.endswith(" city"):
        s = s[:-5]
    s = re.sub(r"\bmunicipality of\b", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "area"


def code10(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace(".0", "")
    s = re.sub(r"\D", "", s)
    return s.zfill(10) if s else ""


def find_header_row(raw: pd.DataFrame) -> int | None:
    for i in range(min(len(raw), 100)):
        vals = [header_norm(v) for v in raw.iloc[i].tolist() if pd.notna(v)]
        has_code = any(
            v in {"10digitpsgc", "psgccode", "10digitpsgccode"}
            or ("psgc" in v and ("10digit" in v or "code" in v))
            for v in vals
        )
        has_level = any(
            v in {"geographiclevel", "geolevel"}
            or ("geographic" in v and "level" in v)
            for v in vals
        )
        has_name = any(
            v in {"name", "geographicname", "geographiclocation"}
            for v in vals
        )
        if has_code and has_level and has_name:
            return i
    return None


def pick_col(columns: list[str], predicates: list[tuple[str, ...]]) -> str:
    normalized = {c: header_norm(c) for c in columns}
    for needles in predicates:
        for c, n in normalized.items():
            if all(needle in n for needle in needles):
                return c
    raise RuntimeError(f"Could not find column matching {predicates}; columns={columns}")


def correspondence_codes(value: object) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    s = str(value).strip().replace(".0", "")
    return re.findall(r"(?<!\d)\d{9}(?!\d)", s)


def load_psgc(path: Path) -> tuple[pd.DataFrame, dict[str, str], dict[str, list[str]]]:
    sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=str, engine="openpyxl")
    selected = None
    for sheet_name, raw in sheets.items():
        h = find_header_row(raw)
        if h is None:
            continue
        frame = raw.iloc[h + 1 :].copy()
        frame.columns = [
            str(v).strip() if pd.notna(v) else f"unnamed_{i}"
            for i, v in enumerate(raw.iloc[h])
        ]
        frame = frame.dropna(how="all")
        selected = (sheet_name, frame)
        break

    if selected is None:
        raise RuntimeError("Could not locate the PSGC data table in the workbook")

    sheet_name, frame = selected
    columns = list(frame.columns)
    code_col = pick_col(columns, [("10digit", "psgc"), ("psgc", "code"), ("psgc",)])
    name_col = pick_col(columns, [("name",), ("geographic", "location")])
    level_col = pick_col(columns, [("geographic", "level"), ("geolevel",)])
    correspondence_col = pick_col(columns, [("correspondence", "code")])

    work = pd.DataFrame(
        {
            "psgc_code": frame[code_col].map(code10),
            "name": frame[name_col].astype(str).str.strip(),
            "level_raw": frame[level_col].astype(str).str.strip(),
        }
    )
    work = work[(work["psgc_code"].str.len() == 10) & (work["name"] != "")]
    work["level_norm"] = work["level_raw"].map(text_norm)

    province_mask = work["level_norm"].isin({"prov", "province"})
    province_names = dict(
        zip(
            work.loc[province_mask, "psgc_code"],
            work.loc[province_mask, "name"],
            strict=True,
        )
    )

    city_levels = {
        "city",
        "huc",
        "icc",
        "cc",
        "highly urbanized city",
        "independent component city",
        "component city",
    }
    muni_levels = {"mun", "municipality"}
    lgu = work[work["level_norm"].isin(city_levels | muni_levels)].copy()
    lgu["kind"] = lgu["level_norm"].map(lambda x: "municipality" if x in muni_levels else "city")
    lgu = lgu.drop_duplicates("psgc_code").sort_values("psgc_code").reset_index(drop=True)

    if len(lgu) != PSGC_EXPECTED:
        levels = work["level_raw"].value_counts(dropna=False).to_dict()
        raise RuntimeError(
            f"Expected {PSGC_EXPECTED} cities+municipalities from the current PSGC workbook, "
            f"found {len(lgu)} on sheet {sheet_name!r}. Geographic levels: {levels}"
        )

    def province_for(code: str) -> str | None:
        candidate = code[:5] + "00000"
        return province_names.get(candidate)

    lgu["province"] = lgu["psgc_code"].map(province_for)

    # The eight Special Geographic Area (SGA) municipalities use current
    # 10-digit PSGC codes beginning 19999. geoBoundaries ADM3 predates them,
    # so retain their current barangay -> legacy PSGC correspondence codes.
    sga_barangays: dict[str, list[str]] = defaultdict(list)
    bgy_levels = {"bgy", "barangay"}
    for _, source_row in frame.iterrows():
        current_code = code10(source_row[code_col])
        level = text_norm(source_row[level_col])
        if level not in bgy_levels or not current_code.startswith("19999"):
            continue
        municipality_code = current_code[:7] + "000"
        for old_code in correspondence_codes(source_row[correspondence_col]):
            sga_barangays[municipality_code].append(old_code)

    sga_codes = set(lgu.loc[lgu["psgc_code"].str.startswith("19999"), "psgc_code"])
    missing_groups = sorted(sga_codes - set(sga_barangays))
    if missing_groups:
        raise RuntimeError(
            "Current PSGC contains SGA municipalities without legacy barangay "
            f"correspondence codes: {missing_groups}"
        )
    for municipality_code, codes in sga_barangays.items():
        sga_barangays[municipality_code] = sorted(set(codes))

    return lgu, province_names, dict(sga_barangays)


def download_reference(cache_dir: Path) -> gpd.GeoDataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    response = requests.get(REF_API, timeout=60)
    response.raise_for_status()
    items = [x for x in response.json() if x.get("type") == "file" and x["name"].endswith(".json")]
    if not items:
        raise RuntimeError("Reference boundary directory returned no GeoJSON files")

    features: list[dict] = []
    for n, item in enumerate(items, 1):
        local = cache_dir / item["name"]
        if not local.exists():
            url = f"{REF_RAW}/{item['path']}"
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            local.write_bytes(r.content)
        payload = json.loads(local.read_text(encoding="utf-8"))
        features.extend(payload.get("features", []))
        if n % 20 == 0 or n == len(items):
            print(f"  reference bundles: {n}/{len(items)}")

    rows = []
    for feature in features:
        props = feature.get("properties") or {}
        geom_json = feature.get("geometry")
        if not geom_json:
            continue
        rows.append(
            {
                "old_psgc": code10(props.get("adm3_psgc")),
                "old_name": str(props.get("adm3_en") or "").strip(),
                "geometry": shape(geom_json),
            }
        )

    ref = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    ref = ref[ref["old_psgc"] != ""].drop_duplicates("old_psgc").reset_index(drop=True)
    return ref


def make_valid_series(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = frame.copy()
    try:
        out["geometry"] = out.geometry.make_valid()
    except Exception:
        out["geometry"] = out.geometry.buffer(0)
    return out[out.geometry.notna() & ~out.geometry.is_empty].copy()


def choose_by_reference(gb: gpd.GeoDataFrame, ref_geom, current_name: str, used: set[int]):
    candidate_idx = list(gb.sindex.query(ref_geom, predicate="intersects"))
    candidate_idx = [int(i) for i in candidate_idx if int(i) not in used]
    if not candidate_idx:
        return None

    best = None
    ref_area = max(float(ref_geom.area), 1e-15)
    name_target = text_norm(current_name)
    for idx in candidate_idx:
        geom = gb.geometry.iloc[idx]
        inter = ref_geom.intersection(geom).area
        if inter <= 0:
            continue
        union = ref_geom.union(geom).area
        iou = float(inter / union) if union else 0.0
        cover = float(inter / ref_area)
        name_bonus = 1.0 if text_norm(gb.iloc[idx]["shapeName"]) == name_target else 0.0
        score = 0.70 * iou + 0.25 * min(cover, 1.0) + 0.05 * name_bonus
        if best is None or score > best[0]:
            best = (score, idx, iou, cover)
    return best


def locality_name_variants(value: str) -> set[str]:
    target = text_norm(value)
    variants = {target}
    if target.startswith("city of "):
        base = target[len("city of "):].strip()
        variants.update({base, f"{base} city"})
    if target.endswith(" city"):
        base = target[:-len(" city")].strip()
        variants.update({base, f"city of {base}"})
    if target.startswith("municipality of "):
        variants.add(target[len("municipality of "):].strip())
    return variants


def choose_by_name(gb: gpd.GeoDataFrame, current_name: str, used: set[int]):
    target_variants = locality_name_variants(current_name)
    matches = [
        int(i)
        for i, value in enumerate(gb["shapeName"])
        if i not in used
        and target_variants.intersection(locality_name_variants(str(value)))
    ]
    return matches[0] if len(matches) == 1 else None


def legacy_parent_psgc9(barangay_code: str) -> str:
    if not re.fullmatch(r"\d{9}", barangay_code):
        raise RuntimeError(
            f"Expected a 9-digit legacy PSGC correspondence code, got {barangay_code!r}"
        )
    return barangay_code[:6] + "000"


def build_sga_geometries(
    sga_barangays: dict[str, list[str]], cache_dir: Path
) -> dict[str, dict]:
    """Build current SGA municipality polygons from constituent legacy barangays.

    The 2019 low-resolution barangay dataset occasionally contains a valid
    feature record whose geometry is null (notably Tamped, legacy PSGC
    124703024).  Use low-res by default, then fill only missing geometries from
    med-res and, if still necessary, hi-res.  This keeps the final SGA geometry
    lightweight without silently dropping a barangay.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)

    needed_codes = {
        code for codes in sga_barangays.values() for code in codes
    }
    needed_parents = sorted({legacy_parent_psgc9(code) for code in needed_codes})
    by_barangay: dict[str, tuple[object, str]] = {}

    def ingest_parent(parent: str, directory: str, suffix: str) -> None:
        filename = f"barangays-municity-ph{parent}.{suffix}.json"
        local = cache_dir / filename
        if not local.exists():
            url = f"{REF_RAW}/{directory}/{filename}"
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            local.write_bytes(r.content)

        payload = json.loads(local.read_text(encoding="utf-8"))
        for feature in payload.get("features", []):
            props = feature.get("properties") or {}
            old_code = str(props.get("ADM4_PCODE") or "").removeprefix("PH")
            if old_code not in needed_codes or old_code in by_barangay:
                continue

            geom_json = feature.get("geometry")
            if not geom_json:
                continue

            by_barangay[old_code] = (
                shape(geom_json),
                str(props.get("ADM4_EN") or "").strip(),
            )

    # First pass: keep everything as lightweight as possible.
    _, low_dir, low_suffix = LEGACY_BGY_SOURCES[0]
    for pos, parent in enumerate(needed_parents, 1):
        ingest_parent(parent, low_dir, low_suffix)
        if pos % 5 == 0 or pos == len(needed_parents):
            print(f"  SGA legacy barangay bundles: {pos}/{len(needed_parents)}")

    # Some low-res records contain geometry=null.  Fill only those missing
    # records from progressively more detailed versions of the same source.
    for label, directory, suffix in LEGACY_BGY_SOURCES[1:]:
        missing = sorted(needed_codes - set(by_barangay))
        if not missing:
            break

        parents = sorted({legacy_parent_psgc9(code) for code in missing})
        print(
            f"  SGA {label} fallback: {len(missing)} missing polygon(s) "
            f"across {len(parents)} bundle(s)"
        )
        for parent in parents:
            ingest_parent(parent, directory, suffix)

    still_missing = sorted(needed_codes - set(by_barangay))
    if still_missing:
        raise RuntimeError(
            "Cannot build SGA municipalities; legacy barangay polygons remain "
            f"missing after low/medium/high-resolution fallback: {still_missing}"
        )

    out: dict[str, dict] = {}
    for municipality_code, old_codes in sorted(sga_barangays.items()):
        pieces = [by_barangay[code][0] for code in old_codes]
        geom = union_all(pieces)
        if geom.is_empty:
            raise RuntimeError(f"Empty SGA union for {municipality_code}")
        out[municipality_code] = {
            "geometry": geom,
            "source_ids": ";".join(old_codes),
            "source_names": ";".join(by_barangay[code][1] for code in old_codes),
        }

    return out

def build_matches(
    lgu: pd.DataFrame,
    gb: gpd.GeoDataFrame,
    ref: gpd.GeoDataFrame,
    sga_geometries: dict[str, dict],
):
    ref_by_code = {row.old_psgc: row.geometry for row in ref.itertuples(index=False)}
    suffix_map: dict[str, list[str]] = defaultdict(list)
    for old_code in ref_by_code:
        suffix_map[old_code[2:]].append(old_code)

    used: set[int] = set()
    output_rows = []
    audit_rows = []

    for pos, row in enumerate(lgu.itertuples(index=False), 1):
        code = row.psgc_code
        name = row.name
        ref_code = code if code in ref_by_code else None
        method = "psgc_2023"
        source = "geoBoundaries gbOpen PHL ADM3 simplified"

        if ref_code is None:
            suffix_hits = suffix_map.get(code[2:], [])
            if len(suffix_hits) == 1:
                ref_code = suffix_hits[0]
                method = "psgc_suffix_recode"

        # The current BARMM SGA municipalities were created after the ADM3
        # geoBoundaries snapshot. Build them from their official current PSGC
        # barangay memberships and legacy low-res barangay polygons.
        if code in sga_geometries:
            sga = sga_geometries[code]
            geom = sga["geometry"]
            source_ids = sga["source_ids"]
            source_names = sga["source_names"]
            score = 1.0
            method = "sga_legacy_barangay_union"
            source = "faeldon/philippines-json-maps 2019 barangay union"

        # Manila is represented as districts in current geoBoundaries; union them.
        elif code == "1380600000" and ref_code is not None:
            ref_geom = ref_by_code[ref_code]
            idxs = list(gb.sindex.query(ref_geom, predicate="intersects"))
            selected = []
            for idx in idxs:
                idx = int(idx)
                if idx in used:
                    continue
                geom = gb.geometry.iloc[idx]
                if geom.area <= 0:
                    continue
                containment = ref_geom.intersection(geom).area / geom.area
                if containment >= 0.90:
                    selected.append(idx)
            if not selected:
                raise RuntimeError("Could not assemble Manila from geoBoundaries districts")
            geom = union_all([gb.geometry.iloc[i] for i in selected])
            source_ids = ";".join(str(gb.iloc[i]["shapeID"]) for i in selected)
            source_names = ";".join(str(gb.iloc[i]["shapeName"]) for i in selected)
            used.update(selected)
            score = 1.0
            method = "manila_district_union"
        else:
            chosen = None
            score = None
            if ref_code is not None:
                best = choose_by_reference(gb, ref_by_code[ref_code], name, used)
                if best is not None:
                    score, chosen, _, _ = best
            if chosen is None:
                chosen = choose_by_name(gb, name, used)
                if chosen is not None:
                    score = 1.0
                    method = "exact_name_fallback"
            if chosen is None:
                raise RuntimeError(
                    f"Could not uniquely match current PSGC {code} {name!r}. "
                    "Stop here and inspect this locality; do not guess."
                )
            geom = gb.geometry.iloc[chosen]
            source_ids = str(gb.iloc[chosen]["shapeID"])
            source_names = str(gb.iloc[chosen]["shapeName"])
            used.add(chosen)

        if geom.is_empty:
            raise RuntimeError(f"Empty geometry for {code} {name}")

        output_rows.append(
            {
                "psgc_code": code,
                "name": name,
                "province": row.province,
                "kind": row.kind,
                "source": source,
                "source_id": source_ids,
                "geometry": geom,
            }
        )
        audit_rows.append(
            {
                "psgc_code": code,
                "name": name,
                "province": row.province,
                "reference_psgc": ref_code,
                "match_method": method,
                "match_score": score,
                "geoboundaries_name": source_names,
                "geoboundaries_id": source_ids,
            }
        )
        if pos % 100 == 0 or pos == len(lgu):
            print(f"  matched: {pos}/{len(lgu)}")

    return output_rows, audit_rows


def assign_slugs(rows: list[dict]) -> None:
    bases = [slugify_name(r["name"]) for r in rows]
    counts = Counter(bases)
    used: set[str] = set()

    for row, base in zip(rows, bases, strict=True):
        slug = base

        if counts[base] > 1:
            province = row.get("province")

            if province is None or pd.isna(province) or not str(province).strip():
                province = None
            else:
                province = str(province).strip()

            if province:
                slug = f"{base}__{slugify_name(province)}"
            elif str(row.get("kind", "")).casefold() == "city":
                slug = f"{base}_city"
            else:
                slug = f"{base}__{row['psgc_code']}"

        if slug in used:
            slug = f"{base}__{row['psgc_code']}"

        row["slug"] = slug
        used.add(slug)


def make_yaml_payload(boundaries: gpd.GeoDataFrame) -> dict:
    records = boundaries.sort_values("slug")
    areas = {}
    for row in records.itertuples(index=False):
        west, south, east, north = row.geometry.bounds
        item = {
            "name": row.name,
            "kind": row.kind,
            "psgc_code": row.psgc_code,
            "aliases": [row.psgc_code],
            "bbox": [round(west, 7), round(south, 7), round(east, 7), round(north, 7)],
            "boundary": {
                "gpkg": "boundaries/areas.gpkg",
                "layer": "areas",
                "field": "psgc_code",
                "value": row.psgc_code,
            },
        }
        if row.province and str(row.province) != "nan":
            item["province"] = row.province
        areas[row.slug] = item

    by_code = boundaries.set_index("psgc_code")
    for slug, composite in COMPOSITES.items():
        members = list(composite["members"])
        missing = [code for code in members if code not in by_code.index]
        if missing:
            raise RuntimeError(f"Composite {slug} references unknown PSGC codes: {missing}")
        geometry = union_all([by_code.loc[code].geometry for code in members])
        west, south, east, north = geometry.bounds
        areas[slug] = {
            "name": composite["name"],
            "kind": "composite",
            "aliases": list(composite.get("aliases", [])),
            "members": members,
            "bbox": [round(west, 7), round(south, 7), round(east, 7), round(north, 7)],
            "boundary": {
                "gpkg": "boundaries/areas.gpkg",
                "layer": "areas",
                "field": "psgc_code",
                "values": members,
            },
        }

    return {"areas": areas}


def write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Generated area catalog: 1,642 canonical Philippine cities/municipalities "
        "plus three composites.\n"
        "# PSGC codes identify localities; composite boundaries dissolve fixed member "
        "PSGCs at runtime.\n"
        "# Regenerate with scripts/build_areas.py; do not hand-edit generated entries.\n\n"
    )
    body = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=120)
    path.write_text(header + body, encoding="utf-8")


def write_attribution(path: Path) -> None:
    path.write_text(
        "# Boundary and PSGC attribution\n\n"
        "Most municipality/city boundary geometry: geoBoundaries gbOpen "
        "Philippines ADM3 simplified, licensed CC BY 3.0 IGO.\n\n"
        "Current PSGC names, 10-digit codes, and SGA barangay memberships: "
        "Philippine Statistics Authority, Philippine Standard Geographic Code "
        "as of 30 June 2026.\n\n"
        "A 2023 PSGC-keyed low-resolution municipal boundary snapshot from "
        "faeldon/philippines-json-maps is used as a spatial crosswalk. "
        "For the eight current BARMM Special Geographic Area municipalities "
        "that postdate the ADM3 snapshot, 2019 barangay polygons from the same "
        "MIT-licensed repository are dissolved according to the current PSA "
        "barangay memberships and correspondence codes. Low-resolution geometry "
        "is preferred, with medium/high-resolution fallback only for missing polygons.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--psgc",
        type=Path,
        required=True,
        help="Official PSA PSGC Q2 2026 Publication Datafile XLSX",
    )
    parser.add_argument(
        "--geoboundaries",
        type=Path,
        required=True,
        help="PHL ADM3 simplified GeoJSON from geoBoundaries",
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.repo_root.resolve()
    psgc_path = args.psgc.resolve()
    gb_path = args.geoboundaries.resolve()
    if not psgc_path.exists():
        raise SystemExit(f"Missing PSGC workbook: {psgc_path}")
    if not gb_path.exists():
        raise SystemExit(f"Missing geoBoundaries GeoJSON: {gb_path}")
    if gb_path.stat().st_size < 1_000_000:
        raise SystemExit(
            f"{gb_path} is too small; it may be a Git-LFS pointer instead of the "
            "actual GeoJSON"
        )

    print("1/5 Reading current PSA PSGC...")
    lgu, _, sga_barangays = load_psgc(psgc_path)
    print(f"  current LGUs: {len(lgu)}")

    print("2/5 Reading current geoBoundaries geometry...")
    gb = gpd.read_file(gb_path)
    required = {"shapeName", "shapeID", "geometry"}
    missing = required - set(gb.columns)
    if missing:
        raise RuntimeError(f"geoBoundaries file is missing columns: {sorted(missing)}")
    if gb.crs is None:
        raise RuntimeError("geoBoundaries file has no CRS")
    gb = make_valid_series(gb.to_crs("EPSG:4326").reset_index(drop=True))
    gb["_norm_name"] = gb["shapeName"].map(text_norm)
    gb = gb.reset_index(drop=True)
    print(f"  source polygons: {len(gb)}")

    print("3/5 Downloading/caching 2023 PSGC spatial crosswalk...")
    ref = download_reference(root / ".sigma-cache" / "psgc-boundary-crosswalk-2023")
    print(f"  reference LGUs: {len(ref)}")
    sga_geometries = build_sga_geometries(
        sga_barangays, root / ".sigma-cache" / "sga-barangays-2019"
    )
    print(f"  SGA municipalities assembled: {len(sga_geometries)}")

    print("4/5 Matching current PSGC to current geometry...")
    rows, audit = build_matches(lgu, gb, ref, sga_geometries)
    if len(rows) != PSGC_EXPECTED:
        raise RuntimeError(f"Expected {PSGC_EXPECTED} output boundaries; got {len(rows)}")
    assign_slugs(rows)
    boundaries = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    if boundaries["psgc_code"].duplicated().any():
        raise RuntimeError("Duplicate PSGC codes in output")
    if boundaries["slug"].duplicated().any():
        raise RuntimeError("Duplicate slugs in output")

    # Runtime assets have one source of truth: package data.
    package_data = root / "src" / "sigma_siphon" / "data"
    package_data.mkdir(parents=True, exist_ok=True)
    package_boundary_dir = package_data / "boundaries"
    package_boundary_dir.mkdir(parents=True, exist_ok=True)

    gpkg = package_boundary_dir / "areas.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    boundaries.to_file(gpkg, layer="areas", driver="GPKG")

    payload = make_yaml_payload(boundaries)
    catalog = package_data / "areas.yml"
    write_yaml(catalog, payload)

    # Build provenance remains outside the runtime package.
    provenance_dir = root / "data" / "boundaries"
    provenance_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(audit).to_csv(
        provenance_dir / "boundary_match_audit.csv",
        index=False,
        encoding="utf-8",
    )
    write_attribution(provenance_dir / "ATTRIBUTION.md")

    print("5/5 Verifying written files...")
    check = gpd.read_file(gpkg, layer="areas")
    if len(check) != PSGC_EXPECTED:
        raise RuntimeError(f"GPKG readback count is {len(check)}, expected {PSGC_EXPECTED}")
    if check["psgc_code"].nunique() != PSGC_EXPECTED:
        raise RuntimeError("GPKG readback has duplicate PSGC codes")
    if check.geometry.isna().any() or check.geometry.is_empty.any():
        raise RuntimeError("GPKG readback contains empty boundary geometry")
    if not bool(check.geometry.is_valid.all()):
        raise RuntimeError("GPKG readback contains invalid boundary geometry")
    configured_expected = PSGC_EXPECTED + len(COMPOSITES)
    if len(payload["areas"]) != configured_expected:
        raise RuntimeError(
            f"areas.yml count is {len(payload['areas'])}, expected {configured_expected}"
        )

    print("SUCCESS")
    print(f"  {gpkg}")
    print(f"  {catalog}")
    print(f"  {provenance_dir / 'boundary_match_audit.csv'}")
    print(f"  canonical localities: {PSGC_EXPECTED}")
    print(f"  composite areas: {len(COMPOSITES)}")
    print(f"  configured areas: {PSGC_EXPECTED + len(COMPOSITES)}")


if __name__ == "__main__":
    main()
