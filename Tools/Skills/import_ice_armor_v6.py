"""Create and save ThirdPersonV6 materials and native Jason skeletal armour."""
import importlib,json,sys
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
OUT=ROOT/'SourceAssets/IceArmor20261017/ThirdPersonV6'
DEST='/Game/Skills/IceArmor20261017/ThirdPersonV6'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
manifest=json.loads((OUT/'geometry-manifest.json').read_text(encoding='utf-8'))
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() and any(E.does_asset_exist(DEST+'/'+n) for n in ['M_IceArmorV6_World']+[entry['name'] for entry in manifest['assets']]):
    raise RuntimeError('End PIE before replacing an existing armour package; first-time creation uses independent assets.')
sys.path.insert(0,str(ROOT/'Tools/Skills'))
import build_ice_armor_v2 as author
author=importlib.reload(author);author.SRC=OUT;author.DEST=DEST;author.RECEIPT=OUT/'assets-saved.json'
E.make_directory(DEST)
name='M_IceArmorV6_World'
m=u.load_asset(DEST+'/'+name) if E.does_asset_exist(DEST+'/'+name) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
for previous in list(L.get_material_expressions(m)):L.delete_material_expression(m,previous)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
m.set_editor_property('two_sided',False);m.set_editor_property('disable_depth_test',False)
m.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
m.set_editor_property('refraction_method',u.RefractionMode.RM_INDEX_OF_REFRACTION)
m.set_editor_property('enable_responsive_aa',True);m.set_editor_property('output_translucent_velocity',True)
L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)

def node(cls):return L.create_material_expression(m,cls)
def wire(a,p,b,q):
    if not L.connect_material_expressions(a,p,b,q):raise RuntimeError('Ice armour input '+q)
def scalar(k,v):
    n=node(u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',k);n.set_editor_property('default_value',v);return n
def vector(k,v):
    n=node(u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',k);n.set_editor_property('default_value',u.LinearColor(*v));return n
def custom(code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
    n=node(u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',kind)
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for key,(expr,pin) in inputs.items():wire(expr,pin,n,key)
    return n
def out(n,prop):
    if not L.connect_material_property(n,'',prop):raise RuntimeError('Ice armour output '+str(prop))

uv=node(u.MaterialExpressionTextureCoordinate)
fit=node(u.MaterialExpressionTextureCoordinate);fit.set_editor_property('coordinate_index',1)
region=node(u.MaterialExpressionTextureCoordinate);region.set_editor_property('coordinate_index',2)
color=node(u.MaterialExpressionVertexColor);view=node(u.MaterialExpressionCameraVectorWS)
position=node(u.MaterialExpressionWorldPosition)
tangent=node(u.MaterialExpressionTransform)
tangent.set_editor_property('transform_source_type',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
tangent.set_editor_property('transform_type',u.MaterialVectorCoordTransform.TRANSFORM_TANGENT);wire(view,'',tangent,'')
depth=custom('float3 v=normalize(V);return clamp(v.xy/max(abs(v.z),.40),-1.2,1.2)*Depth*Thickness;',{'V':(tangent,''),'Depth':(scalar('InternalDepth',.035),''),'Thickness':(color,'B')},u.CustomMaterialOutputType.CMOT_FLOAT2)
tex=node(u.MaterialExpressionTextureObject);tex.set_editor_property('texture',author.load('/Game/Skills/IceSpike/T_IceCracks'))
cracks=custom('''float a=smoothstep(.10,.48,Texture2DSample(T,TSampler,UV*.82+P*.35).r);
float b=smoothstep(.13,.54,Texture2DSample(T,TSampler,UV*1.19+P*1.2).g);
float c=smoothstep(.15,.60,Texture2DSample(T,TSampler,UV*1.73+P*2.1).b);
return saturate((a*.58+b*.28+c*.12)*Contrast);''',{'T':(tex,''),'UV':(uv,''),'P':(depth,''),'Contrast':(scalar('CrackContrast',.90),'')})
bubbles=custom('''float ring=0;float cavity=0;float2 bump=0;
[unroll] for(int layer=0;layer<2;layer++){
 float2 q=(UV+P*(layer+1.1))*(43+layer*14);
 float2 cell=floor(q);float h=frac(sin(dot(cell,float2(127.1,311.7))+layer*37.4)*43758.5453);
 float2 centre=float2(frac(h*17.13),frac(h*31.71))*.55+.225;
 float2 d=frac(q)-centre;float radius=.065+frac(h*7.37)*.065;float dist=length(d)/radius;
 float enabled=step(1-Density,h);float edge=(1-smoothstep(.72,1.12,dist))*smoothstep(.35,.78,dist)*enabled;
 ring+=edge*(layer==0?1:.40);cavity+=(1-smoothstep(.2,.78,dist))*enabled;
 bump+=d/max(radius,.01)*(1-smoothstep(.2,1.15,dist))*enabled;
}return float4(saturate(ring),saturate(cavity),bump);''',{'UV':(uv,''),'P':(depth,''),'Density':(scalar('BubbleDensity',.055),'')},u.CustomMaterialOutputType.CMOT_FLOAT4)
surface=node(u.MaterialExpressionTextureSample);surface.set_editor_property('texture',author.load('/Game/Skills/IceWall/FabIceV3/T_IceSurfaceColor'));surface.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR);wire(uv,'',surface,'UVs')
frost=custom('float cloud=saturate(dot(S,float3(.2126,.7152,.0722)));return saturate(pow(Rim,.85)*(.76+.22*cloud)+C*.08);',{'S':(surface,'RGB'),'Rim':(color,'R'),'C':(cracks,'')})
rim=custom('return pow(1-saturate(abs(dot(normalize(N),normalize(V)))),3);',{'N':(node(u.MaterialExpressionVertexNormalWS),''),'V':(view,'')})
coverage=custom('''float grown=smoothstep(Fit.y-.08,Fit.y+.17,Growth);
float seed=frac(sin(dot(floor(UV*19),float2(12.9898,78.233)))*43758.5453);
float end=1-smoothstep(.06+seed*.25,.48+seed*.25,Dissolve);
float pack=1-Back*smoothstep(.20,.78,Fit.x);
float thigh=1-Thigh*step(.67,Zone)*step(Zone,.83);
return grown*end*Fade*pack*thigh;''',{'Fit':(fit,''),'UV':(uv,''),'Zone':(color,'G'),'Growth':(scalar('Growth',1),''),'Dissolve':(scalar('Dissolve',0),''),'Fade':(scalar('Fade',1),''),'Back':(scalar('HideBack',0),''),'Thigh':(scalar('HideThigh',0),'')})
hit=custom('return pow(saturate(1-distance(P,H.xyz)/30),2)*Impact;',{'P':(position,''),'H':(vector('HitPosition',(0,0,-10000,1)),''),'Impact':(scalar('Impact',0),'')})
wave=custom('return Pulse*(1-smoothstep(.07,.20,abs(Height-Phase)));',{'Pulse':(scalar('Pulse',0),''),'Height':(custom('return UV.x;',{'UV':(region,'')}),''),'Phase':(scalar('PulsePhase',0),'')})
base=custom('float3 core=lerp(float3(.13,.28,.36),float3(.055,.145,.21),Thickness*.65);return lerp(core,float3(.64,.80,.88),saturate(F*.92+C*.15+B.x*.27));',{'Thickness':(color,'B'),'F':(frost,''),'C':(cracks,''),'B':(bubbles,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
opacity=custom('return saturate(Core+F*FrostOpacity+R*.13+C*.14+B.x*.12+H*.14)*Coverage;',{'Core':(scalar('CoreOpacity',.34),''),'FrostOpacity':(scalar('FrostOpacity',.52),''),'F':(frost,''),'R':(rim,''),'C':(cracks,''),'B':(bubbles,''),'H':(hit,''),'Coverage':(coverage,'')})
normal=node(u.MaterialExpressionTextureSample);normal.set_editor_property('texture',author.load('/Game/Ice/Textures/T_Ice6_normal'));normal.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL);wire(uv,'',normal,'UVs')
normal_mix=custom('return normalize(float3(N.xy*Strength+B.zw*.03,N.z));',{'N':(normal,'RGB'),'B':(bubbles,''),'Strength':(scalar('NormalStrength',.22),'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
rough=custom('return clamp(.075+F*.30+B.y*.055,.075,.38);',{'F':(frost,''),'B':(bubbles,'')})
emission=custom('float steady=.015+F*.16+R*RimGlow+C*.09+B.x*.04;float event=Pulse*(F*.48+C*.65)+H*(C*1.3+.11);return float3(.28,.57,.72)*(steady+event)*Coverage/max(Exposure,.05);',{'F':(frost,''),'R':(rim,''),'RimGlow':(scalar('RimGlow',.09),''),'C':(cracks,''),'B':(bubbles,''),'Pulse':(wave,''),'H':(hit,''),'Coverage':(coverage,''),'Exposure':(node(u.MaterialExpressionEyeAdaptation),'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
for expression,prop in ((base,u.MaterialProperty.MP_BASE_COLOR),(opacity,u.MaterialProperty.MP_OPACITY),(normal_mix,u.MaterialProperty.MP_NORMAL),(rough,u.MaterialProperty.MP_ROUGHNESS),(emission,u.MaterialProperty.MP_EMISSIVE_COLOR),(scalar('Specular',.38),u.MaterialProperty.MP_SPECULAR),(scalar('IceRefraction',1.015),u.MaterialProperty.MP_REFRACTION)):out(expression,prop)
errors=L.recompile_material(m)
if errors:raise RuntimeError('World ice armour shader compile: '+str(errors))
L.get_statistics(m)
author.save(m)
target=author.load('/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body')
native,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(target,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot copy the native Jason reference skeleton.')
for entry in manifest['assets']:
    author.geometry(entry['name'],m,native,target)
    print('ICE_ARMOR_V6_SAVED '+entry['name'],flush=True)
(OUT/'material-parameters.json').write_text(json.dumps({str(k):L.get_material_default_scalar_parameter_value(m,k) for k in L.get_scalar_parameter_names(m)},indent=2),encoding='utf-8')
print('ICE_ARMOR_V6_ASSETS_SAVED '+str(len(author.saved)),flush=True)
