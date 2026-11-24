"""Install the saved optical meshes first, then switch the two Frontier options together."""
import argparse
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
import os

parser = argparse.ArgumentParser()
parser.add_argument("project", type=Path)
parser.add_argument("host", type=Path)
args = parser.parse_args()
source = Path(__file__).resolve().parent
spec = json.loads((source / "parts.json").read_bytes())
relative = Path("Weapons/FrontierCompoundBow/ScopedDrawR9")
folder = args.project / "Content" / relative
folder.mkdir(parents=True, exist_ok=True)
catalog = args.project / "Content/ColdSteelData/bow-gunsmith.json"
before = catalog.read_bytes()
doc = json.loads(before)
entry = next(row for row in doc["weapons"] if row["id"] == "bow_frontier_compound")

def replace_bytes(path, payload):
    with NamedTemporaryFile(dir=path.parent, delete=False) as f:
        f.write(payload)
        temporary = Path(f.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

def format_row(row):
    return "\n    ".join(json.dumps(row, indent=2, ensure_ascii=False).splitlines())

old_row = format_row(entry)
for option, mesh in spec["options"].items():
    name = mesh["mesh"]
    saved = args.host / "Content" / relative / (name + ".uasset")
    if not saved.is_file():
        raise FileNotFoundError(saved)
    for package in saved.parent.glob(name + ".*"):
        if package.suffix not in (".uasset", ".uexp", ".ubulk", ".uptnl"):
            continue
        target = folder / package.name
        payload = package.read_bytes()
        if target.exists():
            if target.read_bytes() != payload:
                raise RuntimeError("Different version already installed: " + str(target))
        else:
            replace_bytes(target, payload)
    visual = entry["part_overrides"]["sight"][option]["visual"]
    if visual["bow_scope_magnification"] != mesh["power"]:
        raise ValueError("Optic power changed: " + option)
    visual["bow_part_sight_mesh"] = f"/Game/{relative.as_posix()}/{name}.{name}"
    visual["bow_ads_sight_cm"] = ",".join(format(n, "g") for n in spec["sight_cm"])
    visual["bow_ads_rotation_deg"] = ",".join(format(n, "g") for n in spec["ads_rotation_deg"])

eol = "\r\n" if b"\r\n" in before else "\n"
encoding = "utf-8-sig" if before.startswith(b"\xef\xbb\xbf") else "utf-8"
text = before.decode(encoding).replace("\r\n","\n")
if text.count(old_row) != 1:
    raise RuntimeError("Cannot locate the Frontier row in the catalog")
after = text.replace(old_row,format_row(entry)).replace("\n",eol).encode(encoding)
if after != before:
    if catalog.read_bytes() != before:
        raise RuntimeError("Catalog changed during installation; rerun against the current row")
    replace_bytes(catalog,after)
