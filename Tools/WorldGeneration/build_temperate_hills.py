"""Author only /Game/WorldGeneration/TemperateHills and its independent test map.

Requires the newly compiled FPSGAMEEditor. Run in a separate commandlet process.
No source-pack asset is saved. No existing gameplay map is opened or changed.
"""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'Saved/TemperateHills'
OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/WorldGeneration/TemperateHills'
LEVEL='/Game/GameMaps/L_TemperateHills_Initial'
TOOLS=u.AssetToolsHelpers.get_asset_tools()
LIB=u.MaterialEditingLibrary
EAL=u.EditorAssetLibrary
report={'created':[],'references':[], 'scope':'Selected vegetation, ground, rocks and low fog only; no scene-pack levels/assemblies'}

def load(path):
    obj=u.load_asset(path)
    assert obj,path
    report['references'].append(obj.get_path_name())
    return obj
def save(obj):
    assert EAL.save_loaded_asset(obj,False),obj.get_path_name()
    report['created'].append(obj.get_path_name())
    return obj
def create(name,cls,factory):
    return u.load_asset(DEST+'/'+name) if EAL.does_asset_exist(DEST+'/'+name) else TOOLS.create_asset(name,DEST,cls,factory)
def node(m,cls):return LIB.create_material_expression(m,cls)
def wire(a,b,pin,output=''):assert LIB.connect_material_expressions(a,output,b,pin)
def prop(a,name):assert LIB.connect_material_property(a,'',getattr(u.MaterialProperty,'MP_'+name))
def custom(m,code,inputs,kind):
    n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code)
    n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(kind)))
    entries=[]
    for name in inputs:
        x=u.CustomInput();x.set_editor_property('input_name',name);entries.append(x)
    n.set_editor_property('inputs',entries)
    for name,source in inputs.items():wire(source,n,name)
    return n
def scalar(m,name,value):
    n=node(m,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n

EAL.make_directory(DEST)
tree_source='/ProceduralVegetationEditor/SampleAssets/Materials/MasterMaterials/MA_Foliage_Trees'
load(tree_source)
tree_master_path=DEST+'/M_BlackPoplarPCG'
tree_master=u.load_asset(tree_master_path) if EAL.does_asset_exist(tree_master_path) else EAL.duplicate_asset(tree_source,tree_master_path)
tree_master.set_editor_property('used_with_instanced_skinned_mesh',True)
LIB.recompile_material(tree_master);save(tree_master)
tree_materials=[]
for kind in ('Bark','Foliage'):
    source='/Game/Megaplant_Library/Tree_Black_Poplar/Materials/MI_Black_Poplar_01_'+kind
    target=DEST+'/MI_BlackPoplarPCG_'+kind
    load(source)
    mi=u.load_asset(target) if EAL.does_asset_exist(target) else EAL.duplicate_asset(source,target)
    LIB.set_material_instance_parent(mi,tree_master)
    tree_materials.append(save(mi))
m=create('M_TemperateGround',u.Material,u.MaterialFactoryNew())
# Rebuild only our owned master, allowing the authoring script to be rerun.
LIB.delete_all_material_expressions(m)
world=node(m,u.MaterialExpressionWorldPosition)
normal=node(m,u.MaterialExpressionVertexNormalWS)
uv=custom(m,'return P.xy/350.0;',{'P':world},2)
wet=scalar(m,'Wetness',0)
weights=custom(m,'''float2 q=P.xy*0.00011+float2(7.13,13.9); float2 i=floor(q),f=frac(q); f=f*f*(3-2*f);
float4 h=frac(sin(float4(dot(i,float2(127.1,311.7)),dot(i+float2(1,0),float2(127.1,311.7)),dot(i+float2(0,1),float2(127.1,311.7)),dot(i+1,float2(127.1,311.7))))*43758.5453);
float patch=lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y);
float rock=saturate((0.94-N.z)*5.5); float soil=smoothstep(0.42,0.86,patch)*0.65*(1-rock); return float3(1-rock-soil,soil,rock);''',{'P':world,'N':normal},3)
sets=['GroundGrassMoss','GroundGrassSoil','GroundRockyRoad']
colors=[];normals=[];rough=[]
for family in sets:
    for suffix,target,sampler in [('Albedo',colors,u.MaterialSamplerType.SAMPLERTYPE_COLOR),('Normal',normals,u.MaterialSamplerType.SAMPLERTYPE_NORMAL),('RHAOM',rough,u.MaterialSamplerType.SAMPLERTYPE_MASKS)]:
        t=node(m,u.MaterialExpressionTextureSample)
        t.set_editor_property('texture',load('/Game/UnrealNormandy/Textures/T_LC_'+family+'_00A_'+suffix))
        t.set_editor_property('sampler_type',sampler);wire(uv,t,'UVs');target.append(t)
color=custom(m,'float macro=0.94+0.06*sin(P.x*0.00019+P.y*0.00011); return (A*W.x+B*W.y+C*W.z)*macro*lerp(1.0,0.64,saturate(Wet));',{'A':colors[0],'B':colors[1],'C':colors[2],'W':weights,'P':world,'Wet':wet},3)
detail=custom(m,'return normalize(A*W.x+B*W.y+C*W.z);',{'A':normals[0],'B':normals[1],'C':normals[2],'W':weights},3)
roughness=custom(m,'float r=A.r*W.x+B.r*W.y+C.r*W.z; return lerp(clamp(r,0.52,0.95),0.28,saturate(Wet));',{'A':rough[0],'B':rough[1],'C':rough[2],'W':weights,'Wet':wet},1)
prop(color,'BASE_COLOR');prop(detail,'NORMAL');prop(roughness,'ROUGHNESS')
LIB.recompile_material(m);save(m)

fog=create('MI_ValleyLowFog',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
LIB.set_material_instance_parent(fog,load('/Game/UnrealNormandy/MaterialInstances/MI_VolumeFog_01A'))
for key,value in {'FogOverallDensity':.12,'EmissiveIntensity':.03,'Distance':600,'FogEdgeRoundness':2}.items():LIB.set_material_instance_scalar_parameter_value(fog,key,value)
save(fog)

graphs=[]
for layer,name in enumerate(['PCG_BlackPoplar','PCG_HillsRocks','PCG_HillsShrubs','PCG_HillsGrass']):
    graph=create(name,u.PCGGraph,u.PCGGraphFactory())
    for old in list(graph.get_editor_property('nodes')):graph.remove_node(old)
    graph.set_editor_property('use_hierarchical_generation',True)
    graph.set_editor_property('use_actor_componentless_generation',False)
    graph.set_editor_property('hi_gen_grid_size',[u.PCGHiGenGrid.GRID128,u.PCGHiGenGrid.GRID128,u.PCGHiGenGrid.GRID64,u.PCGHiGenGrid.GRID32][layer])
    graph.set_editor_property('use2d_grid',True)
    graph.set_editor_property('has_default_constructed_inputs',False)
    generator,settings=graph.add_node_of_type(u.TemperateHillsPointsSettings)
    settings.set_editor_property('layer',layer)
    if layer==0:
        output,spawn=graph.add_node_of_type(u.PCGSkinnedMeshSpawnerSettings)
        selector=spawn.get_editor_property('mesh_selector_parameters')
        attribute=selector.get_editor_property('mesh_attribute')
        attribute.import_text('PCGBegin(Mesh)PCGEnd')
        assert attribute.export_text()=='PCGBegin(Mesh)PCGEnd',attribute.export_text()
        selector.set_editor_property('mesh_attribute',attribute)
        assert selector.get_editor_property('mesh_attribute').export_text()=='PCGBegin(Mesh)PCGEnd'
    else:
        output,spawn=graph.add_node_of_type(u.PCGStaticMeshSpawnerSettings)
        spawn.set_mesh_selector_type(u.PCGMeshSelectorByAttribute)
        selector=spawn.get_editor_property('mesh_selector_parameters')
        selector.set_editor_property('attribute_name','Mesh')
    descriptor=selector.get_editor_property('template_descriptor')
    body=descriptor.get_editor_property('body_instance')
    body.set_editor_property('collision_profile_name','BlockAll' if layer==1 else 'NoCollision')
    descriptor.set_editor_property('body_instance',body)
    descriptor.set_editor_property('cast_shadow',layer<3)
    descriptor.set_editor_property('component_tags',['TemperateHills',name])
    if layer>0:
        descriptor.set_editor_property('instance_start_cull_distance',[0,50000,20000,8500][layer])
        descriptor.set_editor_property('instance_end_cull_distance',[0,60000,28000,12500][layer])
    selector.set_editor_property('template_descriptor',descriptor)
    graph.add_edge(generator,'Out',output,'In')
    graph.add_edge(output,'Out',graph.get_output_node(),'Out')
    graphs.append(save(graph))

factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.TemperateHillsAssets)
assets=create('DA_TemperateHills',u.TemperateHillsAssets,factory)
assets.set_editor_property('ground_material',m)
assets.set_editor_property('valley_fog_material',fog)
assets.set_editor_property('valley_fog_class',u.load_class(None,'/Game/UnrealNormandy/Blueprints/BP_LocalFogVolume_Master.BP_LocalFogVolume_Master_C'))
assets.set_editor_property('trunk_collision_mesh',load('/Engine/BasicShapes/Cylinder'))
trees=[]
for variant in 'ABCD':
    source='/Game/Megaplant_Library/Tree_Black_Poplar/Tree_Black_Poplar_01/Tree_Black_Poplar_01_'+variant
    target=DEST+'/SK_BlackPoplarPCG_'+variant
    load(source)
    tree=u.load_asset(target) if EAL.does_asset_exist(target) else EAL.duplicate_asset(source,target)
    slots=list(tree.get_editor_property('materials'))
    assert len(slots)==len(tree_materials)
    for slot,material in zip(slots,tree_materials):slot.set_editor_property('material_interface',material)
    tree.set_editor_property('materials',slots)
    trees.append(save(tree))
assets.set_editor_property('trees',trees)
assets.set_editor_property('rocks',[load('/Game/UnrealNormandy/StaticMeshes/SM_LS_Rock_0'+str(x)+'A') for x in range(4)])
assets.set_editor_property('shrubs',[load('/Game/UnrealNormandy/StaticMeshes/SM_PlantType'+x+'_00A') for x in 'ABC'])
assets.set_editor_property('grass',[load('/Game/UnrealNormandy/StaticMeshes/SM_Grass_0'+str(x)+'A') for x in range(3)]+[load('/Game/UnrealNormandy/StaticMeshes/SM_GrassTall_00A')])
assets.set_editor_property('graphs',graphs);save(assets)

editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
if EAL.does_asset_exist(LEVEL):
    assert editor.load_level(LEVEL)
    owned=(u.TemperateHillsWorld,u.DirectionalLight,u.SkyAtmosphere,u.SkyLight,u.ExponentialHeightFog,u.FPSWeatherManager,u.PostProcessVolume)
    for actor in actors.get_all_level_actors():
        if isinstance(actor,owned):assert actors.destroy_actor(actor)
else:
    assert editor.new_level(LEVEL)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property('default_game_mode',u.TemperateHillsGameMode)
hill=actors.spawn_actor_from_class(u.TemperateHillsWorld,u.Vector(0,0,0))
pcg_world=next(a for a in actors.get_all_level_actors() if isinstance(a,u.PCGWorldActor))
pcg_world.set_actor_label('Hills PCG Runtime Scheduler')
pcg_world.set_editor_property('treat_player_controllers_as_generation_sources',True)
hill.set_actor_label('Temperate Hills - Seeded Vegetation')
hill.set_editor_property('assets',assets)
hill.set_editor_property('seed',122)
hill.set_editor_property('size_meters',1024)
sun=actors.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,18000),u.Rotator(-32,-35,0))
sun.set_actor_label('Hills Sun')
sun.light_component.set_mobility(u.ComponentMobility.MOVABLE)
sun.light_component.set_editor_property('intensity',5.0)
sun.light_component.set_editor_property('atmosphere_sun_light',True)
sun.light_component.set_editor_property('light_source_angle',1.4)
actors.spawn_actor_from_class(u.SkyAtmosphere,u.Vector(0,0,0))
sky=actors.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,15000))
sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
sky.light_component.set_editor_property('real_time_capture',True)
sky.light_component.set_editor_property('intensity',.9)
air=actors.spawn_actor_from_class(u.ExponentialHeightFog,u.Vector(0,0,1800))
air.component.set_editor_property('fog_density',.012)
air.component.set_editor_property('fog_height_falloff',.20)
air.component.set_editor_property('enable_volumetric_fog',True)
air.component.set_editor_property('volumetric_fog_distance',85000)
weather=actors.spawn_actor_from_class(u.FPSWeatherManager,u.Vector(0,0,0))
weather.set_editor_property('automatic_schedule',True)
# A fixed exposure keeps the vegetation study comparable across seed captures.
post=actors.spawn_actor_from_class(u.PostProcessVolume,u.Vector(0,0,0))
post.set_editor_property('unbound',True)
settings=post.get_editor_property('settings')
for key,value in [('override_auto_exposure_min_brightness',True),('override_auto_exposure_max_brightness',True),('auto_exposure_min_brightness',1.0),('auto_exposure_max_brightness',1.0)]:settings.set_editor_property(key,value)
post.set_editor_property('settings',settings)
u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(u.Vector(-29000,-10000,14000),u.Rotator(-12,22,0))
assert editor.save_current_level()
report['map']=LEVEL
report['references']=sorted(set(report['references']))
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('TEMPERATE_AUTHORING_COMPLETE '+LEVEL)
