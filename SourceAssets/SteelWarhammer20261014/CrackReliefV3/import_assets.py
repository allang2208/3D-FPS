"""Save original PBR fracture assets into a new version; no preview or gameplay."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;R=P.parents[2]
D='/Game/Weapons/SteelWarhammer20261014/CrackReliefV3'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
receipt={'saved':[],'complete':False,'runtime_tested':False,'third_party_assets_imported':False}
def save(asset):
    if isinstance(asset,u.Material):
        errors=list(L.recompile_material(asset))
        if errors:raise RuntimeError(str(errors))
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name());(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def node(m,cls):return L.create_material_expression(m,cls)
def wire(a,b,pin):
    a,out=a if isinstance(a,tuple) else (a,'')
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Wire '+pin)
def custom(m,code,inputs,width=1):
    n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code)
    n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for key in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
    n.set_editor_property('inputs',pins)
    for key,value in inputs.items():wire(value,n,key)
    return n
def scalar(m,name,value):
    n=node(m,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
textures={}
for kind in ('Color','Normal','Masks'):
    name='T_WarhammerFracture'+kind
    task=u.AssetImportTask();task.filename=str(P/(name+'.png'));task.destination_path=D;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);t=u.load_asset(D+'/'+name)
    if not t:raise RuntimeError('Texture import failed '+name)
    t.set_editor_property('srgb',kind=='Color')
    t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else
        u.TextureCompressionSettings.TC_MASKS if kind=='Masks' else u.TextureCompressionSettings.TC_DEFAULT)
    t.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);t.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    t.set_editor_property('max_texture_size',2048)
    textures[kind]=t;save(t)
name='M_WarhammerFractureRelief'
m=u.load_asset(D+'/'+name) if E.does_asset_exist(D+'/'+name) else A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(m)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
m.set_editor_property('tangent_space_normal',True)
seed=scalar(m,'Seed',.5);age=scalar(m,'Age',.5)
uv=node(m,u.MaterialExpressionTextureCoordinate)
rotated=custom(m,'float a=Seed*6.283185; float2 p=UV-.5; return float2(cos(a)*p.x-sin(a)*p.y,sin(a)*p.x+cos(a)*p.y)+.5;',{'UV':uv,'Seed':seed},2)
sample={}
for kind in textures:
    n=node(m,u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name',kind)
    n.set_editor_property('texture',textures[kind])
    n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else
        u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='Masks' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    wire(rotated,n,str(L.get_material_expression_input_names(n)[0]));sample[kind]=n
alpha=custom(m,'float r=length((UV-.5)*2); float grow=smoothstep(0,.035,Age)*(1-smoothstep(Age/.20,Age/.20+.10,r)); return Coverage*grow*(1-smoothstep(3.3,5.0,Age));',
    {'UV':rotated,'Age':age,'Coverage':(sample['Masks'],'R')})
normal=custom(m,'float a=Seed*6.283185; return normalize(float3(cos(a)*N.x-sin(a)*N.y,sin(a)*N.x+cos(a)*N.y,N.z));',
    {'N':(sample['Normal'],'RGB'),'Seed':seed},3)
slab=node(m,u.MaterialExpressionSubstrateShadingModels)
slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
wire((sample['Color'],'RGB'),slab,'BaseColor');wire(alpha,slab,'Opacity')
wire((sample['Masks'],'B'),slab,'Roughness');wire(normal,slab,'Normal')
wire(scalar(m,'Specular',.10),slab,'Specular')
convert=node(m,u.MaterialExpressionSubstrateConvertToDecal)
wire(slab,convert,str(L.get_material_expression_input_names(convert)[0]))
if not L.connect_material_property(convert,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Missing Substrate output')
save(m)
receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_FRACTURE_RELIEF_SAVED '+json.dumps(receipt))
