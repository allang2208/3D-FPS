"""Add the ASH-12 to the Cold Steel catalogs.

Writes: Content/ColdSteelData/{gunsmith,items,combat-weapon-formulas}.json and a
receipt next to this script. Idempotent: an existing ue_ash12 entry is replaced.

Run: python SourceAssets/ASH1220260917/Scripts/patch_data.py
"""
import copy
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
DATA = r"D:\FPS3D\FPSGAME\Content\ColdSteelData"

# 12.7x55 mm: heavy hit, slow cycle, 20-round magazine, subsonic-leaning muzzle
# velocity, stiff recoil. Reload times match the imported clips (2.1 s / 2.7 s).
BASE = {
    "ammo_item_id": "ammo_127",
    "ads_smooth": 14.0,
    "mag_size": 20,
    "recoil": 145,
    "camera_shake": 135,
    "fire_interval": 0.13,
    "reload_time": 2.1,
    "empty_reload_time": 2.7,
    "damage": 48,
    "bullet_speed": 78,
    "effective_range": 80,
}
ALLOWED = ["optic", "magazine", "muzzle"]


def load(name):
    with io.open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def save(name, data):
    with io.open(os.path.join(DATA, name), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


receipt = {}

# --- gunsmith -------------------------------------------------------------
catalog = load("gunsmith.json")
source = next(w for w in catalog["weapons"] if w["id"] == "ue_qbz191")
entry = {
    "id": "ue_ash12",
    "model": "ASH12",
    "name": "ASH-12",
    "allowed": copy.deepcopy(ALLOWED),
    "base": copy.deepcopy(BASE),
    "options": {},
}
for slot in ALLOWED:
    options = copy.deepcopy(source["options"][slot])
    for option in options:
        option["description"] = option["description"].replace("QBZ-191", "ASH-12")
    entry["options"][slot] = options
# Only the factory magazine and the factory muzzle plus the shared suppressor are
# certified for this rifle until its extended-magazine seat and own muzzle family
# are authored.
entry["options"]["magazine"] = [{"id": "false", "name": "原厂弹匣", "description": "20 发 12.7×55mm 标准弹匣，安装在握把后方的弹匣井。", "effects": [], "stats": {}}]
entry["options"]["optic"][0]["description"] = "使用 ASH-12 原厂机械瞄具（提把式照门与前准星）。"
entry["options"]["muzzle"] = [copy.deepcopy(o) for o in source["options"]["muzzle"] if o["id"] in ("false", "true")]
entry["options"]["muzzle"][0]["description"] = "恢复 ASH-12 原厂枪口制退器。"

catalog["weapons"] = [w for w in catalog["weapons"] if w["id"] != "ue_ash12"] + [entry]
save("gunsmith.json", catalog)
receipt["gunsmith"] = {"id": entry["id"], "allowed": entry["allowed"],
                       "options": {k: [o["id"] for o in v] for k, v in entry["options"].items()},
                       "base": BASE}

# --- items ----------------------------------------------------------------
items = load("items.json")
items["ue_ash12"] = {
    "category": "weapon",
    "desc": "ASH-12 自动步枪，12.7×55mm 大口径斗牛犬布局，20 发标准弹匣。",
    "equipSlot": "weapon",
    "icon": "Icons/ue_ash12.png",
    "ue_icon": "Icons/ue_ash12.png",
    "id": "ue_ash12",
    "isTwoHanded": True,
    "name": "ASH-12",
    "rarity": "common",
    "stack_max": 1,
    "stats": [
        {"name": "物理攻击", "value": "48"},
        {"name": "弹匣容量", "value": "20"},
    ],
    "type": "武器",
    "weaponType": "rifle",
}
items["ammo_127"] = {
    "category": "material",
    "desc": "ASH-12 使用的 12.7×55mm 弹药。换弹时自动从背包取用，每发独立计数。",
    "icon": "Icons/ammo_556.png",
    "ue_icon": "Icons/ammo_556.png",
    "icon_fallback": "▥",
    "id": "ammo_127",
    "name": "12.7mm 弹药",
    "price": 4,
    "rarity": "common",
    "stack_max": 999,
    "type": "弹药",
}
save("items.json", items)
receipt["items"] = ["ue_ash12", "ammo_127"]

# --- enhancement formula --------------------------------------------------
formulas = load("combat-weapon-formulas.json")
formulas["ue_ash12"] = {
    "source": "ASH12_ITEM",
    "base": 9,
    "enhanceFlat": 0.7,
    "attrs": [
        {"key": "int", "base": 0.32, "perEnhance": 0.05},
        {"key": "wis", "base": 0.32, "perEnhance": 0.05},
    ],
}
save("combat-weapon-formulas.json", formulas)
receipt["formula"] = formulas["ue_ash12"]

receipt["status"] = "catalog entries written; not yet exercised in game"
with io.open(os.path.join(O, "data.json"), "w", encoding="utf-8") as fh:
    json.dump(receipt, fh, ensure_ascii=False, indent=2)
print("ASH12_DATA_DONE", json.dumps(receipt, ensure_ascii=False)[:400])
