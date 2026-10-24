"""
launcher.py — Interactive setup wizard.

Run this instead of main.py when you don't know your RTSP URL.
It will:
  1. Ask for camera brand, IP, credentials, channel
  2. Build the RTSP URL
  3. Test the connection
  4. Launch the HUD

Usage:
    python launcher.py
"""

import os
import sys
import cv2
import time

from rtsp_builder import BRAND_TEMPLATES, build_rtsp_url, print_all_urls


# ──────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _ask(prompt: str, default: str = "") -> str:
    result = input(f"  {prompt}" + (f" [{default}]" if default else "") + " : ").strip()
    return result if result else default


def _test_rtsp(url: str, timeout: int = 6) -> bool:
    """Try to open a VideoCapture and grab one frame within timeout seconds."""
    print(f"\n  Testing connection to:\n  {url}")
    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout * 1000)
    deadline = time.time() + timeout
    ok = False
    while time.time() < deadline:
        ret, _ = cap.read()
        if ret:
            ok = True
            break
    cap.release()
    return ok


# ──────────────────────────────────────────────────────────────────────────────
#  WIZARD
# ──────────────────────────────────────────────────────────────────────────────

BANNER = r"""
 ╔══════════════════════════════════════════════════════╗
 ║   S.P.I.D.E.R  HUD  —  Camera Setup Wizard          ║
 ║   Spider-Man: Brand New Day  //  Facial Scan v2.4    ║
 ╚══════════════════════════════════════════════════════╝
"""

def main():
    print(BANNER)

    # ── Source type ──────────────────────────────────────────────────────────
    print("  Source type:")
    print("    1. Webcam (built-in or USB)")
    print("    2. CCTV / IP Camera (RTSP)")
    print("    3. Video file (mp4, avi ...)")
    print("    4. I already have an RTSP URL")
    choice = _ask("Choose", "1")

    source = None

    if choice == "1":
        idx = int(_ask("Camera index (0=built-in, 1=first external)", "0"))
        source = idx

    elif choice == "2":
        print("\n  Supported brands:")
        brand_keys = list(BRAND_TEMPLATES.keys())
        for i, k in enumerate(brand_keys, 1):
            print(f"    {i}. {BRAND_TEMPLATES[k]['label']}")
        b_choice = int(_ask("Choose brand number", "1")) - 1
        brand    = brand_keys[b_choice]

        ip      = _ask("Camera IP address", "192.168.1.100")
        user    = _ask("Username",          "admin")
        pwd     = _ask("Password",          "")
        channel = int(_ask("Channel number", "1"))
        port    = _ask("Port (leave blank for default)", "")
        port    = int(port) if port else None
        stream  = _ask("Stream quality [main / sub]", "main")

        url = build_rtsp_url(brand, ip, user, pwd, channel, port, stream)
        print(f"\n  Generated URL:\n  {url}")

        # Test connection
        if _ask("\n  Test connection? [y/n]", "y").lower() == "y":
            ok = _test_rtsp(url)
            if ok:
                print("  ✓ Connection successful!\n")
            else:
                print("  ✗ Could not connect. Showing all possible URLs to try:\n")
                print_all_urls(ip, user, pwd, channel)
                manual = _ask("  Paste a different URL to try (or press Enter to exit)", "")
                if manual:
                    url = manual
                else:
                    sys.exit(0)
        source = url

    elif choice == "3":
        path = _ask("Path to video file")
        if not os.path.exists(path):
            print(f"  File not found: {path}")
            sys.exit(1)
        source = path

    elif choice == "4":
        source = _ask("Paste your RTSP URL")

    else:
        print("  Invalid choice.")
        sys.exit(1)

    # ── Target photos ────────────────────────────────────────────────────────
    print("\n" + "─" * 56)
    print("  FACE RECOGNITION TARGETS")
    print("─" * 56)
    targets_dir = os.path.abspath("targets")
    photos = [f for f in os.listdir(targets_dir)
              if os.path.splitext(f)[1].lower() in
              {".jpg", ".jpeg", ".png", ".bmp", ".webp"}]

    if photos:
        print(f"  Found {len(photos)} photo(s) in targets/:")
        for p in photos:
            print(f"    • {p}")
    else:
        print("  No photos found in targets/ folder.")
        print("  Add photos named after the person (e.g. John_Doe.jpg)")
        print("  then re-run. Running in detection-only mode.\n")

    # ── Confirm & launch ─────────────────────────────────────────────────────
    print("\n" + "─" * 56)
    print(f"  Source : {source}")
    print(f"  Targets: {len(photos)} photo(s)")
    print("─" * 56)
    go = _ask("Launch HUD? [y/n]", "y")
    if go.lower() != "y":
        print("  Aborted.")
        sys.exit(0)

    # Patch config at runtime
    import config
    config.VIDEO_SOURCE = source

    # Start HUD
    print("\n  Launching HUD...\n")
    from main import main as hud_main
    hud_main()


if __name__ == "__main__":
    main()
