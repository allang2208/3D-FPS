"""Submit once, resume, and retrieve the Meshy rig for the approved tavern keeper."""
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import requests

ROOT = Path(__file__).resolve().parent
PROJECT = next(p for p in ROOT.parents if (p / "FPSGAME.uproject").is_file())
sys.path.insert(0, str(PROJECT / "Tools" / "VillageBlacksmithNPC"))
import meshy_smith_head as transfer

API = "https://api.meshy.ai/openapi/v1/rigging"


def record(name, value):
    path = ROOT / name
    pending = path.with_suffix(".tmp")
    pending.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    pending.replace(path)


def rig():
    key = transfer.credentials() or getpass.getpass("Meshy session key (hidden): ").strip()
    if not key:
        raise RuntimeError("Missing Meshy credential")
    os.environ["MESHY_API_KEY"] = key
    api = transfer.session()
    api.headers["Authorization"] = "Bearer " + key
    receipt = ROOT / "task.json"
    if receipt.exists():
        task_id = json.loads(receipt.read_text(encoding="utf-8"))["id"]
    else:
        marker = ROOT / "submission_pending.json"
        if marker.exists():
            raise RuntimeError("Check previous submission before retrying.")
        source = json.loads((ROOT.parent / "MeshyR1/task.json").read_text(encoding="utf-8"))["id"]
        payload = {"input_task_id": source, "animation_type": "biped", "height_meters": 1.70,
                   "skeleton_template": "ue5_mannequin", "include_fingers": True}
        record("request.json", payload)
        record(marker.name, {"at": transfer.stamp()})
        response = api.post(API, json=payload, timeout=(20, 90))
        if not response.ok:
            if 400 <= response.status_code < 500:
                marker.unlink()
            record("submission_error.json", {"http": response.status_code, "detail": transfer.safe(response.json())})
            response.raise_for_status()
        task_id = response.json()["result"]
        record(receipt.name, {"id": task_id, "at": transfer.stamp()})
        marker.unlink()
    print("Rig task", task_id, flush=True)
    while True:
        r = api.get(f"{API}/{task_id}", timeout=(20, 60))
        r.raise_for_status()
        task = r.json()
        record("status.json", transfer.safe(task))
        print(task["status"], task.get("progress"), flush=True)
        if task["status"] == "SUCCEEDED":
            break
        if task["status"] in ("FAILED", "CANCELED"):
            raise RuntimeError("Rigging ended: " + task["status"])
        time.sleep(12)
    files = []
    transfer.ROOT = ROOT
    with transfer.session() as cdn:
        for extension in ("glb", "fbx"):
            path = transfer.fetch(cdn, task["result"][f"rigged_character_{extension}_url"],
                                  "TavernKeeper_Rigged." + extension)
            with path.open("rb") as src:
                digest = hashlib.file_digest(src, "sha256").hexdigest()
            files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": digest})
    record("delivery.json", {"id": task_id, "credits": task.get("consumed_credits"), "files": files})
    print("Saved both rigged models.", flush=True)


if __name__ == "__main__":
    try:
        rig()
    except requests.RequestException as exc:
        print("Meshy request error", type(exc).__name__, getattr(exc.response, "status_code", None))
        sys.exit(1)
