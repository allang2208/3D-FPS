"""Submit/resume the herbalist's approved turnaround, then rig that exact Meshy result."""
import base64
import getpass
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

import requests

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / "SourceAssets/VillageHerbalist/FullBody"
sys.path.insert(0, str(PROJECT / "Tools/VillageBlacksmithNPC"))
import meshy_smith_head as transfer

MODEL = ROOT / "MeshyR1"
RIG = ROOT / "RigR1"
VIEWS = ("01_front.png", "02_profile.png", "03_back.png")
SETTINGS = {
    "ai_model": "meshy-7.1", "geometry_resolution": "2k",
    "should_texture": True, "texture_model": "meshy-7", "texture_resolution": "4k",
    "enable_pbr": True, "image_enhancement": False,
    "should_remesh": True, "topology": "triangle", "target_polycount": 80000,
    "target_formats": ["glb", "fbx"],
}


def save(folder, name, value):
    path = folder / name
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def submit_and_wait(api, folder, endpoint, parameters):
    receipt = folder / "task.json"
    if receipt.exists():
        job_id = json.loads(receipt.read_text())["id"]
    else:
        marker = folder / "submission_pending.json"
        with marker.open("x", encoding="utf-8") as stream:
            json.dump({"at": transfer.stamp()}, stream)
        reply = api.post(endpoint, json=parameters, timeout=(30, 180))
        if not reply.ok:
            if 400 <= reply.status_code < 500:
                marker.unlink()
            print("Submission HTTP", reply.status_code, flush=True)
            try:
                print(str(transfer.safe(reply.json().get("message","")))[:300], flush=True)
            except ValueError:
                pass
            reply.raise_for_status()
        job_id = reply.json()["result"]
        save(folder, "task.json", {"id": job_id, "submitted": transfer.stamp()})
        marker.unlink()
    print(folder.name, job_id, flush=True)
    while True:
        try:
            response = api.get(endpoint + "/" + job_id, timeout=(20, 75))
            response.raise_for_status()
        except (requests.Timeout, requests.ConnectionError):
            time.sleep(15)
            continue
        task = response.json()
        save(folder, "status.json", transfer.safe(task))
        print(folder.name, task["status"], task.get("progress"), flush=True)
        if task["status"] == "SUCCEEDED":
            return job_id, task
        if task["status"] in ("FAILED", "CANCELED", "EXPIRED"):
            raise RuntimeError(f'{folder.name}: {task["status"]} {transfer.safe(task.get("task_error"))}')
        time.sleep(15)


def download(folder, job_id, task, entries):
    transfer.ROOT = folder
    files = []
    with transfer.session() as downloads:
        for name, url in entries:
            path = transfer.fetch(downloads, url, name)
            with path.open("rb") as stream:
                checksum = hashlib.file_digest(stream, "sha256").hexdigest()
            files.append({"file":name, "bytes":path.stat().st_size, "sha256":checksum})
    save(folder, "delivery.json", {"id":job_id, "credits":task.get("consumed_credits"), "files":files})


def main():
    key = transfer.credentials() or getpass.getpass("Meshy key (hidden): ").strip()
    with transfer.session() as api:
        api.headers["Authorization"] = "Bearer " + key
        images = []
        inputs = []
        for name in VIEWS:
            data = (MODEL / "Inputs" / name).read_bytes()
            images.append("data:image/png;base64," + base64.b64encode(data).decode("ascii"))
            inputs.append({"view": name, "sha256": hashlib.sha256(data).hexdigest()})
        save(MODEL, "request.json", {"parameters": SETTINGS, "inputs": inputs})
        model_id, model = submit_and_wait(api, MODEL, transfer.API, dict(SETTINGS, image_urls=images, texture_image_urls=images))
        entries = [("model.glb", model["model_urls"]["glb"])]
        if model["model_urls"].get("fbx"):
            entries.append(("model.fbx", model["model_urls"]["fbx"]))
        for index, maps in enumerate(model.get("texture_urls", [])):
            for channel, url in maps.items():
                if url:
                    entries.append((f"Textures/M{index}_{channel}{Path(urlsplit(url).path).suffix}", url))
        download(MODEL, model_id, model, entries)
        params = {"input_task_id":model_id, "animation_type":"biped", "height_meters":1.68,
                  "skeleton_template":"ue5_mannequin", "include_fingers":True}
        save(RIG, "request.json", params)
        rig_id, rig = submit_and_wait(api, RIG, "https://api.meshy.ai/openapi/v1/rigging", params)
        download(RIG, rig_id, rig, [("rigged." + fmt, rig["result"][f"rigged_character_{fmt}_url"]) for fmt in ("glb", "fbx")])


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as error:
        print("Meshy connection error:", type(error).__name__, getattr(error.response, "status_code", None))
        sys.exit(1)
