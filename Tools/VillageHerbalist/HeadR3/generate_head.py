"""Generate or resume the isolated, glasses-free head from Lin Zhi's three portrait angles."""
import base64
import hashlib
import io
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import meshy_asset as pipeline

ROOT = pipeline.ROOT / "HeadR3"
REFERENCES = ROOT / "References"
OUTPUT = ROOT / "Meshy"
VIEWS = ("01_front", "02_three_quarter", "03_profile")

def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(REFERENCES / "Head_Turnaround.png").convert("RGB")
    images, inputs = [], []
    for index, view in enumerate(VIEWS):
        start = round(sheet.width * index / len(VIEWS))
        end = round(sheet.width * (index + 1) / len(VIEWS))
        path = REFERENCES / (view + ".png")
        sheet.crop((start, 0, end, sheet.height)).save(path)
        data = path.read_bytes()
        transport = io.BytesIO()
        sheet.crop((start, 0, end, sheet.height)).save(transport, "JPEG", quality=95, subsampling=0)
        encoded = transport.getvalue()
        inputs.append({"view": path.name, "sha256": hashlib.sha256(data).hexdigest(),
                       "upload_jpeg_sha256": hashlib.sha256(encoded).hexdigest()})
        images.append("data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii"))
    options = dict(pipeline.SETTINGS, target_polycount=64000, target_formats=["glb"])
    request = {"inputs": inputs, "parameters": options}
    if (OUTPUT/"task.json").is_file() and json.loads((OUTPUT/"request.json").read_text()) != request:
        raise RuntimeError("The recorded task uses different inputs")
    pipeline.save(OUTPUT, "request.json", request)
    key = pipeline.transfer.credentials()
    if not key:
        raise SystemExit("Meshy API credential required")
    with pipeline.transfer.session() as api:
        api.headers["Authorization"] = "Bearer " + key
        task_id, task = pipeline.submit_and_wait(api, OUTPUT, pipeline.transfer.API,
            dict(options, image_urls=images))
    entries = []
    for index,maps in enumerate(task.get("texture_urls", [])):
        for channel,url in maps.items():
            if url:
                entries.append((f"Textures/M{index}_{channel}{Path(urlsplit(url).path).suffix}",url))
    # Assemble only after maps are staged and the complete GLB is atomically renamed.
    entries.append(("head.glb", task["model_urls"]["glb"]))
    pipeline.download(OUTPUT, task_id, task, entries)

if __name__ == "__main__":
    main()
