# -*- coding: utf-8 -*-
"""一次性生成器：把旧 dungeon-event-definitions.js 的 63 个事件 buff 目录
（源：source-inventory-1.md §1D）落为 UE 数据通道：
 1) Content/ColdSteelData/dungeon_event_buffs.json —— 事件系统施加用的权威参数；
 2) status_effects.json 增补同名 tile 条目（emoji 占位图标，按用户规则不出美术）。
运行后可归档。"""
import json, io, os, re

ROOT = r"D:\FPS3D\FPSGAME\Content\ColdSteelData"
ROWS = """foremanDebtMark\t工头债印\t📒\t#7a5a3a\tmatk -15%\tfail
minersGratitude\t矿工谢意\t⛏\t#c6a56b\tdef +10%\tsuccess
minersCadence\t掘进节拍\t⚙️\t#b48a5a\tatk +10%, 移速 +10%\tsuccess
deepShaftEcho\t深井回声\t🕳️\t#52515f\tdef -15%\tfail
reedLament\t芦苇哀鸣\t🌾\t#8b9670\t移速 -15%\tfail
bogHunterInstinct\t沼猎直觉\t🏹\t#a59a62\tatk +10%, 移速 +10%\tsuccess
hunterBurden\t猎手重负\t🦴\t#786b55\tdef -10%, 移速 -10%\tfail
druidShelter\t林神庇护\t🌿\t#65a86f\tdef +10%\tsuccess
swampWhisper\t沼语侵扰\t🌀\t#63745b\tmatk -10%\tfail
wildSap\t野性树液\t🍂\t#91a34f\tatk +10%\tsuccess
marshGasNumbness\t沼气麻痹\t☁️\t#9a9b45\t移速 -20%\tfail
livingRootWard\t活根护符\t🌱\t#6f9550\tdef +15%, matk +10%\tsuccess
blackwaterChill\t黑水寒意\t🕯️\t#55777c\tatk -10%, matk -10%\tfail
waterloggedArmor\t浸水护甲\t💧\t#4c6f78\tdef -15%, 移速 -10%\tfail
graveMurmur\t墓洲低语\t🪦\t#7d8862\tmatk -10%\tfail
frogBoneCurse\t蛙骨诅咒\t🦴\t#7f8b56\tdef -10%\tfail
witchDistillate\t女巫馏液\t⚗️\t#8d75a6\tmatk +15%\tsuccess
bogWitchTonic\t沼巫强壮剂\t🥄\t#778f5a\tatk +10%, def +10%\tsuccess
failedWitchBrew\t失败药剂\t🧪\t#66576f\tdef -15%, 移速 -15%\tfail
crocodileHideWard\t鳄神厚皮\t🐊\t#536d4f\tdef +15%\tsuccess
ancientSpell\t古代咒语\t🔮\t#8a7aff\tmatk +25%\tsuccess
bloodFury\t血怒\t🩸\t#aa3333\tatk +20%\tsuccess
cursedArmorShell\t诅咒板甲\t🛡️\t#7a7a7a\tdef +20%\tsuccess
armorCurse\t板甲诅咒\t💀\t#5a5a5a\tdef -20%\tfail
steadyMind\t稳定心神\t🍃\t#7abaff\t移速 +15%\tsuccess
madVision\t疯狂幻象\t👁️\t#8a5a9a\t移速 -25%\tfail
corpseWaxSeal\t尸蜡封层\t🕯️\t#c8b997\tdef +15%\tsuccess
waxStiffness\t尸蜡僵结\t🕯️\t#81745f\t移速 -20%\tfail
funeralTempo\t送葬节拍\t🎼\t#9aa7b5\tatk +20%, matk +20%\tsuccess
discordantEcho\t失谐回声\t🎵\t#746879\tmatk -20%\tfail
plagueAntiserum\t净化血清\t🧬\t#78a995\tdef +20%\tsuccess
plagueExposure\t瘟疫暴露\t☣️\t#76834f\tatk -20%, def -20%, 移速 -15%\tfail
frostDisorientation\t霜途迷向\t🧭\t#8aa8ba\t移速 -15%\tfail
iceBridgePoise\t冰桥定势\t🧊\t#83b4ca\tdef +15%, 移速 +15%\tsuccess
iceBridgeNumbness\t寒桥麻木\t🥶\t#6d91a8\t移速 -15%\tfail
iceBridgeDetourChill\t绕路失温\t🥶\t#6d91a8\t移速 -10%\tfail
frostberryVigor\t霜莓活力\t🫐\t#668bb5\tdef +15%\tsuccess
frostberryChill\t霜莓寒毒\t🫐\t#526b92\t移速 -15%\tfail
whiteStagStride\t白鹿轻步\t🦌\t#b7d7e4\t移速 +20%\tsuccess
whiteStagMercy\t白鹿善意\t🦌\t#b7d7e4\tdef +10%, 移速 +10%\tsuccess
auroraCadence\t极光律动\t🌌\t#77c6d7\tmatk +15%, 移速 +15%\tsuccess
auroraFrostbite\t极光冻伤\t💠\t#7199b8\t移速 -15%\tfail
shroudedAurora\t极光残扰\t🌌\t#718da9\tmatk -10%\tfail
avalancheBrace\t抗崩架势\t🏔️\t#879ba7\tdef +20%\tsuccess
crevasseWhispers\t冰隙低语\t🗣️\t#7796aa\tmatk -15%, 移速 -15%\tfail
glacierLungs\t冰川吐息\t🌬️\t#6fa0bd\tdef +20%\tsuccess
crevasseNumbness\t冰隙失温\t🥶\t#63869c\t移速 -20%\tfail
crevasseDetourNumbness\t冰隙寒侵\t🌬️\t#63869c\t移速 -15%\tfail
frozenSanctuary\t寒堂圣佑\t❄️\t#b7dce8\tdef +20%, matk +20%\tsuccess
rejectedPrayer\t冰堂拒斥\t🕯️\t#778ca0\tmatk -20%\tfail
reliquaryBurden\t圣匣重压\t⛓️\t#70889a\t移速 -20%\tfail
drenchedInIcewater\t冰水浸身\t💧\t#557f9a\t移速 -20%\tfail
signalFlamePace\t烽火引路\t🔥\t#d7a76b\t移速 +20%\tsuccess
blizzardFireguard\t暴雪火卫\t🔥\t#cb8e64\tdef +20%\tsuccess
shutterBruise\t风板挫伤\t🌀\t#6e8798\tatk -15%, 移速 -15%\tfail
frostSpiritMark\t寒灵印记\t👻\t#75b9d2\tmatk +20%\tsuccess
frostSpiritRage\t寒灵震慑\t👻\t#637e9b\tmatk -20%\tfail
crystalBackflow\t寒晶逆流\t💎\t#658da7\tatk -20%, def -20%\tfail
frostSpiritRejection\t寒灵拒斥\t👻\t#637e9b\tmatk -15%\tfail
auroraOmen\t极光战兆\t🌠\t#8cc8d8\tatk +20%, matk +20%\tsuccess
falseOmen\t伪星兆\t🌑\t#686f91\tatk -20%, matk -20%\tfail
starfallFracture\t坠星震裂\t☄️\t#747fa0\tdef -20%\tfail
observatoryFrostFracture\t星镜霜裂\t☄️\t#747fa0\tdef -15%\tfail"""

STAT = {"atk": "atkPercent", "matk": "matkPercent", "def": "defPercent", "移速": "moveSpeedPercent"}
buffs, seen = {}, set()
for line in ROWS.splitlines():
    bid, name, icon, color, nums, trig = line.split("\t")
    assert bid not in seen, f"dup id {bid}"
    seen.add(bid)
    fx = {}
    for part in nums.split(","):
        stat, pct = part.strip().split()
        fx[STAT[stat]] = float(pct.rstrip("%"))
    label = "、".join(f"{s}{'+' if v >= 0 else ''}{int(v)}%" for s, v in
                    ((k.replace("Percent", "").replace("moveSpeed", "移速"), v) for k, v in fx.items()))
    kind = "增益" if trig == "success" else "减益"
    buffs[bid] = {"name": name, "icon": icon, "color": color, "trigger": trig, "battles": 3, "effects": fx}
    buffs[bid]["_desc"] = f"地牢事件{kind}：{label}；按战斗场次消耗（默认3场）。"
assert len(buffs) == 63, len(buffs)

# 1) 事件参数目录
with io.open(os.path.join(ROOT, "dungeon_event_buffs.json"), "w", encoding="utf-8") as f:
    json.dump({k: {kk: vv for kk, vv in v.items() if kk != "_desc"} for k, v in buffs.items()},
              f, ensure_ascii=False, indent=2)
    f.write("\n")

# 2) 状态栏目录增补（保留既有条目与字段序）
path = os.path.join(ROOT, "status_effects.json")
with io.open(path, encoding="utf-8") as f:
    doc = json.load(f)
existing = {e["type"] for e in doc["effects"]}
added = 0
for bid, v in buffs.items():
    if bid in existing:
        continue
    doc["effects"].append({"type": bid, "icon": v["icon"], "name": v["name"],
                           "color": v["color"], "description": v["_desc"]})
    added += 1
with io.open(path, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"entries added={added}, total={len(doc['effects'])}, types_unique={len({e['type'] for e in doc['effects']})}")
