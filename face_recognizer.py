"""
face_recognizer.py — Load target photos and match detected faces in real time.

How it works
────────────
1. On startup, scan the `targets/` folder for images.
2. Each image filename becomes the person's name  (e.g. "John_Doe.jpg" → "John Doe").
3. Encode all target faces with the `face_recognition` library.
4. For every face detected in each frame, compare its encoding against all targets.
5. Return match results (name + confidence %) to the HUD renderer.

Folder layout
─────────────
targets/
  John_Doe.jpg          ← name shown as  "John Doe"
  Jane_Smith.png        ← name shown as  "Jane Smith"
  suspect_001.jpg       ← name shown as  "suspect 001"

Tips
────
• Use a clear, front-facing photo. Multiple photos per person = better accuracy.
• For multiple photos of the same person, name them:
      John_Doe_1.jpg, John_Doe_2.jpg, John_Doe_3.jpg
  The recognizer averages their encodings automatically.
• Minimum recommended face size in photo: 80×80 px.
"""

import os
import re
import time
import threading
import numpy as np
from pathlib import Path
from typing  import Dict, List, Optional, Tuple

try:
    import face_recognition
    FR_AVAILABLE = True
except ImportError:
    FR_AVAILABLE = False
    print("[WARNING] 'face_recognition' not installed. "
          "Running in detection-only mode.\n"
          "  Install: pip install face-recognition")

from config import TARGETS_FOLDER, RECOGNITION_TOLERANCE, RECOGNITION_MATCH_FRAMES


# ──────────────────────────────────────────────────────────────────────────────
#  DATA STRUCTURES
# ──────────────────────────────────────────────────────────────────────────────

class TargetPerson:
    """One registered person with one or more face encodings."""
    def __init__(self, name: str):
        self.name:      str             = name
        self.encodings: List[np.ndarray] = []
        self.threat:    str             = "UNKNOWN"
        self.photo_count: int           = 0

    def add_encoding(self, enc: np.ndarray):
        self.encodings.append(enc)
        self.photo_count += 1

    def mean_encoding(self) -> Optional[np.ndarray]:
        """Return the average encoding across all photos (more robust)."""
        if not self.encodings:
            return None
        return np.mean(self.encodings, axis=0)


class MatchResult:
    """Result of matching one detected face against all targets."""
    def __init__(self, name: str, confidence: float, is_target: bool):
        self.name:       str   = name
        self.confidence: float = confidence   # 0–100 %
        self.is_target:  bool  = is_target    # True = known person, False = unknown

    def __repr__(self):
        return f"<Match {self.name!r} {self.confidence:.1f}%>"


# ──────────────────────────────────────────────────────────────────────────────
#  RECOGNIZER
# ──────────────────────────────────────────────────────────────────────────────

class FaceRecognizer:
    """
    Loads target photos from the targets/ folder and matches live faces.
    Thread-safe: encoding lookup runs on the calling thread; photo reload
    can be triggered without stopping the main loop.
    """

    SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    def __init__(self):
        self._targets:   Dict[str, TargetPerson] = {}  # base_name → TargetPerson
        self._lock       = threading.Lock()
        self._loaded     = False
        self._load_time  = 0.0

    # ── Load Photos ───────────────────────────────────────────────────────────

    def load_targets(self, folder: str = TARGETS_FOLDER) -> int:
        """
        Scan `folder` for images, encode each face, build target DB.
        Returns number of unique persons loaded.
        Prints a summary to stdout.
        """
        if not FR_AVAILABLE:
            print("[Recognizer] face_recognition not available — skipping load.")
            return 0

        folder_path = Path(folder)
        if not folder_path.exists():
            print(f"[Recognizer] targets/ folder not found: {folder_path.resolve()}")
            return 0

        print(f"\n[Recognizer] Loading target photos from: {folder_path.resolve()}")
        new_targets: Dict[str, TargetPerson] = {}

        for img_path in sorted(folder_path.iterdir()):
            if img_path.suffix.lower() not in self.SUPPORTED_EXTS:
                continue

            # Extract base person name  (strip trailing _1, _2, _3 …)
            stem      = img_path.stem
            base_name = re.sub(r"[_\s]\d+$", "", stem)   # "John_Doe_2" → "John_Doe"
            display   = base_name.replace("_", " ").replace("-", " ").title()

            # Load + encode
            try:
                img = face_recognition.load_image_file(str(img_path))
                encs = face_recognition.face_encodings(img)
                if not encs:
                    print(f"  [SKIP] No face found in: {img_path.name}")
                    continue
                enc = encs[0]
            except Exception as e:
                print(f"  [ERROR] {img_path.name}: {e}")
                continue

            if base_name not in new_targets:
                new_targets[base_name] = TargetPerson(display)
            new_targets[base_name].add_encoding(enc)
            print(f"  [OK] {img_path.name}  →  '{display}'")

        with self._lock:
            self._targets   = new_targets
            self._loaded    = True
            self._load_time = time.time()

        total = len(new_targets)
        print(f"[Recognizer] {total} person(s) loaded.\n")
        return total

    def reload_targets(self, folder: str = TARGETS_FOLDER):
        """Reload target photos in a background thread (hot-reload)."""
        t = threading.Thread(target=self.load_targets, args=(folder,), daemon=True)
        t.start()

    # ── Match One Face ────────────────────────────────────────────────────────

    def match(self, face_enc: np.ndarray) -> MatchResult:
        """
        Compare a single face encoding against all targets.
        Returns the best MatchResult.
        """
        if not FR_AVAILABLE or not self._loaded:
            return MatchResult("UNKNOWN", 0.0, False)

        with self._lock:
            if not self._targets:
                return MatchResult("NO TARGETS", 0.0, False)

            best_name  = "UNKNOWN"
            best_dist  = 1.0        # face_recognition distance (lower = better)

            for person in self._targets.values():
                mean_enc = person.mean_encoding()
                if mean_enc is None:
                    continue
                dist = float(face_recognition.face_distance([mean_enc], face_enc)[0])
                if dist < best_dist:
                    best_dist = dist
                    best_name = person.name

        # Convert distance → confidence %
        # distance 0.0 = 100%, distance >= tolerance = 0%
        tol   = RECOGNITION_TOLERANCE
        conf  = max(0.0, (1.0 - best_dist / tol)) * 100.0
        is_match = best_dist <= tol

        if not is_match:
            return MatchResult("UNKNOWN", conf, False)
        return MatchResult(best_name, conf, True)

    # ── Batch Match (for a full frame) ───────────────────────────────────────

    def match_frame(
        self,
        frame_rgb:   np.ndarray,
        face_locations: List[Tuple[int,int,int,int]],
    ) -> List[MatchResult]:
        """
        Encode all detected faces in a frame and match them.
        face_locations: list of (top, right, bottom, left) tuples
                        — the format face_recognition uses.
        Returns a list of MatchResult, one per location.
        """
        if not FR_AVAILABLE or not face_locations:
            return [MatchResult("UNKNOWN", 0.0, False)] * len(face_locations)

        # Down-sample for speed (recognition runs on 1/2-size image)
        small = frame_rgb  # already passed at processing resolution

        try:
            encodings = face_recognition.face_encodings(small, face_locations, num_jitters=1)
        except Exception:
            encodings = []

        results = []
        for enc in encodings:
            results.append(self.match(enc))

        # Pad if any encoding failed
        while len(results) < len(face_locations):
            results.append(MatchResult("UNKNOWN", 0.0, False))

        return results

    # ── Info ──────────────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return FR_AVAILABLE and self._loaded and bool(self._targets)

    @property
    def target_names(self) -> List[str]:
        with self._lock:
            return [p.name for p in self._targets.values()]

    @property
    def target_count(self) -> int:
        with self._lock:
            return len(self._targets)
