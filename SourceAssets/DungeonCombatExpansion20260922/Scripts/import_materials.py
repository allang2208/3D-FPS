"""New dedicated parents; reuse fountain texture encoding and coherent height/normal math."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/CombatExpansion20260922';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
saved=[]
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    saved.append(a.get_path_name());(ROOT/'Receipts/materials.json').write_text(json.dumps({'saved':saved,'tests_run':False},indent=2))
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing dependency '+p)
    return a
def node(k):return L.create_material_expression(mat,getattr(u,'MaterialExpression'+k))
def wire(src,dst,pin):
    a,output=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_expressions(a,output,dst,pin):raise RuntimeError('Wire '+pin)
def out(src,p):
    if not L.connect_material_property(src,'',getattr(u.MaterialProperty,'MP_'+p)):raise RuntimeError('Output '+p)
def scalar(name,v):
    a=node('ScalarParameter');a.set_editor_property('parameter_name',name);a.set_editor_property('default_value',v);return a
def color(name,v):
    a=node('VectorParameter');a.set_editor_property('parameter_name',name);a.set_editor_property('default_value',u.LinearColor(*v,1));return a
def custom(code,inputs,w=3):
    a=node('Custom');a.set_editor_property('code',code);a.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(w)));pins=[]
    for key in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
    a.set_editor_property('inputs',pins)
    for k,v in inputs.items():wire(v,a,k)
    return a
def sample(path,uv,normal=False):
    tex=load(path);a=node('TextureSample');a.set_editor_property('texture',tex);compression=tex.get_editor_property('compression_settings');decoded=normal and compression==u.TextureCompressionSettings.TC_NORMALMAP
    mode='NORMAL' if decoded else 'MASKS' if compression==u.TextureCompressionSettings.TC_MASKS else 'COLOR' if tex.get_editor_property('srgb') else 'LINEAR_COLOR'
    a.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+mode));a.set_editor_property('sampler_source',u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS);wire(uv,a,'UVs')
    return custom('return N*2-1;',{'N':a}) if normal and not decoded else a
def make(name,fluid=False):
    global mat
    path=BASE+'/Materials/'+name;mat=u.load_asset(path)
    if mat:return False
    mat=A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    if fluid:
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        mat.set_editor_property('two_sided',True);mat.set_editor_property('tangent_space_normal',False)
        mat.set_editor_property('screen_space_reflections',True)
    return True
def finish():
    L.layout_material_expressions(mat);errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Material build failed '+str(errors))
    save(mat)
def instance(name,parent,params):
    mi=u.load_asset(BASE+'/Materials/'+name) or A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    mi.modify();L.set_material_instance_parent(mi,parent)
    for k,v in params.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
    L.update_material_instance(mi);save(mi);return mi

for key,path in json.loads((ROOT/'Authored/pipe-textures.json').read_text()).items():
    name='T_PipeEnamel_'+key
    if E.does_asset_exist(BASE+'/Textures/'+name):continue
    task=u.AssetImportTask();task.filename=path;task.destination_path=BASE+'/Textures';task.destination_name=name;task.automated=True;task.save=False;A.import_asset_tasks([task])
    tex=load(BASE+'/Textures/'+name);tex.set_editor_property('srgb',key=='BaseColor')
    if key=='Normal':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
    if key=='Surface':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(tex)
for name in ['M_PipeEnamel','M_PipeInner','M_PipeCutSteel','M_BridgeDeck']:
    if not make(name):continue
    uv=node('TextureCoordinate');n=sample(BASE+'/Textures/T_PipeEnamel_Normal',uv,True);s=sample(BASE+'/Textures/T_PipeEnamel_Surface',uv)
    if name=='M_PipeEnamel':
        out(sample(BASE+'/Textures/T_PipeEnamel_BaseColor',uv),'BASE_COLOR');out(custom('return S.r;',{'S':s},1),'ROUGHNESS');out(custom('return S.g;',{'S':s},1),'METALLIC')
    else:
        colors={'M_PipeInner':(.075,.088,.060),'M_PipeCutSteel':(.22,.25,.24),'M_BridgeDeck':(.085,.11,.097)}
        out(color('FinishColor',colors[name]),'BASE_COLOR');out(scalar('Roughness',.26 if name=='M_PipeInner' else .31 if name=='M_PipeCutSteel' else .42),'ROUGHNESS');out(scalar('Metallic',.5 if name=='M_PipeInner' else .88 if name=='M_PipeCutSteel' else .48),'METALLIC')
    out(custom('return normalize(float3(N.xy*.45,N.z));',{'N':n}),'NORMAL');out(scalar('Specular',.45),'SPECULAR');finish()

if make('M_PusFluidV2',True):
    uv=node('TextureCoordinate');time=node('Time');vc=node('VertexColor');camera=node('CameraVectorWS')
    speed=scalar('FlowSpeed',.055)
    ua=custom('return UV*.42+float2(T*S*.24,-T*S);',{'UV':uv,'T':time,'S':speed},2)
    ub=custom('return UV*1.19+float2(-T*S*.31,T*S*.62);',{'UV':uv,'T':time,'S':speed},2)
    na=sample('/Game/WaterMaterials/Textures/T_Lake_Waves01_Normals',ua,True);nb=sample('/Game/WaterMaterials/Textures/T_Water_Normal',ub,True)
    noise=sample('/Game/Props/RomanFountain20260917/OverflowV8/T_FountainFlowNoiseV8',ua)
    # Analytic H and dH/dx,dH/dy are shared by WPO and world-space normal, as in the fountain.
    wave=custom('''float p1=dot(UV,float2(.954,.300))*2.244-T*.87;
float p2=dot(UV,float2(-.482,.876))*3.927-T*1.23;
float h=sin(p1)*1.20+sin(p2)*.58;
float2 g=cos(p1)*1.20*2.244*float2(.954,.300)+cos(p2)*.58*3.927*float2(-.482,.876);
float foam=0;
for(int i=0;i<3;i++) {
 float phase=i==0?0:(i==1?.34:.73);
 float age=frac(T/1.55+phase-Fall/1.55)*1.55;
 float2 center=float2(0,i==0?0:(i==1?.037:-.032));
 float2 delta=UV-center;float dist=length(delta);float radius=age*.61;
 float q=(dist-radius)/.040;float env=exp(-q*q)*exp(-age*3.3);
 float hh=.20*env*Impact;h+=hh;
 g+=(-2*q/.040)*hh*delta/max(dist,.008);
 foam+=env*Impact*.13;
}
return float4(h,g,foam);''',{'UV':uv,'T':time,'Impact':scalar('ImpactStrength',0),'Fall':scalar('DropFallSeconds',.515)},4)
    height=scalar('WaveScale',1);normal=custom('return normalize(float3((-W.gb/100.0*Height*Slope+(A.xy+B.xy*.42)*Micro)*float2(1,-1),1));',{'W':wave,'Height':height,'Slope':scalar('NormalSlope',1.7),'A':na,'B':nb,'Micro':scalar('MicroNormalStrength',.18)})
    out(normal,'NORMAL');out(custom('return float3(0,0,W.r*Height*V.r);',{'W':wave,'Height':height,'V':vc}),'WORLD_POSITION_OFFSET')
    depth=node('SceneDepth');pixel=node('PixelDepth');depthamount=custom('return saturate(max(0,D-P)/Scale);',{'D':depth,'P':pixel,'Scale':scalar('DepthScaleCm',12)},1)
    fres=custom('return pow(1-saturate(dot(N,V)),5);',{'N':normal,'V':camera},1)
    base=custom('return lerp(Shallow,Deep,saturate(D*.82+Noise.r*.12));',{'Shallow':color('ShallowTint',(.15,.245,.045)),'Deep':color('DeepTint',(.027,.074,.018)),'D':depthamount,'Noise':noise})
    out(base,'BASE_COLOR');out(scalar('Roughness',.085),'ROUGHNESS');out(scalar('Specular',.65),'SPECULAR');out(scalar('Metallic',0),'METALLIC')
    opacity=custom('return V.r*min(.83,Base+Depth*.34+F*.48+Wave.a);',{'V':vc,'Base':scalar('BaseOpacity',.22),'Depth':depthamount,'F':fres,'Wave':wave},1)
    fade=node('DepthFade');wire(opacity,fade,'Opacity');wire(scalar('ContactFadeCm',.45),fade,'FadeDistance');out(fade,'OPACITY')
    # Indoor reflections come from the scene; no emissive outdoor cubemap or opaque scum overlay.
    out(custom('return C*.014;',{'C':base}),'EMISSIVE_COLOR');finish()
parent=load(BASE+'/Materials/M_PusFluidV2');fluids=json.loads((ROOT/'Authored/fluids.json').read_text())
instance('MI_PusChannelFluid',parent,{'WaveScale':1.05,'NormalSlope':1.65,'ImpactStrength':0,'BaseOpacity':.23,'DepthScaleCm':15,'Roughness':.075})
instance('MI_PusPuddleFluid',parent,{'WaveScale':.16,'NormalSlope':2.1,'ImpactStrength':2.5,'BaseOpacity':.18,'DepthScaleCm':4,'Roughness':.065,'DropFallSeconds':fluids['falltime'],'MicroNormalStrength':.12})

for name in ['M_PusDrops','M_PusTongue']:
    if not make(name,True):continue
    uv=node('TextureCoordinate');time=node('Time');vc=node('VertexColor')
    out(color('SlimeTint',(.085,.19,.025)),'BASE_COLOR');out(scalar('Roughness',.065),'ROUGHNESS');out(scalar('Specular',.72),'SPECULAR');out(scalar('Metallic',0),'METALLIC')
    if name=='M_PusDrops':
        age=custom('return frac(T/1.55+UV.x)*1.55;',{'T':time,'UV':uv},1)
        out(custom('float t=min(A,UV.y);return float3(11*t/UV.y,0,-250*t*t);',{'A':age,'UV':uv}),'WORLD_POSITION_OFFSET')
        out(custom('return (1-step(UV.y,A))*.85;',{'A':age,'UV':uv},1),'OPACITY')
    else:
        out(custom('return float3(sin(T*2.2+UV.y*4)*.27*V.r,sin(T*1.8+UV.y*3)*.20*V.r,0);',{'UV':uv,'T':time,'V':vc}),'WORLD_POSITION_OFFSET')
        out(scalar('Opacity',.78),'OPACITY')
    finish()
print('COMBAT_FLUID_PIPE_MATERIALS_SAVED',len(saved))
