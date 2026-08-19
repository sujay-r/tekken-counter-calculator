"""Typed intermediate representation (IR) for normalized Tekken frame data."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EffectKind(str, Enum):
    """Frame-advantage suffix meanings per wavu Notation spec."""

    LAUNCHER = "LAUNCHER"       # a: opponent airborne / full combo
    DOWNED = "DOWNED"           # d: opponent grounded
    GUARD_RECOVER = "GUARD_RECOVER"  # g: opponent can guard during recovery
    CROUCH = "CROUCH"           # c: opponent recovers crouching
    STAGGER = "STAGGER"         # s: opponent floats, recovers standing
    BACK_TURNED = "BACK_TURNED" # b: opponent back-turned
    WALL_CRUSH = "WALL_CRUSH"   # w: wall crush advantage


class HitLevel(str, Enum):
    """Normalized hit levels."""

    HIGH = "HIGH"
    MID = "MID"
    LOW = "LOW"
    SMA = "SMA"      # special mid
    H = "H"          # hits grounded (high)
    M = "M"          # hits grounded (mid)
    L = "L"          # hits grounded (low)
    THROW = "THROW"
    UNKNOWN = "UNKNOWN"


class SafetyKind(str, Enum):
    """Block-safety tri-state."""

    SAFE = "SAFE"           # block >= -9
    SEMI = "SEMI"           # -10 to -14
    PUNISHABLE = "PUNISHABLE"  # <= -15


class StartupRange(BaseModel):
    """Startup frames, inclusive range."""

    model_config = ConfigDict(frozen=True)

    min: int
    max: int


class FrameAdvantage(BaseModel):
    """Parsed frame advantage with raw source preserved."""

    model_config = ConfigDict(frozen=True)

    frames: int | None = None
    effect: EffectKind | None = None
    tech_window: int | None = None
    extra_states: list["FrameAdvantage"] = Field(default_factory=list)
    raw: str


class Categories(BaseModel):
    """Derived utility / reward / risk flags."""

    model_config = ConfigDict(frozen=True)

    launcher: bool = False
    ch_launcher: bool = False
    downed: bool = False
    stagger: bool = False
    wall_crush: bool = False
    guard_recover: bool = False
    crouch: bool = False
    back_turned: bool = False
    safety: SafetyKind | None = None
    unblockable: bool = False
    high_crush: bool = False
    low_crush: bool = False
    homing: bool = False
    powercrush: bool = False
    balcony_break: bool = False
    floor_break: bool = False
    heat_burst: bool = False


class Move(BaseModel):
    """Fully normalized move record."""

    model_config = ConfigDict(frozen=True)

    # identity
    id: str
    name: str
    input: str
    parent: str | None = None

    # per-hit lists (linked across parent chain)
    target: list[HitLevel] = Field(default_factory=list)
    damage: list[int] = Field(default_factory=list)
    startup: list[StartupRange] = Field(default_factory=list)

    # advantage
    block: int | None = None
    block_unblockable: bool = False
    hit: FrameAdvantage
    ch: FrameAdvantage

    # raw preserved fields (no dropped fields)
    raw_target: str | None = None
    raw_damage: str | None = None
    raw_startup: str | None = None
    raw_block: str | None = None
    raw_recv: str | None = None
    raw_tot: str | None = None
    raw_crush: str | None = None
    raw_notes: str | None = None
    raw_alias: str | None = None
    raw_image: str | None = None
    raw_video: str | None = None
    raw_alt: str | None = None

    # merged from seed
    tags: str | None = None
    transitions: str | None = None

    # derived category flags
    categories: Categories = Field(default_factory=Categories)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain JSON-serializable dict."""
        return self.model_dump(mode="json", by_alias=True)
