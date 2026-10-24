from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


VALID_CATEGORIES = {
    "Emergency assistance",
    "Counselling",
    "Legal guidance",
    "Shelter & housing",
    "Medical help",
}
REQUIRED_COLUMNS = {"name", "category", "contact", "verified_on", "source"}
STALE_AFTER_DAYS = 365


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if not value.lower().startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def url_looks_valid(value: str) -> bool:
    parsed = urlparse(normalize_url(value))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and "." in parsed.netloc


def parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def check_link(url: str, timeout: float = 5.0) -> tuple[str, str]:
    """Return a status and note; access blocks are reported as unable to verify."""
    normalized = normalize_url(url)
    request = Request(normalized, method="HEAD", headers={"User-Agent": "HelpBridge resource checker"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return ("ok", f"HTTP {response.status}") if 200 <= response.status < 400 else ("review", f"HTTP {response.status}")
    except HTTPError as error:
        if error.code in {404, 410}:
            return "broken", f"HTTP {error.code}"
        if error.code in {401, 403, 405, 501}:
            fallback = Request(
                normalized,
                headers={"User-Agent": "HelpBridge resource checker", "Range": "bytes=0-0"},
            )
            try:
                with urlopen(fallback, timeout=timeout) as response:
                    return ("ok", f"HTTP {response.status}") if 200 <= response.status < 400 else ("review", f"HTTP {response.status}")
            except HTTPError as fallback_error:
                if fallback_error.code in {404, 410}:
                    return "broken", f"HTTP {fallback_error.code}"
                return "review", f"site did not allow automatic verification (HTTP {fallback_error.code})"
            except (URLError, TimeoutError, OSError):
                return "review", "site did not allow automatic verification"
        return "review", f"server returned HTTP {error.code}; check manually"
    except (URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        return "review", f"could not connect ({reason})"


def validate_rows(rows: list[dict[str, str]], columns: list[str], check_links: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    missing_columns = sorted(REQUIRED_COLUMNS - set(columns))
    if missing_columns:
        errors.append("CSV is missing required column(s): " + ", ".join(missing_columns))
        return errors, warnings

    seen_records: dict[tuple[str, str, str, str], int] = {}
    urls: dict[str, set[int]] = {}
    today = date.today()

    for row_number, row in enumerate(rows, start=2):
        name = row.get("name", "").strip()
        category = row.get("category", "").strip()
        contact = row.get("contact", "").strip()
        source = row.get("source", "").strip()
        website = row.get("website", "").strip()
        verified_on = row.get("verified_on", "").strip()
        location = row.get("location", "").strip()

        if not name:
            errors.append(f"Row {row_number}: name is missing.")
        if category not in VALID_CATEGORIES:
            errors.append(f"Row {row_number}: category must be one of: " + ", ".join(sorted(VALID_CATEGORIES)) + ".")
        if not contact:
            warnings.append(f"Row {row_number} ({name or 'unnamed'}): contact is missing.")
        if not source:
            warnings.append(f"Row {row_number} ({name or 'unnamed'}): source link is missing.")
        elif not url_looks_valid(source):
            errors.append(f"Row {row_number} ({name or 'unnamed'}): source is not a valid web address: {source}")
        if website and not url_looks_valid(website):
            errors.append(f"Row {row_number} ({name or 'unnamed'}): website is not a valid web address: {website}")

        checked = parse_date(verified_on)
        if not verified_on:
            warnings.append(f"Row {row_number} ({name or 'unnamed'}): verified_on date is missing.")
        elif checked is None:
            errors.append(f"Row {row_number} ({name or 'unnamed'}): verified_on must use YYYY-MM-DD format.")
        elif checked > today:
            errors.append(f"Row {row_number} ({name or 'unnamed'}): verified_on is in the future.")
        elif (today - checked).days > STALE_AFTER_DAYS:
            warnings.append(f"Row {row_number} ({name or 'unnamed'}): last checked {verified_on}; recheck this resource.")

        key = (
            re.sub(r"\s+", " ", name).casefold(),
            category.casefold(),
            re.sub(r"\s+", "", contact).casefold(),
            normalize_url(website).rstrip("/").casefold(),
        )
        if any(key) and key in seen_records:
            warnings.append(f"Row {row_number} ({name or 'unnamed'}): may duplicate row {seen_records[key]}.")
        elif any(key):
            seen_records[key] = row_number

        if check_links:
            for field, value in (("website", website), ("source", source)):
                if value and url_looks_valid(value):
                    urls.setdefault(normalize_url(value), set()).add(row_number)

    if check_links:
        for url, row_numbers in urls.items():
            status, note = check_link(url)
            locations = ", ".join(str(number) for number in sorted(row_numbers))
            if status == "broken":
                errors.append(f"Rows {locations}: link appears broken ({note}): {url}")
            elif status == "review":
                warnings.append(f"Rows {locations}: link could not be confirmed automatically ({note}): {url}")

    return errors, warnings


def main() -> int:
    default_csv = Path(__file__).resolve().parent / "data" / "resources.csv"
    parser = argparse.ArgumentParser(description="Check HelpBridge resource CSV quality.")
    parser.add_argument("csv_file", nargs="?", default=str(default_csv), help="CSV path (defaults to data/resources.csv)")
    parser.add_argument("--check-links", action="store_true", help="Check website and source links online; may take a few seconds per link")
    args = parser.parse_args()

    path = Path(args.csv_file)
    if not path.is_file():
        print(f"ERROR: CSV file not found: {path}")
        return 2

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            columns = [column.strip() for column in (reader.fieldnames or [])]
            rows = [
                {str(key).strip(): (value or "").strip() for key, value in row.items() if key is not None}
                for row in reader
            ]
    except (OSError, UnicodeError, csv.Error) as error:
        print(f"ERROR: Could not read CSV: {error}")
        return 2

    errors, warnings = validate_rows(rows, columns, args.check_links)
    print(f"Checked {len(rows)} resource row(s) in {path.name}.")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if not errors and not warnings:
        print("All resource rows passed the checks.")
    elif not errors:
        print(f"Finished with {len(warnings)} warning(s). Review them before sharing updated resource data.")
    else:
        print(f"Finished with {len(errors)} error(s) and {len(warnings)} warning(s). Fix errors before sharing updated resource data.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
