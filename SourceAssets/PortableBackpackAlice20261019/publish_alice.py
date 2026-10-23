"""Publish the portable backpack outfit and catalog icon fields."""
import json,runpy
from pathlib import Path

PROJECT = Path(r"D:\FPS3D\FPSGAME")
SRC = PROJECT / "SourceAssets/PortableBackpackAlice20261019"
ITEMS = PROJECT / "Content/ColdSteelData/items.json"
BODY = PROJECT / "Content/ColdSteelData/player_body.json"
MESH = "/Game/Characters/PortableBackpackAlice20261019/SM_AliceBackpack.SM_AliceBackpack"
ICON = "Icons/ue_portable_backpack.png"


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


items_before=ITEMS.read_bytes()
items = json.loads(items_before.decode('utf-8-sig'))
definition = items["ue_portable_backpack"]
if definition.get('ue_icon')!=ICON:
    definition["ue_icon"] = ICON
    if ITEMS.read_bytes()!=items_before:raise RuntimeError('Catalog changed during ALICE publication; merge from fresh input')
    save(ITEMS, items)

body_before=BODY.read_bytes()
body = json.loads(body_before.decode('utf-8-sig'))
body.setdefault("outfits", {}).setdefault("ue_portable_backpack", {
    "world_static_mesh": MESH,
    "attach_bone": "spine_03",
    "attach_location": [
        15.305443263507001,
        -13.510068117731002,
        0.05872369543331857,
    ],
    "attach_rotation": [
        89.77782305011776,
        171.6564197413504,
        169.99476123539873,
    ],
    "attach_scale": [1.0, 1.0, 1.0],
})
body['outfits']['ue_portable_backpack']['world_static_mesh']=MESH
runpy.run_path(str(PROJECT/'Tools/PlayerBody/config_transaction.py'))['commit'](
    BODY,body_before,body,owned_paths=[('outfits','ue_portable_backpack')],producer=__file__)

receipt = {
    "definition": "ue_portable_backpack",
    "mesh": MESH,
    "icon": ICON,
    "attach_scale": body['outfits']['ue_portable_backpack']['attach_scale'],
    "attach_note": "preserve current mount; update mesh reference only",
    "runtime_tested": False,
}
save(SRC / "published.json", receipt)
print("ALICE_PUBLISHED " + json.dumps(receipt, ensure_ascii=False))
