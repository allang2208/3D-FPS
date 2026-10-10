"""Build/save the dedicated focus orbit material. No preview, render or gameplay test."""
from pathlib import Path
from datetime import datetime
import json
import unreal as u

P=Path(__file__).resolve().parent
D='/Game/Weapons/SpellbookEvildeer20261009/Effects'
NAME='M_Spellbook_GoldOrbit'
E=u.MaterialEditingLibrary
mat=u.load_asset(D+'/'+NAME) or u.AssetToolsHelpers.get_asset_tools().create_asset(
    NAME,D,u.Material,u.MaterialFactoryNew())
if not mat:raise RuntimeError('Could not create spellbook gold material')
E.delete_all_material_expressions(mat)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property('two_sided',True)

def node(cls,**props):
    n=E.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def link(a,b,pin):
    if not E.connect_material_expressions(a,'',b,pin):raise RuntimeError('Connection failed: '+pin)

uv=node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
parameters={name:node(u.MaterialExpressionScalarParameter,parameter_name=name,
    default_value=value,group='Spellbook focus') for name,value in {'GoldAge':0.,'Fade':0.,'PageActivity':0.}.items()}
flow=node(u.MaterialExpressionCustom,code=(P/'gold_orbit.hlsl').read_text(encoding='utf-8'),
    output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
sources={'UV':uv,**parameters};pins=[]
for name in sources:
    pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
flow.set_editor_property('inputs',pins)
for name,source in sources.items():link(source,flow,name)
exposure=node(u.MaterialExpressionEyeAdaptationInverse)
exposure_pins=list(E.get_material_expression_input_names(exposure))
link(flow,exposure,str(exposure_pins[0]))
compensation=node(u.MaterialExpressionConstant,r=.8)
link(compensation,exposure,str(exposure_pins[1]))
depth=node(u.MaterialExpressionDepthFade,fade_distance_default=1.5,opacity_default=1.)
if not E.connect_material_property(exposure,'',u.MaterialProperty.MP_EMISSIVE_COLOR):
    raise RuntimeError('Could not connect emission')
if not E.connect_material_property(depth,'',u.MaterialProperty.MP_OPACITY):
    raise RuntimeError('Could not connect soft intersection fade')
E.layout_material_expressions(mat)
errors=list(E.recompile_material(mat))
if errors:raise RuntimeError('Gold orbit shader compile failed: '+str(errors))
u.EditorAssetLibrary.set_metadata_tag(mat,'SpellbookEffect','Two ribbons and sixteen motes; UV flow; no physics or light')
if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise RuntimeError('Could not save gold material')
(P/'install_receipt.json').write_text(json.dumps({
    'saved_at':datetime.now().isoformat(timespec='seconds'),'material':mat.get_path_name(),
    'shader_build_errors':errors,'triangles':416,'components':1,
    'runtime_tested':False,'rendered':False},indent=2),encoding='utf-8')
u.log('SPELLBOOK_GOLD_ORBIT_SAVED '+mat.get_path_name())
