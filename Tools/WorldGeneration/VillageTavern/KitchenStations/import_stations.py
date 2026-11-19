"""Build kitchen packages in an isolated content mount with real village material bindings."""
import json
from pathlib import Path
import unreal as ue

source=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageTavern/KitchenStations'
dest='/Game/WorldGeneration/VillageTavern/KitchenStations'
assets=ue.AssetToolsHelpers.get_asset_tools()
library=ue.EditorAssetLibrary
editing=ue.MaterialEditingLibrary
village='/Game/WorldGeneration/TemperateHills'
carpenter=village+'/VillageCarpenter/Props/Surfaces/M_Carpenter'
tavern='/Game/WorldGeneration/VillageTavern'
matpaths={'Oak':village+'/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak',
          'Sawn':carpenter+'Sawn','Rot':carpenter+'Rot','Iron':carpenter+'Iron','Endgrain':carpenter+'Cut',
          'OiledOak':tavern+'/Furniture/M_TavernOiledOak','Clay':tavern+'/Service/MI_TavernClay',
          'AshGlaze':tavern+'/Service/MI_TavernAshGlaze'}
materials={k:ue.load_asset(p) for k,p in matpaths.items()}
for key,mat in materials.items():
    if not mat:
        raise RuntimeError('Missing source material '+matpaths[key])
saved=[]

def save(asset):
    if not library.save_loaded_asset(asset,False):
        raise RuntimeError('Unable to save '+asset.get_name())
    saved.append(asset.get_name())

def bring(name,extension,opts=None):
    task=ue.AssetImportTask()
    task.filename=str(source/(name+extension))
    task.destination_path=dest
    task.destination_name=name
    task.automated=True
    task.replace_existing=True
    if opts:
        task.factory=ue.FbxFactory()
        task.options=opts
    assets.import_asset_tasks([task])
    obj=library.load_asset(dest+'/'+name)
    if not obj or not task.imported_object_paths:
        raise RuntimeError('Could not import '+name)
    return obj

cloth=assets.create_asset('M_TavernKitchenLinen',dest,ue.Material,ue.MaterialFactoryNew())
cloth.set_editor_property('used_with_instanced_static_meshes',True)
for i,(suffix,typ,pin) in enumerate((('Color','COLOR','BASE_COLOR'),('Normal','NORMAL','NORMAL'),
                                      ('Rough','MASKS','ROUGHNESS'))):
    tex=bring('T_KitchenLinen_'+suffix,'.png')
    tex.srgb=suffix=='Color'
    if suffix=='Normal':
        tex.compression_settings=ue.TextureCompressionSettings.TC_NORMALMAP
    if suffix=='Rough':
        tex.compression_settings=ue.TextureCompressionSettings.TC_MASKS
    save(tex)
    expression=editing.create_material_expression(cloth,ue.MaterialExpressionTextureSample,-310,i*205)
    expression.texture=tex
    expression.sampler_type=getattr(ue.MaterialSamplerType,'SAMPLERTYPE_'+typ)
    if not editing.connect_material_property(expression,'R' if suffix=='Rough' else 'RGB',
                                             getattr(ue.MaterialProperty,'MP_'+pin)):
        raise RuntimeError('Could not wire '+pin)
editing.recompile_material(cloth)
save(cloth)
materials['Cloth']=cloth
for label in ('PrepBench','PrepBenchRuined','WashStand','WashStandRuined'):
    opts=ue.FbxImportUI()
    opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH
    opts.import_mesh=True
    opts.import_as_skeletal=False
    opts.import_materials=False
    opts.import_textures=False
    data=opts.static_mesh_import_data
    data.combine_meshes=False
    data.convert_scene=True
    data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True
    data.generate_lightmap_u_vs=True
    data.auto_generate_collision=False
    data.one_convex_hull_per_ucx=True
    data.normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=bring('SM_Tavern'+label,'.fbx',opts)
    for i,slot in enumerate(mesh.static_materials):
        key=str(slot.get_editor_property('imported_material_slot_name'))
        mesh.set_material(i,materials[key if key in materials else str(slot.material_slot_name)])
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',
                                                               ue.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    save(mesh)
(Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))/'saved.json').write_text(
    json.dumps(saved,indent=2),encoding='utf8')
