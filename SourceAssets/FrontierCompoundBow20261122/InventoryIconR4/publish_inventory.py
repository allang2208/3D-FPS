"""Publish the two editor-saved UI packages and their PNGs from an inventory icon batch."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import tempfile

project, batch = (Path(arg).resolve() for arg in sys.argv[1:])
relative = Path("Content/ColdSteelData/Icons")
names = ("bow_frontier_compound", "bow_frontier_compound_r2")
saved = json.loads((batch / "saved-textures.json").read_text(encoding="utf-8"))
if set(saved) != set(names):
    raise ValueError("Incomplete inventory icon import")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


files = {}
for name in names:
    for suffix, folder in ((".png", batch / "Export"), (".uasset", batch / "Host" / relative)):
        filename = name + suffix
        source, target = folder / filename, project / relative / filename
        checksum = digest(source)
        previous = digest(batch / "Before" / relative / filename)
        if digest(target) not in (previous, checksum):
            raise RuntimeError(f"Another change to {target} must be preserved")
        files[filename] = (source, target, checksum)

for source, target, checksum in files.values():
    if digest(target) != checksum:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
            with source.open("rb") as original:
                shutil.copyfileobj(original, temporary)
        os.replace(temporary.name, target)

record = {
    "definition": names[0],
    "formal_icon": str(project / relative / (names[0] + ".png")),
    "saved_packages": saved,
    "sha256": {name: digest(target) for name, (_, target, _) in files.items()},
    "producer": "ColdSteelWeaponIconCatalog -Definition=bow_frontier_compound",
    "source": str(Path(__file__).resolve().parent),
    "previous": str(batch / "Before"),
    "editor_build_log": str(batch / "build.log"),
    "gameplay_tested": False,
}
(batch / "published.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
