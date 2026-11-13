"""Import the Pojun grip and its workbench icon into the project."""
from pathlib import Path
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
here = root / "SourceAssets/Zhanmadao20261018/PojunLonghaft"
mesh_name = "SM_Zhanmadao_Grip_Pojun"
icon_name = "ue_zhanmadao_grip_pojun_longhaft"
mesh_dir = "/Game/Weapons/Zhanmadao20261018/PojunLonghaft"
icon_dir = "/Game/ColdSteelData/AttachmentIcons20260913"
targets = {mesh_dir + "/" + mesh_name, icon_dir + "/" + icon_name}
commandlet = "-run=pythonscript" in u.SystemLibrary.get_command_line().lower()
if not commandlet:
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError("PIE active")
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if package.get_name() in targets:
            raise RuntimeError("Unsaved target package: " + package.get_name())

def asset(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError("Asset unavailable: " + path)
    return obj

def import_part(filename, directory, options=None, factory=None):
    task = u.AssetImportTask()
    task.filename = str(here / filename)
    task.destination_path = directory
    task.destination_name = Path(filename).stem
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = False
    task.save = False
    if options:
        task.options = options
    if factory:
        task.factory = factory
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return asset(directory + "/" + task.destination_name)

def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()], False):
        raise RuntimeError("Save failed: " + obj.get_path_name())

materials = {p.rsplit("/", 1)[1]: asset(p) for p in (
    "/Game/Weapons/Zhanmadao20261018/V1/Materials/M_Zhanmadao_Surface_V1",
    "/Game/Weapons/SteelWarhammer20261014/Materials/M_SteelWarhammerSurface",
    "/Game/Weapons/SharedSwordGrips20260927/Materials/M_SharedGrip_Steel",
)}
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_as_skeletal = False
options.import_mesh = True
options.import_materials = False
options.import_textures = False
options.import_animations = False
settings = options.static_mesh_import_data
settings.combine_meshes = True
settings.auto_generate_collision = False
settings.generate_lightmap_u_vs = False
settings.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
settings.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
settings.build_nanite = True
engine = None if commandlet else u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = engine.get_editor_world() if engine else None
flag = "Interchange.FeatureFlags.Import.FBX"
previous = u.SystemLibrary.get_console_variable_int_value(flag)
try:
    if world:
        u.SystemLibrary.execute_console_command(world, flag + " 0")
    mesh = import_part(mesh_name + ".fbx", mesh_dir, options, u.FbxFactory())
finally:
    if world:
        u.SystemLibrary.execute_console_command(world, flag + " " + str(previous))
for index, slot in enumerate(mesh.static_materials):
    mesh.set_material(index, materials[str(slot.material_slot_name)])
nanite = mesh.get_editor_property("nanite_settings")
nanite.enabled = True
nanite.explicit_tangents = True
nanite.fallback_relative_error = 0
mesh.set_editor_property("nanite_settings", nanite)
save(mesh)
icon = import_part(icon_name + ".png", icon_dir, factory=u.TextureFactory())
icon.set_editor_property("lod_group", u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property("compression_settings", u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property("mip_gen_settings", u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
icon.set_editor_property("srgb", True)
icon.set_editor_property("never_stream", True)
save(icon)
print("POJUN_PACKAGES_SAVED " + mesh.get_path_name() + " " + icon.get_path_name())
