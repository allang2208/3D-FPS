"""Author the flying dragon material without spawning gameplay or changing a level."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
D='/Game/Weapons/XuanChiZhenYue20261004/PanChiFlight20261007'
REV='PanChiFlight20261007'
A,E,L=u.AssetToolsHelpers.get_asset_tools(),u.MaterialEditingLibrary,u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Exit PIE before saving flight material')
tex=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/PanChiEffects20261006/T_PanChiDragonSpirit')
if not tex:raise RuntimeError('Original dragon texture missing')
name='M_PanChiFlyingDragon'
m=u.load_asset(D+'/'+name)
if m and L.get_metadata_tag(m,'PanChiFlightRevision')!=REV:raise RuntimeError('Preserved unowned material')
m=m or A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
for old in list(E.get_material_expressions(m)):E.delete_material_expression(m,old)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
m.set_editor_property('two_sided',True)
m.set_editor_property('disable_depth_test',False)
m.set_editor_property('used_with_skeletal_mesh',False)
def node(cls,**kw):
    obj=E.create_material_expression(m,cls)
    for k,v in kw.items():obj.set_editor_property(k,v)
    return obj
def link(a,out,b,pin):
    if not E.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material link failed: '+pin)
inputs={'UV':node(u.MaterialExpressionTextureCoordinate),
        'Dragon':node(u.MaterialExpressionTextureObjectParameter,parameter_name='Dragon',texture=tex),
        'Depth':node(u.MaterialExpressionPixelDepth)}
for key,value in [('Seconds',0.),('Opacity',0.),('Dissolve',0.),('Charge',1.)]:
    inputs[key]=node(u.MaterialExpressionScalarParameter,parameter_name=key,default_value=value)
fields=[]
for key in inputs:
    field=u.CustomInput();field.set_editor_property('input_name',key);fields.append(field)
custom=node(u.MaterialExpressionCustom,code=(P/'flying_dragon.hlsl').read_text(encoding='utf-8'),
            output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,inputs=fields)
for key,value in inputs.items():link(value,'',custom,key)
rgb=node(u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);link(custom,'',rgb,'')
alpha=node(u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True);link(custom,'',alpha,'')
exposed=node(u.MaterialExpressionEyeAdaptationInverse)
link(rgb,'',exposed,str(E.get_material_expression_input_names(exposed)[0]))
fade=node(u.MaterialExpressionDepthFade,fade_distance_default=6.);link(alpha,'',fade,'Opacity')
E.connect_material_property(exposed,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
E.connect_material_property(fade,'',u.MaterialProperty.MP_OPACITY)
surface=node(u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_UNLIT)
link(exposed,'',surface,'Emissive Color');link(fade,'',surface,'Opacity')
if not E.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output failed')
errors=E.recompile_material(m)
if errors:raise RuntimeError(str(errors))
L.set_metadata_tag(m,'PanChiFlightRevision',REV)
if not u.EditorLoadingAndSavingUtils.save_packages([m.get_outermost()],False):raise RuntimeError('Material save failed')
(P/'import_receipt.json').write_text(json.dumps({'complete':True,'assets_saved':[m.get_path_name()],
    'runtime_tested':False,'visual_tested':False},indent=2)+'\n',encoding='utf-8')
print('PANCHI_FLIGHT_MATERIAL_SAVED')
# Keep the full Pan Chi material rebuild on the currently active release design.
import runpy
runpy.run_path(str(P.parent/'PanChiUppercut20261007'/'install_assets.py'))
