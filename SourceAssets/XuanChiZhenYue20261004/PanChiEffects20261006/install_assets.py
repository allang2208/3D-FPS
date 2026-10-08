"""Author and save three new effect assets without opening an editor or running PIE."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
D='/Game/Weapons/XuanChiZhenYue20261004/PanChiEffects20261006'
A,E,L=u.AssetToolsHelpers.get_asset_tools(),u.MaterialEditingLibrary,u.EditorAssetLibrary
REV='PanChiEffects20261006'
GUARD_ONLY=bool(globals().get('PANCHI_GUARD_ONLY',False))
RECEIPT='guard-glow-import-receipt-20261007.json' if GUARD_ONLY else 'import_receipt.json'
receipt={'complete':False,'assets_saved':[],'runtime_tested':False}
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Exit PIE before effect asset authoring')

def owned(path):
    obj=u.load_asset(path)
    if obj and L.get_metadata_tag(obj,'PanChiEffectRevision')!=REV:raise RuntimeError('Preserved unowned asset: '+path)
    return obj
def save(obj):
    L.set_metadata_tag(obj,'PanChiEffectRevision',REV)
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed: '+obj.get_path_name())
    receipt['assets_saved'].append(obj.get_path_name())
    (P/RECEIPT).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return obj
def node(m,cls,**kw):
    n=E.create_material_expression(m,cls)
    for key,value in kw.items():n.set_editor_property(key,value)
    return n
def link(a,out,b,inp):
    if not E.connect_material_expressions(a,out,b,inp):raise RuntimeError('Material link failed: '+inp)
def scalar(m,name,value):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def material(name):
    m=owned(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
    # UE 5.8's DeleteAll walks the same expression array that Delete mutates.
    # Take a snapshot so rebuilding this graph does not leave stale parameters.
    for expression in list(E.get_material_expressions(m)):
        E.delete_material_expression(m,expression)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property('two_sided',True)
    m.set_editor_property('disable_depth_test',False)
    m.set_editor_property('used_with_skeletal_mesh',False)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    return m
def custom(m,file,inputs):
    n=node(m,u.MaterialExpressionCustom,code=(P/file).read_text(encoding='utf-8'),output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    fields=[]
    for key in inputs:
        field=u.CustomInput();field.set_editor_property('input_name',key);fields.append(field)
    n.set_editor_property('inputs',fields)
    for key,value in inputs.items():link(value,'',n,key)
    rgb=node(m,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);link(n,'',rgb,'')
    alpha=node(m,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True);link(n,'',alpha,'')
    exposed=node(m,u.MaterialExpressionEyeAdaptationInverse)
    link(rgb,'',exposed,str(E.get_material_expression_input_names(exposed)[0]))
    E.connect_material_property(exposed,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    E.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
    surface=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_UNLIT)
    link(exposed,'',surface,'Emissive Color');link(alpha,'',surface,'Opacity')
    if not E.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output connection failed')
    return m

if not GUARD_ONLY:
    path=D+'/T_PanChiDragonSpirit';existing=owned(path)
    t=u.AssetImportTask();t.filename=str(P/'PanChi_DragonSpirit.png');t.destination_path=D;t.destination_name='T_PanChiDragonSpirit'
    t.automated=True;t.replace_existing=bool(existing);t.save=False;A.import_asset_tasks([t]);texture=u.load_asset(path)
    if not texture:raise RuntimeError('Dragon texture import failed')
    texture.srgb=True;texture.never_stream=False;texture.max_texture_size=2048
    texture.compression_settings=u.TextureCompressionSettings.TC_BC7
    texture.address_x=u.TextureAddress.TA_CLAMP;texture.address_y=u.TextureAddress.TA_CLAMP;save(texture)

    # The release now uses articulated ribbons and a separate ground convergence.
    # Keep the original texture as the shared artwork source.
    import runpy
    runpy.run_path(str(P.parent/'PanChiRelease20261007'/'install_assets.py'),init_globals={'PANCHI_SKIP_GUARD':True})

m=material('M_PanChiGuardGlow')
uv=node(m,u.MaterialExpressionTextureCoordinate)
world=node(m,u.MaterialExpressionWorldPosition)
local=node(m,u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
link(world,'',local,'')
fresnel=node(m,u.MaterialExpressionFresnel,exponent=3.,base_reflect_fraction=.06)
relief=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/PanChiGuard20261006/Textures/T_PanChi_ORM')
if not relief:raise RuntimeError('Existing guard relief texture missing')
tex=node(m,u.MaterialExpressionTextureObjectParameter,parameter_name='Relief',texture=relief,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
custom(m,'guard_glow.hlsl',{'UV':uv,'LP':local,'Facing':fresnel,'Relief':tex,'Time':node(m,u.MaterialExpressionTime),'Stacks':scalar(m,'Stacks',0.),'Ready':scalar(m,'Ready',1.),'ReleaseFlash':scalar(m,'ReleaseFlash',0.)})
errors=E.recompile_material(m)
if errors:raise RuntimeError(str(errors))
save(m)
receipt['complete']=True
(P/RECEIPT).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print('PANCHI_EFFECT_ASSETS_SAVED '+str(len(receipt['assets_saved'])))
