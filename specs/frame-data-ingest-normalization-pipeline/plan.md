# Implementation Plan: Frame-data ingest & normalization pipeline

## Technical Context

- **Language:** Python 3.11+
- **Build-time only:** ingestion/normalization runs offline and commits a static JSON artifact.
- **Frontend runtime constraint:** no Python runtime in the browser; only the generated `data/moves.clean.json` ships.
- **HTTP:** use `urllib` from the standard library to keep runtime dependencies minimal.
- **Modeling:** Pydantic v2 for the normalized intermediate representation (IR) and for validation during tests.
- **Testing:** pytest, coverage via `pytest-cov`.
- **Data sources:**
  - Canonical: `https://wavu.wiki/w/api.php?action=cargoquery&tables=Move&...`
  - Cross-check/seed: `/home/sujay/viveka_scratchpad/moves.json`
- **Output:** `data/moves.clean.json` — one normalized record per Cargo move, all 6,187 rows.

## Project Structure

```text
/home/sujay/Code/tekken-counter-calculator
├── docs/SCOPE.md
├── specs/frame-data-ingest-normalization-pipeline/plan.md   (this file)
├── pyproject.toml
├── requirements-dev.txt
├── data/
│   └── moves.clean.json                                     (generated)
├── src/tekken_counter/
│   ├── __init__.py
│   ├── characters.py                                        # 41-char roster + wavu prefix mapping
│   ├── client.py                                            # Cargo API urllib client with retry/backoff
│   ├── ingest.py                                            # fetch all chars, merge seed tags, raw record builder
│   ├── schema.py                                            # Pydantic IR models
│   ├── normalize.py                                         # parsers for startup/damage/advantage/hit-level
│   ├── strings.py                                           # parent-chain linkage into per-hit lists
│   ├── categories.py                                        # flag derivation
│   └── cli.py                                               # `python -m tekken_counter` → regenerate moves.clean.json
└── tests/
    ├── conftest.py                                          # shared fixtures: cargo records, seed records
    ├── test_ingest.py                                       # 6,187-row round-trip, uniqueness, seed tag merge
    ├── test_normalize.py                                    # parser unit tests + b+1 hand-check
    ├── test_strings.py                                      # parent-chain linkage
    └── test_categories.py                                   # category flag derivation
```

## Research

- **Cargo API shape verified** with live sample `where=id LIKE 'Steve%'`. Returns the exact fields listed in `docs/SCOPE.md §5` under `cargoquery[].title`.
- **Pagination** uses `limit`/`offset`. Max single-character count in seed is 311 (Yoshimitsu); `limit=500` covers every character in one page, but the client will still paginate defensively.
- **ID prefix mapping** differs from `moves.json` keys. `moves.json` uses slug keys (`armor-king`, `devil-jin`, `jack-8`). Cargo uses space-separated title-case prefixes (`Armor King-`, `Devil Jin-`, `Jack-8-`). A deterministic transform (hyphen → space, title-case each word) covers all 41 rosters; tests will validate round-trip counts.
- **Seed `wavu_id`** equals Cargo `id`. The seed also supplies cleaner `tags`/`transitions` strings that Cargo does not expose; these are merged by `id`.
- **Pydantic** chosen because `docs/SCOPE.md §3` explicitly recommends adopting `tekken-move-schema` style models. This is a build-time dependency only; the generated JSON is plain.

## Design

### Data model (IR) — `src/tekken_counter/schema.py`

```python
class StartupRange(BaseModel):
    min: int
    max: int

class FrameAdvantage(BaseModel):
    frames: int | None          # numeric part; None for blank/"/!"/?
    effect: EffectKind | None   # a/d/g/c/s/b/w
    tech_window: int | None     # parenthesized recovery window, e.g. +18a (+11)
    raw: str                    # original value, never dropped

class Move(BaseModel):
    # identity
    id: str
    name: str
    input: str                  # full joined command, e.g. "1,1,2"
    parent: str | None

    # per-hit lists (linked across parent chain)
    target: list[HitLevel]
    damage: list[int]
    startup: list[StartupRange]

    # advantage
    block: int | None
    block_unblockable: bool     # true when raw block is blank or "!"
    hit: FrameAdvantage
    ch: FrameAdvantage | None   # Cargo may be null; if null, treat as same as hit

    # raw preserved fields (no dropped fields)
    raw_recv: str | None
    raw_tot: str | None
    raw_crush: str | None
    raw_notes: str | None
    raw_alias: str | None
    raw_image: str | None
    raw_video: str | None
    raw_alt: str | None

    # merged from seed
    tags: str | None
    transitions: str | None

    # derived category flags
    categories: Categories

class Categories(BaseModel):
    launcher: bool
    ch_launcher: bool
    downed: bool
    stagger: bool
    wall_crush: bool
    guard_recover: bool
    crouch: bool
    back_turned: bool
    safety: SafetyKind | None   # SAFE / SEMI / PUNISHABLE
    unblockable: bool
    high_crush: bool
    low_crush: bool
    homing: bool
    powercrush: bool
```

Notes:
- `hit` and `ch` keep the original raw string plus parsed parts. Multi-state strings such as `+13 +59a` are parsed into the primary `FrameAdvantage` (first token) with the remaining tokens stored in `hit.extra_states: list[FrameAdvantage]` so no data is lost.
- `block` is `None` for throws/unblockable/aerial moves; `block_unblockable` is set when the raw value is blank or exactly `"!"`.

### Ingest — `src/tekken_counter/client.py` + `ingest.py`

1. `client.fetch_character(char_slug, limit=500)` builds `where=id LIKE '<Prefix>%'` and pages via `offset` until the returned batch is empty.
2. `ingest.fetch_all()` loops over `CHARACTERS`, collects rows, asserts uniqueness on `id`.
3. Seed data (`moves.json`) is loaded and keyed by `wavu_id`; `tags` and `transitions` are attached to matching Cargo rows. A warning is logged for Cargo rows missing seed tags.
4. Returns a list of raw Cargo dicts + merged seed fields.

### Normalization — `src/tekken_counter/normalize.py`

Per `docs/SCOPE.md §5.1` and `§5.2`:

| Raw | Parsed |
|---|---|
| `i15`, `i13-14`, `i15~16` | `StartupRange(min, max)`; `-` and `~` both mean inclusive range |
| `i10, i15` | list of `StartupRange` |
| `5`, `,7`, `7,21` | list of int per hit; strip leading commas |
| `[12;12]` | `[12, 12]` |
| `50 (28)` | `[50]` (total damage; recoverable in raw) |
| `+18a (+11)` | `frames=18`, `effect=LAUNCHER`, `tech_window=11` |
| `+13 +59a` | primary `+13`, extra `[+59a]` |
| `h`, `,h`, `m,m`, `L` | uppercase tokens; `L`/`M`/`H`/`LOW` etc. |
| blank block or `!` | `block=None`, `block_unblockable=True` |
| wiki markup in notes | strip to display text; keep raw |

All parsers are permissive: any unrecognized value returns `None`/empty and preserves raw, never raising.

### String linkage — `src/tekken_counter/strings.py`

For each row, resolve the `parent` chain recursively:
- `input`: concatenate parent input + child input (child inputs start with `,`, e.g. `,2`).
- `target`, `damage`, `startup`: extend parent lists with child per-hit lists.
- If a parent is missing (should not happen for canonical data), fall back to the child's raw value and log a warning.

### Category flags — `src/tekken_counter/categories.py`

Derived from normalized fields plus seed tags:
- `launcher`/`ch_launcher`: `hit.effect == LAUNCHER` / `ch.effect == LAUNCHER`
- `downed`/`stagger`/`wall_crush`/`guard_recover`/`crouch`/`back_turned`: from `hit`/`ch` effects
- `safety`: `SAFE` (block ≥ -9), `SEMI` (-10 to -14 inclusive), `PUNISHABLE` (≤ -15)
- `unblockable`: raw block blank or `"!"`
- `high_crush`/`low_crush`/`homing`/`powercrush`: regex on merged `tags` (`cs`, `js`, `hom`, `pc`)

## Implementation Steps

Ordered by user-story priority.

### US1 — Ingest all 41 characters from Cargo and cross-check seed

1. **`src/tekken_counter/characters.py`** — define `CHARACTERS: list[str]` from `moves.json` keys and `to_cargo_prefix(slug: str) -> str`.
2. **`src/tekken_counter/client.py`** — `fetch_character(slug)` with `urllib`, `limit=500`, `offset` pagination, and exponential backoff on `503`/network errors.
3. **`src/tekken_counter/ingest.py`** — `fetch_all()` aggregates rows, asserts 6,187 total, loads seed, merges `tags`/`transitions` by `id`.
4. **`tests/test_ingest.py`** — verify count, ID uniqueness, every row has required fields, seed tag merge for Steve `b+1`.

### US2 — Normalize every move into typed IR

5. **`src/tekken_counter/schema.py`** — write Pydantic IR models.
6. **`src/tekken_counter/normalize.py`** — implement `parse_startup`, `parse_damage`, `parse_advantage`, `parse_hit_levels`, `clean_notes`.
7. **`tests/test_normalize.py`** — parameterized cases for all gotchas in `§5.2`; hand-check `b+1` → `{startup: 13, block: -14, ch: {61, launch}}`.

### US3 — Join string moves via `parent`

8. **`src/tekken_counter/strings.py`** — `link_strings(rows)` builds parent chains and full per-hit `input`/`target`/`damage`/`startup` lists.
9. **`tests/test_strings.py`** — verify `Steve-1,1,2` expands to `input="1,1,2"`, `target=[H,H,H]`, `damage=[5,7,13]`, `startup=[10,15,13-14]`.

### US4 — pytest round-trip with no dropped fields

10. **`src/tekken_counter/categories.py`** — implement flag derivation.
11. **`src/tekken_counter/cli.py`** — orchestrate ingest → normalize → link → categorize → write `data/moves.clean.json`.
12. **`tests/test_categories.py`** — verify `b+1` flagged CH-launcher, `-13` block punishable moves flagged, etc.
13. **`pyproject.toml` / `requirements-dev.txt`** — declare dev dependencies (`pydantic`, `pytest`, `pytest-cov`).
14. Run full pipeline and `pytest` to confirm all 6,187 rows round-trip and the suite is green.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Cargo API rate-limits or changes field names | Exponential backoff; fail loudly in tests; preserve raw strings so normalization does not lose data if a field is temporarily missing |
| `moves.json` slug → Cargo prefix mapping wrong for edge cases | Unit-test mapping against every seed character; if a mismatch is found, hardcode the exception in `characters.py` |
| Ambiguous raw values (e.g. `?`, `!`, missing `ch`) | Parsers return `None` and rely on raw fields; IR always stores raw values for audit |
| String `parent` chain broken or cyclic | Detect cycles, log warning, fall back to raw child value; tests assert no cycles in canonical data |
| Multi-state advantage strings (`+13 +59a`) | Store primary + extra list; no field dropped |
| Seed tags missing for a new Cargo move | Default to empty tags; tests only enforce presence, not completeness |

## Success Criteria Mapping

From the task Scope Document §7:

- **SC-1:** All 6,187 moves normalized → verified by `test_ingest.py::test_total_count`.
- **SC-2:** No field dropped → every IR model retains a `raw_*` copy of each Cargo field; `test_ingest.py::test_no_dropped_fields` checks presence.
- **SC-3:** pytest green → run `pytest` with coverage over `src/tekken_counter`.
- **SC-4:** `b+1` hand-check → `tests/test_normalize.py::test_b1_ch_launcher` asserts startup 13, block -14, ch frames 61 with launcher effect.
