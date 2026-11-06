"""Create the ridge thrust's translucent ribbon material in the equipped blade folder."""
from pathlib import Path
import unreal as u

here = Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve() != here.parents[1]:
    raise RuntimeError('Wrong project')
dest = '/Game/Weapons/HighlandClaymore20260922/RidgeThrust20261105'
name = 'M_RidgeGather'
path = dest+'/'+name
lib = u.EditorAssetLibrary
material = u.load_asset(path) if lib.does_asset_exist(path) else None
if material:
    if lib.get_metadata_tag(material,'Highland.Author') != 'RidgeGather' or any(
            p.get_name()==path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserving existing material '+path)
else:
    material = u.AssetToolsHelpers.get_asset_tools().create_asset(name,dest,u.Material,u.MaterialFactoryNew())
if not material:
    raise RuntimeError('Could not create '+path)
edit = u.MaterialEditingLibrary
edit.delete_all_material_expressions(material)
material.set_editor_properties(dict(blend_mode=u.BlendMode.BLEND_TRANSLUCENT,
    shading_model=u.MaterialShadingModel.MSM_UNLIT,two_sided=True,disable_depth_test=False,
    translucency_pass=u.MaterialTranslucencyPass.MTP_BEFORE_DOF))
def node(kind, **props):
    expr = edit.create_material_expression(material,kind)
    if props: expr.set_editor_properties(props)
    return expr
uv = node(u.MaterialExpressionTextureCoordinate)
color = node(u.MaterialExpressionCustom,output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,code="""
    float t=saturate(UV.x), d=abs(UV.y*2-1);
    float bloom=exp2(-4*d*d);
    float core=exp2(-30*d*d);
    float offset=d-.52-.12*sin(14*t);
    float strand=exp2(-100*offset*offset);
    float cap=smoothstep(0,.12,t)*(1-smoothstep(.87,1,t));
    float3 rgb=lerp(float3(.09,.48,.75),float3(.84,.97,1.0),core);
    return float4(rgb*(1.2+2.7*core+.55*strand), saturate(cap*(.30*bloom+.55*core+.15*strand))*saturate(Fade)*saturate(Opacity));
""")
pin=u.CustomInput()
pin.set_editor_property('input_name','UV')
fade_pin=u.CustomInput()
fade_pin.set_editor_property('input_name','Fade')
opacity_pin=u.CustomInput()
opacity_pin.set_editor_property('input_name','Opacity')
color.set_editor_property('inputs',[pin,fade_pin,opacity_pin])
edit.connect_material_expressions(uv,'',color,'UV')
fade=node(u.MaterialExpressionScalarParameter,parameter_name='RidgeFade',default_value=1.)
edit.connect_material_expressions(fade,'',color,'Fade')
strength=node(u.MaterialExpressionScalarParameter,parameter_name='RidgeOpacity',default_value=.46)
edit.connect_material_expressions(strength,'',color,'Opacity')
rgb=node(u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
opacity=node(u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
for expr in (rgb,opacity): edit.connect_material_expressions(color,'',expr,'')
exposure=node(u.MaterialExpressionEyeAdaptationInverse)
inputs=edit.get_material_expression_input_names(exposure)
edit.connect_material_expressions(rgb,'',exposure,inputs[0])
edit.connect_material_expressions(node(u.MaterialExpressionConstant,r=1.),'',exposure,inputs[1])
edit.connect_material_property(exposure,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
edit.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
errors=edit.recompile_material(material)
if errors: raise RuntimeError('Ridge gather material compile: '+str(errors))
lib.set_metadata_tag(material,'Highland.Author','RidgeGather')
if not lib.save_loaded_asset(material,False): raise RuntimeError('Could not save '+path)
u.log('RIDGE_GATHER_SAVED '+path)
