"""Compare the rest-pose bone transforms of two viewmodel FBX exports.

Purpose: the pickaxe viewmodel and its five clips reference
`/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Pickaxe_Skeleton`,
which was never saved to disk (the 2026-09-13 importer built it in memory only).
The battle-axe skeleton was persisted on 2026-09-19. Before reusing it we must
prove the two rigs share bone names *and* rest transforms, otherwise the pickaxe
clips would be reinterpreted against a different bind pose.

Read-only: writes a JSON report, never saves a .blend.
"""
import bpy
import json
import os
import sys
import mathutils

EXPORT = r"D:\FPS3D\FPSGAME\SourceAssets\ProductionToolGrip20260913\Export"
OUT = r"D:\FPS3D\FPSGAME\SourceAssets\PickaxeSkeletonRestore20261022\rest_pose_compare.json"


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_fbx(path):
    clear_scene()
    bpy.ops.import_scene.fbx(filepath=path)
    arm = next((o for o in bpy.context.scene.objects if o.type == 'ARMATURE'), None)
    if arm is None:
        raise RuntimeError("no armature in " + path)
    return arm


def collect(arm):
    bones = {}
    for b in arm.data.bones:
        # Rest pose in armature space; independent of any current pose.
        m = b.matrix_local
        bones[b.name] = {
            "head": [round(v, 6) for v in m.translation],
            "parent": b.parent.name if b.parent else None,
            "length": round(b.length, 6),
        }
    return bones


def run():
    report = {"export_dir": EXPORT, "meshes": {}}
    result = {}
    for name in ("SK_Harvest_Axe", "SK_Harvest_Pickaxe"):
        path = os.path.join(EXPORT, name + ".fbx")
        arm = import_fbx(path)
        bones = collect(arm)
        result[name] = bones
        report["meshes"][name] = {
            "armature": arm.name,
            "bone_count": len(bones),
        }

    axe = result["SK_Harvest_Axe"]
    pick = result["SK_Harvest_Pickaxe"]
    common = sorted(set(axe) & set(pick))
    only_axe = sorted(set(axe) - set(pick))
    only_pick = sorted(set(pick) - set(axe))

    deltas = []
    for b in common:
        a, p = axe[b], pick[b]
        d = max(
            abs(a["head"][0] - p["head"][0]),
            abs(a["head"][1] - p["head"][1]),
            abs(a["head"][2] - p["head"][2]),
            abs(a["length"] - p["length"]),
        )
        if a["parent"] != p["parent"]:
            deltas.append({"bone": b, "reason": "parent", "axe": a["parent"], "pick": p["parent"]})
        elif d > 1e-4:
            deltas.append({"bone": b, "reason": "transform", "max_delta": round(d, 6),
                           "axe_head": a["head"], "pick_head": p["head"],
                           "axe_len": a["length"], "pick_len": p["length"]})

    report["compare"] = {
        "common_bones": len(common),
        "only_in_axe": only_axe,
        "only_in_pickaxe": only_pick,
        "differing": deltas,
        "identical": not only_axe and not only_pick and not deltas,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print("WROTE " + OUT)
    print("common=%d only_axe=%d only_pick=%d differing=%d identical=%s" % (
        len(common), len(only_axe), len(only_pick), len(deltas), report["compare"]["identical"]))


run()
