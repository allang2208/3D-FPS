"""Publish the same special muzzle option for the three sniper rifle definitions."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def publish(catalog):
    weapons = {row["id"]: row for row in catalog["weapons"]}
    factory = next(opt for opt in weapons["ue_m24"]["options"]["muzzle"]
                   if opt["id"] == "m24_factory_suppressor")
    option = copy.deepcopy(factory)
    option.update(id="sniper_zhiming", name="止鸣",
                  description="哑黑筒身两端饰有宽环带，双斜杠引出一道暗金声纹，收在镂空的紫芯菱标上。")
    option["stats"].update(crit_damage_bonus=.15, critical_stun_seconds=.25)
    option["effects"].insert(0, {"text": "暴击伤害+15%", "benefit": 1})
    option["special_effects"].append("止鸣｜子弹暴击命中时，使目标眩晕0.25秒。")
    for weapon_id in ("ue_m24", "ue_svd", "ue_svch"):
        options = weapons[weapon_id]["options"]["muzzle"]
        for index, current in enumerate(options):
            if current["id"] == option["id"]:
                options[index]=copy.deepcopy(option)
                break
        else:
            options.append(copy.deepcopy(option))


if __name__ == "__main__":
    path = ROOT / "Content/ColdSteelData/gunsmith.json"
    prior = path.read_bytes()
    data = json.loads(prior)
    publish(data)
    result = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
    if b"\r\n" in prior:
        result = result.replace(b"\n", b"\r\n")
    if prior != result:
        if path.read_bytes() != prior:
            raise RuntimeError("Catalog changed during publication")
        path.write_bytes(result)
