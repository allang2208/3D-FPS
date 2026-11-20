"""Select the saved boot pickup, inventory mesh, description and both icon copies."""
import hashlib
import json
from pathlib import Path
import sys

from ridge_boots_art_render import ROOT, fingerprint
from shoulder_packages import package_path, sha, write_revision

P = Path(__file__).resolve().parents[2]
CAT = P/"Content/ColdSteelData"
KEY = "ue_modern_tactical_boots"
ORIGINAL_DESC = "土棕织物与深褐皮革拼接的中帮战术靴，鞋头带双排压线，鞋底为深色橡胶。"
NEW_DESC = "沙褐色绒面革与织物拼接的高帮系带靴。外侧支撑框从后跟延伸至前掌，橡胶外底带有分区凸齿。"
sys.path.insert(0,str(P/"Tools/BrownLeatherSet"))
from json_entries import replace


def read(path):
    return json.loads(path.read_bytes())


def main():
    legacy = ROOT.parent/"CombatShirtR4"
    old = read(legacy/"artwork-saved.json")["items"][KEY]
    saved = read(ROOT/"artwork-saved.json")
    art = read(ROOT/"artwork.json")
    if saved["fingerprint"]!=art["fingerprint"] or art["fingerprint"]!=fingerprint():
        raise RuntimeError("A new artist export must be saved before selecting the boot item")
    packages = {}
    for role,input_field in (("display","display"),("pickup","pickup"),("texture","standard_icon")):
        entry = saved[role]
        if sha(ROOT/art[input_field])!=entry["source_sha256"]:
            raise RuntimeError("Stale boot asset "+role)
        packages[entry["asset"]] = sha(package_path(entry["asset"]))
    receipt = ROOT/"artwork-published.json"
    old_png = Path(read(legacy/"artwork.json")["items"][KEY]["icon"]["png"])
    allowed = {sha(old_png),saved["texture"]["source_sha256"]}
    if receipt.exists():
        allowed.add(read(receipt)["active"]["texture"]["source_sha256"])
    catalog = CAT/"items.json"
    raw = catalog.read_bytes()
    item = json.loads(raw)[KEY]
    text = original = raw.decode("utf-8-sig")
    target_fields = {"world_mesh":(old["pickup"],saved["pickup"]["asset"]),
                     "ue_equipment_icon_mesh":(old["display"],saved["display"]["asset"]),
                     "desc":(ORIGINAL_DESC,NEW_DESC)}
    for field,(prior,target) in target_fields.items():
        if item[field] not in (prior,target):
            raise RuntimeError("A different change was made to "+field+" on "+KEY)
        if item[field]!=target:
            text = replace(text,[KEY,field],target)
    png = (ROOT/art["standard_icon"]).read_bytes()
    paths = [CAT/item["ue_icon"],CAT/"Icons"/(KEY+".png")]
    previous = [p.read_bytes() for p in paths]
    if any(hashlib.sha256(b).hexdigest() not in allowed for b in previous):
        raise RuntimeError("A different boot icon was selected")
    for path,data in zip(paths,previous):
        if data!=png:
            write_revision(path,data,png)
    if text!=original:
        bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
        write_revision(catalog,raw,bom+text.encode("utf8"))
    receipt.write_text(json.dumps(dict(inventory_id=KEY,active=saved,source_sha256=art["source_sha256"],
        packages=packages,standard_icon=art["standard_icon"],runtime_tested=False),indent=2),encoding="utf8")
    print("RIDGE_BOOT_ITEM_PUBLISHED",len(packages),flush=True)


if __name__=="__main__":
    main()
