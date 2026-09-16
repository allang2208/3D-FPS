"""Restore the authored roughness source for weapon materials whose clamp input is empty.

Background: the backpack/equipment icon rig assembles each weapon with its saved gunsmith
parts. It refuses to cache a modified icon while any participating material reports shader
compile errors, so an unfinished clamp silently downgraded a fully modified AKM/QBZ-191 icon
to the plain catalog image.

Every affected material was authored with a roughness clamp between the roughness map and
MP_ROUGHNESS, but the connection into that clamp is missing on disk. The intended source for
each material is recorded in its authoring script:

  SourceAssets/MeshyPerformanceStock20260913/import_assets.py            n('R')      -> clamp
  SourceAssets/CoreStock20260914/import_assets.py                        rough('G')  -> clamp
  SourceAssets/CoreStock20260914/Meshy0914005605/import_assets.py        n('R')      -> clamp
  SourceAssets/ReferenceSkeletonStock5080_20260913/Refined/import_assets.py rough('G') -> clamp
  SourceAssets/StableAntiSlipRearGrip20260913/Selected91727/import_assets.py node('G') -> clamp
  SourceAssets/QBZ19120260912/SurfacePolish/import.py                    add('')     -> clamp

This script only re-establishes those connections; it does not touch textures, clamp ranges,
other properties or mesh/material slot assignments. Assets that still report errors are left
unsaved, so a failed repair changes nothing on disk.
"""
import json
from pathlib import Path

import unreal

CLAMP = "MaterialExpressionClamp"
SAMPLE = "MaterialExpressionTextureSample"

LIB = unreal.MaterialEditingLibrary

RULES = [
    {
        "material": "/Game/Weapons/QRPerformanceStock/Meshy20260913/M_Stock_Rubber",
        "texture_token": "T_Stock_Roughness",
        "channel": "R",
        "note": "qr_performance stock rubber buttpad",
    },
    {
        "material": "/Game/Weapons/CoreStock20260914/M_CoreStock_Rubber",
        "texture_token": "T_CoreStock_MetalRough",
        "channel": "G",
        "note": "core_stock rubber section",
    },
    {
        "material": "/Game/Weapons/CoreStock20260914/Meshy0914005605/M_CoreStock_Rubber",
        "texture_token": "T_CoreStock_Roughness",
        "channel": "R",
        "note": "core_stock rubber section used by the AKM/M4/QBZ-191 meshes",
    },
    {
        "material": "/Game/Weapons/ReferenceStock5080/Refined91379/M_SkeletonStock_Rubber",
        "texture_token": "T_SkeletonStock_MetalRough",
        "channel": "G",
        "note": "skeleton stock rubber section",
    },
    {
        "material": "/Game/Weapons/StableAntiSlipRearGrip/Selected91727/M_StableAntiSlipRearGrip",
        "texture_token": "T_StableAntiSlipRearGrip_MetalRough",
        "channel": "G",
        "prefer_unused": True,
        "note": "stable anti-slip rear grip",
    },
    {
        "material": "/Game/Weapons/QBZ191/SurfacePolish/M_QBZ191_Body_SurfacePolish",
        "node_class": "MaterialExpressionAdd",
        "channel": "",
        "note": "unreferenced QBZ-191 surface-polish experiment",
    },
    {
        "material": "/Game/Weapons/QBZ191/SurfacePolish/M_QBZ191_Irons_SurfacePolish",
        "node_class": "MaterialExpressionAdd",
        "channel": "",
        "note": "unreferenced QBZ-191 surface-polish experiment",
    },
    {
        "material": "/Game/Weapons/QBZ191/SurfacePolish/M_QBZ191_Magazine_SurfacePolish",
        "node_class": "MaterialExpressionAdd",
        "channel": "",
        "note": "unreferenced QBZ-191 surface-polish experiment",
    },
]

PROPERTIES = {
    "base_color": unreal.MaterialProperty.MP_BASE_COLOR,
    "metallic": unreal.MaterialProperty.MP_METALLIC,
    "roughness": unreal.MaterialProperty.MP_ROUGHNESS,
    "normal": unreal.MaterialProperty.MP_NORMAL,
    "ambient_occlusion": unreal.MaterialProperty.MP_AMBIENT_OCCLUSION,
    "emissive_color": unreal.MaterialProperty.MP_EMISSIVE_COLOR,
    "opacity": unreal.MaterialProperty.MP_OPACITY,
}

REPORT = {"repaired": [], "skipped": [], "failed": []}


def connected_nodes(material):
    used = set()
    for prop in PROPERTIES.values():
        try:
            node = LIB.get_material_property_input_node(material, prop)
        except Exception:  # noqa: BLE001 - unsupported property on this material
            continue
        if node:
            used.add(node.get_name())
    return used


def resolve_source(material, rule, used, clamp):
    if "node_class" in rule:
        for node in LIB.get_material_expressions(material):
            if node.get_class().get_name() == rule["node_class"] and node.get_name() != clamp.get_name():
                return node, rule["channel"]
        return None, None
    candidates = []
    for node in LIB.get_material_expressions(material):
        if node.get_class().get_name() != SAMPLE:
            continue
        texture = node.get_editor_property("texture")
        if texture and rule["texture_token"] in texture.get_name():
            candidates.append(node)
    if not candidates:
        return None, None
    if rule.get("prefer_unused"):
        unused = [node for node in candidates if node.get_name() not in used]
        if unused:
            return unused[0], rule["channel"]
    return candidates[0], rule["channel"]


for rule in RULES:
    path = rule["material"]
    material = unreal.load_asset(path)
    if not material:
        REPORT["failed"].append({"material": path, "error": "asset missing"})
        unreal.log_error("WEAPON_CLAMP_FIX missing " + path)
        continue

    existing_errors = list(LIB.recompile_material(material) or [])
    if not existing_errors:
        REPORT["skipped"].append({"material": path, "reason": "already compiles"})
        unreal.log("WEAPON_CLAMP_FIX skip (already compiles) " + path)
        continue

    clamp = None
    try:
        clamp = LIB.get_material_property_input_node(material, unreal.MaterialProperty.MP_ROUGHNESS)
    except Exception as exc:  # noqa: BLE001 - reported below
        REPORT["failed"].append({"material": path, "error": "roughness lookup: " + str(exc)})
        continue
    if not clamp or clamp.get_class().get_name() != CLAMP:
        REPORT["failed"].append({
            "material": path,
            "error": "no clamp feeding roughness",
            "errors": existing_errors,
        })
        unreal.log_error("WEAPON_CLAMP_FIX unexpected graph " + path)
        continue

    source, channel = resolve_source(material, rule, connected_nodes(material), clamp)
    if not source:
        REPORT["failed"].append({"material": path, "error": "roughness source not found", "errors": existing_errors})
        unreal.log_error("WEAPON_CLAMP_FIX source missing " + path)
        continue

    linked = LIB.connect_material_expressions(source, channel, clamp, "Input")
    if not linked:
        linked = LIB.connect_material_expressions(source, channel, clamp, "")
    if not linked:
        REPORT["failed"].append({"material": path, "error": "connect refused", "errors": existing_errors})
        unreal.log_error("WEAPON_CLAMP_FIX connect refused " + path)
        continue

    remaining = list(LIB.recompile_material(material) or [])
    entry = {
        "material": path,
        "source": source.get_name(),
        "channel": channel,
        "note": rule["note"],
        "errors_before": existing_errors,
        "errors_after": remaining,
    }
    if remaining:
        REPORT["failed"].append(entry)
        unreal.log_error("WEAPON_CLAMP_FIX still broken %s %s" % (path, "; ".join(remaining)))
        continue

    builtin = unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    entry["saved"] = bool(builtin)
    if not builtin:
        REPORT["failed"].append({"material": path, "error": "save failed"})
        unreal.log_error("WEAPON_CLAMP_FIX save failed " + path)
        continue
    REPORT["repaired"].append(entry)
    unreal.log("WEAPON_CLAMP_FIX repaired %s <- %s[%s]" % (path, entry["source"], channel))

output = Path(unreal.Paths.project_saved_dir()) / "BackpackIconModFix20260916"
output.mkdir(parents=True, exist_ok=True)
(output / "repair-report.json").write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
unreal.log("WEAPON_CLAMP_FIX COMPLETE repaired=%d skipped=%d failed=%d"
           % (len(REPORT["repaired"]), len(REPORT["skipped"]), len(REPORT["failed"])))
