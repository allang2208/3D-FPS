"""Install new wrist materials and merge only the two modern shirt recipe fields."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

PROJECT = Path("D:/FPS3D/FPSGAME")
ROOT = PROJECT / "SourceAssets/ModernTacticalSet20261113/BareWrists20261118"
STAGE = ROOT / "Stage/Content"
sys.path.insert(0, str(PROJECT / "Tools/BrownLeatherSet"))
import json_entries


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def install(asset):
    relative = Path(asset.removeprefix("/Game/").split(".")[0] + ".uasset")
    src, dst = STAGE / relative, PROJECT / "Content" / relative
    checksum = sha(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if sha(dst) != checksum:
            raise RuntimeError("Conflicting wrist package: " + str(dst))
    else:
        with tempfile.NamedTemporaryFile(dir=dst.parent, delete=False) as tmp:
            temporary = Path(tmp.name)
            with src.open("rb") as stream:
                shutil.copyfileobj(stream, tmp)
        try:
            if sha(temporary) != checksum:
                raise RuntimeError("Incomplete package: " + str(dst))
            os.link(temporary, dst)
        finally:
            temporary.unlink(missing_ok=True)
    return checksum


def publish():
    receipt = json.loads((ROOT / "saved-materials.json").read_text())
    if not receipt["completed"]:
        raise RuntimeError("Native sources incomplete")
    rows = receipt["skins"]
    packages = {p for row in rows.values() if "material" in row for p in row["packages"]}
    installed = {p: install(p) for p in sorted(packages)}
    cfg = PROJECT / "Content/ColdSteelData/modular_outfits.json"
    for attempt in range(5):
        raw = cfg.read_bytes()
        text = raw.decode("utf-8-sig")
        data = json.loads(text)
        totals = {}
        for sex, prefix, branch in [("Jason", [], data), ("Kaitlin", ["body_variants", "kaitlin"], data["body_variants"]["kaitlin"])]:
            refs = {p.get("native_bare_skin") or p["base"] for p in branch["profiles"].values()}
            missing = refs - rows.keys()
            if missing:
                raise RuntimeError("New native references require wrist fit: " + str(missing))
            maps = {path: {"slot": rows[path]["slot"], "material": rows[path]["material"]} for path in sorted(refs)
                    if "material" in rows[path]}
            shirt = branch["items"]["ue_modern_kevlar_vest"]
            key = prefix + ["items", "ue_modern_kevlar_vest"]
            field = "bare_wrist_materials"
            text = (json_entries.replace(text, key+[field], maps) if field in shirt
                    else json_entries.insert(text, key, field, maps))
            totals[sex] = dict(profiles=len(branch["profiles"]), distinct_skins=len(refs), masked=len(maps))
        if raw.startswith(b"\xef\xbb\xbf"):
            text = "\ufeff" + text
        backup = ROOT / "before-wrists.json"
        if not backup.exists():
            backup.write_bytes(raw)
        with tempfile.NamedTemporaryFile(dir=cfg.parent, delete=False) as tmp:
            tmp.write(text.encode("utf-8"))
            temp = Path(tmp.name)
        try:
            if cfg.read_bytes() != raw:
                continue
            os.replace(temp, cfg)
            break
        finally:
            temp.unlink(missing_ok=True)
    else:
        raise RuntimeError("Outfit configuration kept changing")
    (ROOT / "published.json").write_text(json.dumps(dict(installed=installed, totals=totals,
        runtime_tested=False, completed=True), indent=2), encoding="utf-8")
    print("NATIVE_WRIST_PUBLISHED", len(installed), totals)


if __name__ == "__main__":
    publish()
