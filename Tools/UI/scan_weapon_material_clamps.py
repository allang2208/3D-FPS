"""Find weapon material graphs that cannot compile because a clamp input is empty.

The backpack/equipment icon rig renders each weapon with its saved gunsmith parts, and
it refuses to cache an image while any participating material has compiler errors.
One unfinished clamp therefore turned a fully modified AKM/QBZ-191 icon into the plain
catalog image. This scan locates that defect class across the weapon content.

Only materials that actually contain a clamp expression are recompiled, so the sweep
stays cheap and side effect free (no asset is saved here).
"""
import json
from pathlib import Path

import unreal

ROOTS = ["/Game/Weapons"]

CLAMP = "MaterialExpressionClamp"
SAMPLE = "MaterialExpressionTextureSample"

LIB = unreal.MaterialEditingLibrary
REPORT = {"scanned": 0, "with_clamp": 0, "failures": [], "clamp_materials": []}


def material_assets(root):
    names = unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False)
    for name in names:
        asset_class = unreal.EditorAssetLibrary.find_asset_data(name).asset_class_path.asset_name
        if asset_class in ("Material", "MaterialInstanceConstant"):
            yield name


for root in ROOTS:
    for path in material_assets(root):
        material = unreal.load_asset(path)
        if not material:
            continue
        REPORT["scanned"] += 1
        try:
            expressions = LIB.get_material_expressions(material)
        except Exception as exc:  # noqa: BLE001 - report and continue the sweep
            REPORT["failures"].append({"asset": path, "stage": "expressions", "error": str(exc)})
            continue
        clamps = [node for node in expressions if node.get_class().get_name() == CLAMP]
        if not clamps:
            continue
        REPORT["with_clamp"] += 1
        entry = {
            "asset": path,
            "clamps": [node.get_name() for node in clamps],
            "samplers": [
                {
                    "name": node.get_name(),
                    "texture": (node.get_editor_property("texture").get_name()
                                if node.get_editor_property("texture") else None),
                }
                for node in expressions if node.get_class().get_name() == SAMPLE
            ],
        }
        try:
            entry["compile_errors"] = list(LIB.recompile_material(material) or [])
        except Exception as exc:  # noqa: BLE001 - report and continue the sweep
            entry["compile_errors"] = ["err:" + str(exc)]
        REPORT["clamp_materials"].append(entry)
        if entry["compile_errors"]:
            REPORT["failures"].append({"asset": path, "stage": "compile", "error": entry["compile_errors"]})
            unreal.log_error("WEAPON_CLAMP_SCAN broken " + path + " " + "; ".join(entry["compile_errors"]))

output = Path(unreal.Paths.project_saved_dir()) / "QRStockInspect"
output.mkdir(parents=True, exist_ok=True)
(output / "weapon-material-clamp-scan.json").write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
unreal.log("WEAPON_CLAMP_SCAN COMPLETE scanned=%d with_clamp=%d broken=%d"
           % (REPORT["scanned"], REPORT["with_clamp"], len(REPORT["failures"])))
