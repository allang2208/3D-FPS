"""Read author FBX/glTF skeletons and action names in background Blender.

This catalogs downloaded candidates only. It does not render, retarget, or
publish animations to the UE runtime.
"""
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "SourceAssets/ThirdPersonSwordFree20261005"
SOURCES = {
    "Kevin_Attack2H": OUT / "Kevin/Animations/Male/Combat/2H/HumanM@Attack2H01.fbx",
    "Kevin_CombatIdle2H": OUT / "Kevin/Animations/Male/Combat/2H/HumanM@CombatIdle2H01.fbx",
    "KayKit_Medium_Melee": OUT / "KayKit/KayKit_Character_Animations_1.1/Animations/gltf/Rig_Medium/Rig_Medium_CombatMelee.glb",
}


def curves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


result = {}
for key, source in SOURCES.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if source.suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(source))
    else:
        bpy.ops.import_scene.gltf(filepath=str(source))
    rigs = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
    result[key] = {
        "source": str(source.relative_to(ROOT)),
        "fps": fps,
        "rigs": [{"name": o.name, "bones": [
            {"name": b.name, "parent": b.parent.name if b.parent else None}
            for b in o.data.bones]} for o in rigs],
        "actions": [{"name": a.name, "frame_range": list(a.frame_range),
                     "duration": (a.frame_range[1] - a.frame_range[0]) / fps,
                     "animated_paths": sorted({f.data_path for f in curves(a)})}
                    for a in bpy.data.actions],
    }

(OUT / "skeleton-action-catalog.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for key, row in result.items():
    print("FREE_SWORD_SOURCE", key,
          "bones", [len(r["bones"]) for r in row["rigs"]],
          "actions", [(a["name"], round(a["duration"], 3)) for a in row["actions"]])
