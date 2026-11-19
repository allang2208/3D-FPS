"""Import only the four replacement stoneware meshes into the isolated host."""
from pathlib import Path
import unreal as u


source = Path(__file__).resolve().parents[4] / "SourceAssets/HillsVillageTavern/StonewareDetail"
destination = "/Game/WorldGeneration/VillageTavern/StonewareDetail"
service = "/Game/WorldGeneration/VillageTavern/Service/MI_Tavern"
asset_tools = u.AssetToolsHelpers.get_asset_tools()
mesh_editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)


def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError("Asset unavailable: " + path)
    return asset


materials = {slot: load(service+slot) for slot in ("Clay", "AshGlaze", "HoneyGlaze", "OliveGlaze")}
for role in ("Pitcher", "Tankard", "Dish", "Sherd"):
    name = "SM_Tavern" + role
    task = u.AssetImportTask()
    task.filename = str(source / (name+".fbx"))
    task.destination_path = destination
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.factory = u.FbxFactory()
    task.options = opts = u.FbxImportUI()
    opts.import_mesh = True
    opts.import_as_skeletal = False
    opts.import_materials = False
    opts.import_textures = False
    opts.automated_import_should_detect_type = False
    opts.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    data = opts.static_mesh_import_data
    data.combine_meshes = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.transform_vertex_to_absolute = True
    data.import_mesh_lods = True
    data.generate_lightmap_u_vs = True
    data.auto_generate_collision = False
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    asset_tools.import_asset_tasks([task])
    mesh = load(destination + "/" + name)
    for index, slot in enumerate(mesh.static_materials):
        mesh.set_material(index, materials[str(slot.material_slot_name)])
    mesh_editor.set_lod_screen_sizes(mesh, [1., .15, .042])
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):
        raise RuntimeError("Mesh could not be saved: " + name)
    u.log("Published " + mesh.get_path_name())
u.log("STONEWARE_DETAIL_SAVED")
