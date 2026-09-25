"""把箭并入既有的\"弹药口径\"：group=arrow，走 PouchCount/SpendAmmo/GrantAmmo。

只追加缺失行，不改动火器弹药的既有数据与顺序。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "Content" / "ColdSteelData" / "ammo_types.json"

ROWS = [
    {
        "id": "arrow_wood",
        "group": "arrow",
        "group_name": "箭",
        "name": "猎箭",
        "tier_name": "绿阶",
        "tier_color": "#4CAA70",
        "description": "白蜡木箭杆、铁片箭头的通用猎箭，弓的消耗品。",
        "icon": "",
        "order": 0,
        "enabled": True,
        "allow_infinite_reserve": True,
        "damage_multiplier": 1.0,
        "physical_armor_penetration": 0.0,
    },
    {
        "id": "arrow_broadhead",
        "group": "arrow",
        "group_name": "箭",
        "name": "破甲锥箭",
        "tier_name": "蓝阶",
        "tier_color": "#4C8FD8",
        "description": "锥形钢镞的重箭，穿透更好，代价是初速更低。",
        "icon": "",
        "order": 1,
        "enabled": True,
        "allow_infinite_reserve": False,
        "damage_multiplier": 1.18,
        "physical_armor_penetration": 0.22,
    },
]


def main() -> int:
    payload = json.loads(PATH.read_text(encoding="utf-8-sig"))
    types = payload.setdefault("types", [])
    known = {row.get("id") for row in types if isinstance(row, dict)}
    added = [row["id"] for row in ROWS if row["id"] not in known]
    if not added:
        print("ammo_types.json: 箭已存在，未改动")
        return 0
    types.extend(row for row in ROWS if row["id"] in added)
    PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ammo_types.json: 追加 {added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
