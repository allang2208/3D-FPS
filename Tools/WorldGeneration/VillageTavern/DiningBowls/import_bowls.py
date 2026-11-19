"""Save the three dressed/undressed taproom props to an isolated project mount."""
import json
from pathlib import Path

import unreal as ue

source = Path(__file__).resolve().parents[4] / "SourceAssets/HillsVillageTavern/DiningBowls"
dest = "/Game/WorldGeneration/VillageTavern/DiningBowls"
service = "/Game/WorldGeneration/VillageTavern/Service/MI_Tavern"
assets = ue.AssetToolsHelpers.get_asset_tools()
library = ue.EditorAssetLibrary
edit = ue.MaterialEditingLibrary
mesh_edit = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
saved = []


def save(obj):
    if not library.save_loaded_asset(obj, False):
        raise RuntimeError("Could not save " + obj.get_path_name())
    saved.append(obj.get_name())


materials = {}
for slot in ("Clay","HoneyGlaze","AshGlaze"):
    materials[slot] = ue.load_asset(service + slot)
    if not materials[slot]:
        raise RuntimeError("Missing taproom surface " + service + slot)

food = assets.create_asset("M_TavernBarleyStew", dest, ue.Material, ue.MaterialFactoryNew())
food.set_editor_property("used_with_instanced_static_meshes", True)
color = edit.create_material_expression(food, ue.MaterialExpressionVertexColor, -320, 0)
for channel, prop in [("", ue.MaterialProperty.MP_BASE_COLOR), ("A", ue.MaterialProperty.MP_ROUGHNESS)]:
    if not edit.connect_material_property(color,channel,prop):
        raise RuntimeError("Missing stew material channel " + channel)
edit.recompile_material(food)
save(food)
materials["Pottage"] = food

for role in ("EatingBowl","BrokenBowl","StewBowl"):
    name = "SM_Tavern" + role
    task = ue.AssetImportTask()
    task.filename = str(source / (name + ".fbx"))
    task.destination_name = name
    task.destination_path = dest
    task.automated = True
    task.replace_existing = True
    task.factory = ue.FbxFactory()
    ui = ue.FbxImportUI()
    ui.automated_import_should_detect_type = False
    ui.mesh_type_to_import = ue.FBXImportType.FBXIT_STATIC_MESH
    ui.import_as_skeletal = False
    ui.import_materials = False
    ui.import_textures = False
    ui.import_mesh = True
    data = ui.static_mesh_import_data
    data.combine_meshes = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.transform_vertex_to_absolute = True
    data.import_mesh_lods = True
    data.generate_lightmap_u_vs = True
    data.auto_generate_collision = False
    data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option = ue.VertexColorImportOption.REPLACE
    task.options = ui
    assets.import_asset_tasks([task])
    mesh = library.load_asset(dest + "/" + name)
    if not task.imported_object_paths or not mesh:
        raise RuntimeError("Could not import " + name)
    for i,slot in enumerate(mesh.static_materials):
        mesh.set_material(i,materials[str(slot.material_slot_name)])
    mesh_edit.set_lod_screen_sizes(mesh,[1.,.13,.037])
    save(mesh)

project_dir = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
(project_dir/"saved.json").write_text(json.dumps(saved,indent=2),encoding="utf8")
