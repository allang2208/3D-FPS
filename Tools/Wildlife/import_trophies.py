"""Import the hills trophy meshes and assign their authored surface maps."""
from pathlib import Path
import unreal as ue

src = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())) / "SourceAssets/HillsWildlifeLoot"
dest = "/Game/Monsters/Wildlife/Trophies"
library, tools, edit = ue.EditorAssetLibrary, ue.AssetToolsHelpers.get_asset_tools(), ue.MaterialEditingLibrary
library.make_directory(dest)


def save(obj):
    if not library.save_loaded_asset(obj, False):
        raise RuntimeError("Cannot save " + obj.get_path_name())


def load_or_create(name, cls, factory):
    if library.does_asset_exist(dest + "/" + name):
        return library.load_asset(dest + "/" + name)
    return tools.create_asset(name, dest, cls, factory)


def import_file(name, extension):
    task = ue.AssetImportTask()
    task.filename = str(src / (name + extension))
    task.destination_path, task.destination_name = dest, name
    task.automated, task.replace_existing = True, True
    if extension == ".fbx":
        opts = ue.FbxImportUI()
        opts.automated_import_should_detect_type = False
        opts.mesh_type_to_import = ue.FBXImportType.FBXIT_STATIC_MESH
        opts.import_materials, opts.import_textures = False, False
        opts.static_mesh_import_data.combine_meshes = True
        opts.static_mesh_import_data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.factory, task.options = ue.FbxFactory(), opts
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError("Import failed: " + task.filename)
    return library.load_asset(task.imported_object_paths[0])


for key, roughness in {"deer_hide":.87,"boar_hide":.91,"fox_pelt":.82,"wolf_pelt":.85,
                       "deer_antler":.66,"boar_tusk":.47,"crow_feather":.56}.items():
    color = import_file("T_" + key + "_BC", ".png")
    normal = import_file("T_" + key + "_N", ".png")
    normal.set_editor_property("compression_settings", ue.TextureCompressionSettings.TC_NORMALMAP)
    normal.set_editor_property("srgb", False)
    save(normal)
    save(color)
    material = load_or_create("M_" + key, ue.Material, ue.MaterialFactoryNew())
    edit.delete_all_material_expressions(material)
    for tex, prop, sampler in ((color,ue.MaterialProperty.MP_BASE_COLOR,ue.MaterialSamplerType.SAMPLERTYPE_COLOR),
                               (normal,ue.MaterialProperty.MP_NORMAL,ue.MaterialSamplerType.SAMPLERTYPE_NORMAL)):
        expr = edit.create_material_expression(material, ue.MaterialExpressionTextureSample)
        expr.set_editor_property("texture", tex)
        expr.set_editor_property("sampler_type", sampler)
        edit.connect_material_property(expr,"RGB",prop)
    rough = edit.create_material_expression(material,ue.MaterialExpressionConstant)
    rough.set_editor_property("r",roughness)
    edit.connect_material_property(rough,"",ue.MaterialProperty.MP_ROUGHNESS)
    edit.recompile_material(material)
    save(material)
    mesh = import_file("SM_" + key, ".fbx")
    mesh.set_material(0,material)
    save(mesh)
ue.log("Saved seven hills wildlife trophy meshes and their materials.")
