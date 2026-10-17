"""Create the approved helmet material and native mesh; no scene changes or tests."""
import importlib,json,sys
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()));OUT=ROOT/'SourceAssets/IceArmor20261017/HelmetV5'
DEST='/Game/Skills/IceArmor20261017/HelmetV5';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
names=('M_IceHelmet_FirstPerson','SM_IceHelmet_FirstPerson')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() and any(E.does_asset_exist(DEST+'/'+name) for name in names):
    raise RuntimeError('End PIE before updating an existing helmet asset. First-time creation uses an independent package.')
sys.path.insert(0,str(ROOT/'Tools/Skills'))
import build_ice_armor_v2 as author
author=importlib.reload(author);author.SRC=OUT;author.DEST=DEST;author.RECEIPT=OUT/'assets-saved.json'
E.make_directory(DEST)
m=u.load_asset(DEST+'/'+names[0]) if E.does_asset_exist(DEST+'/'+names[0]) else u.AssetToolsHelpers.get_asset_tools().create_asset(names[0],DEST,u.Material,u.MaterialFactoryNew())
for previous in list(L.get_material_expressions(m)):L.delete_material_expression(m,previous)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
m.set_editor_property('two_sided',False);m.set_editor_property('disable_depth_test',True)
m.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_AFTER_DOF)
m.set_editor_property('refraction_method',u.RefractionMode.RM_NONE)
m.set_editor_property('enable_responsive_aa',True);m.set_editor_property('output_translucent_velocity',True)
def node(cls):return L.create_material_expression(m,cls)
def wire(a,p,b,q):
    if not L.connect_material_expressions(a,p,b,q):raise RuntimeError('Helmet material input: '+q)
def scalar(name,value):
    n=node(u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def vector(name,value):
    n=node(u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*value));return n
def custom(code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
    n=node(u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',kind)
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for name,(source,output) in inputs.items():wire(source,output,n,name)
    return n
def connect(n,prop):
    if not L.connect_material_property(n,'',prop):raise RuntimeError('Helmet material output: '+str(prop))
uv=node(u.MaterialExpressionTextureCoordinate);meta=node(u.MaterialExpressionTextureCoordinate);meta.set_editor_property('coordinate_index',2)
color=node(u.MaterialExpressionVertexColor);view=node(u.MaterialExpressionCameraVectorWS);position=node(u.MaterialExpressionWorldPosition)
tangent=node(u.MaterialExpressionTransform);tangent.set_editor_property('transform_source_type',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD);tangent.set_editor_property('transform_type',u.MaterialVectorCoordTransform.TRANSFORM_TANGENT);wire(view,'',tangent,'')
detail_uv=custom('return float2((UV.x-.5)*Aspect+.5,UV.y);',{'UV':(uv,''),'Aspect':(scalar('HelmetAspect',16/9),'')},u.CustomMaterialOutputType.CMOT_FLOAT2)
parallax=custom('float3 v=normalize(V);return clamp(v.xy/max(abs(v.z),.4),-1.2,1.2)*Depth*Thickness;',{'V':(tangent,''),'Depth':(scalar('InternalDepth',.026),''),'Thickness':(color,'B')},u.CustomMaterialOutputType.CMOT_FLOAT2)
crack_tex=node(u.MaterialExpressionTextureObject);crack_tex.set_editor_property('texture',author.load('/Game/Skills/IceSpike/T_IceCracks'))
cracks=custom('''float a=smoothstep(.10,.48,Texture2DSample(T,TSampler,UV*.82+P*.35).r);
float b=smoothstep(.13,.54,Texture2DSample(T,TSampler,UV*1.19+P*1.2).g);
float c=smoothstep(.15,.60,Texture2DSample(T,TSampler,UV*1.73+P*2.1).b);
return saturate((a*.58+b*.28+c*.12)*Contrast);''',{'T':(crack_tex,''),'UV':(detail_uv,''),'P':(parallax,''),'Contrast':(scalar('CrackContrast',.85),'')})
bubbles=custom('''float ring=0;float cavity=0;float2 bump=0;
[unroll] for(int layer=0;layer<2;layer++){
 float2 q=(UV+P*(layer+1.1))*float2(43+layer*14,43+layer*14);
 float2 cell=floor(q);float h=frac(sin(dot(cell,float2(127.1,311.7))+layer*37.4)*43758.5453);
 float2 centre=float2(frac(h*17.13),frac(h*31.71))*.55+.225;
 float2 d=frac(q)-centre;float radius=.065+frac(h*7.37)*.065;float dist=length(d)/radius;
 float enabled=step(1-Density,h);float edge=(1-smoothstep(.72,1.12,dist))*smoothstep(.35,.78,dist)*enabled;
 ring+=edge*(layer==0?1:.40);cavity+=(1-smoothstep(.2,.78,dist))*enabled;
 bump+=d/max(radius,.01)*(1-smoothstep(.2,1.15,dist))*enabled;
}return float4(saturate(ring),saturate(cavity),bump);''',{'UV':(detail_uv,''),'P':(parallax,''),'Density':(scalar('BubbleDensity',.07),'')},u.CustomMaterialOutputType.CMOT_FLOAT4)
surface=node(u.MaterialExpressionTextureSample);surface.set_editor_property('texture',author.load('/Game/Skills/IceWall/FabIceV3/T_IceSurfaceColor'));surface.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR);wire(detail_uv,'',surface,'UVs')
frost=custom('float cloud=saturate(dot(S,float3(.2126,.7152,.0722)));return saturate(pow(Rim,.85)*(.74+.24*cloud)+C*.10);',{'S':(surface,'RGB'),'Rim':(color,'R'),'C':(cracks,'')})
rim=custom('return pow(1-saturate(abs(dot(normalize(N),normalize(V)))),3);',{'N':(node(u.MaterialExpressionVertexNormalWS),''),'V':(view,'')})
coverage=custom('''float phase=.06+UV.y*.73;
float grown=smoothstep(phase-.10,phase+.14,Growth);
float seed=frac(sin(UV.x*27.2+UV.y*13.1)*31.17);
float end=1-smoothstep(.08+seed*.24,.46+seed*.24,Dissolve);
return grown*end*Fade;''',{'UV':(uv,''),'Growth':(scalar('Growth',1),''),'Dissolve':(scalar('Dissolve',0),''),'Fade':(scalar('Fade',1),'')})
hit=custom('return pow(saturate(1-distance(P,H.xyz)/25),2)*Impact;',{'P':(position,''),'H':(vector('HitPosition',(0,0,-10000,1)),''),'Impact':(scalar('Impact',0),'')})
wave=custom('return P*(1-smoothstep(.10,.25,abs(UV.y-Phase)));',{'UV':(uv,''),'P':(scalar('Pulse',0),''),'Phase':(scalar('PulsePhase',0),'')})
base=custom('float3 core=lerp(float3(.16,.34,.43),float3(.055,.16,.23),Thickness*.65);return lerp(core,float3(.61,.79,.87),saturate(F*.92+C*.14+B.x*.28));',{'Thickness':(color,'B'),'F':(frost,''),'C':(cracks,''),'B':(bubbles,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
opacity=custom('return saturate(Core+F*FrostOpacity+R*.13+C*.15+B.x*.11+H*.12)*Coverage;',{'Core':(scalar('CoreOpacity',.23),''),'FrostOpacity':(scalar('FrostOpacity',.58),''),'F':(frost,''),'R':(rim,''),'C':(cracks,''),'B':(bubbles,''),'H':(hit,''),'Coverage':(coverage,'')})
normal=node(u.MaterialExpressionTextureSample);normal.set_editor_property('texture',author.load('/Game/Ice/Textures/T_Ice6_normal'));normal.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL);wire(detail_uv,'',normal,'UVs')
normal_mix=custom('return normalize(float3(N.xy*Strength+B.zw*.035,N.z));',{'N':(normal,'RGB'),'B':(bubbles,''),'Strength':(scalar('NormalStrength',.23),'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
rough=custom('return clamp(.07+F*.30+B.y*.055,.07,.37);',{'F':(frost,''),'B':(bubbles,'')})
emission=custom('float steady=.018+F*.18+R*RimGlow+C*.10+B.x*.06;float event=P*(F*.52+C*.75)+H*(C*1.4+.12);return float3(.28,.57,.72)*(steady+event)*Coverage/max(Exposure,.05);',{'F':(frost,''),'R':(rim,''),'RimGlow':(scalar('RimGlow',.13),''),'C':(cracks,''),'B':(bubbles,''),'P':(wave,''),'H':(hit,''),'Coverage':(coverage,''),'Exposure':(node(u.MaterialExpressionEyeAdaptation),'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
for expr,prop in ((base,u.MaterialProperty.MP_BASE_COLOR),(opacity,u.MaterialProperty.MP_OPACITY),(normal_mix,u.MaterialProperty.MP_NORMAL),(rough,u.MaterialProperty.MP_ROUGHNESS),(emission,u.MaterialProperty.MP_EMISSIVE_COLOR),(scalar('Specular',.38),u.MaterialProperty.MP_SPECULAR)):connect(expr,prop)
errors=L.recompile_material(m)
if errors:raise RuntimeError('Ice helmet material compile: '+str(errors))
L.get_statistics(m) # Complete the required shader compilation before saving.
author.save(m);author.geometry(names[1],m,None,None)
(OUT/'material-parameters.json').write_text(json.dumps({str(k):L.get_material_default_scalar_parameter_value(m,k) for k in L.get_scalar_parameter_names(m)},indent=2),encoding='utf-8')
print('ICE_HELMET_V5_ASSETS_SAVED '+str(len(author.saved)),flush=True)
