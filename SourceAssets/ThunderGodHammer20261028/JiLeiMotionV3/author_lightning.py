"""Isolated blue-white Ji Lei charge lightning material; other seats stay gold."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
D='/Game/Weapons/ThunderGodHammer20261028/JiLeiSeatV1'
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
name='M_JiLei_BlueWhiteLightning'
m=u.load_asset(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
m.modify();L.delete_all_material_expressions(m)
m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
m.set_editor_property('two_sided',True)
def node(cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
strength=node(u.MaterialExpressionScalarParameter,parameter_name='Strength',default_value=4.)
uv=node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
v=node(u.MaterialExpressionComponentMask,r=False,g=True,b=False,a=False)
wave=node(u.MaterialExpressionSine,period=1.)
absolute=node(u.MaterialExpressionAbs)
edge=node(u.MaterialExpressionPower,const_exponent=3.)
blue=node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.12,1.8,9.,1.))
white=node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(8.,12.,16.,1.))
core=node(u.MaterialExpressionLinearInterpolate)
for source,target,pin in [(uv,v,''),(v,wave,''),(wave,absolute,''),(absolute,edge,'Base'),(blue,core,'A'),(white,core,'B'),(edge,core,'Alpha')]:
 if not L.connect_material_expressions(source,'',target,pin):raise RuntimeError('Material pin connection failed: '+pin)
glow=node(u.MaterialExpressionMultiply)
L.connect_material_expressions(core,'',glow,'A');L.connect_material_expressions(strength,'',glow,'B')
L.connect_material_property(glow,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
L.layout_material_expressions(m)
errors=L.recompile_material(m)
if errors:raise RuntimeError(str(errors))
if not u.EditorLoadingAndSavingUtils.save_packages([m.get_outermost()],False):raise RuntimeError('Blue white lightning save failed')
(P/'lightning-receipt.json').write_text(json.dumps({'complete':True,'asset':m.get_path_name(),'color':'blue edge / white-blue hot core','runtime_tested':False},indent=2))
print('JI_LEI_BLUE_WHITE_MATERIAL_SAVED',flush=True)
