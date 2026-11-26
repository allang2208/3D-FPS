"""Save Quixel microhabitats, local RVT and village component overrides headlessly."""
import json
import runpy
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
TASK=ROOT/'SourceAssets/HillsEcologyUpgrade20261114'
BASE='/Game/WorldGeneration/TemperateHills'
DEST=BASE+'/EcologyUpgrade'
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
AT=u.AssetToolsHelpers.get_asset_tools()
helpers=runpy.run_path(str(ROOT/'Tools/WorldGeneration/temperate_render_budget.py'))
cache=runpy.run_path(str(ROOT/'Tools/WorldGeneration/temperate_ground_cache.py'))
saved=[]

def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save '+obj.get_path_name())
    saved.append(obj.get_path_name())

def import_file(file,dest,name):
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=dest;t.destination_name=name
    t.automated=True;t.replace_existing=False;t.save=False
    AT.import_asset_tasks([t]);return t.get_objects()

E.make_directory(DEST)
data=u.load_asset(BASE+'/DA_TemperateHillsStreaming');helpers['backup'](data)
fungi=[]
fungi_root=DEST+'/Fungi'
existing=E.list_assets(fungi_root,True,False) if E.does_directory_exist(fungi_root) else []
for p in existing:
    a=u.load_asset(p)
    if isinstance(a,u.StaticMesh):fungi.append(a)
if not fungi:
    objects=import_file(TASK/'Quixel/ScatterMushrooms/Extracted/pdvv2_tier_2.gltf',fungi_root,'SM_QuixelScatterMushrooms')
    fungi=[a for a in objects if isinstance(a,u.StaticMesh)]
    for obj in objects:
        if isinstance(obj,u.Texture2D):obj.set_editor_property('max_texture_size',2048)
        save(obj)
if not E.save_directory(fungi_root,True,True):raise RuntimeError('Cannot save imported Quixel dependencies')
if not fungi:raise RuntimeError('Quixel mushroom import produced no meshes')
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for mesh in fungi:
    sm.remove_collisions(mesh)
    save(mesh)
data.set_editor_property('forest_fungi',fungi)
usage=runpy.run_path(str(ROOT/'Tools/WorldGeneration/repair_hills_audit_materials.py'))
saved.extend(usage['repair_fungi_instancing']())

# A thin, irregular masked patch uses existing Quixel moss scans, with no new texture set.
name=DEST+'/M_NurseLogMoss'
mat=u.load_asset(name) if E.does_asset_exist(name) else AT.create_asset('M_NurseLogMoss',DEST,u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(mat)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
mat.set_editor_property('used_with_instanced_static_meshes',True)
def node(cls):return L.create_material_expression(mat,cls)
def wire(a,b,pin,output=''):
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError(pin)
uv=node(u.MaterialExpressionTextureCoordinate)
channels={}
for suffix,stype in [('BaseColor','COLOR'),('Normal','NORMAL'),('ARH','MASKS')]:
    tex=u.load_asset(BASE+'/WetForest/Textures/T_RainforestMoss_'+suffix)
    if not tex:raise RuntimeError('Missing Quixel moss scan '+suffix)
    t=node(u.MaterialExpressionTextureSample);t.texture=tex
    if suffix=='ARH' and tex.compression_settings!=u.TextureCompressionSettings.TC_MASKS:stype='LINEAR_COLOR'
    t.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+stype);wire(uv,t,'UVs');channels[suffix]=t
def custom(code,inputs,width):
    n=node(u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for k in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',k);pins.append(p)
    n.set_editor_property('inputs',pins)
    for k,v in inputs.items():
        a,o=v if isinstance(v,tuple) else (v,'');wire(a,n,k,o)
    return n
color=custom('return C*float3(.52,.59,.44);',{'C':channels['BaseColor']},3)
coverage=custom('float2 q=(UV-.5)*2; float r=length(q); float rag=sin(UV.x*39+sin(UV.y*25))*.065; return saturate((.91+rag-r)*7)*(0.45+0.55*H);',{'UV':uv,'H':(channels['ARH'],'B')},1)
dither=node(u.MaterialExpressionMaterialFunctionCall);dither.set_editor_property('material_function',u.load_asset('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
wire(coverage,dither,L.get_material_expression_input_names(dither)[0])
for a,out,prop in [(color,'',u.MaterialProperty.MP_BASE_COLOR),(channels['Normal'],'RGB',u.MaterialProperty.MP_NORMAL),
                   (channels['ARH'],'G',u.MaterialProperty.MP_ROUGHNESS),(channels['ARH'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),(dither,'',u.MaterialProperty.MP_OPACITY_MASK)]:
    if not L.connect_material_property(a,out,prop):raise RuntimeError('Moss output')
L.recompile_material(mat);save(mat)
plane=DEST+'/SM_NurseLogMoss'
mesh=u.load_asset(plane) if E.does_asset_exist(plane) else E.duplicate_asset('/Engine/BasicShapes/Plane',plane)
mesh.set_material(0,mat);sm.remove_collisions(mesh);save(mesh);data.set_editor_property('forest_moss',[mesh])

color_cache,height_cache=cache['make_caches']()
data.set_editor_property('village_color_cache',color_cache)
data.set_editor_property('village_height_cache',height_cache)
save(data)
def stage_stamp(name):
    return TASK/(name+'-saved.json')
def checkpoint(name, result):
    stage_stamp(name).write_text(json.dumps(result,indent=2),encoding='utf-8')
checkpoint('microhabitat',{'fungi':[m.get_path_name() for m in fungi],'moss':mesh.get_path_name(),'palette':data.get_path_name()})
for p in (BASE+'/M_TemperateGround',BASE+'/PebbleShore/M_PebbleShoreGround'):helpers['backup'](u.load_asset(p))
if not stage_stamp('dry-ground-v2').exists():
    runpy.run_path(str(ROOT/'Tools/WorldGeneration/build_hills_ground_v2.py'),run_name='__main__')
    checkpoint('dry-ground-v2',{'surface':color_cache.get_path_name(),'height':height_cache.get_path_name()})

level=BASE+'/AbandonedVillage/L_AbandonedVillage'
world=u.EditorLoadingAndSavingUtils.load_map(level)
if not world:raise RuntimeError('Cannot load owned village sublevel')
helpers['backup'](world)
receivers={};changed=0;shadow_off=0
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
        mesh=comp.get_editor_property('static_mesh')
        if not mesh:continue
        blended,shadow=cache['dress_component'](comp,helpers['leaf_instance'],receivers)
        changed+=blended
        shadow_off+=int(shadow)
if not u.EditorLoadingAndSavingUtils.save_map(world,level):raise RuntimeError('Cannot save village overrides')
saved.append(level)
runpy.run_path(str(ROOT/'Tools/WorldGeneration/temperate_wind_budget.py'),run_name='__main__')
(TASK/'ecology-assets-saved.json').write_text(json.dumps({'saved':saved,'fungi':[m.get_path_name() for m in fungi],
    'village_receiver_slots':changed,'village_shadow_off_components':shadow_off,'tested':False},indent=2),encoding='utf-8')
u.log('HILLS_ECOLOGY_ASSETS_SAVED')
