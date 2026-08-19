# Scope Document — Tekken Counter Calculator

> **Quest:** 43 (Gamemaster) · **Repo:** `/home/sujay/Code/tekken-counter-calculator`
> **Canonical source:** this file (`docs/SCOPE.md`)
> **Status:** v3 — Cargo-only data source
> **Last updated:** 2026-08-16

---

## 1. Problem Statement

Steve (Tekken 8) is a counter-hit specialist with very few neutral launchers. His gameplan is safe pokes and fishing for counter-hits — which means knowing, per opponent move, *which Steve tool wins and how* is the entire matchup grind. Today that means sitting in practice mode, reading the opponent's frame data, and manually reverse-engineering the counter out of Steve's moveset.

We're building a tool that answers the question directly: **given an opponent's move or string, which Steve moves beat it — and how?** Frame math done for you, ranked by tunable heuristics, usable on a phone mid-session or on a second monitor.

### 1.1 User Stories

**US1 — Block punishment (Priority: P1)**
As a Steve player, I input an opponent move so I can see every Steve punisher (startup ≤ my frame advantage), ranked, with reward/risk flags.
*Why first:* it's the core of matchup knowledge and the simplest, most deterministic frame calculation.
*Independent test:* entering a known −13 move returns `b+1` flagged as CH-launcher.

**US2 — Whiff punishment (Priority: P2)**
As a Steve player, I input an opponent move so I can see which Steve moves are fast enough to punish a whiff (startup ≤ recovery − reaction).
*Independent test:* entering a move with long recovery returns fast Steve tools (`1`, `1+2`, `f+1+2`) ranked.

**US3 — Counter-hit frame traps (Priority: P2)**
As a Steve player, I input an opponent move *and* their likely follow-up, so I can see which Steve CH tools counter-hit the follow-up (the "does my b+1 beat their mash?" question).
*Independent test:* a −1 blocked move followed by their i13 → Steve's i13 `b+1` is flagged as trading/counter-hitting per the inequality.

**US4 — Hit-level defense (Priority: P3)**
As a Steve player, I input a high-hitting opponent move so I can see which Steve punishers work from crouch (WS) after ducking, and whether the move is linear (sidesteppable).
*Independent test:* a high `f+4` returns WS punishers (`WS.1`, `WS.1,2`) and a "linear → sidestep" flag.

---

## 2. Tech Stack (locked)

| Layer | Choice |
|---|---|
| Build-time engine | Python 3 — ingest, normalize, precompute; tested with pytest |
| Frontend | Vue 3 + Vite + TypeScript, static build, PWA-ready |
| Hosting | GitHub Pages (static, no server, no Python at runtime) |
| Data source | wavu.wiki **Cargo API** — sole source of truth; re-fetched on every compile (no local seed) |

Explicitly **not** used: a backend server, PyScript/Pyodide, a database.

Reuse (see §3): the `heihachi` Cargo client + JSON exporter and `tekken-move-schema` Pydantic models are adopted as starting points rather than writing a parser from scratch.

---

## 3. Prior Art & Reuse

### 3.1 What already exists (and why we don't rebuild it)

| Project | What it is | Reuse decision |
|---|---|---|
| **wavu.wiki Cargo API** | MediaWiki `Move` table queryable as raw JSON (`action=cargoquery`). Our `wavu_id` field is the Cargo `id`. | **Canonical data source.** Pull directly; patch-regenerable. |
| **TLNBS2405/heihachi** | Python Discord bot (MIT) with a Cargo client + per-character JSON exporter. | **Adopt** its `frame_service/wavu` + `framedb` modules as our ingest layer. |
| **AbhijeetKrishnan/tekken-move-schema** | IETF JSON Schema + Pydantic models aligned to wavu's movelist layout. | **Adopt** as our schema starting point (its TODO list = our normalization problems). |
| **rherwig/tekken-parser** | ANTLR grammar for Tekken notation. | Reference only. |
| **wavu `Notation` page** | De-facto spec for frame-data representation (suffixes, ranges, damage, markers). | **Adopt wholesale** (see §5). |
| **tekkenpunisher.com** | "Opponent move → my punish" tool — Tekken 7 only, unmaintained. | **UX reference** + cautionary tale (such tools die without maintenance). |
| **wavu `<Char> punishers` "tricky moves" tables** | Hand-curated per-matchup punish tables. | We *automate* what these do; consider contributing results back to wavu. |
| **heihachi `/ms`** | Frame-value → *own* character's moves query. | Intra-character only; does not cross characters — not a duplicate of our core idea. |

### 3.2 The genuine gap (our opportunity)

No live Tekken 8 tool does cross-character "opponent move → my counter":

1. **Dynamic T8 punish recommendation** — `tekkenpunisher.com` did it for T7 and died. No T8 equivalent.
2. **Counter-hit / frame-trap calculation from frame data** — absent from every tool surveyed.
3. **Patch-regenerable, full-movelist matchup punish knowledge** — existing matchup info is hand-curated and incomplete.
4. **Whiff-punish recommendations** using recovery + range data — absent.

A **Steve-specific, frame-data-derived counter calculator (block punish + whiff punish + CH trap) is unclaimed territory.**

---

## 4. Architecture — ingest → normalize → precompute → lookup

The "compiler for Tekken frame data" model. Four stages:

1. **Ingest** — pull every `Move` row from the wavu Cargo API (via a heihachi-derived client); re-fetched on every compile (no local seed).
2. **Normalize (IR)** — every move becomes a typed object: `startup {min,max}`, `block int`, `hit/ch {frames, effect}`, `damage [int...]`, hit-level list, category flags. Strip wiki markup (`[[Steve_combos#Staples|+61a]]` → `+61a`).
3. **Precompute (codegen)** — derive static facts and build lookup tables → `steve_index.json`:
   - `punish[N]` — Steve moves with `startup ≤ N`, for N in 10..30
   - launcher / CH-launcher / knockdown / wall-crush / guard-recover lists (sorted by startup)
   - whiff-punish table keyed by recovery
4. **Lookup (browser)** — the static site does table lookups. The *only* runtime math is the counter-hit trade (a two-input inequality); everything else is precomputed.

The UI never parses anything.

---

## 5. Data Source & Schema

- **Canonical source:** wavu Cargo API — `https://wavu.wiki/w/api.php?action=cargoquery&tables=Move&fields=…&where=id LIKE 'Char%'&format=json`, paginated (`limit=500`/`offset`).
- **Cargo fields:** `id`, `name`, `input`, `parent`, `target`, `damage`, `startup`, `recv`, `tot`, `crush`, `block`, `hit`, `ch`, `notes`, `alias`, `image`, `video`, `alt`.
- **Roster & counts:** 6,437 total `Move` rows (as of 2026-08-16) = 41 playable characters + `Generic` (18) + okizeme/state groups (`BT.`, `EXD.`, `FDFA.`, `FDFT.`, `FUFA.`, `FUFT.`). Cargo `id` prefixes are title-case (e.g. `Armor King`, `Devil Jin`, `Jack`, `Hwoarang`, `Miary Zo`).
- **Derived utility flags:** `crush` column holds crush/parry/powercrush states (`cs…`, `js…`, `pc…`, `ps…`); homing and stage-break/heat flags come from `notes` bullets (`Homing`, `Balcony Break`, `Floor Break`, `Heat Burst`). No seed tags needed.
- **String linkage:** Cargo stores string hits per-move with leading-comma values (`input=",1"`, `damage=",7"`, `startup="i15"`) joined via `parent`. Normalize into full per-hit lists.

### 5.1 Frame-advantage suffixes (corrected — wavu `Notation` spec)

| Suffix | Meaning | Flag |
|---|---|---|
| `a` | opponent floats airborne, recovers grounded | **launcher** (on `hit`) / **CH-launcher** (on `ch`) |
| `d` | opponent grounded, recovers grounded (downed) | knockdown / oki |
| `g` | opponent **can guard during recovery** | guard-recover (≠ "guard break") |
| `c` | opponent recovers crouching | — |
| `s` | opponent floats, recovers standing (stagger) | stagger |
| `b` | opponent recovers back-turned | back-turned |
| `w` | frame advantage from **wall crush** | wall crush |

Additional rules: `+0` is never bare `0`; a number in parentheses is a **tech-recovery window** (`+18a (+11)`), not damage; multiple space-separated numbers = distinct recovery states (`+13 +59a`).

### 5.2 Ranges, damage, markers (gotchas to normalize)

| Raw | Meaning |
|---|---|
| `i15~16` (rendered) vs `i13-14` (Cargo) | inclusive startup range — **normalize `-` and `~` to one form** |
| `i10, i15` | multi-hit startups (comma-separated) |
| leading `,` | count from *this* move's start, not the string's start (strings only) |
| `[12;12]` | "damage dealt; recoverable damage" — a *derived* render; Cargo stores per-hit comma-separated damage instead |
| `50 (28)` | total (recoverable) — a third rendering, not Cargo format |
| `!` | **unblockable** modifier |
| uppercase hit level (`L`) | hits grounded |
| `pc` / `ps` / `js`/`cs`/`fs`/`gs`/`is` | powercrush / parry / jump/crouch/float/grounded/intangible states |
| blank `block` | can't be blocked (unblockable/aerial); for throws = advantage when broken |
| blank `ch` | CH identical to normal hit |

---

## 6. Counter Math (the engine)

1. **Block punish:** Steve move punishes iff `startup ≤ −block`.
2. **Whiff punish:** Steve move punishes iff `startup ≤ recovery − reaction_time` (reaction is a user-tunable constant, default ~15f).
3. **Counter-hit frame trap:** after blocking an opponent move (`block = B`, my advantage `A = −B`), a Steve CH tool (`startup S`) counter-hits the opponent's follow-up (`startup So`) iff `A < S < A + So`.
4. **Hit-level defense (US4):** high attacks can be ducked → WS punishers; moves without the `hom` tag are linear → sidesteppable.

---

## 7. Category Taxonomy (filters/views)

Every flag is a precomputed boolean/number per Steve move; "views" are client-side filters + a sort.

### Reward — what you get if it lands
| Category | Source | Notes |
|---|---|---|
| Damage | `damage` (per-hit, summed) | raw reward |
| Launcher | `hit` suffix `a` | full combo |
| CH-launcher | `ch` suffix `a` | Steve's identity (`b+1`) |
| Knockdown / oki | suffix `d` | ends downed → Steve pressure |
| Stagger | suffix `s` | guaranteed followup |
| Wall crush | suffix `w` | wall payoff |
| Stage break | `notes` bullets (`Balcony Break`, `Floor Break`) | balcony/wall/floor |

### Risk — what happens if blocked
| Category | Source | Notes |
|---|---|---|
| Safety on block | `block` frames | safe / semi-safe / punishable tri-state |

### Utility / defensive
| Category | Source | Notes |
|---|---|---|
| Armor / power crush | `crush` column (`pc…`) | power through a frame-late trade |
| High crush | `crush` column (`cs…`) | evades highs (beats jab-mash) |
| Low crush | `crush` column (`js…`) | evades lows |
| Homing | `notes` bullet `Homing` | beats sidestep |

---

## 8. Sort Heuristics (locked)

Three user-togglable sorts. Default is **Recommended**.

**Recommended (default)** — priority order:
1. Normal-hit launcher
2. CH-launcher
3. Knockdown (`d`) or stagger (`s`)
4. Damage, descending
5. Tie-break: fastest startup

**Max damage** — damage desc → launcher → fastest startup.

**Fastest startup** — startup asc → damage desc.

---

## 9. In-Scope
- Python ingest/normalize pipeline + tests over all 6,437 Cargo `Move` rows (no field dropped)
- Static Vue/TS frontend deployed to GitHub Pages
- Matching engine for US1–US4
- Precomputed category flags + punish/whiff/launcher lookup tables
- Search by command or move name; character selector
- Steve matchup only (Steve counters for any opponent move)

## 10. Out-of-Scope (v1)
- String-gap math (needs input timing data we don't have)
- Range/spacing/step simulation
- A backend, accounts, saved user data
- Non-Steve matchups
- Full combo damage extrapolation (beyond the launch flag)
- Live in-game overlay integration (TekkenOverlay-style memory reads)

## 11. Assumptions
- The wavu Cargo API is authoritative and stable for Tekken 8 frame data.
- Frame data is static (no patch-awareness in v1 beyond re-running ingest).
- Queries are single move/string in → ranked list out (no full sequence simulation).
- "Launcher" = `a` suffix, confirmed against known moves (e.g. `b+1` → `ch: +61a`).

## 12. Constraints
- Static hosting (GitHub Pages): no server, no Python at runtime, no database.
- Touch/mobile-first: used in practice mode, on a phone or second screen.
- Data ingestion must be reproducible (pipeline committed, tests runnable, regenerate on patch).

## 13. Open Questions
1. **Wiki-markup stripping** — `ch`/`notes` embed wiki markup (`[[Steve_combos#Staples|+61a]]`). Strip to bare values, or preserve link targets for deep-linking to combo pages?
2. **`crush` field semantics** — ✅ RESOLVED: the `crush` column holds `cs…`/`js…`/`pc…`/`ps…`; `Homing` is a `notes` bullet. No seed-derived tag extraction needed.
3. **Reaction-time default** — the whiff-punish constant (~15f) needs confirmation/tunability design.
4. **CH-trade precompute vs runtime** — full-pair precompute rejected (O(n²)); runtime one-line inequality is the plan. Confirm acceptable.
5. **Contributing back to wavu** — whether our derived matchup punish data should be surfaced as a wavu contributor aid (deferred; record intent only).

## 14. Success Criteria
1. Query "opponent char + move" returns correct, ranked Steve counters for US1–US4.
2. Ingest/normalize round-trips all 6,437 Cargo `Move` rows with no dropped fields (pytest over full dataset).
3. Frame math verified against hand-checked cases (`−13 → b+1`, `−10 → 1`, `−12 → 2`).
4. Site builds, deploys to GitHub Pages, and is usable on mobile.
5. `docs/SCOPE.md` stays the living spec (updated as decisions land).
