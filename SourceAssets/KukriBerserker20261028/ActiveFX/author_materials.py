"""Create the owned screen flame, rising arm cloud and whole-weapon red overlay."""
import json
from pathlib import Path
import unreal as u
P=Path(globals().get('__file__') or r'D:/FPS3D/FPSGAME/SourceAssets/KukriBerserker20261028/ActiveFX/author_materials.py').resolve().parent
ROOT='/Game/Weapons/Kukri20261020/Berserker20261028/ActiveFX'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('Preserve the running game; material saving needs the preview to end')
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(ROOT) for p in dirty):raise RuntimeError('Preserve unsaved active FX assets')

def node(mat,cls,**props):
    value=L.create_material_expression(mat,cls)
    for k,v in props.items():value.set_editor_property(k,v)
    return value

def link(a,b,pin,out=''):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)

def custom(mat,code,inputs,size):
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    value=node(mat,u.MaterialExpressionCustom,code=code,inputs=pins,output_type=size)
    for key,source in inputs.items():link(source,value,key)
    return value

def material(name):
    path=ROOT+'/'+name
    m=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,ROOT,u.Material,u.MaterialFactoryNew())
    if not m:raise RuntimeError('Cannot create '+path)
    L.delete_all_material_expressions(m)
    return m

def output(mat,value,prop):
    if not L.connect_material_property(value,'',prop):raise RuntimeError('Material output failed')

edge=material('M_BerserkerEdge')
edge.set_editor_properties({'material_domain':u.MaterialDomain.MD_UI,'blend_mode':u.BlendMode.BLEND_TRANSLUCENT})
values={'UV':node(edge,u.MaterialExpressionTextureCoordinate)}
for key in ('Age','Strength','EntryBurst'):
    values[key]=node(edge,u.MaterialExpressionScalarParameter,parameter_name=key,default_value=0.)
shader=custom(edge,(P/'BerserkerEdge.hlsl').read_text('utf-8'),values,u.CustomMaterialOutputType.CMOT_FLOAT4)
rgb=node(edge,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);link(shader,rgb,str(L.get_material_expression_input_names(rgb)[0]))
alpha=node(edge,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True);link(shader,alpha,str(L.get_material_expression_input_names(alpha)[0]))
output(edge,rgb,u.MaterialProperty.MP_EMISSIVE_COLOR);output(edge,alpha,u.MaterialProperty.MP_OPACITY)

ember=material('M_BerserkerEmber')
ember.set_editor_properties({'blend_mode':u.BlendMode.BLEND_TRANSLUCENT,'shading_model':u.MaterialShadingModel.MSM_UNLIT,
    'two_sided':True,'disable_depth_test':False,'allow_front_layer_translucency':False,
    'output_translucent_velocity':False,'is_translucency_velocity_from_depth':False,
    'translucency_pass':u.MaterialTranslucencyPass.MTP_AFTER_DOF})
L.set_base_material_usage(ember,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
channels=[]
for index in range(3):
    value=node(ember,u.MaterialExpressionPerInstanceCustomData,data_index=index,const_default_value=0.)
    interp=node(ember,u.MaterialExpressionVertexInterpolator)
    link(value,interp,str(L.get_material_expression_input_names(interp)[0]));channels.append(interp)
shader=custom(ember,(P/'BerserkerEmber.hlsl').read_text('utf-8'),
    {'UV':node(ember,u.MaterialExpressionTextureCoordinate),'Alpha':channels[0],'Life':channels[1],
     'Kind':channels[2]},u.CustomMaterialOutputType.CMOT_FLOAT4)
color=node(ember,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
link(shader,color,str(L.get_material_expression_input_names(color)[0]))
mask=node(ember,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
link(shader,mask,str(L.get_material_expression_input_names(mask)[0]))
exposed=node(ember,u.MaterialExpressionEyeAdaptationInverse)
link(color,exposed,str(L.get_material_expression_input_names(exposed)[0]))
output(ember,exposed,u.MaterialProperty.MP_EMISSIVE_COLOR);output(ember,mask,u.MaterialProperty.MP_OPACITY)
slab=node(ember,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_UNLIT)
link(exposed,slab,'Emissive Color');link(mask,slab,'Opacity')
output(ember,slab,u.MaterialProperty.MP_FRONT_MATERIAL)
weapon=material('M_BerserkerWeaponGlow')
weapon.set_editor_properties({'blend_mode':u.BlendMode.BLEND_TRANSLUCENT,'shading_model':u.MaterialShadingModel.MSM_UNLIT,
    'two_sided':True,'disable_depth_test':False,'allow_front_layer_translucency':False,
    'output_translucent_velocity':False,'is_translucency_velocity_from_depth':False,
    'translucency_pass':u.MaterialTranslucencyPass.MTP_AFTER_DOF})
values={'Normal':node(weapon,u.MaterialExpressionPixelNormalWS),'ToEye':node(weapon,u.MaterialExpressionCameraVectorWS)}
for key in ('Age','Strength','EntryBurst'):
    values[key]=node(weapon,u.MaterialExpressionScalarParameter,parameter_name=key,default_value=0.)
shader=custom(weapon,(P/'BerserkerWeaponGlow.hlsl').read_text('utf-8'),values,u.CustomMaterialOutputType.CMOT_FLOAT4)
color=node(weapon,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
link(shader,color,str(L.get_material_expression_input_names(color)[0]))
mask=node(weapon,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
link(shader,mask,str(L.get_material_expression_input_names(mask)[0]))
exposed=node(weapon,u.MaterialExpressionEyeAdaptationInverse)
link(color,exposed,str(L.get_material_expression_input_names(exposed)[0]))
output(weapon,exposed,u.MaterialProperty.MP_EMISSIVE_COLOR);output(weapon,mask,u.MaterialProperty.MP_OPACITY)
slab=node(weapon,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_UNLIT)
link(exposed,slab,'Emissive Color');link(mask,slab,'Opacity')
output(weapon,slab,u.MaterialProperty.MP_FRONT_MATERIAL)
materials=(edge,ember,weapon)
for m in materials:
    E.set_metadata_tag(m,'SourceAuthoring',str(P/'author_materials.py'))
    errors=list(L.recompile_material(m))
    if errors:raise RuntimeError(m.get_path_name()+': '+str(errors))
if not u.PoisonMaggotMonster.compile_material_assets(list(materials)):raise RuntimeError('Active FX material compilation failed')
for m in materials:
    if not E.save_loaded_asset(m,False):raise RuntimeError('Cannot save '+m.get_path_name())
(P/'material-receipt.json').write_text(json.dumps({'complete':True,'assets':[m.get_path_name() for m in materials],
    'revision':'RisingArmCloudAndWholeWeaponRedV2','particles_per_hand':128,'maximum_particles':256,
    'compiled':True,'runtime_tested':False},indent=2),encoding='utf-8')
u.log('BERSERKER_ACTIVE_FX_SAVED')
