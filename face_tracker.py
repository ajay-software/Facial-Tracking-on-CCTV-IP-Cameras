"""
face_tracker.py — MediaPipe-based face detection with simple IoU tracker.

Each detected face is assigned a stable track ID that persists across frames,
enabling per-face state machines (SCANNING → LOCKED → ALERT).
"""

import time
import math
import random
import string
import numpy as np
import mediapipe as mp
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict

from config import (
    FACE_DETECTION_CONFIDENCE,
    MIN_FACE_FRACTION,
    MAX_FACE_FRACTION,
    TRACK_TTL_FRAMES,
    SCAN_SPEED,
    LOCK_HOLD_FRAMES,
)


# ──────────────────────────────────────────────────────────────────────────────
#  DATA STRUCTURES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class FaceTrack:
    """A single tracked face with HUD state."""
    track_id:   str
    x1: int; y1: int; x2: int; y2: int      # Bounding box (pixel coords)
    landmarks:  List[Tuple[int, int]] = field(default_factory=list)

    # Scan animation state
    state:      str   = "scanning"           # "scanning" | "locked" | "alert"
    sweep_y:    int   = 0                    # Current sweep-line Y
    arc_angle:  float = 0.0                  # Current spinner angle (degrees)
    lock_timer: int   = 0                    # Frames remaining in LOCKED state

    # Readout data (populated by generate_scan_data)
    scan_data:  Dict  = field(default_factory=dict)

    # Internal
    ttl:        int   = TRACK_TTL_FRAMES     # Frames before track is dropped
    first_seen: float = field(default_factory=time.time)
    confidence: float = 1.0


def _random_id() -> str:
    """Generate a fake hex ID string."""
    return "".join(random.choices(string.hexdigits.upper(), k=8))


def _iou(a: Tuple[int,int,int,int], b: Tuple[int,int,int,int]) -> float:
    """Intersection-over-Union of two (x1,y1,x2,y2) boxes."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


# ──────────────────────────────────────────────────────────────────────────────
#  SCAN DATA GENERATOR
# ──────────────────────────────────────────────────────────────────────────────

_THREAT_LEVELS = ["LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL"]
_AGE_RANGES    = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]

def generate_scan_data(track: "FaceTrack") -> Dict:
    """Return (or refresh) the fake biometric readout for a face track."""
    if track.scan_data:            # Already generated — keep stable
        return track.scan_data
    data = {
        "ID":       track.track_id,
        "THREAT":   random.choice(_THREAT_LEVELS),
        "AGE EST.": random.choice(_AGE_RANGES),
        "CONF.":    f"{random.uniform(84, 99):.1f}%",
        "TRACK":    f"#{random.randint(100, 999)}",
        "TIME":     time.strftime("%H:%M:%S"),
    }
    track.scan_data = data
    return data


# ──────────────────────────────────────────────────────────────────────────────
#  FACE TRACKER
# ──────────────────────────────────────────────────────────────────────────────

class FaceTracker:
    """
    Wraps MediaPipe FaceDetection and maintains a set of FaceTrack objects
    with IoU-based assignment and per-track HUD state machines.
    """

    def __init__(self):
        self._mp_fd = mp.solutions.face_detection
        self._detector = self._mp_fd.FaceDetection(
            model_selection=1,                        # 1 = full-range model
            min_detection_confidence=FACE_DETECTION_CONFIDENCE,
        )
        self._tracks: Dict[str, FaceTrack] = {}

    # ── Detection ─────────────────────────────────────────────────────────────

    def _detect(self, frame_rgb: np.ndarray) -> List[Tuple[int,int,int,int,List,float]]:
        """Run MediaPipe detection; return list of (x1,y1,x2,y2,landmarks,conf)."""
        h, w = frame_rgb.shape[:2]
        result = self._detector.process(frame_rgb)
        boxes = []
        if not result.detections:
            return boxes
        for det in result.detections:
            bbox = det.location_data.relative_bounding_box
            x1 = max(0, int(bbox.xmin * w))
            y1 = max(0, int(bbox.ymin * h))
            x2 = min(w - 1, int((bbox.xmin + bbox.width)  * w))
            y2 = min(h - 1, int((bbox.ymin + bbox.height) * h))

            # Size filter
            bw = x2 - x1
            bh = y2 - y1
            if bw < w * MIN_FACE_FRACTION or bw > w * MAX_FACE_FRACTION:
                continue

            # Keypoints
            kps = []
            for kp in det.location_data.relative_keypoints:
                kps.append((int(kp.x * w), int(kp.y * h)))

            conf = det.score[0] if det.score else 1.0
            boxes.append((x1, y1, x2, y2, kps, conf))
        return boxes

    # ── IoU Assignment ────────────────────────────────────────────────────────

    def _assign(self, detections):
        """
        Match new detections to existing tracks by IoU.
        Unmatched detections → new tracks.
        Unmatched tracks → TTL countdown → removal.
        """
        matched_track_ids = set()

        for (x1, y1, x2, y2, kps, conf) in detections:
            det_box = (x1, y1, x2, y2)
            best_id, best_iou = None, 0.4          # IOU threshold

            for tid, track in self._tracks.items():
                if tid in matched_track_ids:
                    continue
                trk_box = (track.x1, track.y1, track.x2, track.y2)
                iou = _iou(det_box, trk_box)
                if iou > best_iou:
                    best_iou = iou
                    best_id  = tid

            if best_id:
                # Update existing track
                t = self._tracks[best_id]
                t.x1, t.y1, t.x2, t.y2 = x1, y1, x2, y2
                t.landmarks  = kps
                t.confidence = conf
                t.ttl        = TRACK_TTL_FRAMES
                matched_track_ids.add(best_id)
            else:
                # New track
                new_id = _random_id()
                self._tracks[new_id] = FaceTrack(
                    track_id=new_id,
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    landmarks=kps,
                    confidence=conf,
                    sweep_y=y1,
                )

        # Decrement TTL for unmatched tracks
        to_remove = []
        for tid in self._tracks:
            if tid not in matched_track_ids:
                self._tracks[tid].ttl -= 1
                if self._tracks[tid].ttl <= 0:
                    to_remove.append(tid)
        for tid in to_remove:
            del self._tracks[tid]

    # ── State Machine ─────────────────────────────────────────────────────────

    def _update_states(self):
        """Advance per-track animations and state machines."""
        for track in self._tracks.values():
            # Spin the arc
            track.arc_angle = (track.arc_angle + 3.5) % 360

            if track.state == "scanning":
                # Advance sweep line downward
                track.sweep_y += SCAN_SPEED
                if track.sweep_y >= track.y2:
                    # Scan complete → locked
                    track.state      = "locked"
                    track.lock_timer = LOCK_HOLD_FRAMES
                    generate_scan_data(track)          # Freeze readout values

            elif track.state == "locked":
                track.lock_timer -= 1
                if track.lock_timer <= 0:
                    # Return to scanning for next pass
                    track.state   = "scanning"
                    track.sweep_y = track.y1
                    track.scan_data = {}               # Reset for fresh pass

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, frame_rgb: np.ndarray) -> List[FaceTrack]:
        """
        Run detection + tracking + state updates on a single RGB frame.
        Returns the current list of live FaceTrack objects.
        """
        detections = self._detect(frame_rgb)
        self._assign(detections)
        self._update_states()
        return list(self._tracks.values())

    def release(self):
        self._detector.close()
