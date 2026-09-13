"""Import the locally downloaded free river assets and connect the existing hills.

Authoring only: no map opening, gameplay, screenshots or acceptance runs.
Requires the river-enabled FPSGAMEEditor module. Source packs stay unchanged.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
CACHE = ROOT.parent/'VaultCache/FabLibrary'
BASE = '/Game/WorldGeneration/TemperateHills'
DEST = BASE+'/Rivers'
OUT = ROOT/'Saved/TemperateRivers'
OUT.mkdir(parents=True, exist_ok=True)
LIB = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
REPORT = {'sources': [], 'created': [], 'scope': 'Free river assets; authoring only; no gameplay or visual tests'}
EAL.make_directory(DEST)

def load(path):
    obj = u.load_asset(path)
    if obj is None:
        raise RuntimeError('Required river authoring asset missing: '+path)
    return obj

def save(obj):
    if not EAL.save_loaded_asset(obj, False):
        raise RuntimeError('Could not save '+obj.get_path_name())
    REPORT['created'].append(obj.get_path_name())
    return obj

def create(name, cls, factory):
    path = DEST+'/'+name
    return load(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(name, DEST, cls, factory)

def node(mat, cls):
    return LIB.create_material_expression(mat, cls)

def wire(source, dest, pin, output=''):
    if not LIB.connect_material_expressions(source, output, dest, pin):
        raise RuntimeError('Could not connect material input '+pin)

def prop(source, name):
    if not LIB.connect_material_property(source, '', getattr(u.MaterialProperty, 'MP_'+name)):
        raise RuntimeError('Could not connect material property '+name)

def custom(mat, code, inputs, width=3):
    expr = node(mat, u.MaterialExpressionCustom)
    expr.set_editor_property('code', code)
    expr.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT'+str(width)))
    entries=[]
    for name in inputs:
        entry=u.CustomInput(); entry.set_editor_property('input_name',name); entries.append(entry)
    expr.set_editor_property('inputs',entries)
    for name, source in inputs.items():
        wire(source,expr,name)
    return expr

def scalar(mat, name, value):
    expr=node(mat,u.MaterialExpressionScalarParameter)
    expr.set_editor_property('parameter_name',name); expr.set_editor_property('default_value',value)
    return expr

def color(mat, name, rgb):
    expr=node(mat,u.MaterialExpressionVectorParameter)
    expr.set_editor_property('parameter_name',name)
    expr.set_editor_property('default_value',u.LinearColor(*rgb,1))
    return expr

def texture_sample(mat, texture, uv, normal=False, linear=False):
    expr=node(mat,u.MaterialExpressionTextureSample)
    expr.set_editor_property('texture',texture)
    use_linear=linear or not texture.get_editor_property('srgb')
    expr.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else
        u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if use_linear else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    expr.set_editor_property('sampler_source',u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
    wire(uv,expr,'UVs')
    return expr

def source_file(folder, pattern):
    paths=sorted((CACHE/folder).rglob(pattern))
    if not paths:
        raise RuntimeError('Local Fab download missing: '+str(CACHE/folder/pattern))
    return paths[0]

def import_texture(source, name, kind):
    path=DEST+'/'+name
    if EAL.does_asset_exist(path):
        tex=load(path)
    else:
        task=u.AssetImportTask()
        task.set_editor_property('filename',str(source))
        task.set_editor_property('destination_path',DEST)
        task.set_editor_property('destination_name',name)
        task.set_editor_property('automated',True)
        task.set_editor_property('save',False)
        TOOLS.import_asset_tasks([task])
        tex=load(path)
    tex.set_editor_property('srgb',kind=='BaseColor')
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property('max_texture_size',2048)
    REPORT['sources'].append({'file':str(source),'asset':path})
    return save(tex)

def texture_set(folder, prefix):
    return {kind:import_texture(source_file(folder,'*_'+kind+'.jpg'),'T_'+prefix+'_'+kind,kind)
            for kind in ('BaseColor','Normal','Roughness')}

shore=texture_set('Shoreline_Beach_Rocks-1a759058','RiverShore')
pebbles=texture_set('Small_Pebbles_Ground-a0e6a70f','RiverPebbles')
rock_maps=texture_set('Nordic_Beach_Rocks-80de6243','RiverNordic')

# Reuse the existing hill/grass/moss formula and weather Wetness input away from
# the river vertex mask, authoring only a river-owned material output.
ground=create('M_TemperateRiverGround',u.Material,u.MaterialFactoryNew())
backup_root=OUT/('BeforeAuthoring-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
for relative in ('WorldGeneration/TemperateHills/DA_TemperateHillsStreaming.uasset',
                 'WorldGeneration/TemperateHills/Rivers/M_TemperateRiverGround.uasset'):
    source=ROOT/'Content'/relative
    if source.is_file():
        destination=backup_root/relative; destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)

# MaterialEditingLibrary copies individual expressions but not their connections;
# author the complete small ground graph using the same three existing texture sets.
LIB.delete_all_material_expressions(ground)
world=node(ground,u.MaterialExpressionWorldPosition)
normal_ws=node(ground,u.MaterialExpressionVertexNormalWS)
mask=node(ground,u.MaterialExpressionVertexColor)
uv=custom(ground,'return P.xy/350.0;',{'P':world},2)
river_uv=custom(ground,'return P.xy/200.0;',{'P':world},2)
wet=scalar(ground,'Wetness',0)
weights=custom(ground,'''float2 q=P.xy*0.00011+float2(7.13,13.9); float2 i=floor(q),f=frac(q); f=f*f*(3-2*f);
float4 h=frac(sin(float4(dot(i,float2(127.1,311.7)),dot(i+float2(1,0),float2(127.1,311.7)),dot(i+float2(0,1),float2(127.1,311.7)),dot(i+1,float2(127.1,311.7))))*43758.5453);
float patch=lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y);
float rock=saturate((0.94-N.z)*5.5); float soil=smoothstep(0.42,0.86,patch)*0.65*(1-rock); return float3(1-rock-soil,soil,rock);''',{'P':world,'N':normal_ws})
colors=[]; normals=[]; rough=[]
for family in ('GroundGrassMoss','GroundGrassSoil','GroundRockyRoad'):
    for suffix,target,sampler in (('Albedo',colors,u.MaterialSamplerType.SAMPLERTYPE_COLOR),
            ('Normal',normals,u.MaterialSamplerType.SAMPLERTYPE_NORMAL),('RHAOM',rough,u.MaterialSamplerType.SAMPLERTYPE_MASKS)):
        tex=load('/Game/UnrealNormandy/Textures/T_LC_'+family+'_00A_'+suffix)
        expr=node(ground,u.MaterialExpressionTextureSample)
        expr.set_editor_property('texture',tex); expr.set_editor_property('sampler_type',sampler)
        expr.set_editor_property('sampler_source',u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        wire(uv,expr,'UVs');target.append(expr)
old_color=custom(ground,'float macro=0.94+0.06*sin(P.x*0.00019+P.y*0.00011); return (A*W.x+B*W.y+C*W.z)*macro*lerp(1.0,0.64,saturate(Wet));',
    {'A':colors[0],'B':colors[1],'C':colors[2],'W':weights,'P':world,'Wet':wet})
old_normal=custom(ground,'return normalize(A*W.x+B*W.y+C*W.z);',{'A':normals[0],'B':normals[1],'C':normals[2],'W':weights})
old_rough=custom(ground,'float r=A.r*W.x+B.r*W.y+C.r*W.z; return lerp(clamp(r,0.52,0.95),0.28,saturate(Wet));',{'A':rough[0],'B':rough[1],'C':rough[2],'W':weights,'Wet':wet},1)
bank_samples=[]
for maps in (shore,pebbles):
    bank_samples.append({kind:texture_sample(ground,tex,river_uv,normal=kind=='Normal',linear=kind=='Roughness') for kind,tex in maps.items()})
mix=custom(ground,'return saturate(0.35+0.20*sin(P.x*.002+sin(P.y*.0011))+(1-M.g)*.25);',{'P':world,'M':mask},1)
bank_color=custom(ground,'return lerp(A,B,T)*lerp(1.0,0.56,max(M.g,Wet));',{'A':bank_samples[0]['BaseColor'],'B':bank_samples[1]['BaseColor'],'T':mix,'M':mask,'Wet':wet})
bank_normal=custom(ground,'return normalize(lerp(A,B,T));',{'A':bank_samples[0]['Normal'],'B':bank_samples[1]['Normal'],'T':mix})
bank_rough=custom(ground,'return lerp(clamp(lerp(A.r,B.r,T),.5,.95),.24,max(M.g,Wet));',{'A':bank_samples[0]['Roughness'],'B':bank_samples[1]['Roughness'],'T':mix,'M':mask,'Wet':wet},1)
prop(custom(ground,'return lerp(A,B,saturate(M.r));',{'A':old_color,'B':bank_color,'M':mask}),'BASE_COLOR')
prop(custom(ground,'return normalize(lerp(A,B,saturate(M.r)));',{'A':old_normal,'B':bank_normal,'M':mask}),'NORMAL')
prop(custom(ground,'return lerp(A,B,saturate(M.r));',{'A':old_rough,'B':bank_rough,'M':mask},1),'ROUGHNESS')
LIB.recompile_material(ground);save(ground)

# Flow follows ribbon UV.x in metres of arc length, so bends/chunk boundaries do
# not reset or stretch the animation. Two normal samples, one foam sample, no WPO.
water=create('M_TemperateRiverWater',u.Material,u.MaterialFactoryNew())
LIB.delete_all_material_expressions(water)
water.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
water.set_editor_property('two_sided',True)
water.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
texcoord=node(water,u.MaterialExpressionTextureCoordinate)
time=node(water,u.MaterialExpressionTime)
speed=scalar(water,'FlowSpeed',.14)
water_mask=node(water,u.MaterialExpressionVertexColor)
flow_a=custom(water,'return UV-float2(T*Speed,T*.018);',{'UV':texcoord,'T':time,'Speed':speed},2)
flow_b=custom(water,'return UV*1.73-float2(T*Speed*.79,-T*.013)+float2(3.1,1.7);',{'UV':texcoord,'T':time,'Speed':speed},2)
wave_a=texture_sample(water,load('/Game/WaterMaterials/Textures/T_River_Waves01_Normals'),flow_a,normal=True)
wave_b=texture_sample(water,load('/Game/WaterMaterials/Textures/T_River_Waves02_Normals'),flow_b,normal=True)
foam_texture=texture_sample(water,load('/Game/WaterMaterials/Textures/T_Ocean_Foam'),flow_a)
foam=custom(water,'return saturate(M.r*.55+smoothstep(.76,.98,F.r)*.12);',{'M':water_mask,'F':foam_texture},1)
tint=color(water,'WaterTint',(.022,.090,.075))
prop(custom(water,'return lerp(C,float3(.62,.69,.64),F);',{'C':tint,'F':foam}),'BASE_COLOR')
prop(custom(water,'return normalize(float3((A.xy+B.xy)*.30,1));',{'A':wave_a,'B':wave_b}),'NORMAL')
prop(custom(water,'return lerp(.12,.4,F);',{'F':foam},1),'ROUGHNESS')
prop(scalar(water,'Specular',.5),'SPECULAR')
opacity=custom(water,'return .32+F*.5;',{'F':foam},1)
fade=node(water,u.MaterialExpressionDepthFade)
fade.set_editor_property('fade_distance_default',45.0)
wire(opacity,fade,'Opacity');prop(fade,'OPACITY')
LIB.recompile_material(water);save(water)

rock_material=create('M_TemperateRiverRock',u.Material,u.MaterialFactoryNew())
LIB.delete_all_material_expressions(rock_material)
rock_material.set_editor_property('used_with_instanced_static_meshes',True)
rock_uv=node(rock_material,u.MaterialExpressionTextureCoordinate)
rock_color=texture_sample(rock_material,rock_maps['BaseColor'],rock_uv)
rock_normal=texture_sample(rock_material,rock_maps['Normal'],rock_uv,normal=True)
rock_rough=texture_sample(rock_material,rock_maps['Roughness'],rock_uv,linear=True)
damp=scalar(rock_material,'RockDampness',.55)
prop(custom(rock_material,'return C*lerp(1.0,.65,W);',{'C':rock_color,'W':damp}),'BASE_COLOR')
prop(rock_normal,'NORMAL')
prop(custom(rock_material,'return lerp(clamp(R.r,.4,.95),.3,W);',{'R':rock_rough,'W':damp},1),'ROUGHNESS')
LIB.recompile_material(rock_material);save(rock_material)

rock_path=DEST+'/SM_NordicRiverRocks'
fbx=source_file('Nordic_Beach_Rocks-80de6243','*.fbx')
if EAL.does_asset_exist(rock_path):
    rock=load(rock_path)
else:
    options=u.FbxImportUI()
    options.set_editor_property('import_mesh',True)
    options.set_editor_property('import_as_skeletal',False)
    options.set_editor_property('import_materials',False)
    options.set_editor_property('import_textures',False)
    options.set_editor_property('automated_import_should_detect_type',False)
    options.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
    options.static_mesh_import_data.set_editor_property('combine_meshes',True)
    options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    task=u.AssetImportTask()
    task.set_editor_property('filename',str(fbx))
    task.set_editor_property('destination_path',DEST)
    task.set_editor_property('destination_name','SM_NordicRiverRocks')
    task.set_editor_property('automated',True)
    task.set_editor_property('factory',u.FbxFactory())
    task.set_editor_property('options',options)
    task.set_editor_property('save',False)
    TOOLS.import_asset_tasks([task])
    rock=load(rock_path)
rock.set_material(0,rock_material)
mesh_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
mesh_editor.remove_collisions(rock)
mesh_editor.add_simple_collisions(rock,u.ScriptCollisionShapeType.NDOP18)
# The downloaded High mesh is small enough for conventional instancing. Generate
# ordinary LODs during authoring, avoiding first-use Nanite compilation in play.
reduction=u.StaticMeshReductionOptions()
reduction.set_editor_property('auto_compute_lod_screen_size',False)
levels=[]
for percent,screen in ((1.0,1.0),(.45,.18),(.15,.06)):
    setting=u.StaticMeshReductionSettings()
    setting.set_editor_property('percent_triangles',percent)
    setting.set_editor_property('screen_size',screen)
    levels.append(setting)
reduction.set_editor_property('reduction_settings',levels)
mesh_editor.set_lods(rock,reduction)
save(rock)
REPORT['sources'].append({'file':str(fbx),'asset':rock_path})

# Soft references keep the new payload in the existing loading / resource-retention
# lifecycle. The current map already references this data asset; no map rewrite.
assets=load(BASE+'/DA_TemperateHillsStreaming')
assets.set_editor_property('ground_material',ground)
assets.set_editor_property('river_material',water)
assets.set_editor_property('river_rocks',[rock])
save(assets)
REPORT['references']={'water_normals':'/Game/WaterMaterials/Textures/T_River_Waves01_Normals',
    'foam':'/Game/WaterMaterials/Textures/T_Ocean_Foam','configuration':assets.get_path_name()}
(OUT/'authoring.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('TEMPERATE_RIVERS_AUTHORING_COMPLETE')
