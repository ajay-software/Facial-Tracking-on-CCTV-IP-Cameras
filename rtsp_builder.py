"""
rtsp_builder.py — Auto-generate RTSP URLs for major CCTV brands.

Usage:
    from rtsp_builder import build_rtsp_url, SUPPORTED_BRANDS
    url = build_rtsp_url("hikvision", "192.168.1.100", "admin", "pass123", channel=1)
"""

from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
#  BRAND TEMPLATES
# ──────────────────────────────────────────────────────────────────────────────

BRAND_TEMPLATES = {
    "hikvision": {
        "label":    "Hikvision",
        "port":     554,
        "main":     "rtsp://{user}:{pwd}@{ip}:{port}/Streaming/Channels/{channel:03d}01",
        "sub":      "rtsp://{user}:{pwd}@{ip}:{port}/Streaming/Channels/{channel:03d}02",
        "notes":    "Main stream = 01, Sub stream = 02. Default port 554.",
    },
    "dahua": {
        "label":    "Dahua",
        "port":     554,
        "main":     "rtsp://{user}:{pwd}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=0",
        "sub":      "rtsp://{user}:{pwd}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=1",
        "notes":    "subtype=0 main, subtype=1 sub.",
    },
    "cpplus": {
        "label":    "CP Plus",
        "port":     554,
        "main":     "rtsp://{user}:{pwd}@{ip}:{port}/stream{channel}",
        "sub":      "rtsp://{user}:{pwd}@{ip}:{port}/stream{channel}_sub",
        "notes":    "Some CP Plus models use /h264/ch{channel}/main/av_stream",
    },
    "cpplus_alt": {
        "label":    "CP Plus (Alt)",
        "port":     554,
        "main":     "rtsp://{user}:{pwd}@{ip}:{port}/h264/ch{channel}/main/av_stream",
        "sub":      "rtsp://{user}:{pwd}@{ip}:{port}/h264/ch{channel}/sub/av_stream",
        "notes":    "Try this if the default CP Plus URL fails.",
    },
    "axis": {
        "label":    "Axis",
        "port":     554,
        "main":     "rtsp://{user}:{pwd}@{ip}:{port}/axis-media/media.amp?camera={channel}",
        "sub":      "rtsp://{user}:{pwd}@{ip}:{port}/axis-media/media.amp?camera={channel}&resolution=640x360",
        "notes":    "Axis cameras may also respond on port 80.",
    },
    "onvif": {
        "label":    "Generic ONVIF",
        "port":     554,
        "main":     "rtsp://{user}:{pwd}@{ip}:{port}/onvif1",
        "sub":      "rtsp://{user}:{pwd}@{ip}:{port}/onvif2",
        "notes":    "Try /onvif1, /onvif2, /live, /stream1 if this fails.",
    },
    "reolink": {
        "label":    "Reolink",
        "port":     554,
        "main":     "rtsp://{user}:{pwd}@{ip}:{port}//h264Preview_{channel:02d}_main",
        "sub":      "rtsp://{user}:{pwd}@{ip}:{port}//h264Preview_{channel:02d}_sub",
        "notes":    "Double slash before h264 is intentional.",
    },
    "amcrest": {
        "label":    "Amcrest / Lorex",
        "port":     554,
        "main":     "rtsp://{user}:{pwd}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=0",
        "sub":      "rtsp://{user}:{pwd}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=1",
        "notes":    "Same format as Dahua (OEM).",
    },
}

SUPPORTED_BRANDS = list(BRAND_TEMPLATES.keys())


def build_rtsp_url(
    brand:   str,
    ip:      str,
    user:    str,
    pwd:     str,
    channel: int  = 1,
    port:    Optional[int] = None,
    stream:  str  = "main",   # "main" or "sub"
) -> str:
    """
    Build an RTSP URL for a given brand and camera credentials.

    Args:
        brand:   Brand key from SUPPORTED_BRANDS (case-insensitive).
        ip:      Camera IP address (e.g. "192.168.1.100").
        user:    Camera username.
        pwd:     Camera password.
        channel: Channel number (default 1).
        port:    Override default port if needed.
        stream:  "main" (high quality) or "sub" (lower quality, faster).

    Returns:
        RTSP URL string.

    Raises:
        ValueError: If brand is not recognised.
    """
    brand = brand.lower().replace(" ", "").replace("-", "")
    if brand not in BRAND_TEMPLATES:
        raise ValueError(
            f"Unknown brand '{brand}'. "
            f"Supported: {', '.join(SUPPORTED_BRANDS)}"
        )

    tmpl = BRAND_TEMPLATES[brand]
    p    = port if port is not None else tmpl["port"]
    key  = "main" if stream == "main" else "sub"

    url = tmpl[key].format(
        user=user, pwd=pwd, ip=ip, port=p, channel=channel
    )
    return url


def print_all_urls(ip: str, user: str, pwd: str, channel: int = 1) -> None:
    """Print all possible RTSP URLs for a camera (useful for troubleshooting)."""
    print(f"\n{'─'*60}")
    print(f"  RTSP URLs for {ip} (user={user})")
    print(f"{'─'*60}")
    for brand_key, tmpl in BRAND_TEMPLATES.items():
        p = tmpl["port"]
        for stream in ("main", "sub"):
            try:
                url = build_rtsp_url(brand_key, ip, user, pwd, channel, stream=stream)
                label = f"{tmpl['label']} [{stream}]"
                print(f"  {label:<28} {url}")
            except Exception:
                pass
    print(f"{'─'*60}\n")
