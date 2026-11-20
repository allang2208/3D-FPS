"""Prepare and publish the body-specific TS01 shoulder revisions."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import numpy as np

P = Path(__file__).resolve().parents[2]
S = P / "SourceAssets/ModernTacticalSet20261113"
OUT = S / "ShoulderFit20261118"
R4 = S / "CombatShirtR4"
CONFIG = P / "Content/ColdSteelData/modular_outfits.json"
KEY = "ue_modern_kevlar_vest"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def package_path(asset):
    return P / "Content" / (asset.removeprefix("/Game/").split(".")[0]+".uasset")


def write_revision(path, original, result):
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as tmp:
        tmp.write(result)
    try:
        if path.read_bytes()!=original:
            raise RuntimeError(f"Concurrent change at {path}. Read its current revision before publishing.")
        os.replace(tmp.name,path)
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def publish_inventory():
    sys.path.insert(0,str(P/"Tools/BrownLeatherSet"))
    from json_entries import replace
    saved=read(OUT/"inventory-saved.json")
    previous=read(R4/"artwork-saved.json")["items"][KEY]
    catalog=CONFIG.with_name("items.json")
    before=catalog.read_bytes()
    item=json.loads(before)[KEY]
    text=before.decode("utf-8-sig")
    for field,kind in (("world_mesh","pickup"),("ue_equipment_icon_mesh","display")):
        if item[field] not in (previous[kind],saved[kind]):
            raise RuntimeError(f"Vest {field} changed during production")
        text=replace(text,[KEY,field],saved[kind])
    hashes={value:sha(package_path(value)) for value in saved.values()}
    png=Path(read(OUT/"artwork.json")["icon"]["png"]).read_bytes()
    prior_png=Path(read(R4/"artwork.json")["items"][KEY]["icon"]["png"]).read_bytes()
    for path in {catalog.parent/item["ue_icon"],catalog.parent/"Icons"/(KEY+".png")}:
        original=path.read_bytes()
        if original!=prior_png and original!=png:
            raise RuntimeError(f"Vest icon has changed at {path}")
        if original!=png:
            write_revision(path,original,png)
    if json.loads(text)[KEY]["world_mesh"]!=saved["pickup"]:
        raise RuntimeError("Inventory item lost its pickup during publication")
    write_revision(catalog,before,(b"\xef\xbb\xbf" if before.startswith(b"\xef\xbb\xbf") else b"")+text.encode("utf-8"))
    (OUT/"inventory-published.json").write_text(json.dumps(dict(packages=hashes,icon_sha256=hashlib.sha256(png).hexdigest()),indent=2))
    print("Published the vest pickup, inventory display and icons.")


def prepare():
    rows = [row for row in read(R4/"authored.json")["rows"]
            if row["rig"] in ("Jason","Kaitlin") and not row.get("kind")]
    installed = {Path(row["path"]):row["sha256"] for row in read(R4/"installed.json")["packages"]}
    for rig in ("Jason","Kaitlin"):
        edits = [np.load(OUT/f"{rig}-{part}.npz") for part in ("cloth","carrier")]
        np.concatenate([np.hstack((data["before"],data["after"])) for data in edits]).astype("<f4").tofile(OUT/f"{rig}.bin")
        selected = []
        for row in rows:
            if row["rig"]!=rig:
                continue
            old = row["asset"]
            if sha(package_path(old))!=installed[package_path(old)]:
                raise RuntimeError(f"R4 source has changed: {old}")
            selected.append(old)
        for i in range(0,len(selected),3):
            (OUT/f"{rig}-{i//3}.txt").write_text("\n".join(selected[i:i+3])+"\n",encoding="utf-8")


def publish():
    sys.path.insert(0,str(P/"Tools/BrownLeatherSet"))
    from json_entries import span
    before = CONFIG.read_bytes()
    doc = json.loads(before)
    text = before.decode("utf-8-sig")
    changed = []
    receipts = {}
    def visit(node, fields):
        if isinstance(node,dict):
            for k,v in node.items():
                visit(v,fields+[k])
        elif isinstance(node,str) and "/CombatShirtR4/Wear/" in node and "/SK_TS01_Combat_" in node:
            if fields[-1] not in ("Jason","Kaitlin"):
                return
            new = node.replace("/CombatShirtR4/","/ShoulderFit20261118/")
            target = package_path(new)
            if new not in receipts:
                if not target.is_file():
                    raise RuntimeError(f"Missing saved mesh: {target}")
                receipts[new] = sha(target)
            changed.append((fields,node,new))
    visit(doc["items"][KEY],["items",KEY])
    visit(doc["body_variants"]["kaitlin"]["items"][KEY],["body_variants","kaitlin","items",KEY])
    expected = {row["asset"].replace("/CombatShirtR4/","/ShoulderFit20261118/") for row in read(R4/"authored.json")["rows"]
                if row["rig"] in ("Jason","Kaitlin") and not row.get("kind")}
    if {key.split(".")[0] for key in receipts} != expected:
        raise RuntimeError("Live waist/body paths diverged from the 36 source packages")
    # All values are paths. Locate both owned item sections once, then replace
    # complete quoted values only; keys and unrelated config text stay intact.
    for base in (["items",KEY],["body_variants","kaitlin","items",KEY]):
        a,b = span(text,base)
        section = text[a:b]
        for old,new in {(old,new) for fields,old,new in changed if fields[:len(base)]==base}:
            section=section.replace(json.dumps(old),json.dumps(new))
        text=text[:a]+section+text[b:]
    candidate=json.loads(text)
    for fields,old,new in changed:
        dest=candidate
        for key in fields:
            dest=dest[key]
        if dest!=new:
            raise RuntimeError(f"Failed to set {fields}")
    write_revision(CONFIG,before,(b"\xef\xbb\xbf" if before.startswith(b"\xef\xbb\xbf") else b"")+text.encode("utf-8"))
    (OUT/"published.json").write_text(json.dumps(dict(packages=receipts,fields=len(changed),lods_per_mesh=3),indent=2),encoding="utf-8")
    print("Saved and routed",len(receipts),"body meshes through",len(changed),"fields")


if __name__ == "__main__":
    {"prepare":prepare,"publish":publish,"inventory":publish_inventory}[sys.argv[1]]()
