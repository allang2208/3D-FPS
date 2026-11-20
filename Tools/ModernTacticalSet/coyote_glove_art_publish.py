"""Wire the saved glove artwork into the existing item and its standard icon fallbacks."""
import hashlib
import json
from pathlib import Path
import sys

from shoulder_packages import package_path,sha,write_revision

P=Path(__file__).resolve().parents[2]
S=P/"SourceAssets/ModernTacticalSet20261113"
R=S/"CoyoteGlovesR2"
CAT=P/"Content/ColdSteelData"
KEY="ue_modern_tactical_gloves"
sys.path.insert(0,str(P/"Tools/BrownLeatherSet"))
from json_entries import replace


def read(p):
    return json.loads(p.read_bytes())


def main():
    saved=read(R/"artwork-saved.json")
    art=read(R/"artwork.json")
    prior=read(S/"CombatShirtR4/artwork-saved.json")["items"][KEY]
    if art["source_sha256"]!=sha(R/art["source"]):
        raise RuntimeError("Artwork no longer corresponds to the equipped source")
    packages={}
    for role,field in (("pickup","pickup"),("display","display"),("texture","standard_icon")):
        if saved[role]["source_sha256"]!=sha(R/art[field]):
            raise RuntimeError(f"Unexpected artwork source revision for {role}")
        asset=saved[role]["asset"];packages[asset]=sha(package_path(asset))
    catalog=CAT/"items.json"
    before=catalog.read_bytes();item=json.loads(before)[KEY]
    encoded=before.decode("utf-8-sig")
    for key,role in (("world_mesh","pickup"),("ue_equipment_icon_mesh","display")):
        previous=item[key];new=saved[role]["asset"]
        if previous not in (prior[role],new):
            raise RuntimeError(f"Concurrent change to glove {key}")
        encoded=replace(encoded,[KEY,key],new)
    old_png=Path(read(S/"CombatShirtR4/artwork.json")["items"][KEY]["icon"]["png"]).read_bytes()
    updated_png=(R/art["standard_icon"]).read_bytes()
    receipt=R/"artwork-published.json"
    previous_sha=read(receipt)["active"]["texture"]["source_sha256"] if receipt.is_file() else None
    for dst in {CAT/item["ue_icon"],CAT/"Icons"/(KEY+".png")}:
        existing=dst.read_bytes()
        if existing not in (old_png,updated_png) and hashlib.sha256(existing).hexdigest()!=previous_sha:
            raise RuntimeError(f"Concurrent glove icon change at {dst}")
        if existing!=updated_png:write_revision(dst,existing,updated_png)
    data=(b"\xef\xbb\xbf" if before.startswith(b"\xef\xbb\xbf") else b"")+encoded.encode("utf8")
    if data!=before:write_revision(catalog,before,data)
    receipt.write_text(json.dumps(dict(packages=packages,old_meshes=prior,active=saved,
              inventory_id=KEY,png=art["standard_icon"],runtime_tested=False),indent=2),encoding="utf8")
    print("COYOTE_GLOVE_ITEM_PUBLISHED",len(packages),flush=True)


if __name__=="__main__":main()
