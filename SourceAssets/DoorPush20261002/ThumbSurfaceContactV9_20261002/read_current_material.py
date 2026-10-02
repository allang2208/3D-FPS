"""Read only the material inputs needed to author the existing M16 thumb surface."""
from pathlib import Path
import json
import unreal as u

HERE = Path(__file__).resolve().parent
MESH = "/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny.SK_M16_Manny"
mesh = u.load_asset(MESH)
if mesh is None:
    raise RuntimeError("Current M16 mesh not available")
results = []
for index, slot in enumerate(mesh.get_editor_property("materials")):
    material = slot.material_interface
    row = {"slot": index, "slot_name": str(slot.material_slot_name),
           "material": material.get_path_name() if material else None}
    current = material
    chain = []
    while isinstance(current, u.MaterialInstanceConstant):
        entry = {"path": current.get_path_name(), "textures": {}, "scalars": {}}
        for value in current.get_editor_property("texture_parameter_values"):
            texture = value.parameter_value
            entry["textures"][str(value.parameter_info.name)] = {
                "path": texture.get_path_name() if texture else None,
                "compression": str(texture.get_editor_property("compression_settings")) if texture else None,
                "srgb": texture.get_editor_property("srgb") if texture else None,
                "lod_bias": texture.get_editor_property("lod_bias") if texture else None,
                "max_texture_size": texture.get_editor_property("max_texture_size") if texture else None,
            }
        for value in current.get_editor_property("scalar_parameter_values"):
            entry["scalars"][str(value.parameter_info.name)] = value.parameter_value
        chain.append(entry)
        current = current.get_editor_property("parent")
    row["instance_chain"] = chain
    row["base_material"] = current.get_path_name() if current else None
    results.append(row)
(HERE / "current-material-inputs.json").write_text(json.dumps({"mesh": MESH, "materials": results},
    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
u.log("M16_THUMB_MATERIAL_INPUTS_READ " + str(len(results)))
