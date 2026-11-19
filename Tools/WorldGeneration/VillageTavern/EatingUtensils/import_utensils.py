"""Create the native table-implement meshes, textured hardwood and its three maps."""
import json
from pathlib import Path

import unreal as ue


SOURCE = Path(__file__).resolve().parents[4] / 'SourceAssets/HillsVillageTavern/EatingUtensils'
DEST = '/Game/WorldGeneration/VillageTavern/EatingUtensils'
assets = ue.AssetToolsHelpers.get_asset_tools()
library = ue.EditorAssetLibrary
editing = ue.MaterialEditingLibrary
mesh_editor = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
saved = []


def save(obj):
    if not library.save_loaded_asset(obj, False):
        raise RuntimeError('Could not save '+obj.get_path_name())
    saved.append(obj.get_name())


def bring(name, extension, options=None):
    task = ue.AssetImportTask()
    task.filename = str(SOURCE/(name+extension))
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    if options:
        task.factory = ue.FbxFactory()
        task.options = options
    assets.import_asset_tasks([task])
    obj = library.load_asset(DEST+'/'+name)
    if not obj or not task.imported_object_paths:
        raise RuntimeError('Could not import '+name)
    return obj


material = assets.create_asset('M_TavernEatingWood',DEST,ue.Material,ue.MaterialFactoryNew())
material.set_editor_property('used_with_instanced_static_meshes',True)
for idx,(suffix,sampler,pin,comp) in enumerate((
    ('Color','COLOR','BASE_COLOR',None),
    ('Roughness','MASKS','ROUGHNESS',ue.TextureCompressionSettings.TC_MASKS),
    ('Normal','NORMAL','NORMAL',ue.TextureCompressionSettings.TC_NORMALMAP))):
    tex = bring('T_TavernEatingWood_'+suffix,'.png')
    tex.srgb = suffix=='Color'
    if comp is not None:
        tex.compression_settings = comp
    save(tex)
    expression = editing.create_material_expression(material,ue.MaterialExpressionTextureSample,-320,idx*220)
    expression.texture = tex
    expression.sampler_type = getattr(ue.MaterialSamplerType,'SAMPLERTYPE_'+sampler)
    channel = 'R' if suffix=='Roughness' else 'RGB'
    if not editing.connect_material_property(expression,channel,getattr(ue.MaterialProperty,'MP_'+pin)):
        raise RuntimeError('Could not wire '+pin)
editing.recompile_material(material)
save(material)

for name in ('SM_TavernChopsticks','SM_TavernWoodSpoon'):
    opts = ue.FbxImportUI()
    opts.automated_import_should_detect_type = False
    opts.mesh_type_to_import = ue.FBXImportType.FBXIT_STATIC_MESH
    opts.import_mesh = True
    opts.import_as_skeletal = False
    opts.import_materials = False
    opts.import_textures = False
    data = opts.static_mesh_import_data
    data.combine_meshes = True
    data.import_mesh_lods = True
    # The FBX already has the intended numerical X and Z axes.
    data.convert_scene = False
    data.convert_scene_unit = True
    data.transform_vertex_to_absolute = True
    data.auto_generate_collision = False
    data.generate_lightmap_u_vs = True
    data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh = bring(name,'.fbx',opts)
    mesh.set_material(0,material)
    if not mesh_editor.set_lod_screen_sizes(mesh,[1.,.077,.021]):
        raise RuntimeError('Could not assign LOD screen sizes for '+name)
    save(mesh)

host = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
(host/'saved.json').write_text(json.dumps(saved,indent=2),encoding='utf8')
