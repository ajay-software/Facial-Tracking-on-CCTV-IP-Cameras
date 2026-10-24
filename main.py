"""
main.py — Spider-Man: Brand New Day Facial Scanning HUD
Entry point.  Run:
    python launcher.py          ← interactive wizard (recommended)
    python main.py              ← uses config.VIDEO_SOURCE directly
    python main.py --source 0   ← webcam
    python main.py --source "rtsp://user:pass@192.168.1.100:554/..."

Press  Q  to quit,  S  to screenshot,  P  to pause,  R  to reload targets.
"""

import cv2
import sys
import time
import argparse
import numpy as np

import config
from face_tracker    import FaceTracker, generate_scan_data
from face_recognizer import FaceRecognizer, MatchResult
from hud_renderer    import (
    draw_brackets,
    draw_scan_arc,
    draw_sweep_line,
    draw_data_panel,
    draw_landmarks,
    draw_global_hud,
)


# ──────────────────────────────────────────────────────────────────────────────
#  ARGUMENT PARSING
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Spider-Man HUD Facial Scanner")
    parser.add_argument("--source", "-s", default=None,
                        help="Video source: int for webcam index, file path, or RTSP URL.")
    parser.add_argument("--width",  "-W", type=int, default=None)
    parser.add_argument("--height", "-H", type=int, default=None)
    parser.add_argument("--fps",    "-f", type=float, default=None)
    parser.add_argument("--no-recognition", action="store_true",
                        help="Disable face recognition (detection only).")
    return parser.parse_args()


# ──────────────────────────────────────────────────────────────────────────────
#  COLOUR BY STATE
# ──────────────────────────────────────────────────────────────────────────────

def _state_colors(state: str):
    return {
        "scanning":    (config.COLOR_SCANNING,    config.COLOR_SCANNING,    config.COLOR_CORNER),
        "locked":      (config.COLOR_LOCKED,       config.COLOR_LOCKED,       config.COLOR_CORNER),
        "identified":  (config.COLOR_IDENTIFIED,   config.COLOR_IDENTIFIED,   config.COLOR_IDENTIFIED),
        "alert":       (config.COLOR_ACCENT,        config.COLOR_ACCENT,       config.COLOR_ACCENT),
    }.get(state, (config.COLOR_SCANNING, config.COLOR_SCANNING, config.COLOR_CORNER))


# ──────────────────────────────────────────────────────────────────────────────
#  PER-FACE RENDERING
# ──────────────────────────────────────────────────────────────────────────────

def render_face(frame: np.ndarray, track, match: MatchResult):
    x1, y1, x2, y2 = track.x1, track.y1, track.x2, track.y2
    h, w = frame.shape[:2]

    # Override state to "identified" if we have a match
    display_state = track.state
    if match.is_target and track.state in ("locked", "scanning"):
        display_state = "identified"

    arc_color, sweep_color, bracket_color = _state_colors(display_state)
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    radius = max((x2 - x1), (y2 - y1)) // 2 + 20

    # 1. Spinning arc
    draw_scan_arc(frame, cx, cy, radius, track.arc_angle, arc_color)

    # 2. Bracket box
    draw_brackets(frame, x1, y1, x2, y2, bracket_color, state=display_state)

    # 3. Sweep line (only while scanning)
    if track.state == "scanning":
        draw_sweep_line(frame, x1, y1, x2, y2, track.sweep_y, sweep_color)

    # 4. Facial landmark dots
    if track.landmarks:
        draw_landmarks(frame, track.landmarks, arc_color)

    # 5. Label above box
    label = match.name if match.is_target else f"ID:{track.track_id[:6]}"
    font = cv2.FONT_HERSHEY_DUPLEX
    (tw, th), _ = cv2.getTextSize(label, font, 0.45, 1)
    lx = max(0, cx - tw // 2)
    ly = max(th + 4, y1 - 6)
    cv2.putText(frame, label, (lx + 1, ly + 1), font, 0.45, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(frame, label, (lx,     ly),     font, 0.45, arc_color,  1, cv2.LINE_AA)

    # 6. Data panel
    panel_x = x2 + 10
    panel_y = y1
    if panel_x + 230 > w:
        panel_x = max(0, x1 - 235)

    # Build panel data
    scan_data = generate_scan_data(track)
    panel_data = {
        "NAME":    match.name if match.is_target else "UNIDENTIFIED",
        "STATUS":  display_state.upper(),
        "MATCH %": f"{match.confidence:.1f}%" if match.is_target else "---",
        "THREAT":  scan_data.get("THREAT", "---"),
        "TRACK":   scan_data.get("TRACK", "---"),
        "TIME":    time.strftime("%H:%M:%S"),
    }
    draw_data_panel(frame, panel_x, panel_y, panel_data, display_state)

    # 7. IDENTIFIED banner
    if display_state == "identified":
        banner = f">>> IDENTIFIED: {match.name.upper()} <<<"
        (bw, bh), _ = cv2.getTextSize(banner, font, 0.5, 1)
        bx = max(0, cx - bw // 2)
        by = y2 + 22
        if by + bh < h:
            cv2.putText(frame, banner, (bx+1, by+1), font, 0.5, (0,0,0), 2, cv2.LINE_AA)
            cv2.putText(frame, banner, (bx,   by),   font, 0.5, config.COLOR_IDENTIFIED, 1, cv2.LINE_AA)

    # 8. LOCKED banner (when no match)
    elif track.state == "locked":
        lock_text = ">>> LOCKED <<<"
        (lw2, lh2), _ = cv2.getTextSize(lock_text, font, 0.5, 1)
        lx2 = max(0, cx - lw2 // 2)
        ly2 = y2 + 22
        if ly2 + lh2 < h:
            cv2.putText(frame, lock_text, (lx2+1, ly2+1), font, 0.5, (0,0,0), 2, cv2.LINE_AA)
            cv2.putText(frame, lock_text, (lx2, ly2),     font, 0.5, config.COLOR_LOCKED, 1, cv2.LINE_AA)


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN LOOP
# ──────────────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    source = args.source if args.source is not None else config.VIDEO_SOURCE
    try:
        source = int(source)
    except (ValueError, TypeError):
        pass

    if args.width:  config.PROCESS_WIDTH  = args.width
    if args.height: config.PROCESS_HEIGHT = args.height
    if args.fps:    config.TARGET_FPS     = args.fps

    # ── Open video ───────────────────────────────────────────────────────────
    print(f"[HUD] Opening source: {source!r}")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video source: {source!r}")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.PROCESS_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.PROCESS_HEIGHT)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[HUD] Frame size: {actual_w}×{actual_h}")

    # ── Init tracker + recognizer ─────────────────────────────────────────────
    tracker    = FaceTracker()
    recognizer = FaceRecognizer()

    use_recognition = not args.no_recognition
    if use_recognition:
        recognizer.load_targets(config.TARGETS_FOLDER)
        if recognizer.is_ready:
            print(f"[HUD] Recognition active — targets: {recognizer.target_names}")
        else:
            print("[HUD] Recognition DISABLED (no targets loaded or library missing).")
            print(f"      Drop photos into:  {config.TARGETS_FOLDER}/")

    # Per-track match cache  {track_id: MatchResult}
    match_cache: dict = {}
    frame_count = 0

    # ── Window ───────────────────────────────────────────────────────────────
    win_name = "S.P.I.D.E.R HUD — Q quit | S screenshot | P pause | R reload targets"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, actual_w, actual_h)

    fps_counter = 0
    fps_display = 0.0
    fps_timer   = time.time()
    start_time  = time.time()
    paused      = False
    frame_delay = max(1, int(1000 / config.TARGET_FPS))
    screenshot_count = 0
    frame = np.zeros((actual_h, actual_w, 3), dtype=np.uint8)

    print("[HUD] Running — press Q in the window to quit.")

    while True:
        # ── Key handling ─────────────────────────────────────────────────────
        key = cv2.waitKey(frame_delay) & 0xFF
        if key in (ord('q'), 27):
            break
        if key == ord('p'):
            paused = not paused
            print(f"[HUD] {'Paused' if paused else 'Resumed'}")
        if key == ord('s'):
            fname = f"screenshot_{screenshot_count:03d}.png"
            cv2.imwrite(fname, frame)
            screenshot_count += 1
            print(f"[HUD] Screenshot saved: {fname}")
        if key == ord('r'):
            print("[HUD] Reloading target photos...")
            recognizer.reload_targets(config.TARGETS_FOLDER)
            match_cache.clear()

        if paused:
            cv2.imshow(win_name, frame)
            continue

        # ── Capture ──────────────────────────────────────────────────────────
        ret, frame = cap.read()
        if not ret:
            print("[HUD] End of stream or capture error.")
            break

        frame_count += 1
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # ── Detection + tracking ─────────────────────────────────────────────
        tracks = tracker.update(frame_rgb)

        # ── Recognition (every N frames) ──────────────────────────────────────
        if use_recognition and recognizer.is_ready and (frame_count % config.RECOGNITION_INTERVAL == 0):
            for track in tracks:
                # Convert bounding box to face_recognition format (top,right,bottom,left)
                fr_loc = [(track.y1, track.x2, track.y2, track.x1)]
                results = recognizer.match_frame(frame_rgb, fr_loc)
                if results:
                    match_cache[track.track_id] = results[0]

        # ── Render faces ─────────────────────────────────────────────────────
        no_match = __import__("face_recognizer").MatchResult("UNKNOWN", 0.0, False)
        for track in tracks:
            match = match_cache.get(track.track_id, no_match)
            render_face(frame, track, match)

        # Remove stale entries from cache
        live_ids = {t.track_id for t in tracks}
        match_cache = {k: v for k, v in match_cache.items() if k in live_ids}

        # ── Global HUD chrome ─────────────────────────────────────────────────
        elapsed = time.time() - start_time
        draw_global_hud(frame, len(tracks), fps_display, elapsed)

        # ── FPS counter ───────────────────────────────────────────────────────
        fps_counter += 1
        if time.time() - fps_timer >= 1.0:
            fps_display = fps_counter / (time.time() - fps_timer)
            fps_counter = 0
            fps_timer   = time.time()

        # ── Display ───────────────────────────────────────────────────────────
        cv2.imshow(win_name, frame)

    # ── Cleanup ───────────────────────────────────────────────────────────────
    print("[HUD] Shutting down.")
    cap.release()
    tracker.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
