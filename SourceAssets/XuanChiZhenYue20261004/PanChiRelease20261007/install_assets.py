"""Save the Pan Chi release materials. Authoring only: no scene or player edits."""
import json
import runpy
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent
D='/Game/Weapons/XuanChiZhenYue20261004/PanChiRelease20261007'
REV='PanChiRelease20261007'
SPIRIT_ONLY=bool(globals().get('PANCHI_SPIRIT_ONLY',False))
RECEIPT='spirit-visibility-import-20261007.json' if SPIRIT_ONLY else 'import_receipt.json'
A,E,L=u.AssetToolsHelpers.get_asset_tools(),u.MaterialEditingLibrary,u.EditorAssetLibrary
receipt={'complete':False,'assets_saved':[],'runtime_tested':False,'visual_tested':False}
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Exit PIE before authoring release materials')
texture=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/PanChiEffects20261006/T_PanChiDragonSpirit')
if not texture:raise RuntimeError('Original Pan Chi dragon artwork asset is missing')

def node(m,cls,**kw):
    n=E.create_material_expression(m,cls)
    for k,v in kw.items():n.set_editor_property(k,v)
    return n
def link(a,out,b,inp):
    if not E.connect_material_expressions(a,out,b,inp):raise RuntimeError('Material link failed: '+inp)
def scalar(m,name,value):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def author(name,shader,ground=False,motes=False):
    m=u.load_asset(D+'/'+name)
    if m and L.get_metadata_tag(m,'PanChiReleaseRevision')!=REV:
        raise RuntimeError('Preserved unowned material: '+name)
    m=m or A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
    for old in list(E.get_material_expressions(m)):E.delete_material_expression(m,old)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided',True)
    m.set_editor_property('disable_depth_test',False)
    m.set_editor_property('used_with_skeletal_mesh',False)
    inputs={'UV':node(m,u.MaterialExpressionTextureCoordinate),'Charge':scalar(m,'Charge',1.)}
    if not motes:
        inputs['Seconds']=scalar(m,'Seconds',1.3)
        inputs['Dragon']=node(m,u.MaterialExpressionTextureObjectParameter,parameter_name='Dragon',texture=texture)
    if ground:
        inputs['Converge']=node(m,u.MaterialExpressionVectorParameter,parameter_name='Converge',default_value=u.LinearColor(.4,.5,0,0))
    else:inputs['Meta']=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=1)
    n=node(m,u.MaterialExpressionCustom,code=(P/shader).read_text(encoding='utf-8'),output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    fields=[]
    for key in inputs:
        field=u.CustomInput();field.set_editor_property('input_name',key);fields.append(field)
    n.set_editor_property('inputs',fields)
    for key,value in inputs.items():link(value,'',n,key)
    rgb=node(m,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);link(n,'',rgb,'')
    alpha=node(m,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True);link(n,'',alpha,'')
    exposed=node(m,u.MaterialExpressionEyeAdaptationInverse)
    link(rgb,'',exposed,str(E.get_material_expression_input_names(exposed)[0]))
    depth=node(m,u.MaterialExpressionDepthFade,fade_distance_default=3. if ground else (12. if motes else 6.))
    link(alpha,'',depth,'Opacity')
    E.connect_material_property(exposed,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    E.connect_material_property(depth,'',u.MaterialProperty.MP_OPACITY)
    substrate=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_UNLIT)
    link(exposed,'',substrate,'Emissive Color');link(depth,'',substrate,'Opacity')
    if not E.connect_material_property(substrate,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate connection failed')
    errors=E.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    L.set_metadata_tag(m,'PanChiReleaseRevision',REV)
    if not u.EditorLoadingAndSavingUtils.save_packages([m.get_outermost()],False):raise RuntimeError('Could not save '+name)
    receipt['assets_saved'].append(m.get_path_name())
    (P/RECEIPT).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')

if not SPIRIT_ONLY:author('M_PanChiConvergence','convergence.hlsl',ground=True)
author('M_PanChiSpiritRibbon','spirit_ribbon.hlsl')
if not SPIRIT_ONLY:author('M_PanChiGoldenMotes','golden_motes.hlsl',motes=True)
if not SPIRIT_ONLY and not globals().get('PANCHI_SKIP_GUARD',False):
    runpy.run_path(str(P.parent/'PanChiEffects20261006'/'install_assets.py'),init_globals={'PANCHI_GUARD_ONLY':True})
    receipt['assets_saved'].append('/Game/Weapons/XuanChiZhenYue20261004/PanChiEffects20261006/M_PanChiGuardGlow.M_PanChiGuardGlow')
receipt['complete']=True
(P/RECEIPT).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
if not SPIRIT_ONLY:
    runpy.run_path(str(P.parent/'PanChiFlight20261007'/'install_assets.py'))
print('PANCHI_RELEASE_MATERIALS_SAVED '+str(len(receipt['assets_saved'])))
