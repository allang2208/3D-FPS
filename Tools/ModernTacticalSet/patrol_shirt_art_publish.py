"""Select the saved revised shirt and original carrier in the live item record."""
import hashlib
import json
from pathlib import Path
import sys

from patrol_shirt_art_render import KEY, ROOT, fingerprint
from shoulder_packages import package_path, sha, write_revision

P = Path(__file__).resolve().parents[2]
CAT = P/"Content/ColdSteelData"
sys.path.insert(0,str(P/"Tools/BrownLeatherSet"))
from json_entries import replace

OLD = "土棕色凯夫拉防弹衣搭配男女独立裁片的低圆领作战上衣；弹力胸背、防撕裂插肩袖、圆角袖袋与护肘，自然布料褶皱，袖口和后摆保留搭接。"
DESCRIPTION = "土棕色凯夫拉防弹衣搭配作战上衣。弹力躯干连接防撕裂插肩袖，上臂带拉链袋，肘部有活动褶与补强裁片，袖口以织物袢收紧。"


def read(path):
    return json.loads(path.read_bytes())


def main():
    prior = ROOT.parent/"ShoulderFit20261118"
    old = read(prior/"inventory-saved.json")
    art = read(ROOT/"artwork.json")
    saved = read(ROOT/"artwork-saved.json")
    if saved["fingerprint"]!=art["fingerprint"] or fingerprint()!=art["fingerprint"]:
        raise RuntimeError("The saved product no longer matches the authored shirt")
    packages = {}
    for role,field in (("display","display"),("pickup","pickup"),("texture","standard_icon")):
        entry = saved[role]
        if sha(ROOT/art[field])!=entry["source_sha256"]:
            raise RuntimeError("Stale "+role+" product")
        packages[entry["asset"]] = sha(package_path(entry["asset"]))
    png = (ROOT/art["standard_icon"]).read_bytes()
    receipt = ROOT/"artwork-published.json"
    allowed = {read(prior/"inventory-published.json")["icon_sha256"],saved["texture"]["source_sha256"]}
    if receipt.exists():
        allowed.add(read(receipt)["active"]["texture"]["source_sha256"])
    catalog = CAT/"items.json"
    raw = catalog.read_bytes()
    item = json.loads(raw)[KEY]
    text = original = raw.decode("utf-8-sig")
    for key,previous,revised in (("world_mesh",old["pickup"],saved["pickup"]["asset"]),
                                 ("ue_equipment_icon_mesh",old["display"],saved["display"]["asset"]),
                                 ("desc",OLD,DESCRIPTION)):
        if item[key] not in (previous,revised):
            raise RuntimeError("Another edit was made to "+key+" on "+KEY)
        if item[key]!=revised:
            text = replace(text,[KEY,key],revised)
    paths = [CAT/item["ue_icon"],CAT/"Icons"/(KEY+".png")]
    previous = [file.read_bytes() for file in paths]
    if any(hashlib.sha256(b).hexdigest() not in allowed for b in previous):
        raise RuntimeError("Another catalogue image has been selected")
    for file,data in zip(paths,previous):
        if data!=png:
            write_revision(file,data,png)
    if original!=text:
        bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        write_revision(catalog,raw,bom+text.encode("utf8"))
    receipt.write_text(json.dumps(dict(inventory_id=KEY,active=saved,packages=packages,
                        source_sha256=art["source_sha256"],standard_icon=art["standard_icon"],runtime_tested=False),indent=2),encoding="utf8")
    print("PATROL_SHIRT_INVENTORY_PUBLISHED",len(packages),flush=True)


if __name__=="__main__":
    main()
