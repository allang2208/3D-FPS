"""Generate or resume the baker's bareheaded Meshy asset using his approved portrait sheet."""
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from PIL import Image

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Tools" / "VillageHerbalist"))
import meshy_asset as pipeline

BAKER = PROJECT / "SourceAssets" / "VillageBaker"
OUTPUT = BAKER / "HeadR1" / "Meshy"
REFERENCES = OUTPUT.parent / "References"
SHEET = BAKER / "Concept" / "R1" / "Baker_Head_Turnaround.png"
VIEWS = (("front", 405), ("three_quarter", 1024), ("profile", 1642))


def main():
    key = pipeline.transfer.credentials()
    if not key:
        raise SystemExit("Set MESHY_API_KEY to submit or resume the baker head.")
    REFERENCES.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    uploads = []
    inputs = []
    with Image.open(SHEET) as sheet:
        for view, center in VIEWS:
            box = (center - 305, 34, center + 305, 644)
            portrait = sheet.crop(box).convert("RGB")
            portrait.save(REFERENCES / (view + ".png"))
            jpeg = io.BytesIO()
            portrait.save(jpeg, "JPEG", quality=95, subsampling=0)
            raw = jpeg.getvalue()
            inputs.append({"view": view, "crop": list(box), "jpeg_sha256": hashlib.sha256(raw).hexdigest()})
            uploads.append("data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii"))
    settings = dict(pipeline.SETTINGS, target_polycount=64000, target_formats=["glb"])
    manifest = {"source": SHEET.name, "inputs": inputs, "parameters": settings}
    if (OUTPUT / "task.json").exists() and json.loads((OUTPUT / "request.json").read_text()) != manifest:
        raise RuntimeError("Recorded task and requested reference set differ.")
    pipeline.save(OUTPUT, "request.json", manifest)
    with pipeline.transfer.session() as api:
        api.headers["Authorization"] = "Bearer " + key
        job, task = pipeline.submit_and_wait(api, OUTPUT, pipeline.transfer.API, dict(settings, image_urls=uploads))
    files = []
    for index, maps in enumerate(task.get("texture_urls") or []):
        for channel, url in maps.items():
            if url:
                suffix = Path(urlsplit(url).path).suffix
                files.append((f"Textures/M{index}_{channel}{suffix}", url))
    files.append(("head.glb", task["model_urls"]["glb"]))
    if task.get("thumbnail_url"):
        url = task["thumbnail_url"]
        files.append(("preview" + Path(urlsplit(url).path).suffix, url))
    pipeline.download(OUTPUT, job, task, files)


if __name__ == "__main__":
    main()
