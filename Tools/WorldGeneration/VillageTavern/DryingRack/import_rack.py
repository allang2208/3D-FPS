"""Import both rail states into a private Unreal asset host before scoped publication."""
import json
from pathlib import Path
import unreal as u

source=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageTavern/DryingRack'
dest='/Game/WorldGeneration/VillageTavern/DryingRack'
assets=u.AssetToolsHelpers.get_asset_tools()
library=u.EditorAssetLibrary
editing=u.MaterialEditingLibrary
mesh_api=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
saved=[]

def save(obj):
    if not library.save_loaded_asset(obj,False):raise RuntimeError('Could not save '+obj.get_path_name())
    saved.append(obj.get_name())

def bring(name,suffix,options=None):
    task=u.AssetImportTask()
    task.automated=True
    task.replace_existing=True
    task.filename=str(source/(name+suffix))
    task.destination_path=dest
    task.destination_name=name
    if options:
        task.factory=u.FbxFactory()
        task.options=options
    assets.import_asset_tasks([task])
    obj=library.load_asset(dest+'/'+name)
    if not obj:raise RuntimeError('Import failed: '+name)
    return obj

textures={}
for suffix in ('Color','Normal','ORM'):
    tex=bring('T_TavernDryGoods_'+suffix,'.png')
    tex.srgb=suffix=='Color'
    if suffix=='Normal':tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP
    if suffix=='ORM':tex.compression_settings=u.TextureCompressionSettings.TC_MASKS
    textures[suffix]=tex
    save(tex)
material=assets.create_asset('M_TavernDryGoods',dest,u.Material,u.MaterialFactoryNew())
material.set_editor_property('used_with_instanced_static_meshes',True)
for y,(suffix,kind,channels) in enumerate((
        ('Color','COLOR',[('RGB','BASE_COLOR')]),('Normal','NORMAL',[('RGB','NORMAL')]),
        ('ORM','MASKS',[('R','AMBIENT_OCCLUSION'),('G','ROUGHNESS'),('B','METALLIC')]))):
    node=editing.create_material_expression(material,u.MaterialExpressionTextureSample,-400,y*245-220)
    node.texture=textures[suffix]
    node.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind)
    for channel,pin in channels:
        if not editing.connect_material_property(node,channel,getattr(u.MaterialProperty,'MP_'+pin)):
            raise RuntimeError('Material pin '+pin)
editing.recompile_material(material)
save(material)

for name in ('SM_TavernDryingRack','SM_TavernDryingRackRuined'):
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
    mesh=bring(name,'.fbx',options)
    mesh.set_material(0,material)
    mesh_api.set_lod_screen_sizes(mesh,[1.,.19,.06])
    save(mesh)
stage=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
(stage/'saved.json').write_text(json.dumps(saved,indent=2),encoding='utf8')
u.log('VILLAGE_DRYING_RAIL_SAVED')
