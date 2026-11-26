"""Build a textured blacksmith head using the Chapel Nun four-view settings."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import requests

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / "ChapelNun"))
from meshy_head import API, INPUTS, PARAMS, PROXY, safe, stamp

ROOT = TOOLS.parent / "SourceAssets" / "VillageBlacksmithNPC20261118" / "Meshy" / "CombinedR1"
TASK = ROOT / "task.json"


def write_json(name, value):
    target = ROOT / name
    pending = target.with_suffix(".json.tmp")
    pending.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    pending.replace(target)


def credentials():
    if "--prompt-key" in sys.argv:
        from getpass import getpass
        return getpass("Meshy session key (hidden): ").strip()
    key = os.getenv("MESHY_API_KEY")
    if key or os.name != "nt":
        return key
    import winreg
    for hive, section in [(winreg.HKEY_CURRENT_USER, "Environment"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")]:
        try:
            with winreg.OpenKey(hive, section) as entry:
                return winreg.QueryValueEx(entry, "MESHY_API_KEY")[0].strip()
        except OSError:
            pass


def request_images():
    pictures = []
    records = []
    for name in INPUTS:
        path = ROOT / "Inputs" / name
        raw = path.read_bytes()
        pictures.append("data:image/png;base64," + base64.b64encode(raw).decode("ascii"))
        records.append({"path": "Inputs/" + name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
    write_json("request.json", {"service": API, "parameters": PARAMS, "images": records})
    return pictures


def session():
    client = requests.Session()
    client.trust_env = False
    client.proxies.update(PROXY)
    return client


def fetch(client, url, filename):
    target = ROOT / filename
    if target.is_file() and target.stat().st_size:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    for attempt in range(4):
        try:
            with client.get(url, stream=True, timeout=(30, 180)) as response:
                response.raise_for_status()
                with partial.open("wb") as output:
                    for block in response.iter_content(1024 * 1024):
                        output.write(block)
            if filename == "head.glb" and partial.read_bytes()[:4] != b"glTF":
                raise RuntimeError("Invalid GLB response")
            partial.replace(target)
            return target
        except requests.RequestException:
            if attempt == 3:
                raise RuntimeError("Download failed: " + filename) from None
            time.sleep(8)


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    pictures = request_images()
    key = credentials()
    if not key:
        write_json("awaiting_credentials.json", {"state": "awaiting_local_MESHY_API_KEY", "time": stamp()})
        print("Meshy inputs ready; local credential missing.")
        return 2
    os.environ["MESHY_API_KEY"] = key
    client = session()
    client.headers["Authorization"] = "Bearer " + key
    for file in ["awaiting_credentials.json", "blocked.json"]:
        (ROOT / file).unlink(missing_ok=True)
    if TASK.exists():
        task_id = json.loads(TASK.read_text())["id"]
    else:
        if (ROOT / "submission_pending.json").exists():
            raise RuntimeError("Prior submission outcome unknown. Resolve before creating another task.")
        write_json("submission_pending.json", {"time": stamp()})
        response = client.post(API, json={**PARAMS, "image_urls": pictures, "texture_image_urls": pictures}, timeout=(30, 240))
        if not response.ok:
            if 400 <= response.status_code < 500:
                (ROOT / "submission_pending.json").unlink()
            write_json("submission_error.json", {"status": response.status_code, "error": safe(response.text[:1000])})
            raise RuntimeError("Submission HTTP " + str(response.status_code))
        task_id = response.json()["result"]
        write_json("task.json", {"id": task_id, "submitted": stamp()})
        (ROOT / "submission_pending.json").unlink()
    print("Meshy task " + task_id, flush=True)
    failures = 0
    while True:
        try:
            response = client.get(API + "/" + task_id, timeout=(30, 90))
            response.raise_for_status()
            state = response.json()
            failures = 0
        except requests.RequestException:
            failures += 1
            if failures == 8:
                raise RuntimeError("Status unavailable. Resume using the saved task id.") from None
            time.sleep(15)
            continue
        write_json("status.json", safe(state))
        print(state["status"], state.get("progress"), flush=True)
        if state["status"] == "SUCCEEDED":
            break
        if state["status"] in ("FAILED", "CANCELED"):
            raise RuntimeError("Generation " + state["status"])
        time.sleep(15)
    downloads = session()
    models = state.get("model_urls", {})
    assets = [("head.glb", models["glb"])]
    for fmt in ("fbx", "obj"):
        if models.get(fmt):
            assets.append(("Source/head." + fmt, models[fmt]))
    for index, maps in enumerate(state.get("texture_urls", [])):
        for kind, url in maps.items():
            if url:
                suffix = Path(url.split("?", 1)[0]).suffix
                assets.append((f"Source/texture_{index}_{kind}{suffix}", url))
    rows = []
    for name, url in assets:
        path = fetch(downloads, url, name)
        with path.open("rb") as handle:
            checksum = hashlib.file_digest(handle, "sha256").hexdigest()
        rows.append({"path": name, "bytes": path.stat().st_size, "sha256": checksum})
    write_json("delivery.json", {"id": task_id, "consumed_credits": state.get("consumed_credits"), "files": rows})
    return 0


if __name__ == "__main__":
    sys.exit(main())

