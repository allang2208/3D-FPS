"""Import the two owned rune surfaces/icons and publish Thor-only options."""
from pathlib import Path
import json,shutil,os
import unreal as u
P=Path(__file__).resolve().parent;R=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
ROOT='/Game/Weapons/ThunderGodHammer20261028/ExclusiveRunesV1'
SHARED='/Game/Weapons/MeleeRunes20260915/SurfaceV2'
IDS=('lei_ming_rune','hui_xiang_rune')
receipt={'complete':False,'saved_assets':[],'runtime_tested':False}

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name());return asset

def texture(src,folder,name,kind):
    task=u.AssetImportTask();task.filename=str(src);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    tex=u.load_asset(folder+'/'+name)
    if not tex:raise RuntimeError('Import '+name)
    tex.set_editor_property('srgb',kind=='icon');tex.set_editor_property('never_stream',kind=='icon')
    tex.set_editor_property('max_texture_size',1024 if kind=='icon' else 4096)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON if kind=='icon' else
        u.TextureCompressionSettings.TC_NORMALMAP if kind=='normal' else u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI if kind=='icon' else
        u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='normal' else u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR)
    if kind=='icon':tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    return save(tex)

texs={}
for id in IDS:
    texs[id]={}
    for label,kind in [('Mask','mask'),('Normal','normal'),('Roughness','mask'),('Height','mask')]:
        name='T_'+label+'_'+id
        texs[id][label]=texture(P/(name+'.png'),SHARED if label=='Mask' else ROOT+'/Textures',name,kind)
    # Hammer rune icons intentionally resolve through the blade_2 semantic key.
    key='ue_thunder_god_hammer_blade_2_'+id
    target=R/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png')
    shutil.copy2(P/(id+'_icon.png'),target)
    texture(target,'/Game/ColdSteelData/AttachmentIcons20260913',key,'icon')

name='M_SilverRuneSurface_ThunderExclusiveV1'
old=u.load_asset('/Game/Weapons/ThunderGodHammer20261028/ModulesV1/Runes/M_SilverRuneSurface_ThunderGodHammerShaftV1')
if not old:raise RuntimeError('Thor shaft projection donor missing')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name()==ROOT+'/'+name:raise RuntimeError('Unsaved owned material')
mat=u.load_asset(ROOT+'/'+name) or A.duplicate_asset(name,ROOT,old)
# The original donor is never altered.
nodes=list(E.get_material_expressions(mat))
custom=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'HaloRadiusTexels' in n.get_editor_property('code'))
def node(cls,**kw):
    n=E.create_material_expression(mat,cls)
    for k,v in kw.items():n.set_editor_property(k,v)
    return n
def link(a,out,b,pin):
    if not E.connect_material_expressions(a,out,b,pin):raise RuntimeError('Connect '+pin)
def prop(a,out,p):
    if not E.connect_material_property(a,out,p):raise RuntimeError('Output '+str(p))
def custom_input(name):
    value=u.CustomInput();value.set_editor_property('input_name',name);return value
mat.set_editor_property('tangent_space_normal',False)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
position=node(u.MaterialExpressionWorldPosition)
local=node(u.MaterialExpressionTransformPosition,
    transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
    transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
link(position,'',local,'')
uv='''float2 radial=P.xy-float2(-.0445214100,.1056659501);
float radius=max(length(radial),.001);float angle=atan2(radial.x,-radial.y);
angle-=3.14159265359*floor((angle+1.57079632679)/3.14159265359);
float2 uv=saturate(float2(.5+angle*radius/(33.5*.25),1-(P.z+35.5)/33.5));
'''
normal_map=node(u.MaterialExpressionTextureObjectParameter,parameter_name='RuneNormal',texture=texs[IDS[0]]['Normal'])
normal=node(u.MaterialExpressionCustom,description='Thor rune bevel normal in cylindrical local basis',
    output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
    inputs=[custom_input('P'),custom_input('RuneNormal')],
    code=uv+'''float2 xy=Texture2DSample(RuneNormal,RuneNormalSampler,uv).rg*2-1;
float3 n=float3(xy,sqrt(saturate(1-dot(xy,xy))));
float3 radialN=normalize(float3(radial,0));float3 tangent=float3(-radialN.y,radialN.x,0);
return normalize(tangent*n.x-float3(0,0,1)*n.y+radialN*n.z);''')
link(local,'',normal,'P');link(normal_map,'',normal,'RuneNormal')
world_normal=node(u.MaterialExpressionTransform,
    transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
    transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
link(normal,'',world_normal,'')
rough_map=node(u.MaterialExpressionTextureObjectParameter,parameter_name='RuneRoughness',texture=texs[IDS[0]]['Roughness'])
rough=node(u.MaterialExpressionCustom,description='Thor rune bevel roughness',output_type=u.CustomMaterialOutputType.CMOT_FLOAT1,
    inputs=[custom_input('P'),custom_input('RuneRoughness')],
    code=uv+'return Texture2DSample(RuneRoughness,RuneRoughnessSampler,uv).r;')
link(local,'',rough,'P');link(rough_map,'',rough,'RuneRoughness')
rgb=node(u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
alpha=node(u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
link(custom,'',rgb,'');link(custom,'',alpha,'')
silver=node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.48,.52,.57,1))
metal=node(u.MaterialExpressionConstant,r=.86)
slab=node(u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
for src,pin,target,mp in [(silver,'','BaseColor',u.MaterialProperty.MP_BASE_COLOR),
    (metal,'','Metallic',u.MaterialProperty.MP_METALLIC),(rough,'','Roughness',u.MaterialProperty.MP_ROUGHNESS),
    (world_normal,'','Normal',u.MaterialProperty.MP_NORMAL),(rgb,'','Emissive Color',u.MaterialProperty.MP_EMISSIVE_COLOR),
    (alpha,'','Opacity',u.MaterialProperty.MP_OPACITY)]:
    link(src,pin,slab,target);prop(src,pin,mp)
prop(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
E.layout_material_expressions(mat)
errors=list(E.recompile_material(mat))
if errors:raise RuntimeError('Rune shader compile: '+str(errors))
save(mat)

catalog=R/'Content/ColdSteelData/thunder-god-hammer-gunsmith.json'
before=catalog.read_bytes();data=json.loads(before.decode('utf-8-sig'))
column=next(c for c in data['columns'] if c['key']=='rune')
options=[
 dict(id=IDS[0],name='雷鸣符文',tier='special',weapons=['ue_thunder_god_hammer'],stats={},effects=[],
    description='雷神之锤专属。折雷主印由双侧编结环抱，嵌银笔画沿锤柄向下收束。',
    appearance='北欧折雷主印 · 双侧编结 · 蓝白流光',
    special_effects=['雷鸣附印｜该武器任何形式的有效攻击命中均有50%概率额外叠加1层感电，每个目标独立判定。落雷原有2层感电与本次触发合并结算。']),
 dict(id=IDS[1],name='回响符文',tier='special',weapons=['ue_thunder_god_hammer'],stats={},effects=[],
    description='雷神之锤专属。相向回环围绕菱形主印，两枚留存印记承接过载后的余雷。',
    appearance='双回环主印 · 双留存印记 · 冰青流光',
    special_effects=['过载回响｜持有此武器以任何形式触发5层感电过载时，过载眩晕额外延长0.25秒；触发后保留2层感电。伤害、范围及其他控制规则沿用原有效果。'])]
column['options']=[o for o in column['options'] if o['id'] not in IDS]+options
column['description']='保留原生雷纹，可在长柄上附加通用符文或雷神之锤专属符文。'
if catalog.read_bytes()!=before:raise RuntimeError('Concurrent rune catalog edit; assets saved, publication deferred')
temp=catalog.with_name(catalog.name+'.thor-runes-pending')
temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(temp,catalog)
receipt['complete']=True;receipt['options']=list(IDS);receipt['catalog']=str(catalog)
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('THOR_EXCLUSIVE_RUNES_SAVED '+str(len(receipt['saved_assets'])))
