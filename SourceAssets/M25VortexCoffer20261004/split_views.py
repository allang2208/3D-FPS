"""Recreate only the three requested independent image crops."""
from pathlib import Path
from PIL import Image
import json

root = Path(__file__).resolve().parent
data = json.loads((root / "views.json").read_text(encoding="utf-8"))
source = Image.open(root / data["source"]).convert("RGB")
for view in data["views"]:
    source.crop(tuple(view["crop_xyxy"])).save(root / view["file"])
