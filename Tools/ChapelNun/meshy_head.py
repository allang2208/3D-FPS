"""Generate and archive the approved Chapel Nun head using four Meshy views.
The credential is read from process environment or stdin; it is never saved.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit
import requests

ROOT = Path(__file__).resolve().parents[2] / "SourceAssets" / "ChapelNun20261115" / "MeshyHeadR1"
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

def write_json(name, data):
    path = ROOT / name
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

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

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("MESHY_API_KEY") or sys.stdin.readline().strip()
    if not key:
        raise RuntimeError("MESHY_API_KEY is required via environment or stdin")
    os.environ["MESHY_API_KEY"] = key
    api = requests.Session()
    api.trust_env = False
    api.proxies.update(PROXY)
    api.headers.update({"Authorization": "Bearer " + key})
    task_file = ROOT / "task.json"
    if task_file.exists():
        task_id = json.loads(task_file.read_text(encoding="utf-8"))["id"]
        print("Resuming task " + task_id, flush=True)
    else:
        if (ROOT / "submission_pending.json").exists():
            raise RuntimeError("Submission outcome is uncertain. Resolve the existing submission before retrying.")
        images, records = [], []
        for name in INPUTS:
            blob = (ROOT / "Inputs" / name).read_bytes()
            images.append("data:image/png;base64," + base64.b64encode(blob).decode("ascii"))
            records.append({"path": "Inputs/" + name, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()})
        write_json("request.json", {"endpoint": API, "parameters": PARAMS, "images": records,
                                   "texture_views_same_as_geometry": True, "created_at": stamp()})
        write_json("submission_pending.json", {"submitted_at": stamp(), "endpoint": API})
        print("Submitting four-view textured head", flush=True)
        response = api.post(API, json={**PARAMS, "image_urls": images, "texture_image_urls": images},
                            timeout=(30, 240))
        if response.status_code not in (200, 201, 202):
            write_json("submission_error.json", {"http_status": response.status_code, "body": safe(response.text[:3000])})
            if 400 <= response.status_code < 500:
                (ROOT / "submission_pending.json").unlink()
            raise RuntimeError("Meshy submission returned HTTP " + str(response.status_code))
        task_id = response.json()["result"]
        write_json("task.json", {"id": task_id, "endpoint": API, "submitted_at": stamp()})
        (ROOT / "submission_pending.json").unlink()
        print("Task created " + task_id, flush=True)
    last = None
    errors = 0
    while True:
        try:
            response = api.get(API + "/" + task_id, timeout=(30, 90))
            response.raise_for_status()
            task = response.json()
            errors = 0
        except requests.RequestException as exc:
            errors += 1
            print("Status request delayed: " + type(exc).__name__, flush=True)
            if errors >= 12:
                raise RuntimeError("Status requests repeatedly failed; task ID is saved for resuming")
            time.sleep(15)
            continue
        write_json("status.json", {**safe(task), "observed_at": stamp()})
        current = (task.get("status"), task.get("progress"))
        if current != last:
            print("Status %s; progress %s" % current, flush=True)
            last = current
        if task.get("status") == "SUCCEEDED":
            break
        if task.get("status") in ("FAILED", "CANCELED"):
            raise RuntimeError("Meshy task " + task["status"] + ": " + json.dumps(safe(task.get("task_error"))))
        time.sleep(15)

    # A separate, unauthenticated session must fetch CDN assets.
    downloads = requests.Session()
    downloads.trust_env = False
    downloads.proxies.update(PROXY)
    entries = []
    source = ROOT / "Source"
    source.mkdir(exist_ok=True)

    def fetch(label, url):
        if not url:
            return
        suffix = Path(urlsplit(url).path).suffix or ".bin"
        path = source / (re.sub(r"[^a-zA-Z0-9_-]", "_", label) + suffix)
        partial = path.with_suffix(path.suffix + ".part")
        print("Downloading " + path.name, flush=True)
        for attempt in range(3):
            try:
                with downloads.get(url, stream=True, timeout=(30, 180)) as reply:
                    reply.raise_for_status()
                    with partial.open("wb") as handle:
                        for chunk in reply.iter_content(1024 * 1024):
                            handle.write(chunk)
                partial.replace(path)
                break
            except requests.RequestException:
                if attempt == 2:
                    raise RuntimeError("Download failed for " + label + "; resume with saved task ID")
                time.sleep(5)
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        entries.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
                        "sha256": digest.hexdigest(), "source": safe(url)})
        write_json("downloads.json", {"id": task_id, "files": entries})

    for fmt, url in task.get("model_urls", {}).items():
        fetch("NunHead_R1_" + fmt, url)
    for index, maps in enumerate(task.get("texture_urls", [])):
        for kind, url in maps.items():
            fetch("NunHead_R1_M%02d_%s" % (index, kind), url)
    fetch("NunHead_R1_preview", task.get("thumbnail_url"))
    write_json("delivery.json", {
        "id": task_id, "status": "source_downloaded", "completed_at": stamp(),
        "consumed_credits": task.get("consumed_credits"), "files": entries,
        "multi_view_inputs": 4, "geometry_resolution": "2k", "texture_resolution": "4k",
        "production_state": {
            "head_source_generated": True, "retopology": False, "facial_rig": False,
            "neck_fitted_to_kaitlin": False, "separate_groom": False, "ue_assets_imported": False
        }
    })
    print("Source download complete; consumed credits " + str(task.get("consumed_credits")), flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        message = safe(str(exc))
        write_json("run_error.json", {"type": type(exc).__name__, "message": message, "time": stamp()})
        print(type(exc).__name__ + ": " + message, flush=True)
        sys.exit(1)
