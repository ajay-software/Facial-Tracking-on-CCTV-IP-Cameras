"""
hud_renderer.py — All OpenCV drawing routines for the Spider-Man HUD.

Responsible for:
  • Corner-bracket target boxes
  • Rotating / pulsing scan arcs
  • Side data-panel readout
  • Global HUD chrome (header bar, scan lines, compass, timer)
  • Scan-sweep line animation
"""

import cv2
import math
import time
import numpy as np
from config import *


# ──────────────────────────────────────────────────────────────────────────────
#  LOW-LEVEL HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _overlay_alpha(frame: np.ndarray, overlay: np.ndarray, alpha: float) -> None:
    """Blend a same-shape BGRA or BGR overlay onto frame in-place."""
    cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)


def _draw_dashed_line(img, pt1, pt2, color, thickness=1, dash=8, gap=5):
    """Draw a dashed line between two points."""
    x1, y1 = pt1
    x2, y2 = pt2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    pos = 0.0
    drawing = True
    while pos < length:
        seg = dash if drawing else gap
        end = min(pos + seg, length)
        if drawing:
            sx, sy = int(x1 + ux * pos), int(y1 + uy * pos)
            ex, ey = int(x1 + ux * end), int(y1 + uy * end)
            cv2.line(img, (sx, sy), (ex, ey), color, thickness)
        pos = end
        drawing = not drawing


def _glow_circle(img, center, radius, color, thickness=1, blur_k=7):
    """Draw a circle with a soft glow effect."""
    glow = np.zeros_like(img)
    cv2.circle(glow, center, radius, color, thickness)
    glow = cv2.GaussianBlur(glow, (blur_k, blur_k), 0)
    cv2.addWeighted(img, 1.0, glow, 0.6, 0, img)
    cv2.circle(img, center, radius, color, max(1, thickness - 1))


def _glow_line(img, pt1, pt2, color, thickness=1, blur_k=5):
    """Draw a line with a soft glow effect."""
    glow = np.zeros_like(img)
    cv2.line(glow, pt1, pt2, color, thickness + 2)
    glow = cv2.GaussianBlur(glow, (blur_k, blur_k), 0)
    cv2.addWeighted(img, 1.0, glow, 0.5, 0, img)
    cv2.line(img, pt1, pt2, color, thickness)


def _put_text_shadow(img, text, pos, font, scale, color, thickness=1):
    """Draw text with a dark drop shadow for legibility."""
    x, y = pos
    cv2.putText(img, text, (x + 1, y + 1), font, scale, (0, 0, 0), thickness + 1, cv2.LINE_AA)
    cv2.putText(img, text, pos, font, scale, color, thickness, cv2.LINE_AA)


# ──────────────────────────────────────────────────────────────────────────────
#  CORNER BRACKETS
# ──────────────────────────────────────────────────────────────────────────────

def draw_brackets(img, x1, y1, x2, y2, color, arm_frac=BRACKET_LEN_FRAC,
                  thickness=BRACKET_THICKNESS, state="scanning"):
    """Draw the iconic corner-bracket target box."""
    w = x2 - x1
    h = y2 - y1
    arm_x = max(12, int(w * arm_frac))
    arm_y = max(12, int(h * arm_frac))

    corners = [
        # (outer corner, horizontal end, vertical end)
        ((x1, y1), (x1 + arm_x, y1), (x1, y1 + arm_y)),
        ((x2, y1), (x2 - arm_x, y1), (x2, y1 + arm_y)),
        ((x1, y2), (x1 + arm_x, y2), (x1, y2 - arm_y)),
        ((x2, y2), (x2 - arm_x, y2), (x2, y2 - arm_y)),
    ]

    for corner, h_end, v_end in corners:
        cv2.line(img, corner, h_end, color, thickness, cv2.LINE_AA)
        cv2.line(img, corner, v_end, color, thickness, cv2.LINE_AA)
        # Small pip at each corner
        cv2.circle(img, corner, 3, color, -1, cv2.LINE_AA)

    # Dashed box outline (subtler)
    dim = tuple(max(0, c) for c in [
        int(c * 0.6 + 0.4 * COLOR_DIM[i]) for i, c in enumerate(color)
    ])
    _draw_dashed_line(img, (x1, y1), (x2, y1), dim, 1, 10, 6)
    _draw_dashed_line(img, (x2, y1), (x2, y2), dim, 1, 10, 6)
    _draw_dashed_line(img, (x2, y2), (x1, y2), dim, 1, 10, 6)
    _draw_dashed_line(img, (x1, y2), (x1, y1), dim, 1, 10, 6)


# ──────────────────────────────────────────────────────────────────────────────
#  SCAN ARC / SPINNER
# ──────────────────────────────────────────────────────────────────────────────

def draw_scan_arc(img, cx, cy, radius, angle_deg, color, arc_span=120,
                  thickness=2, n_ticks=8):
    """Rotating arc that orbits the face bounding-box centre."""
    # Main arc
    start = int(angle_deg - arc_span // 2) % 360
    end   = int(angle_deg + arc_span // 2) % 360
    cv2.ellipse(img, (cx, cy), (radius, radius), 0, start, end,
                color, thickness, cv2.LINE_AA)

    # Tick marks evenly spaced around the full circle
    for i in range(n_ticks):
        tick_angle = math.radians(i * 360 / n_ticks + angle_deg)
        ix = int(cx + (radius - 5) * math.cos(tick_angle))
        iy = int(cy + (radius - 5) * math.sin(tick_angle))
        ox = int(cx + (radius + 3) * math.cos(tick_angle))
        oy = int(cy + (radius + 3) * math.sin(tick_angle))
        cv2.line(img, (ix, iy), (ox, oy), color, 1, cv2.LINE_AA)

    # Small filled dot at arc tip
    tip_x = int(cx + radius * math.cos(math.radians(angle_deg + arc_span // 2)))
    tip_y = int(cy + radius * math.sin(math.radians(angle_deg + arc_span // 2)))
    cv2.circle(img, (tip_x, tip_y), 4, color, -1, cv2.LINE_AA)


# ──────────────────────────────────────────────────────────────────────────────
#  SWEEP LINE
# ──────────────────────────────────────────────────────────────────────────────

def draw_sweep_line(img, x1, y1, x2, y2, sweep_y, color):
    """Horizontal glowing sweep line inside bounding box."""
    sy = max(y1, min(y2, sweep_y))
    _glow_line(img, (x1, sy), (x2, sy), color, thickness=1, blur_k=7)

    # Gradient fade below the sweep line
    fade_h = min(30, sy - y1)
    if fade_h > 0:
        overlay = img.copy()
        grad_color = tuple(int(c * 0.35) for c in color)
        cv2.rectangle(overlay, (x1, sy - fade_h), (x2, sy), grad_color, -1)
        cv2.addWeighted(overlay, 0.25, img, 0.75, 0, img)


# ──────────────────────────────────────────────────────────────────────────────
#  DATA PANEL
# ──────────────────────────────────────────────────────────────────────────────

def draw_data_panel(img, x, y, data: dict, state: str):
    """Side readout panel with facial scan data."""
    font = cv2.FONT_HERSHEY_DUPLEX
    small = cv2.FONT_HERSHEY_SIMPLEX
    line_h = 22
    pad = 10
    panel_w = 220

    state_color = {
        "scanning": COLOR_SCANNING,
        "locked":   COLOR_LOCKED,
        "alert":    COLOR_ACCENT,
    }.get(state, COLOR_PRIMARY)

    # Background panel
    overlay = img.copy()
    panel_h = pad * 2 + line_h * (len(data) + 2)
    px1, py1 = x, y
    px2, py2 = x + panel_w, y + panel_h
    # Clamp to frame
    h_img, w_img = img.shape[:2]
    px2 = min(px2, w_img - 2)
    py2 = min(py2, h_img - 2)
    cv2.rectangle(overlay, (px1, py1), (px2, py2), COLOR_PANEL_BG, -1)
    cv2.addWeighted(overlay, PANEL_ALPHA + 0.2, img, 1 - (PANEL_ALPHA + 0.2), 0, img)

    # Header bar
    cv2.rectangle(img, (px1, py1), (px2, py1 + line_h + 4), state_color, -1)
    _put_text_shadow(img, f"[ {state.upper()} ]", (px1 + pad, py1 + line_h - 2),
                     font, 0.45, (0, 0, 0), 1)

    # Border
    cv2.rectangle(img, (px1, py1), (px2, py2), state_color, 1, cv2.LINE_AA)

    # Data rows
    row_y = py1 + line_h + 4 + pad
    for label, value in data.items():
        _put_text_shadow(img, f"{label}:", (px1 + pad, row_y),
                         small, 0.35, COLOR_DIM, 1)
        _put_text_shadow(img, str(value), (px1 + pad + 80, row_y),
                         small, 0.38, state_color, 1)
        row_y += line_h


# ──────────────────────────────────────────────────────────────────────────────
#  FACIAL LANDMARK DOTS
# ──────────────────────────────────────────────────────────────────────────────

def draw_landmarks(img, landmarks, color):
    """Draw sparse face landmark dots."""
    for pt in landmarks:
        x, y = int(pt[0]), int(pt[1])
        cv2.circle(img, (x, y), 2, color, -1, cv2.LINE_AA)
        # Tiny cross-hair
        cv2.line(img, (x - 4, y), (x + 4, y), color, 1, cv2.LINE_AA)
        cv2.line(img, (x, y - 4), (x, y + 4), color, 1, cv2.LINE_AA)


# ──────────────────────────────────────────────────────────────────────────────
#  GLOBAL HUD CHROME
# ──────────────────────────────────────────────────────────────────────────────

def draw_global_hud(img, face_count: int, fps: float, elapsed: float):
    """Top header bar, bottom status bar, scan-line effect, compass ring."""
    h, w = img.shape[:2]
    font = cv2.FONT_HERSHEY_DUPLEX
    small = cv2.FONT_HERSHEY_SIMPLEX

    # ── Subtle CRT scan-line texture ────────────────────────────────────────
    scanline_overlay = np.zeros_like(img)
    for row in range(0, h, 4):
        scanline_overlay[row, :] = [8, 8, 8]
    cv2.addWeighted(img, 1.0, scanline_overlay, 0.18, 0, img)

    # ── Top header bar ───────────────────────────────────────────────────────
    bar_h = 36
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (w, bar_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.65, img, 0.35, 0, img)
    cv2.line(img, (0, bar_h), (w, bar_h), COLOR_PRIMARY, 1)

    _put_text_shadow(img, HUD_TITLE,
                     (12, 24), font, 0.52, COLOR_PRIMARY, 1)

    time_str = time.strftime("%H:%M:%S")
    _put_text_shadow(img, time_str, (w - 90, 24), font, 0.50, COLOR_PRIMARY, 1)

    # ── Bottom status bar ────────────────────────────────────────────────────
    bot_y = h - 28
    overlay2 = img.copy()
    cv2.rectangle(overlay2, (0, bot_y), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay2, 0.65, img, 0.35, 0, img)
    cv2.line(img, (0, bot_y), (w, bot_y), COLOR_DIM, 1)

    status_text = (
        f"FACES: {face_count:02d}   "
        f"FPS: {fps:05.1f}   "
        f"ELAPSED: {int(elapsed // 60):02d}:{int(elapsed % 60):02d}   "
        f"{HUD_SUBTITLE}"
    )
    _put_text_shadow(img, status_text, (12, h - 10), small, 0.35, COLOR_DIM, 1)

    # ── Compass / radar ring (bottom-right) ──────────────────────────────────
    cx, cy = w - 55, h - 55
    _glow_circle(img, (cx, cy), 38, COLOR_DIM, 1)
    _glow_circle(img, (cx, cy), 26, COLOR_DIM, 1)
    # Rotating needle
    needle_angle = math.radians((elapsed * 40) % 360)
    nx = int(cx + 34 * math.cos(needle_angle))
    ny = int(cy + 34 * math.sin(needle_angle))
    cv2.line(img, (cx, cy), (nx, ny), COLOR_PRIMARY, 1, cv2.LINE_AA)
    for deg in [0, 90, 180, 270]:
        rad = math.radians(deg)
        tx = int(cx + 42 * math.cos(rad))
        ty = int(cy + 42 * math.sin(rad))
        label = ["N", "E", "S", "W"][deg // 90]
        _put_text_shadow(img, label, (tx - 4, ty + 4), small, 0.28, COLOR_DIM, 1)

    # ── Corner tick marks (frame edges) ──────────────────────────────────────
    tick_len = 20
    corners_frame = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    dirs = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    for (cx_, cy_), (dx, dy) in zip(corners_frame, dirs):
        cv2.line(img, (cx_, cy_), (cx_ + dx * tick_len, cy_), COLOR_DIM, 1)
        cv2.line(img, (cx_, cy_), (cx_, cy_ + dy * tick_len), COLOR_DIM, 1)

    # ── Face count indicator (top-right area) ────────────────────────────────
    count_x = w - 180
    _put_text_shadow(img, f"TARGETS: {face_count:02d}", (count_x, 24),
                     font, 0.48,
                     COLOR_ACCENT if face_count > 0 else COLOR_DIM, 1)
