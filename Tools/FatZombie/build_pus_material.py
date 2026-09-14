"""Author an independent pus film from the project's existing river-water recipe.

Reuses installed water textures; no texture generation, gameplay, or preview run.
Can run in the existing FatZombieAuthoring host with the source dependencies copied in.
"""
import json
from pathlib import Path
import unreal as u

DEST = '/Game/Monsters/FatZombieMeshy/Pus'
SOURCE = '/Game/WorldGeneration/TemperateHills/Rivers/M_TemperateRiverWater'
OUT = Path('D:/FPS3D/FPSGAME/Saved/FatZombiePus')
OUT.mkdir(parents=True, exist_ok=True)
lib = u.MaterialEditingLibrary
assets = u.EditorAssetLibrary
tools = u.AssetToolsHelpers.get_asset_tools()
assets.make_directory(DEST)

def load(path):
    obj = u.load_asset(path)
    if not obj: raise RuntimeError('Missing pus source asset: '+path)
    return obj

path = DEST+'/M_FatZombie_Pus'
mat = load(path) if assets.does_asset_exist(path) else assets.duplicate_asset(SOURCE, path)
if not mat: raise RuntimeError('Could not derive pus material from river water')
lib.delete_all_material_expressions(mat)
mat.set_editor_property('blend_mode', u.BlendMode.BLEND_MASKED)
mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
mat.set_editor_property('two_sided', True)
mat.set_editor_property('opacity_mask_clip_value', .333)

def node(cls): return lib.create_material_expression(mat, cls)
def wire(source, dest, pin):
    expression, output_pin = source if isinstance(source, tuple) else (source, '')
    if not lib.connect_material_expressions(expression, output_pin, dest, pin): raise RuntimeError('Material connection failed: '+pin)
def output(source, name):
    if not lib.connect_material_property(source, '', getattr(u.MaterialProperty, 'MP_'+name)): raise RuntimeError('Material output failed: '+name)
def scalar(name, value):
    n=node(u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name', name);n.set_editor_property('default_value', value)
    return n
def color(name, value):
    n=node(u.MaterialExpressionVectorParameter)
    n.set_editor_property('parameter_name', name);n.set_editor_property('default_value', u.LinearColor(*value,1))
    return n
def custom(code, inputs, width=3):
    n=node(u.MaterialExpressionCustom)
    n.set_editor_property('code',code)
    n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    entries=[]
    for name in inputs:
        entry=u.CustomInput();entry.set_editor_property('input_name',name);entries.append(entry)
    n.set_editor_property('inputs',entries)
    for name, value in inputs.items(): wire(value,n,name)
    return n

textures=[]
def sample(path, uv, normal=False):
    texture=load(path);textures.append(path)
    n=node(u.MaterialExpressionTextureSample)
    n.set_editor_property('texture',texture)
    sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else (u.MaterialSamplerType.SAMPLERTYPE_COLOR if texture.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    n.set_editor_property('sampler_type',sampler)
    n.set_editor_property('sampler_source',u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
    wire(uv,n,'UVs')
    return n

uv=node(u.MaterialExpressionTextureCoordinate)
time=node(u.MaterialExpressionTime)
mask=node(u.MaterialExpressionVertexColor)
speed=scalar('FlowSpeed',.007)
variation=scalar('Variation',.5)
visibility=scalar('Visibility',1.)
spread=scalar('SpreadProgress',1.)
dry=scalar('Dryness',0.)
normal_strength=scalar('NormalStrength',.055)
uv_a=custom('return UV*.8+float2(V*7.13,V*3.71)+float2(T*Speed,T*Speed*.43);',{'UV':uv,'T':time,'Speed':speed,'V':variation},2)
uv_b=custom('return UV*1.73+float2(V*13.1,2.73)-float2(T*Speed*.71,-T*Speed*.31);',{'UV':uv,'T':time,'Speed':speed,'V':variation},2)
wave_a=sample('/Game/WaterMaterials/Textures/T_River_Waves01_Normals',uv_a,True)
wave_b=sample('/Game/WaterMaterials/Textures/T_River_Waves02_Normals',uv_b,True)
foam=sample('/Game/WaterMaterials/Textures/T_Ocean_Foam',uv_b)
dirt_uv=custom('return UV*.37+float2(V*3.3,V*.73);',{'UV':uv,'V':variation},2)
dirt=sample('/Game/RuralAustralia/Water/T_Water_01_M',dirt_uv)
cloud=custom('return saturate(M.r*.55+M.g*.3+M.b*.15);',{'M':dirt},1)
scum=custom('return smoothstep(.78,.97,F.r)*(.12+.22*V.r);',{'F':foam,'V':mask},1)
thin=color('ThinTint',(.26,.34,.035))
dense=color('DenseTint',(.12,.17,.015))
cream=color('ScumTint',(.43,.46,.10))
base=custom('''float density=saturate(V.r*.68+Cloud*.27+V.g*.08);
float3 c=lerp(Thin,Dense,density);
c=lerp(c,Cream,Scum);
float grey=dot(c,float3(.2126,.7152,.0722));
return lerp(c,float3(grey*.63,grey*.58,grey*.36),Dry*.7);''',
    {'Thin':thin,'Dense':dense,'Cream':cream,'V':mask,'Cloud':cloud,'Scum':scum,'Dry':dry})
output(base,'BASE_COLOR')
output(custom('return normalize(float3((A.xy+B.xy*.55)*Strength*(1-Dry*.8),1));',{'A':wave_a,'B':wave_b,'Strength':normal_strength,'Dry':dry}),'NORMAL')
output(custom('return lerp(.11+Cloud*.10+Scum*.22,.72,Dry);',{'Cloud':cloud,'Scum':scum,'Dry':dry},1),'ROUGHNESS')
output(scalar('Specular',.65),'SPECULAR')
output(scalar('Metallic',0.),'METALLIC')
# Pus is turbid residue, not transparent river water. Its wet PBR surface writes
# normal scene depth; only the outer coverage fringe and final drying fade use
# temporal coverage. Do not multiply a millimetre film by SceneDepth-PixelDepth:
# a near-coplanar ground sample can erase the entire visible surface.
# VertexColor's default output is RGB; coverage comes from its separate Alpha.
opacity=custom('''float wet=Spread>=.9999?1:smoothstep(Arrival-.02,Arrival+.02,Spread);
return smoothstep(0,.22,Coverage)*saturate(Visible)*wet;''',
    {'Coverage':(mask,'A'),'Arrival':(mask,'B'),'Visible':visibility,'Spread':spread},1)
dither=node(u.MaterialExpressionMaterialFunctionCall)
dither.set_editor_property('material_function', load('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
alpha_pin = lib.get_material_expression_input_names(dither)[0]
wire(opacity,dither,alpha_pin);output(dither,'OPACITY_MASK')
lib.layout_material_expressions(mat)
compile_errors = lib.recompile_material(mat)
if compile_errors:
    raise RuntimeError('Pus material shader compilation failed: ' + '; '.join(compile_errors))
if not assets.save_loaded_asset(mat,False): raise RuntimeError('Could not save pus material')

instance_path=DEST+'/MI_FatZombie_Pus'
instance=load(instance_path) if assets.does_asset_exist(instance_path) else tools.create_asset('MI_FatZombie_Pus',DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
lib.set_material_instance_parent(instance,mat)
for name,value in {'FlowSpeed':.007,'NormalStrength':.055,'Specular':.65,'Metallic':0.,'Visibility':1.,'Dryness':0.,'SpreadProgress':1.}.items():
    lib.set_material_instance_scalar_parameter_value(instance,name,value)
lib.update_material_instance(instance)
if not assets.save_loaded_asset(instance,False): raise RuntimeError('Could not save pus instance')
report={'source_material':SOURCE,'source_recipe':'Tools/WorldGeneration/build_temperate_rivers.py',
        'reused_textures':textures,'created':[mat.get_path_name(),instance.get_path_name()],
        'scope':'material authoring only; no gameplay, rendering or visual acceptance',
        'changes':'masked wet PBR; vertex B arrival field reveals expanding film and staggered drops using SpreadProgress; vertex Alpha retains final coverage and drying fade; existing water normals and colors retained',
        'material_compile_errors':list(compile_errors)}
(OUT/'material_authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('FAT_PUS_MATERIAL_SAVED')
