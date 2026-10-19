"""Author and save the cyan palette using the approved Beiwei/Chixiao ribbon graph."""
import json
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent
D='/Game/Weapons/Zhanmadao20261018/ZhufengCyanTrailV1/Materials'
A=u.AssetToolsHelpers.get_asset_tools()
E=u.MaterialEditingLibrary
L=u.EditorAssetLibrary
name='M_ZhufengSwordTrail'
material=u.load_asset(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
for expression in list(E.get_material_expressions(material)):
    E.delete_material_expression(material,expression)
material.set_editor_properties(dict(
    blend_mode=u.BlendMode.BLEND_TRANSLUCENT,
    shading_model=u.MaterialShadingModel.MSM_UNLIT,
    two_sided=True,disable_depth_test=False,
    translucency_pass=u.MaterialTranslucencyPass.MTP_BEFORE_DOF))

def node(cls,**properties):
    result=E.create_material_expression(material,cls)
    if properties:result.set_editor_properties(properties)
    return result

def wire(source,target,pin=''):
    E.connect_material_expressions(source,'',target,pin)

uv=node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
custom=node(u.MaterialExpressionCustom,code=(P/'sword_trail.hlsl').read_text('utf-8'),
            output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
pin=u.CustomInput()
pin.set_editor_property('input_name','UV')
custom.set_editor_property('inputs',[pin])
wire(uv,custom,'UV')
rgb=node(u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
alpha=node(u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
wire(custom,rgb)
wire(custom,alpha)
exposure=node(u.MaterialExpressionEyeAdaptationInverse)
wire(rgb,exposure,E.get_material_expression_input_names(exposure)[0])
wire(node(u.MaterialExpressionConstant,r=1.),exposure,E.get_material_expression_input_names(exposure)[1])
E.connect_material_property(exposure,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
E.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
E.recompile_material(material)
L.set_metadata_tag(material,'ZhufengTrailRevision','ZhufengCyanTrailV1')
if not L.save_loaded_asset(material,False):raise RuntimeError('Cyan trail material was not saved')
(P/'asset-save.json').write_text(json.dumps({
    'saved':True,'asset':material.get_path_name(),'game_tested':False,
    'reference':'../ChixiaoLegendaryV1/install_assets.py'},indent=2)+'\n',encoding='utf-8')
print('ZHUFENG_CYAN_TRAIL_SAVED',material.get_path_name(),flush=True)
