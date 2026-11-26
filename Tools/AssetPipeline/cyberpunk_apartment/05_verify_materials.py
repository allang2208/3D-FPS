"""Verify glTF materials kept their textures, using the asset registry."""
import json

import unreal

BASE = "/Game/Props/CyberpunkApartment20261020/CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_material_report.json"

out = {"materials": [], "with_tex": 0, "without_tex": [], "errors": []}

try:
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    mat_dir = unreal.Name(BASE + "/Materials")
    opts = unreal.AssetRegistryDependencyOptions(
        include_soft_package_references=False,
        include_hard_package_references=True,
        include_searchable_names=False,
        include_soft_management_references=False,
        include_hard_management_references=False)

    for p in sorted(unreal.EditorAssetLibrary.list_assets(
            BASE + "/Materials", recursive=False, include_folder=False)):
        short = p.split("/")[-1].split(".")[0]
        try:
            deps = ar.get_dependencies(unreal.Name(short), mat_dir, opts)
            tex = [str(d).split(".")[-1] for d in deps if "Texture" in str(d) or "_alb" in str(d) or "_nrm" in str(d)]
        except Exception:
            tex = []
        entry = {"name": short, "textures": tex}
        out["materials"].append(entry)
        if tex:
            out["with_tex"] += 1
        else:
            out["without_tex"].append(short)
except Exception as exc:  # noqa: BLE001
    out["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("MATERIAL_REPORT_WRITTEN")