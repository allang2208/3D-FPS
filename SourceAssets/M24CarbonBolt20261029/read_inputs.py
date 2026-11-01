"""Read the currently installed M24 material inputs for the carbon-bolt recipe."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent;L=u.MaterialEditingLibrary
mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
slots=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in mesh.materials]
m=u.load_asset('/Game/Weapons/M24/Surface20261027/Materials/M_M24RegionalSurface')
nodes=[]
for n in L.get_material_expressions(m):
    if isinstance(n,u.MaterialExpressionCustom):nodes.append({'name':str(n.get_editor_property('description')),'code':n.get_editor_property('code'),'inputs':[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]})
(O/'inputs.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'slots':slots,'customs':nodes},indent=2),encoding='utf-8')
print('M24_CARBON_INPUTS_SAVED',slots)
