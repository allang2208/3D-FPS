"""Import the game-ready board pair in a private UE content host."""
import json
from pathlib import Path
import unreal as u

folder='/Game/WorldGeneration/VillageTavern/TableGame'
source=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageTavern/TableGame'
tools=u.AssetToolsHelpers.get_asset_tools()
library=u.EditorAssetLibrary
materials=u.MaterialEditingLibrary
meshes=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
saved=[]

def store(obj):
    if not library.save_loaded_asset(obj,False):
        raise RuntimeError('Could not save '+obj.get_path_name())
    saved.append(obj.get_name())

def import_asset(name,extension,options=None):
    task=u.AssetImportTask()
    task.filename=str(source/(name+extension))
    task.destination_path=folder
    task.destination_name=name
    task.automated=True
    task.replace_existing=True
    if options:
        task.options=options
        task.factory=u.FbxFactory()
    tools.import_asset_tasks([task])
    obj=library.load_asset(folder+'/'+name)
    if not obj:raise RuntimeError('Import failed for '+name)
    return obj

material=tools.create_asset('M_TavernTablesAtlas',folder,u.Material,u.MaterialFactoryNew())
material.set_editor_property('used_with_instanced_static_meshes',True)
for y,(suffix,kind,outputs) in enumerate((
    ('Color','COLOR',[('RGB','BASE_COLOR')]),
    ('Normal','NORMAL',[('RGB','NORMAL')]),
    ('ORM','MASKS',[('R','AMBIENT_OCCLUSION'),('G','ROUGHNESS'),('B','METALLIC')])
)):
    tex=import_asset('T_TavernTables_'+suffix,'.png')
    tex.srgb=suffix=='Color'
    if suffix!='Color':
        tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if suffix=='Normal' else u.TextureCompressionSettings.TC_MASKS
    store(tex)
    sample=materials.create_material_expression(material,u.MaterialExpressionTextureSample,-370,y*235-235)
    sample.texture=tex
    sample.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind)
    for channel,target in outputs:
        if not materials.connect_material_property(sample,channel,getattr(u.MaterialProperty,'MP_'+target)):
            raise RuntimeError('Could not connect '+target)
materials.recompile_material(material)
store(material)

for name in ('SM_TavernTablesBoard','SM_TavernTablesBoardRuined'):
    options=u.FbxImportUI()
    options.import_mesh=True
    options.import_as_skeletal=False
    options.import_materials=False
    options.import_textures=False
    options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data
    data.combine_meshes=True
    data.convert_scene=True
    data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True
    data.auto_generate_collision=False
    data.import_mesh_lods=True
    data.generate_lightmap_u_vs=True
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=import_asset(name,'.fbx',options)
    mesh.set_material(0,material)
    meshes.set_lod_screen_sizes(mesh,[1.,.17,.046])
    store(mesh)
root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
(root/'saved.json').write_text(json.dumps(saved,indent=2))
u.log('TAVERN_TABLE_GAME_SAVED')
