"""Generate the three independent village defense masters from their orthographic views."""
from concurrent.futures import ThreadPoolExecutor
import getpass
import importlib.util
import json
import msvcrt
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
PARTS = ("A_HighWall", "B_WestArch", "C_WestGrille")
SOURCE = ROOT.parents[1] / "WitchMeshy20260919" / "meshy_pipeline.py"
spec = importlib.util.spec_from_file_location("village_meshy_client", SOURCE)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
api.ROOT = ROOT
api.OUT = ROOT / "Meshy"
api.SETTINGS["proxy"] = os.environ.get("MESHY_PROXY", api.SETTINGS["proxy"])
api.SETTINGS["common"] = {
    "ai_model": "meshy-7.1", "geometry_resolution": "standard",
    "should_texture": True, "texture_model": "meshy-7", "texture_resolution": "2k",
    "enable_pbr": True, "target_formats": ["glb", "fbx"],
}
api.SETTINGS["assets"] = {
    part: {"images": [f"Components/{part}/{view}.png" for view in ("front", "right", "back")],
           "options": {}} for part in PARTS
}


def collect(part):
    folder = api.OUT / part
    receipt = json.loads((folder / "task.json").read_text(encoding="utf-8"))
    endpoint = receipt["endpoint"] + "/" + receipt["task_id"]
    state = None
    retries = 0
    while not (folder / "model.glb").exists():
        try:
            response = api.api("GET", endpoint)
            api.write_json(folder / "response.json", response)
            current = (response["status"], response.get("progress"))
            if current != state:
                print(part, *current, flush=True)
                state = current
            if current[0] in ("FAILED", "CANCELED"):
                raise ValueError(f"{part}: {api.safe(response.get('task_error'))}")
            if current[0] == "SUCCEEDED":
                api.download_result(folder, response)
                glb = folder / "downloads" / "model_urls_glb.glb"
                os.link(glb, folder / "model.glb")
                print(part, "saved", glb.stat().st_size, "bytes", response.get("consumed_credits"), "credits", flush=True)
                return
            retries = 0
        except (OSError, RuntimeError) as exc:
            retries += 1
            if retries >= 5:
                raise
            print(part, "retrying status or transfer:", api.safe(str(exc)), flush=True)
        time.sleep(15)


def main():
    if all((api.OUT / part / "model.glb").is_file() for part in PARTS):
        return
    try:
        api.key_from_environment()
    except RuntimeError:
        os.environ["MESHY_API_KEY"] = getpass.getpass("Meshy credential (hidden): ").strip()
    api.OUT.mkdir(exist_ok=True)
    with (api.OUT / "batch.lock").open("a+b") as lock:
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        for part in PARTS:
            api.submit(part)
        with ThreadPoolExecutor(max_workers=len(PARTS)) as pool:
            list(pool.map(collect, PARTS))
        api.balance("after_high_wall")


if __name__ == "__main__":
    main()
