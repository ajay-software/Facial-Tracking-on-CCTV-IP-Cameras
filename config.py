"""
Spider-Man: Brand New Day — Facial Scanning HUD
Configuration file. Edit these values to match your setup.
"""

# ─────────────────────────────────────────────
#  VIDEO SOURCE
# ─────────────────────────────────────────────
# Use 0 for built-in webcam, 1 for external USB cam.
# For CCTV / IP cameras, use an RTSP URL, e.g.:
#   "rtsp://username:password@192.168.1.100:554/stream"
# Or set to None and use the interactive launcher (launcher.py).
VIDEO_SOURCE = 0

# Resize captured frame to this resolution for processing (width × height).
PROCESS_WIDTH  = 1280
PROCESS_HEIGHT = 720

# Target display frame-rate.
TARGET_FPS = 30

# ─────────────────────────────────────────────
#  FACE DETECTION
# ─────────────────────────────────────────────
FACE_DETECTION_CONFIDENCE = 0.6

MIN_FACE_FRACTION = 0.04
MAX_FACE_FRACTION = 0.90

# How many frames a track must be absent before it is dropped.
TRACK_TTL_FRAMES = 10

# ─────────────────────────────────────────────
#  FACE RECOGNITION
# ─────────────────────────────────────────────
# Folder containing target person photos.
TARGETS_FOLDER = "targets"

# Matching tolerance (lower = stricter). Recommended: 0.5–0.6.
# 0.4 = very strict (fewer false positives)
# 0.6 = lenient      (more matches, may false-positive)
RECOGNITION_TOLERANCE = 0.52

# How many consecutive frames must match before showing IDENTIFIED state.
# Higher = more stable but slower to trigger.
RECOGNITION_MATCH_FRAMES = 3

# Run recognition every N frames (1 = every frame, 3 = every 3rd frame).
# Higher = faster but recognition updates less often.
RECOGNITION_INTERVAL = 2

# ─────────────────────────────────────────────
#  HUD APPEARANCE  (Brand New Day palette)
# ─────────────────────────────────────────────
# All colours are (B, G, R) tuples (OpenCV convention).
COLOR_PRIMARY      = (0, 220, 255)   # Vivid cyan-yellow — scan lines / text
COLOR_ACCENT       = (0, 80, 255)    # Hot red-orange — alert / scan arc
COLOR_LOCKED       = (0, 255, 80)    # Green — face locked / confirmed
COLOR_IDENTIFIED   = (255, 120, 0)   # Blue — known person identified
COLOR_SCANNING     = (0, 200, 255)   # Amber — actively scanning
COLOR_CORNER       = (255, 255, 255) # Bright white — corner brackets
COLOR_DIM          = (0, 100, 130)   # Muted version for background elements
COLOR_PANEL_BG     = (0, 0, 0)       # Panel fill (with alpha)

PANEL_ALPHA        = 0.45
BRACKET_LEN_FRAC   = 0.20
BRACKET_THICKNESS  = 2
SCAN_SPEED         = 8
LOCK_HOLD_FRAMES   = 45

# ─────────────────────────────────────────────
#  DATA PANEL
# ─────────────────────────────────────────────
PANEL_FIELDS = [
    "NAME",
    "STATUS",
    "MATCH %",
    "THREAT",
    "TRACK",
    "TIME",
]

HUD_TITLE    = "S.P.I.D.E.R  //  FACIAL-SCAN v2.4"
HUD_SUBTITLE = "AUTHORIZED ACCESS ONLY — CCTV FEED ACTIVE"
