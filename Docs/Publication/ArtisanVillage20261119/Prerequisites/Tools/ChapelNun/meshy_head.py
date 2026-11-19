"""Shared four-view Meshy settings and response sanitization used by the village smith."""

import os
import time
from urllib.parse import urlsplit

API = "https://api.meshy.ai/openapi/v1/multi-image-to-3d"

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

INPUTS = ["01_front.png", "02_three_quarter.png", "03_profile.png", "04_back.png"]

PARAMS = {
    "ai_model": "meshy-7.1",
    "geometry_resolution": "2k",
    "should_texture": True,
    "texture_model": "meshy-7",
    "texture_resolution": "4k",
    "enable_pbr": True,
    "should_remesh": False,
    "image_enhancement": False,
    "target_formats": ["glb", "fbx", "obj"],
}

def safe(data):
    if isinstance(data, dict):
        return {k: safe(v) for k, v in data.items()}
    if isinstance(data, list):
        return [safe(v) for v in data]
    if isinstance(data, str):
        if data.startswith("data:"):
            return "[input data URI omitted]"
        if data.startswith(("https://", "http://")):
            u = urlsplit(data)
            return u._replace(query="", fragment="").geturl()
        return data.replace(os.environ.get("MESHY_API_KEY", "[no key]"), "[credential removed]")
    return data

def stamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
