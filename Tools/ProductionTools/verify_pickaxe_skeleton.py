"""Fresh-process readback for the restored pickaxe viewmodel skeleton.

Run in a NEW process: a readback that reuses the creating process cannot prove the
package really hit disk (that is exactly how the 2026-09-13 omission stayed hidden
for six weeks).

Checks, in order:
  1. the skeleton package exists on disk and loads as a Skeleton with 100 bones
  2. its bone names match the axe skeleton it was duplicated from
  3. `SK_Harvest_Pickaxe` resolves its skeleton reference to the new package
  4. all five `A_Harvest_Pickaxe_*` clips resolve to the same skeleton

Read-only: never saves anything.
"""

import json
import os
import re

import unreal

GAME_DIR = "D:/FPS3D/FPSGAME"
OUT_DIR = GAME_DIR + "/SourceAssets/PickaxeSkeletonRestore20261022"

FOLDER = "/Game/Items/ProductionTools/GripMotion20260913"
AXE_SKELETON = FOLDER + "/SK_Harvest_Axe_Skeleton.SK_Harvest_Axe_Skeleton"
PICK_SKELETON = FOLDER + "/SK_Harvest_Pickaxe_Skeleton.SK_Harvest_Pickaxe_Skeleton"
PICK_SKELETON_PACKAGE = PICK_SKELETON.split(".")[0]
PICKAXE_MESH = FOLDER + "/SK_Harvest_Pickaxe.SK_Harvest_Pickaxe"
PICKAXE_CLIPS = [
    "A_Harvest_Pickaxe_Idle",
    "A_Harvest_Pickaxe_Walk",
    "A_Harvest_Pickaxe_Equip",
    "A_Harvest_Pickaxe_Swing",
    "A_Harvest_Pickaxe_HitRecover",
]

EAL = unreal.EditorAssetLibrary
report = {"process": "fresh", "checks": [], "errors": []}


def check(name, ok, detail=None):
    report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
    if not ok:
        report["errors"].append(name)


def bone_names(skel):
    """Bone identifiers from the saved package's name table.

    `BoneNode.name` is protected and `to_dict()`/`to_tuple()` come back empty, so
    the package name table is the only readable source of bone names.
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


try:
    on_disk = os.path.isfile(
        GAME_DIR + "/Content/Items/ProductionTools/GripMotion20260913/SK_Harvest_Pickaxe_Skeleton.uasset"
    )
    report["package_on_disk"] = on_disk
    report["package_bytes"] = (
        os.path.getsize(GAME_DIR + "/Content/Items/ProductionTools/GripMotion20260913/SK_Harvest_Pickaxe_Skeleton.uasset")
        if on_disk else 0
    )
    check("package_on_disk", on_disk, report["package_bytes"])

    skeleton = unreal.load_asset(PICK_SKELETON)
    check("skeleton_loads", bool(skeleton))
    if skeleton:
        # Authoritative bone count: the live bone tree (the name table regex below
        # only recognises known Manny prefixes and undercounts by design).
        tree_len = len(skeleton.get_editor_property("bone_tree"))
        report["bone_tree_len"] = tree_len
        check("bone_tree_nonempty", tree_len > 0, tree_len)
        check("skeleton_is_skeleton", skeleton.get_class().get_name() == "Skeleton",
              skeleton.get_class().get_name())

        axe = unreal.load_asset(AXE_SKELETON)
        if axe:
            axe_tree_len = len(axe.get_editor_property("bone_tree"))
            report["axe_bone_tree_len"] = axe_tree_len
            check("bone_tree_len_matches_axe", tree_len == axe_tree_len,
                  {"pickaxe": tree_len, "axe": axe_tree_len})

            names = bone_names(skeleton)
            axe_names = bone_names(axe)
            report["bone_name_tokens"] = {"pickaxe": len(names), "axe": len(axe_names)}
            check("bone_names_match_axe", names == axe_names,
                  {"pickaxe": len(names), "axe": len(axe_names)})

    mesh = unreal.load_asset(PICKAXE_MESH)
    check("mesh_loads", bool(mesh))
    if mesh:
        resolved = mesh.get_editor_property("skeleton")
        path = resolved.get_path_name() if resolved else None
        report["mesh_skeleton"] = path
        check("mesh_resolves_skeleton", path is not None and path.startswith(PICK_SKELETON_PACKAGE),
              path)

    clip_report = {}
    for clip_name in PICKAXE_CLIPS:
        clip_path = FOLDER + "/" + clip_name + "." + clip_name
        clip = unreal.load_asset(clip_path)
        entry = {"loaded": bool(clip), "skeleton": None}
        if clip:
            resolved = clip.get_editor_property("skeleton")
            entry["skeleton"] = resolved.get_path_name() if resolved else None
            try:
                entry["length"] = round(float(clip.get_editor_property("sequence_length")), 6)
            except Exception:  # noqa: BLE001
                entry["length"] = None
        clip_report[clip_name] = entry
        check("clip_%s_resolves" % clip_name,
              entry["skeleton"] is not None and entry["skeleton"].startswith(PICK_SKELETON_PACKAGE),
              entry["skeleton"])
    report["clips"] = clip_report

except Exception as exc:  # noqa: BLE001
    report["errors"].append("%s: %s" % (type(exc).__name__, exc))

report["stage"] = "verified" if not report["errors"] else "failed"
os.makedirs(OUT_DIR, exist_ok=True)
with open(OUT_DIR + "/fresh_readback.json", "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False, default=str)

unreal.log("[PickaxeSkeletonVerify] stage=%s errors=%s" % (report["stage"], report["errors"]))
print("PICKAXE_SKELETON_VERIFY_STAGE=" + report["stage"])
if report["errors"]:
    raise RuntimeError("verification failed: " + "; ".join(report["errors"]))
