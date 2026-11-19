"""Import the editable sign exports and bind their shared PBR atlas."""
import json
from pathlib import Path
import unreal as u

dest = '/Game/WorldGeneration/VillageTavern/Sign'
source = Path(__file__).resolve().parents[4] / 'SourceAssets/HillsVillageTavern/Sign'
api = u.AssetToolsHelpers.get_asset_tools()
lib = u.EditorAssetLibrary
matlib = u.MaterialEditingLibrary
mesh_api = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
saved = []


def save(obj):
    if not lib.save_loaded_asset(obj,False):
        raise RuntimeError('Unable to save '+obj.get_path_name())
    saved.append(obj.get_path_name().split('.')[0])


def import_asset(name, extension, options=None):
    entry = u.AssetImportTask()
    entry.filename = str(source/(name+extension))
    entry.destination_path = dest
    entry.destination_name = name
    entry.automated = True
    entry.replace_existing = True
    if options is not None:
        entry.options = options
        entry.factory = u.FbxFactory()
    api.import_asset_tasks([entry])
    asset = lib.load_asset(dest+'/'+name)
    if not asset:
        raise RuntimeError('Could not import '+name)
    return asset


textures={}
for suffix in ('Color','Normal','ORM'):
    tex=import_asset('T_TavernSign_'+suffix,'.png')
    tex.srgb=suffix=='Color'
    if suffix in ('Normal','ORM'):
        tex.compression_settings=(u.TextureCompressionSettings.TC_NORMALMAP if suffix=='Normal'
                                  else u.TextureCompressionSettings.TC_MASKS)
    save(tex)
    textures[suffix]=tex

material=api.create_asset('M_TavernSign',dest,u.Material,u.MaterialFactoryNew())
material.set_editor_property('used_with_instanced_static_meshes',True)
for y,(suffix,kind,channels) in enumerate((
    ('Color','COLOR',[('RGB','BASE_COLOR')]),('Normal','NORMAL',[('RGB','NORMAL')]),
    ('ORM','MASKS',[('R','AMBIENT_OCCLUSION'),('G','ROUGHNESS'),('B','METALLIC')])
)):
    sample=matlib.create_material_expression(material,u.MaterialExpressionTextureSample,-400,y*240-220)
    sample.texture=textures[suffix]
    sample.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind)
    for channel,output in channels:
        if not matlib.connect_material_property(sample,channel,getattr(u.MaterialProperty,'MP_'+output)):
            raise RuntimeError('Could not connect material output '+output)
matlib.recompile_material(material)
save(material)

for name in ('SM_TavernSign','SM_TavernSignRuined'):
    options=u.FbxImportUI()
    options.automated_import_should_detect_type=False
    options.import_mesh=True
    options.import_as_skeletal=False
    options.import_materials=False
    options.import_textures=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data
    data.combine_meshes=True
    data.convert_scene=True
    data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True
    data.import_mesh_lods=True
    data.generate_lightmap_u_vs=True
    data.auto_generate_collision=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=import_asset(name,'.fbx',options)
    mesh.set_material(0,material)
    mesh_api.set_lod_screen_sizes(mesh,[1.,.16,.043])
    save(mesh)

project=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
(project/'saved.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
u.log('TAVERN_SIGN_PACKAGES_SAVED')
