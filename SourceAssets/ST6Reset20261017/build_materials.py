"""Make native-body cloth materials; retain the artist's original sleeve material."""
import json,sys,math
from pathlib import Path
import unreal as u
O=Path(__file__).parent;sys.path.insert(0,str(O))
from recipe import DEST
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
M=DEST+'/Materials';E.make_directory(M)
name='M_ST6NativeFabric';mat=u.load_asset(M+'/'+name) or A.create_asset(name,M,u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(mat)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
mat.set_editor_property('two_sided',False)
L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)

def node(cls,**props):
    v=L.create_material_expression(mat,cls)
    for k,x in props.items():v.set_editor_property(k,x)
    return v
def wire(a,b,pin,output=''):
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Material connection '+pin)
def interp(a):
    v=node(u.MaterialExpressionVertexInterpolator);wire(a,v,'');return v
def vector(name,value):return node(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value,1))
def scalar(name,value):return node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
texture=u.load_asset('/Game/Weapons/Super90/Cransh20261006/Textures/T_S90_sleeve_st6_generalist_Base_color')
if not texture:raise RuntimeError('Original ST6 fabric is missing')
inputs={
    'RestPosition':interp(node(u.MaterialExpressionPreSkinnedPosition)),
    'RestNormal':interp(node(u.MaterialExpressionPreSkinnedNormal)),
    'Fabric':node(u.MaterialExpressionTextureObjectParameter,parameter_name='OriginalFabric',texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR),
    'Origin':vector('Origin',(0,0,0)),
    'WidthAxis':vector('WidthAxis',(1,0,0)),
    'UpAxis':vector('UpAxis',(0,0,1)),
    'FrontAxis':vector('FrontAxis',(0,-1,0)),
    'ShoulderHeight':scalar('ShoulderHeight',52),
    'TorsoMode':scalar('TorsoMode',0),
}
custom=node(u.MaterialExpressionCustom,code=(O/'native_fabric.ush').read_text(),output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,description='ST6 original sleeves with rest-pose fabric on native body')
pins=[]
for key in inputs:
    p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
custom.set_editor_property('inputs',pins)
out=u.CustomOutput();out.set_editor_property('output_name','OutRoughness');out.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
custom.set_editor_property('additional_outputs',[out])
for key,value in inputs.items():wire(value,custom,key)
L.connect_material_property(custom,'',u.MaterialProperty.MP_BASE_COLOR)
L.connect_material_property(custom,'OutRoughness',u.MaterialProperty.MP_ROUGHNESS)
specular=node(u.MaterialExpressionConstant,r=.26);L.connect_material_property(specular,'',u.MaterialProperty.MP_SPECULAR)
L.recompile_material(mat)
if not E.save_loaded_asset(mat,False):raise RuntimeError('Cannot save native cloth material')
saved={'fabric':mat.get_path_name()}
surfaces={}
for profile in ('Body','Jason'):
    body=json.loads((O/'Read'/f'{profile}.json').read_text());bones=body['bones']
    origin=bones['pelvis']['position'];height=(bones['clavicle_l']['position'][2]+bones['clavicle_r']['position'][2])*.5-origin[2]
    name='MI_ST6Torso_'+profile
    instance=u.load_asset(M+'/'+name) or A.create_asset(name,M,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(instance,mat)
    L.set_material_instance_vector_parameter_value(instance,'Origin',u.LinearColor(*origin,1))
    L.set_material_instance_scalar_parameter_value(instance,'ShoulderHeight',height)
    L.set_material_instance_scalar_parameter_value(instance,'TorsoMode',1)
    L.update_material_instance(instance)
    if not E.save_loaded_asset(instance,False):raise RuntimeError('Cannot save torso material '+profile)
    saved[profile]=instance.get_path_name();surfaces[profile]={'origin':origin,'shoulder_height':height}
(O/'material_receipt.json').write_text(json.dumps({'saved':saved,'surfaces':surfaces},indent=2))
print('ST6_NATIVE_MATERIALS_SAVED',len(saved),flush=True)
