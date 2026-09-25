""" bows.json 与代码读取点的一致性自检（纯文本，不需要 UE）。

用法：python Tools/Bow/check_bow_consistency.py
退出码非 0 表示有不一致；口径与 Tools/Weapons/check_attachment_consistency.py 一致。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "Content" / "ColdSteelData"

# UBowWeaponComponent::ApplyNumbers 实际读取的数值键。
NUMBERS = [
    "nock_seconds", "draw_seconds", "hold_seconds", "release_seconds", "recover_seconds",
    "full_damage", "min_damage_ratio", "full_speed_cm", "min_speed_ratio",
    "arrow_gravity_cm", "range_cm", "stamina_cost", "critical_chance", "toughness_multiplier",
    "bow_length_cm", "bow_depth_cm", "arrow_length_cm", "sway_amplitude_cm", "steady_sway_scale",
]
# 锚点键：留空即用代码里的实测默认值，写了就必须是三个数。
VECTORS = [
    "nock_upper_cm", "nock_lower_cm", "brace_nock_cm", "draw_anchor_cm", "arrow_rest_cm",
    "bow_location_cm", "bow_rotation_deg", "bow_grip_trim_cm", "bow_arms_rotation_deg",
]
# 非部件的其余资源键（允许留空）。
OPTIONAL_PATHS = ["bow_viewmodel", "bow_animation_prefix", "arrow_head_mesh",
                  "bow_draw_sound", "bow_release_sound", "bow_nock_sound"]
# 部件槽的每个键：mesh / material 是路径，rods / radius_cm / scale 是数字，hide_slot 是文本。
PART_SUFFIXES_PATH = ("mesh", "material")
PART_SUFFIXES_NUMBER = ("rods", "radius_cm", "scale")

problems: list[str] = []


def load(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        problems.append(f"缺少数据表：{path.relative_to(ROOT)}")
        return {}
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def check_asset(definition: str, key: str, value: str) -> None:
    if value.startswith("/Game/"):
        package = value.split(".", 1)[0]
        # /Game 是 Content 的挂载名，落盘检查要换回 Content。
        on_disk = (ROOT / "Content" / Path(*package[len("/Game/"):].split("/"))).with_suffix(".uasset")
        if not on_disk.exists():
            problems.append(f"{definition}: {key} 指向的资产不在盘上：{on_disk.relative_to(ROOT)}")
    elif value.split(".", 1)[0]:
        problems.append(f"{definition}: {key} 必须是 /Game 资产路径，实为 {value!r}")


bows = load("bows.json")
ammo = load("ammo_types.json")

ammo_ids: set[str] = set()
if ammo:
    rows = ammo.get("types") or ammo.get("ammo_types") or []
    ammo_ids = {row.get("id") for row in rows if isinstance(row, dict)}

for definition, row in sorted(bows.items()):
    if not isinstance(row, dict):
        problems.append(f"{definition}: 条目不是对象")
        continue
    for key, want in (("category", "weapon_bow"), ("weaponType", "bow"), ("equipSlot", "weapon")):
        if row.get(key) != want:
            problems.append(f'{definition}: {key} 必须是 "{want}"（库存与装备判定按它走）')
    if not row.get("isTwoHanded"):
        problems.append(f"{definition}: 弓必须标 isTwoHanded，否则可与副手同时装备")
    for key in NUMBERS:
        if key not in row:
            problems.append(f"{definition}: 缺少数值键 {key}")
        elif not isinstance(row[key], (int, float)):
            problems.append(f"{definition}: {key} 必须是数字，实为 {type(row[key]).__name__}")
    for key in VECTORS:
        if key not in row:
            continue
        parts = str(row[key]).split(",")
        if len(parts) != 3:
            problems.append(f'{definition}: {key} 必须是 "x,y,z"，实为 {row[key]!r}')
            continue
        try:
            [float(p) for p in parts]
        except ValueError:
            problems.append(f"{definition}: {key} 含非数字分量：{row[key]!r}")
    for key in OPTIONAL_PATHS:
        if key not in row:
            problems.append(f"{definition}: 缺少资源键 {key}（不用也要留空串）")
        elif row[key]:
            check_asset(definition, key, str(row[key]))

    slots = [s.strip() for s in str(row.get("bow_part_slots", "")).split(",") if s.strip()]
    if not slots:
        problems.append(f"{definition}: 缺 bow_part_slots（至少 riser,string,arrow_rest）")
    for slot in slots:
        present = [key for key in row if key.startswith(f"bow_part_{slot}_")]
        if not present:
            problems.append(f"{definition}: 槽 {slot} 列在 bow_part_slots 里但没有任何 bow_part_{slot}_* 键")
        rods = row.get(f"bow_part_{slot}_rods", 0)
        if not isinstance(rods, int) or rods < 0:
            problems.append(f"{definition}: bow_part_{slot}_rods 必须是非负整数")
            rods = 0
        for suffix in PART_SUFFIXES_PATH:
            key = f"bow_part_{slot}_{suffix}"
            if key not in row:
                problems.append(f"{definition}: 缺 {key}（不用也要留空串）")
            elif row[key]:
                check_asset(definition, key, str(row[key]))
        for suffix in PART_SUFFIXES_NUMBER:
            key = f"bow_part_{slot}_{suffix}"
            if key in row and not isinstance(row[key], (int, float)):
                problems.append(f"{definition}: {key} 必须是数字")
        # 纯程序化槽（有细杆、没网格）与实体槽（有网格）至少得有一个来源。
        if not rods and not row.get(f"bow_part_{slot}_mesh"):
            problems.append(f"{definition}: 槽 {slot} 既无 _rods 也无 _mesh，画不出任何东西")
        if row.get(f"bow_part_{slot}_material") and not row.get(f"bow_part_{slot}_hide_slot"):
            problems.append(f"{definition}: 槽 {slot} 给了替换材质却没给 bow_part_{slot}_hide_slot")
    for required in ("riser", "string", "arrow_rest"):
        if required not in slots:
            problems.append(f"{definition}: bow_part_slots 缺 {required}（弓体／弓弦／弦上箭三件是运行前提）")

    arrow = str(row.get("arrow_ammo", ""))
    if not arrow:
        problems.append(f"{definition}: 缺 arrow_ammo")
    elif arrow not in ammo_ids:
        problems.append(f"{definition}: arrow_ammo={arrow} 不在 ammo_types.json 里")
    for key in ("name", "desc"):
        if not str(row.get(key, "")).strip():
            problems.append(f"{definition}: 缺 {key}")

missing = sorted({"arrow_wood", "arrow_broadhead"} - ammo_ids)
if missing:
    problems.append(f"ammo_types.json 缺箭种：{', '.join(missing)}")

if problems:
    print(" bows.json / ammo_types.json 自检未通过：")
    for line in problems:
        print("  - " + line)
    sys.exit(1)

summary = "; ".join(
    f"{definition}[{', '.join(s.strip() for s in str(row.get('bow_part_slots', '')).split(',') if s.strip())}]"
    for definition, row in sorted(bows.items())
)
print(f" 弓表自检通过：{len(bows)} 把弓，部件槽 {summary}；"
      f"箭种 {sorted(ammo_ids & {'arrow_wood', 'arrow_broadhead'})}")
