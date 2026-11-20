"""Generate the tavern keeper from her three full-length views or resume her existing Meshy job."""
import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parent
PROJECT = next(p for p in ROOT.parents if (p / "FPSGAME.uproject").is_file())
sys.path.insert(0, str(PROJECT / "Tools" / "VillageBlacksmithNPC"))
from meshy_smith_head import API, fetch, safe, session, stamp

FILES = ("01_front.png", "02_profile.png", "03_back.png")
PARAMETERS = {
    "ai_model": "meshy-7.1", "geometry_resolution": "2k",
    "should_texture": True, "texture_model": "meshy-7", "texture_resolution": "4k",
    "enable_pbr": True, "image_enhancement": False,
    "should_remesh": True, "topology": "triangle", "target_polycount": 80000,
    "target_formats": ["glb", "fbx"],
}


def record(name, value):
    path = ROOT / name
    pending = path.with_suffix(".tmp")
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.replace(path)


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def run():
    key = os.getenv("MESHY_API_KEY") or getpass.getpass("Meshy session key (hidden): ").strip()
    if not key:
        raise ValueError("No credential supplied")
    os.environ["MESHY_API_KEY"] = key
    api = session()
    api.headers["Authorization"] = "Bearer " + key
    task_file = ROOT / "task.json"
    if task_file.exists():
        task_id = json.loads(task_file.read_text(encoding="utf-8"))["id"]
    else:
        marker = ROOT / "submission_pending.json"
        if marker.exists():
            raise RuntimeError("Previous submission has no receipt; resolve it before retrying.")
        balance = api.get("https://api.meshy.ai/openapi/v1/balance", timeout=(15, 35))
        balance.raise_for_status()
        images = []
        inputs = []
        for filename in FILES:
            path = ROOT / "Inputs" / filename
            images.append("data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii"))
            inputs.append({"file": filename, "sha256": digest(path)})
        record("request.json", {"parameters": PARAMETERS, "inputs": inputs, "balance_before": balance.json().get("balance")})
        record("submission_pending.json", {"at": stamp()})
        response = api.post(API, json={**PARAMETERS, "image_urls": images, "texture_image_urls": images}, timeout=(30, 180))
        if not response.ok:
            if 400 <= response.status_code < 500:
                marker.unlink()
            detail = response.json().get("message", "") if response.headers.get("content-type", "").startswith("application/json") else ""
            raise RuntimeError(f"Submission HTTP {response.status_code}: {safe(detail)[:250]}")
        task_id = response.json()["result"]
        record("task.json", {"id": task_id, "submitted": stamp()})
        marker.unlink()
    print("Task", task_id, flush=True)
    while True:
        reply = api.get(API + "/" + task_id, timeout=(30, 90))
        reply.raise_for_status()
        task = reply.json()
        record("status.json", safe(task))
        print(task["status"], task.get("progress"), flush=True)
        if task["status"] == "SUCCEEDED":
            break
        if task["status"] in ("FAILED", "CANCELED"):
            raise RuntimeError("Generation ended: " + task["status"])
        time.sleep(15)

    assets = [(f"TavernKeeper_FullBody.{fmt}", link) for fmt, link in task["model_urls"].items()
              if fmt in PARAMETERS["target_formats"] and link]
    if not any(name.endswith(".glb") for name, _ in assets):
        raise RuntimeError("Meshy returned no GLB download")
    for index, maps in enumerate(task.get("texture_urls", [])):
        for kind, link in maps.items():
            if link:
                assets.append((f"Textures/M{index}_{kind}{Path(urlsplit(link).path).suffix}", link))
    if task.get("thumbnail_url"):
        link = task["thumbnail_url"]
        assets.append(("MeshyPreview" + Path(urlsplit(link).path).suffix, link))
    import meshy_smith_head
    meshy_smith_head.ROOT = ROOT
    with session() as cdn:
        files = []
        for name, url in assets:
            path = fetch(cdn, url, name)
            files.append({"path": name, "bytes": path.stat().st_size, "sha256": digest(path)})
    record("delivery.json", {"id": task_id, "completed": stamp(), "consumed_credits": task.get("consumed_credits"), "files": files})
    print("Downloaded", len(files), "files. Credits:", task.get("consumed_credits"), flush=True)


if __name__ == "__main__":
    try:
        run()
    except requests.RequestException as exc:
        print("Connection error:", type(exc).__name__, getattr(exc.response, "status_code", None), flush=True)
        sys.exit(1)
