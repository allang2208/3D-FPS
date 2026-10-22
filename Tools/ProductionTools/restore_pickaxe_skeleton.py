"""Restore the missing pickaxe viewmodel skeleton package.

Background
----------
The 2026-09-13 grip-motion import saved 15 packages but never saved a Skeleton
package for either tool. On 2026-09-19 the battle-axe skeleton was persisted as a
side effect of re-importing the axe mesh; the pickaxe half was left broken.

Consequence: `SK_Harvest_Pickaxe` and its five clips still carry an import-table
dependency on

    /Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Pickaxe_Skeleton

which does not exist. Cook reports the missing package six times and then asserts
in `AnimSequence.cpp:2172` (`!Hash.IsZero()`), exiting with code 25.

Why duplication and not a re-import
-----------------------------------
`compare_rest_pose.py` (this folder) imported both viewmodel FBX exports into
Blender and compared every bone: 100 common bones, 0 only-in-axe, 0 only-in-pickaxe,
0 differing rest transforms, parents identical. The two rigs are the same rig.

So the fix is to materialise the same skeleton at the missing path. That restores
the dangling reference without touching any of:

  * `SK_Harvest_Pickaxe` (mesh) and its bind pose / materials / weights
  * the five `A_Harvest_Pickaxe_*` clips and their timing
  * `production_tools.json`, C++ or any config

Duplicating the axe skeleton asset copies its bone tree verbatim, which is exactly
the rig the pickaxe clips were authored against.

This script is read-mostly: it creates and saves ONE new package, then reads the
result back in the same process. Per project workflow the readback must also be
repeated in a fresh process; that is done by a separate run.
"""

import json
import os

import unreal

GAME_DIR = "D:/FPS3D/FPSGAME"
OUT_DIR = GAME_DIR + "/SourceAssets/PickaxeSkeletonRestore20261022"

FOLDER = "/Game/Items/ProductionTools/GripMotion20260913"
SOURCE_SKELETON = FOLDER + "/SK_Harvest_Axe_Skeleton.SK_Harvest_Axe_Skeleton"
TARGET_SKELETON = FOLDER + "/SK_Harvest_Pickaxe_Skeleton.SK_Harvest_Pickaxe_Skeleton"
TARGET_SKELETON_PACKAGE = TARGET_SKELETON.split(".")[0]

PICKAXE_MESH = FOLDER + "/SK_Harvest_Pickaxe.SK_Harvest_Pickaxe"
PICKAXE_CLIPS = [
    FOLDER + "/A_Harvest_Pickaxe_Idle.A_Harvest_Pickaxe_Idle",
    FOLDER + "/A_Harvest_Pickaxe_Walk.A_Harvest_Pickaxe_Walk",
    FOLDER + "/A_Harvest_Pickaxe_Equip.A_Harvest_Pickaxe_Equip",
    FOLDER + "/A_Harvest_Pickaxe_Swing.A_Harvest_Pickaxe_Swing",
    FOLDER + "/A_Harvest_Pickaxe_HitRecover.A_Harvest_Pickaxe_HitRecover",
]

EAL = unreal.EditorAssetLibrary
report = {"stage": "start", "created": False, "errors": []}


def note(key, value):
    report[key] = value


def log(msg):
    unreal.log("[PickaxeSkeleton] " + msg)


def bone_names(skel):
    """Bone identifiers available through UE Python.

    `BoneNode` exposes no readable `name` (`to_dict()`/`to_tuple()` are empty and
    `name` is protected; `export_text()` emits only the retargeting mode). So we
    use the name table embedded in the saved package, which is the same source the
    engine resolves bones from. Cleaned up in the fresh-readback script.
    """
    import re
    path = GAME_DIR + "/Content/Items/ProductionTools/GripMotion20260913/" \
           + skel.get_name() + ".uasset"
    with open(path, "rb") as fh:
        blob = fh.read()
    pattern = re.compile(
        rb"(?:clavicle|upperarm|lowerarm|hand|index|middle|ring|pinky|thumb|spine|neck|"
        rb"head|pelvis|root|thigh|calf|foot|ball|ik_|VM_|WPN_)[A-Za-z0-9_]*")
    return sorted({m.group(0).decode("latin1") for m in pattern.finditer(blob)})


def describe_skeleton(skel):
    """Bone count from the live object plus a name fingerprint from its package."""
    if not skel:
        return None
    info = {"tree_nodes": len(skel.get_editor_property("bone_tree"))}
    try:
        names = bone_names(skel)
        info.update({"names": len(names), "first": names[:3], "last": names[-3:]})
    except Exception as exc:  # noqa: BLE001 - diagnostics only
        info["names_error"] = str(exc)[:200]
    return info


def exists(path):
    try:
        return bool(EAL.does_asset_exist(path))
    except Exception:  # noqa: BLE001
        return False


try:
    # ---------------------------------------------------------------- preflight
    report["before"] = {
        "source_exists": exists(SOURCE_SKELETON),
        "target_exists": exists(TARGET_SKELETON),
    }
    if not report["before"]["source_exists"]:
        raise RuntimeError("source axe skeleton is missing; refusing to fabricate one")
    if report["before"]["target_exists"]:
        raise RuntimeError("target already exists; this script never overwrites")

    source = unreal.load_asset(SOURCE_SKELETON)
    if not source:
        raise RuntimeError("cannot load " + SOURCE_SKELETON)
    report["source_skeleton"] = describe_skeleton(source)
    report["source_class"] = source.get_class().get_name()
    source_names = bone_names(source)

    # ------------------------------------------------------------------ create
    log("duplicating %s -> %s" % (SOURCE_SKELETON, TARGET_SKELETON_PACKAGE))
    duplicated = EAL.duplicate_asset(SOURCE_SKELETON, TARGET_SKELETON_PACKAGE)
    if not duplicated:
        raise RuntimeError("duplicate_asset returned nothing for the skeleton")
    report["created_object"] = duplicated.get_path_name()

    if not EAL.save_asset(TARGET_SKELETON_PACKAGE, only_if_is_dirty=False):
        raise RuntimeError("save_asset failed for " + TARGET_SKELETON_PACKAGE)
    report["created"] = True
    report["stage"] = "saved"

    # ---------------------------------------------------------------- readback
    # Drop the in-memory copy so the reload comes from the saved package.
    unreal.SystemLibrary.unload_primary_asset(TARGET_SKELETON)
    restored = unreal.load_asset(TARGET_SKELETON)
    if not restored:
        raise RuntimeError("saved skeleton did not load back")
    report["restored_skeleton"] = describe_skeleton(restored)
    restored_names = bone_names(restored)
    report["restored_matches_source"] = (restored_names == source_names)
    if not report["restored_matches_source"]:
        report["errors"].append("restored bone name set differs from the source axe skeleton")

    # Does the mesh now resolve its previously dangling reference?
    mesh = unreal.load_asset(PICKAXE_MESH)
    if not mesh:
        raise RuntimeError("cannot load " + PICKAXE_MESH)
    mesh_skeleton = mesh.get_editor_property("skeleton")
    report["mesh"] = {
        "asset": PICKAXE_MESH,
        "skeleton": mesh_skeleton.get_path_name() if mesh_skeleton else None,
    }

    clips = {}
    for clip_path in PICKAXE_CLIPS:
        clip = unreal.load_asset(clip_path)
        entry = {"loaded": bool(clip)}
        if clip:
            clip_skeleton = clip.get_editor_property("skeleton")
            entry["skeleton"] = clip_skeleton.get_path_name() if clip_skeleton else None
            try:
                entry["length"] = round(float(clip.get_editor_property("sequence_length")), 6)
            except Exception:  # noqa: BLE001
                entry["length"] = None
        clips[clip_path.rsplit("/", 1)[-1].split(".")[0]] = entry
    report["clips"] = clips

    unresolved = [n for n, c in clips.items() if not c.get("skeleton")]
    if unresolved:
        report["errors"].append("clips still without skeleton: " + ", ".join(unresolved))
    if not report["mesh"]["skeleton"]:
        report["errors"].append("pickaxe mesh still has no skeleton")

    report["stage"] = "verified" if not report["errors"] else "verified_with_errors"

except Exception as exc:  # noqa: BLE001 - the receipt must record the failure
    report["errors"].append("%s: %s" % (type(exc).__name__, exc))
    report["stage"] = "failed"

os.makedirs(OUT_DIR, exist_ok=True)
with open(OUT_DIR + "/restore_receipt.json", "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)

log("stage=%s created=%s errors=%s" % (report["stage"], report["created"], report["errors"]))
print("PICKAXE_SKELETON_STAGE=" + report["stage"])
print("PICKAXE_SKELETON_CREATED=%s" % report["created"])
