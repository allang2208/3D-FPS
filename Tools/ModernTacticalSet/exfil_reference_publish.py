"""Publish the saved reference helmet through the existing headgear and item IDs."""
import hashlib
import json
import runpy
import sys
from pathlib import Path

from shoulder_packages import write_revision

P=Path(__file__).resolve().parents[2]
ROOT=P/"SourceAssets/ModernTacticalSet20261113/ExfilReferenceR4"
CAT=P/"Content/ColdSteelData"
KEY="ue_modern_tactical_helmet"
sys.path.insert(0,str(P/"Tools/BrownLeatherSet"))
from json_entries import replace


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    read=lambda path:json.loads(path.read_bytes())
    saved=read(ROOT/"saved.json");art=read(ROOT/"artwork.json");surfaces=read(ROOT/"saved-surfaces.json")
    if not saved["completed"] or len(surfaces["materials"])!=10 or len(surfaces["textures"])!=30:
        raise RuntimeError("Incomplete EXFIL material or mesh packages")
    for rel,value in art["source_sha256"].items():
        if sha(ROOT/rel)!=value:
            raise RuntimeError(f"Artwork was generated from another revision: {rel}")
    files={"Jason":ROOT/"Authored/helmet_Jason_wear.json","Kaitlin":ROOT/"Authored/helmet_Kaitlin_wear.json",
           "pickup":Path(art["pickup"]),"display":Path(art["icon"]["display"])}
    for role,file in files.items():
        if saved["meshes"][role]["source_sha"]!=sha(file):
            raise RuntimeError(f"Saved {role} geometry is stale")
    icon=Path(art["icon"]["png"])
    if saved["icon_sha"]!=sha(icon):
        raise RuntimeError("Saved inventory icon does not match the new model render")
    objects=[row["asset"] for row in saved["meshes"].values()]+[saved["icon"],*surfaces["materials"].values(),*surfaces["textures"].values()]
    packages={}
    for obj in objects:
        if "/ModernTacticalSet20261113/ExfilReferenceR4/" not in obj:
            raise RuntimeError(f"Unexpected package for this publication: {obj}")
        file=P/"Content"/(obj.removeprefix("/Game/").split(".")[0]+".uasset")
        packages[obj]=sha(file)
    path=CAT/"player_body.json";before=path.read_bytes();doc=json.loads(before);owned=[]
    def check(current,new):
        previous=new.replace("_JawFit","")
        if current not in (new,previous,previous.replace("/ExfilReferenceR4/","/HelmetNapeR3/")):
            raise RuntimeError(f"Helmet route changed since production started: {current}")
    for rig,keys in (("Jason",("head_equipment",KEY)),("Kaitlin",("body_variants","kaitlin","head_equipment",KEY))):
        row=doc
        for key in keys:row=row[key]
        new=saved["meshes"][rig]["asset"];check(row["static_mesh"],new)
        row["static_mesh"]=new;owned.append(keys+("static_mesh",))
    receipt=runpy.run_path(str(P/"Tools/PlayerBody/config_transaction.py"))["commit"](path,before,doc,owned_paths=owned,producer=__file__)
    path=CAT/"items.json";before=path.read_bytes();text=before.decode("utf-8-sig");item=json.loads(before)[KEY]
    for field,role in (("world_mesh","pickup"),("ue_equipment_icon_mesh","display")):
        new=saved["meshes"][role]["asset"];check(item[field],new)
        text=replace(text,[KEY,field],new)
    old_icon=(ROOT.parent/"HelmetNapeR3/Icons"/icon.name).read_bytes()
    for target in {CAT/item["ue_icon"],CAT/"Icons"/icon.name}:
        previous=target.read_bytes();updated=icon.read_bytes()
        if previous not in (old_icon,updated):
            raise RuntimeError(f"Concurrent change to {target}")
        if previous!=updated:write_revision(target,previous,updated)
    encoded=(b"\xef\xbb\xbf" if before.startswith(b"\xef\xbb\xbf") else b"")+text.encode("utf-8")
    if encoded!=before:write_revision(path,before,encoded)
    (ROOT/"published.json").write_text(json.dumps(dict(packages=packages,body=receipt,materials=10,textures=30,
                                inventory_texture=saved["icon"],meshes=saved["meshes"],gameplay_tested=False),indent=2),encoding="utf-8")
    print("EXFIL headgear now selected by both bodies and the inventory.",len(packages),"saved packages.")


if __name__=="__main__":
    main()
