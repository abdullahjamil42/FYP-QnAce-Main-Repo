"""
Q&Ace — Avatar Rendering Engine.

Architecture per ADR-005:
  - Primary: LivePortrait + MuseTalk  (lip-synced avatar, ~25 ms / frame).
  - Fallback: Static avatar image with energy-based mouth animation.
  - Source features pre-computed once at session start and cached.
  - Fixed interviewer persona (single face).

Per-frame rendering targets ≤ 25 ms (40+ FPS).
Output: (H, W, 3) uint8 RGB numpy array.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("qace.avatar")

AVATAR_W = 512
AVATAR_H = 512
TARGET_FPS = 30


@dataclass
class AvatarFrame:
    """A single rendered avatar frame."""

    frame_rgb: np.ndarray  # (H, W, 3) uint8
    timestamp_ms: float = 0.0
    render_ms: float = 0.0


@dataclass
class SourceFeatures:
    """Pre-computed source face features (LivePortrait)."""

    appearance: Any = None       # f_s
    canonical_kp: Any = None     # x_s
    rotation: Any = None         # R_s
    translation: Any = None      # t_s
    scale: Any = None            # scale_s
    source_image: Optional[np.ndarray] = None
    precompute_ms: float = 0.0


# ---------------------------------------------------------------------------
# Expression micro-expression drivers (future: per-context)
# ---------------------------------------------------------------------------

EXPRESSION_PRESETS: dict[str, dict[str, float]] = {
    "neutral":  {"brow_raise": 0.0, "smile": 0.0, "nod": 0.0},
    "question": {"brow_raise": 0.3, "smile": 0.0, "nod": 0.0},
    "encourage": {"brow_raise": 0.1, "smile": 0.4, "nod": 0.2},
    "thinking": {"brow_raise": 0.15, "smile": 0.0, "nod": 0.0},
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class AvatarEngine:
    """
    Avatar rendering engine.

    Pipeline:
      1. LivePortrait + MuseTalk  (full lip sync + expressions)
      2. Static avatar with energy-based mouth animation (fallback)
    """

    def __init__(
        self,
        avatar_image_path: Optional[str] = None,
        liveportrait_model: Any = None,
        musetalk_model: Any = None,
    ):
        self._liveportrait = liveportrait_model
        self._musetalk = musetalk_model
        self._source_features: Optional[SourceFeatures] = None
        self._avatar_image: Optional[np.ndarray] = None
        self._frame_count = 0
        self._engine_name: str = "unknown"

        self._load_avatar_image(avatar_image_path)
        self._detect_engine()

    # ── bootstrap ──

    def _detect_engine(self) -> None:
        if self._liveportrait is not None and self._musetalk is not None:
            self._engine_name = "liveportrait-musetalk"
            logger.info("Avatar engine: LivePortrait + MuseTalk")
        else:
            self._engine_name = "static-animated"
            logger.info("Avatar engine: static image with mouth animation")

    def _load_avatar_image(self, path: Optional[str] = None) -> None:
        if path and Path(path).exists():
            try:
                from PIL import Image

                img = Image.open(path).convert("RGB").resize((AVATAR_W, AVATAR_H))
                self._avatar_image = np.array(img, dtype=np.uint8)
                logger.info("Avatar image loaded from %s", path)
                return
            except Exception as exc:
                logger.warning("Failed to load avatar image (%s) — generating default", exc)
        self._avatar_image = _generate_default_avatar()
        logger.info("Using generated default avatar image")

    @property
    def engine_name(self) -> str:
        return self._engine_name

    # ── source features ──

    def precompute_source_features(self) -> SourceFeatures:
        """Pre-compute source face features — called once at session start."""
        t0 = time.perf_counter()

        if self._liveportrait is not None and self._avatar_image is not None:
            # TODO(phase-4): self._liveportrait.extract_source(self._avatar_image)
            pass

        features = SourceFeatures(
            source_image=self._avatar_image,
            precompute_ms=(time.perf_counter() - t0) * 1000.0,
        )
        self._source_features = features
        logger.info("Source features pre-computed in %.1fms", features.precompute_ms)
        return features

    # ── per-frame rendering ──

    def render_frame(
        self,
        audio_energy: float = 0.0,
        expression: str = "neutral",
        is_speaking: bool = False,
    ) -> AvatarFrame:
        t0 = time.perf_counter()
        self._frame_count += 1

        if self._engine_name == "liveportrait-musetalk":
            rgb = self._render_liveportrait(audio_energy, expression)
        else:
            rgb = self._render_static_animated(audio_energy, is_speaking)

        return AvatarFrame(
            frame_rgb=rgb,
            timestamp_ms=time.time() * 1000.0,
            render_ms=(time.perf_counter() - t0) * 1000.0,
        )

    def render_idle_frame(self) -> AvatarFrame:
        return self.render_frame(audio_energy=0.0, is_speaking=False)

    # ── LivePortrait + MuseTalk path ──

    def _render_liveportrait(self, audio_energy: float, expression: str) -> np.ndarray:
        # TODO(phase-4): wire model inference
        #   1. MuseTalk: audio features → latent lip params
        #   2. expression driver: micro-expression overlay
        #   3. LivePortrait: motion estimation → warping → SPADE → stitching
        return self._render_static_animated(audio_energy, audio_energy > 0.005)

    # ── Static animated fallback ──

    def _render_static_animated(
        self, audio_energy: float, is_speaking: bool
    ) -> np.ndarray:
        if self._avatar_image is None:
            return np.zeros((AVATAR_H, AVATAR_W, 3), dtype=np.uint8)

        frame = self._avatar_image.copy()

        if is_speaking:
            mouth_open = min(audio_energy * 4.0, 1.0)
            # subtle oscillation for natural feel
            osc = math.sin(self._frame_count * 0.6) * 0.15
            mouth_open = max(0.0, min(1.0, mouth_open + osc))
            _draw_mouth(frame, mouth_open)
        else:
            # gentle idle breathing animation
            breathe = 0.02 * math.sin(self._frame_count * 0.08)
            if breathe > 0.005:
                _draw_mouth(frame, breathe)

        return frame


# ---------------------------------------------------------------------------
# Default avatar generation (no external assets needed)
# ---------------------------------------------------------------------------


def _generate_default_avatar() -> np.ndarray:
    """Procedurally generate a simple interviewer avatar."""
    img = np.full((AVATAR_H, AVATAR_W, 3), 40, dtype=np.uint8)

    # background gradient
    for y in range(AVATAR_H):
        r = y / AVATAR_H
        img[y, :, 0] = int(30 + 20 * r)
        img[y, :, 1] = int(35 + 25 * r)
        img[y, :, 2] = int(50 + 40 * r)

    cy, cx = AVATAR_H // 2 - 20, AVATAR_W // 2

    # face oval
    for y in range(AVATAR_H):
        for x in range(AVATAR_W):
            dy = (y - cy) / 140.0
            dx = (x - cx) / 110.0
            if dy * dy + dx * dx < 1.0:
                img[y, x] = [210, 180, 150]

    # eyes
    for ex in (cx - 45, cx + 45):
        for y in range(cy - 25, cy - 5):
            for x in range(ex - 12, ex + 12):
                if 0 <= y < AVATAR_H and 0 <= x < AVATAR_W:
                    dy2 = ((y - (cy - 15)) / 10.0) ** 2
                    dx2 = ((x - ex) / 12.0) ** 2
                    if dy2 + dx2 < 1.0:
                        img[y, x] = [60, 42, 32]

    # nose
    for y in range(cy - 5, cy + 25):
        if 0 <= y < AVATAR_H:
            img[y, cx] = [185, 155, 125]

    # closed mouth line
    mouth_y = cy + 45
    for x in range(cx - 25, cx + 25):
        if 0 <= mouth_y < AVATAR_H and 0 <= x < AVATAR_W:
            img[mouth_y, x] = [170, 105, 95]

    return img


def _draw_mouth(frame: np.ndarray, openness: float) -> None:
    """Draw an animated mouth on the avatar (openness 0-1)."""
    cx = AVATAR_W // 2
    cy = AVATAR_H // 2 - 20 + 45
    h = int(3 + openness * 16)
    for dy in range(-h // 2, h // 2 + 1):
        y = cy + dy
        if y < 0 or y >= AVATAR_H:
            continue
        half_w = int(25 * max(0.0, 1.0 - abs(dy) / (h / 2 + 1)))
        for x in range(cx - half_w, cx + half_w):
            if 0 <= x < AVATAR_W:
                depth = 1.0 - abs(dy) / (h / 2 + 1)
                r = int(80 * (1.0 - depth) + 50 * depth)
                g = int(40 * (1.0 - depth) + 20 * depth)
                b = int(40 * (1.0 - depth) + 25 * depth)
                frame[y, x] = [r, g, b]


def create_avatar_engine(
    avatar_image_path: Optional[str] = None,
    liveportrait_model: Any = None,
    musetalk_model: Any = None,
) -> AvatarEngine:
    """Factory — creates an avatar engine with the best available backend."""
    return AvatarEngine(
        avatar_image_path=avatar_image_path,
        liveportrait_model=liveportrait_model,
        musetalk_model=musetalk_model,
    )
