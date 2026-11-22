"""Build the approved head and rig its assembled, full-height NPC counterpart."""
import base64
import getpass
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

from PIL import Image

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Tools/VillageHerbalist"))
import meshy_asset as pipeline

SRC = PROJECT / "SourceAssets/VillageGunsmith"
RIG_URL = "https://api.meshy.ai/openapi/v1/rigging"


def submit(api, folder, url, settings, inputs, payload):
    manifest = {"settings": settings, "inputs": inputs}
    receipt = folder / "request.json"
    if (folder / "task.json").exists() and json.loads(receipt.read_text()) != manifest:
        raise RuntimeError("A recorded task has different input data.")
    pipeline.save(folder, "request.json", manifest)
    return pipeline.submit_and_wait(api, folder, url, {**settings, **payload})


def head(api):
    folder = SRC / "Meshy"
    images, inputs = [], []
    with Image.open(SRC / "Concept/Approved.png") as sheet:
        for name, box in (("front", (0, 0, 588, 627)), ("three_quarter", (590, 0, 1174, 627)),
                          ("profile", (1183, 0, 1774, 627))):
            view = sheet.crop(box).convert("RGB")
            view.save(folder / "References" / (name + ".png"))
            image = io.BytesIO()
            view.save(image, "JPEG", quality=96, subsampling=0)
            raw = image.getvalue()
            inputs.append({"view": name, "crop": box, "sha256": hashlib.sha256(raw).hexdigest()})
            images.append("data:image/jpeg;base64," + base64.b64encode(raw).decode())
    params = dict(pipeline.SETTINGS, target_polycount=64000, target_formats=["glb"])
    job, task = submit(api, folder, pipeline.transfer.API, params, json.loads(json.dumps(inputs)),
                       {"image_urls": images})
    entries = [("head.glb", task["model_urls"]["glb"])]
    for index, textures in enumerate(task.get("texture_urls") or []):
        for channel, url in textures.items():
            if url:
                entries.append((f"Textures/M{index}_{channel}{Path(urlsplit(url).path).suffix}", url))
    pipeline.download(folder, job, task, entries)


def rig(api):
    folder = SRC / "Rig"
    raw = (folder / "assembled.glb").read_bytes()
    params = {"animation_type": "biped", "height_meters": 1.81,
              "skeleton_template": "ue5_mannequin", "include_fingers": True}
    job, task = submit(api, folder, RIG_URL, params, {"assembled.glb": hashlib.sha256(raw).hexdigest()},
                       {"model_url": "data:model/gltf-binary;base64," + base64.b64encode(raw).decode()})
    pipeline.download(folder, job, task, [("rigged." + ext, task["result"]["rigged_character_" + ext + "_url"])
                                          for ext in ("glb", "fbx")])


if __name__ == "__main__":
    with pipeline.transfer.session() as session:
        key = os.getenv("MESHY_API_KEY") or getpass.getpass("Meshy API key: ").strip()
        os.environ["MESHY_API_KEY"] = key
        session.headers["Authorization"] = "Bearer " + key
        {"head": head, "rig": rig}[sys.argv[1]](session)
