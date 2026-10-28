"""Build two independent, exposure-stable red particle materials for the shared pool."""
import unreal as u
import json
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT='/Game/Combat/Bleeding20261027'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Preserve active game; save and close UE before the background build/import.')
saved=[]
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for name,value in props.items():n.set_editor_property(name,value)
    return n
def link(a,b,pin):
    if not L.connect_material_expressions(a,'',b,pin):raise RuntimeError('Cannot connect '+pin)
def custom(m,code,inputs,size=1):
    pins=[]
    for key in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
    n=node(m,u.MaterialExpressionCustom,code=code,inputs=pins,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3 if size==3 else u.CustomMaterialOutputType.CMOT_FLOAT1)
    for key,value in inputs.items():link(value,n,key)
    return n
for kind in ('Drop','Mist'):
    name='M_BleedBurst'+kind;path=ROOT+'/'+name
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if path in dirty:raise RuntimeError('Preserve unsaved '+path)
    m=u.load_asset(path) if E.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,u.Material,u.MaterialFactoryNew())
    if not m:raise RuntimeError('Cannot create '+path)
    L.delete_all_material_expressions(m)
    m.set_editor_properties({'blend_mode':u.BlendMode.BLEND_TRANSLUCENT,'shading_model':u.MaterialShadingModel.MSM_UNLIT,
        'two_sided':True,'disable_depth_test':False,'allow_front_layer_translucency':False,
        'output_translucent_velocity':False,'is_translucency_velocity_from_depth':False,
        'translucency_pass':u.MaterialTranslucencyPass.MTP_BEFORE_DOF})
    L.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    channels=[]
    for index in range(6):
        value=node(m,u.MaterialExpressionPerInstanceCustomData,data_index=index,const_default_value=0.)
        interpolated=node(m,u.MaterialExpressionVertexInterpolator)
        link(value,interpolated,str(L.get_material_expression_input_names(interpolated)[0]));channels.append(interpolated)
    uv=node(m,u.MaterialExpressionTextureCoordinate)
    mask=custom(m,(P/('Bleed'+kind+'.hlsl')).read_text(encoding='utf-8'),
        {'UV':uv,'Alpha':channels[3],'Age':channels[4],'Variation':channels[5]})
    fade=node(m,u.MaterialExpressionDepthFade,fade_distance_default=.65 if kind=='Drop' else 2.)
    link(mask,fade,'Opacity')
    tint=custom(m,'return float3(R,G,B)*lerp(1,.78,saturate(Age));',
        {'R':channels[0],'G':channels[1],'B':channels[2],'Age':channels[4]},3)
    exposed=node(m,u.MaterialExpressionEyeAdaptationInverse)
    link(tint,exposed,str(L.get_material_expression_input_names(exposed)[0]))
    for prop,value in ((u.MaterialProperty.MP_EMISSIVE_COLOR,exposed),(u.MaterialProperty.MP_OPACITY,fade)):
        if not L.connect_material_property(value,'',prop):raise RuntimeError('Material output failed')
    surface=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_UNLIT)
    link(exposed,surface,'Emissive Color');link(fade,surface,'Opacity')
    if not L.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output failed')
    E.set_metadata_tag(m,'Source',str(P/('Bleed'+kind+'.hlsl')))
    E.set_metadata_tag(m,'Purpose','Shared bounded bleed pulse, red liquid particles, no lights or decals')
    L.recompile_material(m);saved.append(m)
if not u.PoisonMaggotMonster.compile_material_assets(saved):raise RuntimeError('Bleed material compilation failed')
for m in saved:
    if not E.save_loaded_asset(m,False):raise RuntimeError('Cannot save '+m.get_path_name())
(P/'material-receipt.json').write_text(json.dumps({'complete':True,'assets':[m.get_path_name() for m in saved],
    'compiled':True,'runtime_tested':False},indent=2),encoding='utf-8')
u.log('BLEED_MATERIALS_SAVED '+str(len(saved)))
