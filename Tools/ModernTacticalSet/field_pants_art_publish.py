"""Select the saved TS01 folded pickup, equipment display and 2-by-3 icon."""
import hashlib
import json
from pathlib import Path
import sys

from shoulder_packages import package_path,sha,write_revision

P=Path(__file__).resolve().parents[2]
S=P/"SourceAssets/ModernTacticalSet20261113"
R=S/"FieldTrousersR2"
CAT=P/"Content/ColdSteelData"
KEY="ue_modern_tactical_pants"
sys.path.insert(0,str(P/"Tools/BrownLeatherSet"))
from json_entries import replace


def read(p):
    return json.loads(p.read_bytes())


def main():
    art=read(R/"artwork.json");saved=read(R/"artwork-saved.json")
    before=read(S/"CombatShirtR4/artwork-saved.json")["items"][KEY]
    if sha(R/art["source"])!=art["source_sha256"]:raise RuntimeError("Trouser source was revised")
    packages={}
    for role,name in (("display","display"),("pickup","pickup"),("texture","standard_icon")):
        if saved[role]["source_sha256"]!=sha(R/art[name]):raise RuntimeError("Stale "+role+" asset")
        path=saved[role]["asset"];packages[path]=sha(package_path(path))
    receipt=R/"artwork-published.json"
    previous=read(receipt) if receipt.is_file() else {}
    catalog=CAT/"items.json";raw=catalog.read_bytes();item=json.loads(raw)[KEY]
    original=raw.decode("utf-8-sig");text=original
    for field,role in (("world_mesh","pickup"),("ue_equipment_icon_mesh","display")):
        target=saved[role]["asset"]
        if item[field] not in (before[role],target):raise RuntimeError("Concurrent trousers change to "+field)
        if item[field]!=target:text=replace(text,[KEY,field],target)
    png=(R/art["standard_icon"]).read_bytes()
    old=Path(read(S/"CombatShirtR4/artwork.json")["items"][KEY]["icon"]["png"])
    allowed={sha(old),saved["texture"]["source_sha256"]}
    if previous:allowed.add(previous["active"]["texture"]["source_sha256"])
    for dst in {CAT/item["ue_icon"],CAT/"Icons"/(KEY+".png")}:
        existing=dst.read_bytes()
        if hashlib.sha256(existing).hexdigest() not in allowed:
            raise RuntimeError("A different outfit icon was selected at "+str(dst))
        if existing!=png:write_revision(dst,existing,png)
    if text!=original:
        bom=b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        write_revision(catalog,raw,bom+text.encode("utf8"))
    receipt.write_text(json.dumps(dict(inventory_id=KEY,source_sha256=art["source_sha256"],active=saved,
        old_meshes=before,packages=packages,png=art["standard_icon"],runtime_tested=False),indent=2))
    print("FIELD_TROUSER_ITEM_PUBLISHED",len(packages),flush=True)


if __name__=="__main__":main()
