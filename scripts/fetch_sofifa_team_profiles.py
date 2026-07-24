#!/usr/bin/env python3
"""Scrape SoFIFA team ratings for the local top-100 club mapping.

Default project layout expected by this script:
- script: scripts/fetch_sofifa_team_profiles.py
- input mapping: data/sofifa_team_map.csv
- raw HTML output: data/raw/sofifa/team_profiles/
- parsed CSV output: data/sofifa_team_profiles_full.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEAM_MAP_CSV = PROJECT_ROOT / "data/sofifa_team_map.csv"
RAW_HTML_DIR = PROJECT_ROOT / "data/raw/sofifa/team_profiles"
OUTPUT_CSV = PROJECT_ROOT / "data/sofifa_team_profiles_full.csv"
LOG_CSV = PROJECT_ROOT / "data/sofifa_team_profiles_fetch_log.csv"
ERROR_TXT = PROJECT_ROOT / "data/sofifa_team_profiles_error.txt"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://sofifa.com/",
}

PROFILE_FIELDS = [
    "fetched_at",
    "roster_id",
    "rank",
    "uefa_club_name",
    "club_key",
    "sofifa_team_id",
    "sofifa_team_name",
    "sofifa_url",
    "http_status",
    "raw_html_path",
    "club_league_name",
    "club_rating_from_player_csv",
    "page_title",
    "page_team_name",
    "overall",
    "attack",
    "midfield",
    "defence",
    "domestic_prestige",
    "international_prestige",
    "transfer_budget",
    "wage_budget",
    "average_age",
    "players_count",
    "raw_summary_text",
]

LOG_FIELDS = [
    "fetched_at",
    "roster_id",
    "sofifa_team_id",
    "sofifa_team_name",
    "url",
    "status",
    "http_status",
    "raw_html_path",
    "error",
    "elapsed_seconds",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_env(path: Path) -> dict[str, str]:
    """Read a minimal .env file without adding a dependency."""
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def request_headers(auth_mode: str) -> dict[str, str]:
    """Add API_SOFIFA from .env only if the selected auth mode needs it."""
    headers = dict(HEADERS)
    api_key = load_env(PROJECT_ROOT / ".env").get("API_SOFIFA", "")

    if not api_key or auth_mode == "none":
        return headers
    if auth_mode == "bearer":
        headers["Authorization"] = f"Bearer {api_key}"
    elif auth_mode == "authorization":
        headers["Authorization"] = api_key
    elif auth_mode == "x-api-key":
        headers["X-API-Key"] = api_key
    else:
        raise ValueError(f"Unknown auth mode: {auth_mode}")

    return headers


def fetch_url(url: str, headers: dict[str, str]) -> tuple[int | None, str]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return None, str(exc.reason)


def append_csv_row(path: Path, row: dict[str, Any], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fieldnames})


def load_team_map(path: Path) -> pd.DataFrame:
    """Load teams already matched to SoFIFA IDs."""
    teams = pd.read_csv(path, dtype=str)
    teams = teams[teams["sofifa_team_id"].notna()].copy()
    teams["sofifa_team_id"] = teams["sofifa_team_id"].str.strip()
    teams = teams[teams["sofifa_team_id"].ne("")]
    teams = teams.drop_duplicates("sofifa_team_id")
    teams["rank_sort"] = pd.to_numeric(teams["rank"], errors="coerce")
    teams = teams.sort_values(["rank_sort", "sofifa_team_name"])
    return teams.drop(columns=["rank_sort"])


def read_done_profiles(path: Path, roster_id: str) -> set[str]:
    if not path.exists():
        return set()

    with path.open(newline="", encoding="utf-8") as handle:
        return {
            row["sofifa_team_id"]
            for row in csv.DictReader(handle)
            if row.get("sofifa_team_id") and row.get("roster_id") == roster_id
        }


def build_team_url(sofifa_team_id: str, roster_id: str) -> str:
    return f"https://api.sofifa.com/team/{sofifa_team_id}/{roster_id}/?hl=en-US"


def compact_text(value: str) -> str:
    return " ".join(value.split())


def label_key(value: str) -> str:
    value = value.casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def first_number(value: str) -> str:
    match = re.search(r"\b([1-9]\d?|100)\b", value)
    return match.group(1) if match else ""


def first_money(value: str) -> str:
    match = re.search(r"([€$£][\d,.]+[KMB]?)", value, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def find_value_near_label(lines: list[str], labels: list[str], value_type: str = "number") -> str:
    """Find a value on the same, previous, or next text line as a label."""
    normalized_labels = [label_key(label) for label in labels]
    extractor = first_money if value_type == "money" else first_number

    for index, line in enumerate(lines[:300]):
        if not any(label in label_key(line) for label in normalized_labels):
            continue

        candidates = [line]
        if index > 0:
            candidates.append(lines[index - 1])
        if index + 1 < len(lines):
            candidates.append(lines[index + 1])

        for candidate in candidates:
            value = extractor(candidate)
            if value:
                return value

    return ""


def parse_team_html(html: str) -> dict[str, str]:
    """Extract stable, simple fields from the raw SoFIFA team page."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    lines = [compact_text(value) for value in soup.stripped_strings if compact_text(value)]

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    heading = soup.find("h1")
    page_team_name = compact_text(heading.get_text(" ", strip=True)) if heading else ""
    if not page_team_name and title:
        page_team_name = compact_text(title.split(" - ")[0])

    return {
        "page_title": title,
        "page_team_name": page_team_name,
        "overall": find_value_near_label(lines, ["overall", "ova"]),
        "attack": find_value_near_label(lines, ["attack", "attacking", "att"]),
        "midfield": find_value_near_label(lines, ["midfield", "mid"]),
        "defence": find_value_near_label(lines, ["defence", "defense", "def"]),
        "domestic_prestige": find_value_near_label(lines, ["domestic prestige"]),
        "international_prestige": find_value_near_label(lines, ["international prestige"]),
        "transfer_budget": find_value_near_label(lines, ["transfer budget"], "money"),
        "wage_budget": find_value_near_label(lines, ["wage budget"], "money"),
        "average_age": find_value_near_label(lines, ["average age", "avg age"]),
        "players_count": find_value_near_label(lines, ["players", "squad size"]),
        "raw_summary_text": " | ".join(lines[:80])[:1000],
    }


def write_error_report(path: Path, team: pd.Series, url: str, roster_id: str, error: str, http_status: int | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "SoFIFA team profile scrape stopped",
                f"stopped_at={utc_now()}",
                f"roster_id={roster_id}",
                f"sofifa_team_id={team.get('sofifa_team_id', '')}",
                f"sofifa_team_name={team.get('sofifa_team_name', '')}",
                f"url={url}",
                f"http_status={http_status or ''}",
                f"error={error}",
            ]
        ),
        encoding="utf-8",
    )


def scrape_teams(args: argparse.Namespace) -> None:
    teams = load_team_map(args.team_map_csv)
    if args.limit:
        teams = teams.head(args.limit)

    headers = request_headers(args.auth_mode)
    done_ids = read_done_profiles(args.output_csv, args.roster_id)

    for _, team in teams.iterrows():
        sofifa_team_id = str(team["sofifa_team_id"])
        if sofifa_team_id in done_ids:
            print(f"skip existing team={sofifa_team_id} {team.get('sofifa_team_name', '')}")
            continue

        url = build_team_url(sofifa_team_id, args.roster_id)
        raw_path = args.raw_html_dir / args.roster_id / f"{sofifa_team_id}.html"
        started_at = time.perf_counter()
        status = "ok"
        http_status: int | None = 200
        error = ""

        try:
            if raw_path.exists():
                html = raw_path.read_text(encoding="utf-8")
                status = "cached"
            elif args.cache_only:
                html = ""
                status = "missing_cache"
                error = "raw HTML cache absent"
            else:
                http_status, html = fetch_url(url, headers)
                if http_status == 200:
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    raw_path.write_text(html, encoding="utf-8")
                else:
                    status = "error"
                    error = f"HTTP {http_status}"

            if html:
                parsed = parse_team_html(html)
                append_csv_row(
                    args.output_csv,
                    {
                        "fetched_at": utc_now(),
                        "roster_id": args.roster_id,
                        "rank": team.get("rank", ""),
                        "uefa_club_name": team.get("uefa_club_name", ""),
                        "club_key": team.get("club_key", ""),
                        "sofifa_team_id": sofifa_team_id,
                        "sofifa_team_name": team.get("sofifa_team_name", ""),
                        "sofifa_url": url,
                        "http_status": http_status or "",
                        "raw_html_path": display_path(raw_path),
                        "club_league_name": team.get("club_league_name", ""),
                        "club_rating_from_player_csv": team.get("club_rating_from_player_csv", ""),
                        **parsed,
                    },
                    PROFILE_FIELDS,
                )

        except Exception as exc:  # noqa: BLE001 - fetch scripts must log the exact failed team.
            status = "error"
            error = str(exc)

        elapsed_seconds = round(time.perf_counter() - started_at, 3)
        append_csv_row(
            args.log_csv,
            {
                "fetched_at": utc_now(),
                "roster_id": args.roster_id,
                "sofifa_team_id": sofifa_team_id,
                "sofifa_team_name": team.get("sofifa_team_name", ""),
                "url": url,
                "status": status,
                "http_status": http_status or "",
                "raw_html_path": display_path(raw_path),
                "error": error,
                "elapsed_seconds": elapsed_seconds,
            },
            LOG_FIELDS,
        )

        print(f"{status} team={sofifa_team_id} {team.get('sofifa_team_name', '')} http={http_status or ''}")

        if status == "error" and (args.stop_on_error or http_status in {403, 429}):
            write_error_report(args.error_txt, team, url, args.roster_id, error, http_status)
            raise RuntimeError(f"Stopped on team={sofifa_team_id}: {error}")

        if status != "cached" and not args.cache_only:
            time.sleep(args.sleep)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch SoFIFA team ratings from a local team mapping CSV.")
    parser.add_argument("--team-map-csv", default=str(TEAM_MAP_CSV.relative_to(PROJECT_ROOT)))
    parser.add_argument("--raw-html-dir", default=str(RAW_HTML_DIR.relative_to(PROJECT_ROOT)))
    parser.add_argument("--output-csv", default=str(OUTPUT_CSV.relative_to(PROJECT_ROOT)))
    parser.add_argument("--log-csv", default=str(LOG_CSV.relative_to(PROJECT_ROOT)))
    parser.add_argument("--error-txt", default=str(ERROR_TXT.relative_to(PROJECT_ROOT)))
    parser.add_argument("--roster-id", default="260008")
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--auth-mode", choices=["none", "bearer", "authorization", "x-api-key"], default="bearer")
    parser.add_argument("--cache-only", action="store_true", help="Parse existing raw HTML files without network calls.")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop on the first failed team.")
    args = parser.parse_args()

    args.team_map_csv = project_path(args.team_map_csv)
    args.raw_html_dir = project_path(args.raw_html_dir)
    args.output_csv = project_path(args.output_csv)
    args.log_csv = project_path(args.log_csv)
    args.error_txt = project_path(args.error_txt)
    return args


def main() -> None:
    args = parse_args()
    scrape_teams(args)
    print(f"output CSV: {display_path(args.output_csv)}")
    print(f"log CSV: {display_path(args.log_csv)}")


if __name__ == "__main__":
    main()
