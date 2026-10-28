"""Read the reported grip and optic packages, without running gameplay."""
import unreal as u
import json
from pathlib import Path
P=Path(__file__).parent
root='/Game/Weapons/WoodSteelLongbow20261026/'
names=['SM_WoodSteelLongbow_Grip_Linen','SM_WoodSteelLongbow_Optic2x','SM_WoodSteelLongbow_Optic4x']
report={'meshes':{},'materials':{},'dirty_packages':[x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
for name in names:
    mesh=u.load_asset(root+name)
    report['meshes'][name]=[
        {'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None}
        for s in mesh.static_materials]
paths={s['material'] for slots in report['meshes'].values() for s in slots if s['material']}
for path in sorted(paths):
    mat=u.load_asset(path)
    row={'class':mat.get_class().get_name()}
    if isinstance(mat,u.Material):
        row.update(blend=str(mat.get_editor_property('blend_mode')),two_sided=mat.get_editor_property('two_sided'),
            expressions=u.MaterialEditingLibrary.get_num_material_expressions(mat))
        for label,prop in [('base',u.MaterialProperty.MP_BASE_COLOR),('normal',u.MaterialProperty.MP_NORMAL),('emissive',u.MaterialProperty.MP_EMISSIVE_COLOR),('opacity',u.MaterialProperty.MP_OPACITY)]:
            expr=u.MaterialEditingLibrary.get_material_property_input_node(mat,prop)
            row[label]=expr.get_class().get_name() if expr else None
            if expr and isinstance(expr,u.MaterialExpressionConstant3Vector):row[label+'_value']=str(expr.constant)
    report['materials'][path]=row
(P/'asset-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
