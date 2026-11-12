"""Install the three authored joint profiles, retaining backups and engine readback."""
from pathlib import Path
import gzip
import hashlib
import json
import os
import zipfile
import unreal as u

here = Path(__file__).resolve().parent
root = here.parent
project = root.parents[1]
original = json.loads((root / "install_receipt.json").read_text())["saved"]
receipt_path = here / "support_install.json"
receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
names = {"M249": "DA_M249_Handguard", "LMG201": "DA_LMG201_Stability", "PKM": "DA_PKM_Stability"}
jobs = []
for key, name in names.items():
    path = "/Game/Weapons/LMGStabilityGrip20261111/" + name
    disk = project / ("Content/" + path[6:] + ".uasset")
    digest = hashlib.sha256(disk.read_bytes()).hexdigest()
    if digest not in (original[path], receipt.get(key, {}).get("sha256")):
        raise RuntimeError("Another revision changed " + path)
    jobs.append((key, path, disk))
archive = here / "profiles-before.zip"
if not archive.exists():
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as backup:
        for key, path, disk in jobs:
            backup.write(disk, str(disk.relative_to(project)))

for key, path, disk in jobs:
    if key not in os.environ.get("LMG_REVIEW_KEYS", "M249 LMG201 PKM").split():
        continue
    asset = u.load_asset(path)
    with gzip.open(root / (key + "_profile.json.gz"), "rt") as stream:
        data = json.load(stream)
    if not asset or not asset.set_shared_clips_from_json(json.dumps(data)):
        raise RuntimeError("Failed importing " + key)
    if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError("Failed saving " + key)
    digest = hashlib.sha256(disk.read_bytes()).hexdigest()
    receipt[key] = {"path": path, "sha256": digest}
    receipt_path.write_text(json.dumps(receipt, indent=2))
    get = lambda obj, name: obj.get_editor_property(name)
    readback = {"family": str(get(asset, "family")), "clips": []}
    for clip in get(asset, "clips"):
        tracks = [{"bone": str(get(t, "bone")), "times": list(get(t, "times")), "values": list(get(t, "values"))} for t in get(clip, "tracks")]
        readback["clips"].append({"base": get(clip, "base").get_path_name(), "duration": get(clip, "duration"), "tracks": tracks})
    with gzip.open(here / ("saved_" + key + ".json.gz"), "wt") as stream:
        json.dump(readback, stream)
    print("SAVED_GRIP_REVIEW", key, digest, len(readback["clips"]))
