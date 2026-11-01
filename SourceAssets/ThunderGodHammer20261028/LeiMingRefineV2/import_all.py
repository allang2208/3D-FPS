"""Publish only the approved Lei Ming visual refinement; gameplay is unchanged."""
from pathlib import Path
import json, shutil, os
import unreal as u

P=Path(__file__).resolve().parent
R=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
ROOT='/Game/Weapons/ThunderGodHammer20261028/LeiMingRefineV2'
TEXROOT='/Game/Weapons/ThunderGodHammer20261028/ExclusiveRunesV1/Textures'
SHARED='/Game/Weapons/MeleeRunes20260915/SurfaceV2'
NAME='M_SilverRuneSurface_LeiMingRefineV2'
ICON='ue_thunder_god_hammer_blade_2_lei_ming_rune'
targets=[SHARED+'/T_Mask_lei_ming_rune',ROOT+'/'+NAME,
    '/Game/ColdSteelData/AttachmentIcons20260913/'+ICON]
targets += [TEXROOT+'/T_'+x+'_lei_ming_rune' for x in ('Normal','Roughness','Height')]
for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if pkg.get_name() in targets:raise RuntimeError('Preserve unsaved asset: '+pkg.get_name())
receipt=dict(complete=False,saved_assets=[],runtime_tested=False,
    approved_design=str(P.parent/'LeiMingConceptV2/lei_ming_rune_design_v2.png'))

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    return asset

def preserve(path):
    if not path.exists():return
    dest=P/'PreviousAssets'/path.relative_to(R/'Content')
    if dest.exists():return
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)

for path in targets:
    preserve(R/'Content'/(path.removeprefix('/Game/')+'.uasset'))
icon_source=R/'Content/ColdSteelData/AttachmentIcons20260913'/(ICON+'.png')
preserve(icon_source)

def texture(label,kind):
    name=ICON if kind=='icon' else 'T_'+label+'_lei_ming_rune'
    src=P/('lei_ming_rune_icon.png' if kind=='icon' else name+'.png')
    folder='/Game/ColdSteelData/AttachmentIcons20260913' if kind=='icon' else SHARED if label=='Mask' else TEXROOT
    task=u.AssetImportTask();task.filename=str(src);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);tex=u.load_asset(folder+'/'+name)
    if not tex:raise RuntimeError('Texture import: '+name)
    tex.set_editor_property('srgb',kind=='icon')
    tex.set_editor_property('never_stream',kind=='icon')
    tex.set_editor_property('max_texture_size',1024 if kind=='icon' else 4096)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON if kind=='icon' else
        u.TextureCompressionSettings.TC_NORMALMAP if kind=='normal' else u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI if kind=='icon' else
        u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='normal' else u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR)
    if kind=='icon':tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    return save(tex)

texs={x:texture(x,'normal' if x=='Normal' else 'mask') for x in ('Mask','Normal','Roughness','Height')}
texture('Icon','icon')
shutil.copy2(P/'lei_ming_rune_icon.png',icon_source)

old=u.load_asset('/Game/Weapons/ThunderGodHammer20261028/ExclusiveRunesV1/M_SilverRuneSurface_ThunderExclusiveV1')
if not old:raise RuntimeError('Missing lit Thor rune donor')
mat=u.load_asset(ROOT+'/'+NAME) or A.duplicate_asset(NAME,ROOT,old)
E.delete_all_material_expressions(mat)
mat.set_editor_property('tangent_space_normal',False)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
mat.set_editor_property('used_with_skeletal_mesh',False)

def node(cls,**values):
    n=E.create_material_expression(mat,cls)
    for k,v in values.items():n.set_editor_property(k,v)
    return n
def link(a,b,pin='',out=''):
    if not E.connect_material_expressions(a,out,b,pin):raise RuntimeError('Connect: '+pin)
def output(a,p):
    if not E.connect_material_property(a,'',p):raise RuntimeError('Material output: '+str(p))
def inp(name):
    value=u.CustomInput();value.set_editor_property('input_name',name);return value
def custom(description,code,result,inputs):
    n=node(u.MaterialExpressionCustom,description=description,code=code,output_type=result,
        inputs=[inp(name) for name in inputs])
    for name,src in inputs.items():link(src,n,name)
    return n
def scalar(name,value):return node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def vector(name,value):return node(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value,1))
def texture_node(name,label):
    return node(u.MaterialExpressionTextureObjectParameter,parameter_name=name,texture=texs[label],
        sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if label=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
def mask(src,channel):
    n=node(u.MaterialExpressionComponentMask,r=channel=='r',g=channel=='g',b=channel=='b',a=channel=='a')
    link(src,n);return n

wp=node(u.MaterialExpressionWorldPosition)
local=node(u.MaterialExpressionTransformPosition,
    transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
    transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
link(wp,local)
wn=node(u.MaterialExpressionVertexNormalWS)
localn=node(u.MaterialExpressionTransform,
    transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
    transform_type=u.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
link(wn,localn)
uvcode='''float along=P.z+35.5;
float2 radial=P.xy-float2(-.0445214100,.1056659501);
float radius=max(length(radial),.001);
float angle=atan2(radial.x,-radial.y);
angle-=3.14159265359*floor((angle+1.57079632679)/3.14159265359);
float2 uv=saturate(float2(.5+angle*radius/(33.5*.25),1-along/33.5));
'''
rune=texture_node('RuneTexture','Mask')
normalmap=texture_node('RuneNormal','Normal')
roughmap=texture_node('RuneRoughness','Roughness')
time=node(u.MaterialExpressionTime)
preview=scalar('PreviewTime',-1)
mode=scalar('RuneMode',2)
strength=scalar('GlowStrength',.65)
color=vector('ConductionGlowColor',(.56,.76,1))

emitcode=uvcode+'''float3 ink=Texture2DSample(RuneTexture,RuneTextureSampler,uv).rgb;
float inside=smoothstep(0,.6,along)*(1-smoothstep(32.9,33.5,along));
inside*=smoothstep(0,.07,1.57079632679-abs(angle));
inside*=1-smoothstep(.2,.55,abs(normalize(N).z));
inside*=step(-.5,RuneMode);
float time=PreviewTime>=0?PreviewTime:T;
float breath=smoothstep(.22,.92,.5+.5*sin(along*.48-time*1.6));
float pulse=.46+1.18*breath;
float3 bluewhite=lerp(ConductionGlowColor,float3(.86,.94,1),.32);
float3 emission=bluewhite*ink.g*pulse*GlowStrength*2.1;
// Coverage is permanent silver. Only the narrow recessed channels carry current.
return float4(emission,ink.r*inside);'''
emission=custom('Lei Ming: permanent silver, blue-white current in carved channels only',emitcode,
    u.CustomMaterialOutputType.CMOT_FLOAT4,dict(P=local,N=localn,RuneTexture=rune,T=time,
        PreviewTime=preview,RuneMode=mode,GlowStrength=strength,ConductionGlowColor=color))
normalcode=uvcode+'''float2 xy=Texture2DSample(RuneNormal,RuneNormalSampler,uv).rg*2-1;
float nz=sqrt(saturate(1-dot(xy,xy)));
float3 radialN=normalize(float3(radial,0));
float3 tangent=float3(-radialN.y,radialN.x,0);
// Authored DirectX green stores +dH/d(image V); image V runs along local -Z.
return normalize(tangent*xy.x+float3(0,0,1)*xy.y+radialN*nz);'''
normal=custom('Physical relief normal in the shaft cylindrical basis',normalcode,
    u.CustomMaterialOutputType.CMOT_FLOAT3,dict(P=local,RuneNormal=normalmap))
normalworld=node(u.MaterialExpressionTransform,
    transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
    transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
link(normal,normalworld)
surf=custom('Authored roughness, silver tone, metal and groove occlusion',
    uvcode+'return Texture2DSample(RuneRoughness,RuneRoughnessSampler,uv);',
    u.CustomMaterialOutputType.CMOT_FLOAT4,dict(P=local,RuneRoughness=roughmap))
base=custom('Silver ridges and dark chased recesses','return float3(.64,.67,.70)*Tone;',
    u.CustomMaterialOutputType.CMOT_FLOAT3,dict(Tone=mask(surf,'g')))
emitrgb=node(u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);link(emission,emitrgb)
opacity=mask(emission,'a')
slab=node(u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
for src,pin,prop in [(base,'BaseColor',u.MaterialProperty.MP_BASE_COLOR),
    (mask(surf,'r'),'Roughness',u.MaterialProperty.MP_ROUGHNESS),
    (mask(surf,'b'),'Metallic',u.MaterialProperty.MP_METALLIC),
    (normalworld,'Normal',u.MaterialProperty.MP_NORMAL),
    (emitrgb,'Emissive Color',u.MaterialProperty.MP_EMISSIVE_COLOR),
    (opacity,'Opacity',u.MaterialProperty.MP_OPACITY)]:
    link(src,slab,pin);output(src,prop)
output(slab,u.MaterialProperty.MP_FRONT_MATERIAL)
output(mask(surf,'a'),u.MaterialProperty.MP_AMBIENT_OCCLUSION)
E.layout_material_expressions(mat)
errors=list(E.recompile_material(mat))
if errors:raise RuntimeError('Shader build failed: '+str(errors))
save(mat)
(P/'rune_emission.hlsl').write_text(emitcode,encoding='utf-8')
(P/'rune_normal.hlsl').write_text(normalcode,encoding='utf-8')
receipt['complete']=True
receipt['material']=mat.get_path_name()
receipt['icon_runtime_key']=ICON
receipt['native_material_selector']='FrostSwordRunes.h: WarhammerRuneMaterial'
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('LEIMING_REFINED_SAVED '+str(len(receipt['saved_assets'])))
