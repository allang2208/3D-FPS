"""Read material instance texture parameters properly."""
import json

import unreal

BASE = "/Game/Props/CyberpunkApartment20261020/CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_mi_report.json"

out = {"single": [], "params": [], "errors": []}
eal = unreal.EditorAssetLibrary
E = unreal.MaterialEditingLibrary

try:
    for p in sorted(eal.list_assets(BASE + "/Materials", recursive=False,
                                                        include_folder=False)):
        short = p.split("/")[-1].split(".")[0]
        m = eal.load_asset(p)
        entry = {"name": short, "class": m.get_class().get_name(), "parent": None,
                 "textures": [], "scalars": []}
        if isinstance(m, unreal.MaterialInstanceConstant):
            try:
                entry["parent"] = m.get_editor_property("parent").get_name()
            except Exception:
                pass
            try:
                for inf in m.get_editor_property("texture_parameter_values"):
                    entry["textures"].append({
                        "name": str(inf.get_editor_property("parameter_info").get_editor_property("name")),
                        "value": str(inf.get_editor_property("parameter_value").get_name())
                        if inf.get_editor_property("parameter_value") else None})
            except Exception as e:
                entry["tex_err"] = str(e)
            try:
                for inf in m.get_editor_property("scalar_parameter_values"):
                    entry["scalars"].append({
                        "name": str(inf.get_editor_property("parameter_info").get_editor_property("name")),
                        "value": inf.get_editor_property("parameter_value")})
            except Exception as e:
                entry["sc_err"] = str(e)
        out["params"].append(entry)
except Exception as exc:  # noqa: BLE001
    out["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("MI_REPORT_WRITTEN")