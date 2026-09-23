"""Create dedicated fracture and viscous-fluid materials; preserve original monster/fountain assets."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/HazardPolish20260922'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
(ROOT/'Receipts').mkdir(exist_ok=True)
receipt={'saved':[],'tests_run':False}
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    (ROOT/'Receipts/materials.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Required asset missing '+path)
    return asset
def instance(name,parent):
    obj=u.load_asset(BASE+'/Materials/'+name)
    if not obj:obj=A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    obj.modify();L.set_material_instance_parent(obj,parent);return obj
data=json.loads((ROOT/'Authored/materials.json').read_text())
textures={}
for channel,filename in data['channels'].items():
    task=u.AssetImportTask();task.filename=filename;task.destination_path=BASE+'/Textures';task.destination_name='T_FractureAggregate_'+channel
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;A.import_asset_tasks([task])
    tex=load(task.destination_path+'/'+task.destination_name);tex.set_editor_property('srgb',channel=='BaseColor')
    if channel=='Normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
    elif channel=='Height':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_HALF_FLOAT)
    elif channel=='Surface':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(tex);textures[channel]=tex
fracture=instance('MI_FracturedConcrete',load('/Game/Dungeons/AtmosphereV2/WallRelief/Materials/M_WallMortarRelief'))
for channel,tex in textures.items():L.set_material_instance_texture_parameter_value(fracture,channel+'Texture',tex)
for key,value in {'WallReliefDepthCm':data['height_range_cm'],'WallTileSizeCm':64,'WallNormalStrength':1,'WallMacroAmount':.025,'WallSpecular':.22}.items():L.set_material_instance_scalar_parameter_value(fracture,key,value)
L.update_material_instance(fracture);save(fracture)

path=BASE+'/Materials/M_DungeonViscousPus'
mat=u.load_asset(path) or E.duplicate_asset('/Game/Monsters/FatZombieMeshy/Pus/M_FatZombie_Pus',path)
mat.modify();L.delete_all_material_expressions(mat)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
mat.set_editor_property('two_sided',True)
mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
def node(cls):return L.create_material_expression(mat,cls)
def wire(source,target,pin):
    n,output=source if isinstance(source,tuple) else (source,'')
    if not L.connect_material_expressions(n,output,target,pin):raise RuntimeError('Connection failed '+pin)
def out(source,name):
    if not L.connect_material_property(source,'',getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError('Output failed '+name)
def scalar(name,value):
    n=node(u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def color(name,value):
    n=node(u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*value,1));return n
def custom(code,inputs,width=3):
    n=node(u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    entries=[]
    for name in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',name);entries.append(p)
    n.set_editor_property('inputs',entries)
    for key,source in inputs.items():wire(source,n,key)
    return n
def sample(path,uv,normal=False):
    texture=load(path);n=node(u.MaterialExpressionTextureSample);n.set_editor_property('texture',texture)
    decoded=normal and texture.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_NORMALMAP
    n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if decoded else u.MaterialSamplerType.SAMPLERTYPE_COLOR if texture.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    n.set_editor_property('sampler_source',u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS);wire(uv,n,'UVs')
    # Fountain pack contains both raw linear normals and BC5 normals. Match each asset,
    # without changing texture settings used by the already accepted fountain.
    return custom('return N*2-1;',{'N':n}) if normal and not decoded else n
uv=node(u.MaterialExpressionTextureCoordinate);time=node(u.MaterialExpressionTime);vc=node(u.MaterialExpressionVertexColor)
speed=scalar('FlowSpeed',.027)
uv_a=custom('return UV*.73+float2(sin(UV.y*1.7+T*.15)*.024,-T*Speed);',{'UV':uv,'T':time,'Speed':speed},2)
uv_b=custom('return UV*1.63+float2(.31+T*Speed*.23,-T*Speed*.63);',{'UV':uv,'T':time,'Speed':speed},2)
na=sample('/Game/WaterMaterials/Textures/T_Lake_Waves01_Normals',uv_a,True)
nb=sample('/Game/WaterMaterials/Textures/T_Water_Normal',uv_b,True)
density_uv=custom('return UV*.48+float2(A.x,A.y)*.055+float2(0,-T*S*.31);',{'UV':uv,'A':na,'T':time,'S':speed},2)
density=sample('/Game/RuralAustralia/Water/T_Water_01_M',density_uv)
features=custom('''float2 cell=floor(UV/.45); float2 q=frac(UV/.45)-.5;
float h=frac(sin(dot(cell,float2(127.1,311.7)))*43758.5453);
q-=(float2(h,frac(h*7.17))-.5)*.28;
float2 p=q*.45;float d=length(p);float age=frac(T/(5.0+h*3.7)+h*5.3);
float radius=lerp(.012,.091,smoothstep(.54,.98,age));
float active=smoothstep(.57,.7,age)*(1-smoothstep(.93,1.,age))*step(.62,h);
float ring=exp(-pow((d-radius)/.008,2))*active;
float2 slope=(d>.001?p/d:float2(0,0))*ring*.22;
float wave=sin(UV.y*6.7-T*.62+sin(UV.x*3.7))*.34+sin(UV.x*10.1+UV.y*3.1-T*.43)*.15;
return float4(slope,ring,wave+ring*.12);''',{'UV':uv,'T':time},4)
base=custom('return lerp(lerp(Thin,Dense,saturate(D.r*.75+D.g*.2)),Scum,F.b*.3);',{'Thin':color('ThinTint',(.24,.35,.035)),'Dense':color('DenseTint',(.075,.15,.012)),'Scum':color('ScumTint',(.34,.43,.065)),'D':density,'F':features})
out(base,'BASE_COLOR')
normal=custom('return normalize(float3((A.xy+B.xy*.53)*Strength+F.rg,1));',{'A':na,'B':nb,'F':features,'Strength':scalar('NormalStrength',.24)})
out(normal,'NORMAL')
out(custom('return clamp(.095+D.r*.055+F.b*.1,.08,.29);',{'D':density,'F':features},1),'ROUGHNESS')
out(scalar('Specular',.72),'SPECULAR');out(scalar('Metallic',0),'METALLIC')
fres=node(u.MaterialExpressionFresnel)
out(custom('return saturate(.82+D.r*.075+F*.075);',{'D':density,'F':fres},1),'OPACITY')
out(custom('return float3(0,0,F.a*Height*V.r);',{'F':features,'Height':scalar('WaveHeightCm',.85),'V':vc}),'WORLD_POSITION_OFFSET')
out(custom('return Base*.035;',{'Base':base}),'EMISSIVE_COLOR')
out(scalar('Refraction',1.008),'REFRACTION')
L.layout_material_expressions(mat)
errors=L.recompile_material(mat)
if errors:raise RuntimeError('Fluid material compilation failed '+str(errors))
save(mat)
mi=instance('MI_DungeonViscousPus',mat);L.update_material_instance(mi);save(mi)
receipt['stage']='materials_saved';receipt['reuse']=['FatZombie corrosion palette','Fountain dual normal flow, surface lighting, analytic ripple method','Existing water normal and density textures']
(ROOT/'Receipts/materials.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('DUNGEON_HAZARD_MATERIALS_SAVED',len(receipt['saved']))
