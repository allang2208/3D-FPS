"""Copy only missing Epic template animation sources; never replace project assets.

Run with CPython before import_manny_assets.py. Source is the locally installed
UE 5.8 template, under its existing Unreal Engine license. Binary assets stay local.
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(r"E:\Program Files (x86)\UE_5.8\Templates\TemplateResources\High\Characters\Content\Mannequins\Anims")
DEST = ROOT / "Content/Characters/Mannequins/Anims"
DIRECTIONS = ["Fwd", "Fwd_Right", "Right", "Bwd_Right", "Bwd", "Bwd_Left", "Left", "Fwd_Left"]
clips = {}
for family in ("Unarmed", "Rifle", "Pistol"):
    clips[f"{family}.Idle"] = f"{family}/MM_Idle" if family == "Unarmed" else f"{family}/MF_{family}_Idle_ADS"
    for speed in ("Walk", "Jog"):
        for direction in DIRECTIONS:
            clips[f"{family}.{speed}.{direction}"] = f"{family}/{speed}/MF_{family}_{speed}_{direction}"
    if family != "Unarmed":
        for action in ("Reload", "Equip"):
            clips[f"{family}.{action}"] = f"{family}/MM_{family}_{action}"
clips.update({"Jump": "Unarmed/Jump/MM_Jump", "Fall": "Unarmed/Jump/MM_Fall_Loop", "Land": "Unarmed/Jump/MM_Land", "Dead": "Death/MM_Death_Front_01"})
copied = []
for name in clips.values():
    source = SOURCE / (name + ".uasset")
    target = DEST / (name + ".uasset")
    if not source.is_file():
        raise FileNotFoundError(source)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(str(target.relative_to(ROOT)))

config = {
    "version": 1,
    "body_mesh": "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple",
    "clips": {key: "/Game/Characters/Mannequins/Anims/" + value + "." + Path(value).name for key, value in clips.items()},
    "outfits": {},
}
config_path = ROOT / "Content/ColdSteelData/player_body.json"
if not config_path.exists():
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
output = ROOT / "SourceAssets/PlayerBody20260921"
output.mkdir(parents=True, exist_ok=True)
(output / "template_sources.json").write_text(json.dumps({"source": str(SOURCE), "license": "Epic Unreal Engine template content; no raw asset redistribution", "clips": clips, "copied": copied}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"copied": len(copied), "clips": len(clips), "configuration": str(config_path)}))
