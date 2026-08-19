"""Low-level wavu Cargo API client."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

CARGO_URL = "https://wavu.wiki/w/api.php"
USER_AGENT = "tekken-counter-calculator/0.1 (pytest build pipeline)"
FIELDS = (
    "id,name,input,parent,target,damage,startup,recv,tot,crush,block,hit,ch,notes,"
    "alias,image,video,alt"
)
DEFAULT_LIMIT = 500
MAX_RETRIES = 5


def _build_url(prefix: str, limit: int, offset: int) -> str:
    # Escape single quotes by doubling them, then close the LIKE pattern.
    escaped_prefix = prefix.replace("'", "''")
    where = f"id LIKE '{escaped_prefix}%'"
    params: dict[str, Any] = {
        "action": "cargoquery",
        "tables": "Move",
        "fields": FIELDS,
        "where": where,
        "limit": limit,
        "offset": offset,
        "format": "json",
    }
    return f"{CARGO_URL}?{urllib.parse.urlencode(params)}"


def fetch_character(
    prefix: str,
    *,
    limit: int = DEFAULT_LIMIT,
    max_retries: int = MAX_RETRIES,
    base_delay: float = 1.0,
) -> list[dict[str, Any]]:
    """Fetch every Move row whose ``id`` starts with ``prefix``.

    Uses Cargo's ``limit``/``offset`` pagination. Retries on 503/network errors
    with exponential backoff.
    """
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        url = _build_url(prefix, limit, offset)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.load(resp)
                break
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 503) and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Cargo returned %s for %s (attempt %d/%d); retrying in %.1fs",
                        exc.code,
                        prefix,
                        attempt + 1,
                        max_retries,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                raise
            except urllib.error.URLError as exc:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Cargo network error for %s (attempt %d/%d): %s; retrying in %.1fs",
                        prefix,
                        attempt + 1,
                        max_retries,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                raise
        else:
            raise RuntimeError(f"Failed to fetch {prefix} after {max_retries} attempts")

        batch = data.get("cargoquery", [])
        if not batch:
            break

        for item in batch:
            row = item.get("title", {})
            # Cargo returns empty strings for nulls; normalize to None for consistency.
            rows.append({k: (v if v not in ("", None) else None) for k, v in row.items()})

        if len(batch) < limit:
            break
        offset += limit

    logger.info("Fetched %d rows for prefix %r", len(rows), prefix)
    return rows
