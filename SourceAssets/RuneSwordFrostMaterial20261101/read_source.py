from pathlib import Path
import json
import unreal as u
P=Path(__file__).resolve().parent
L=u.MaterialEditingLibrary
mesh=u.load_asset('/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SM_FrostSword_Blade_factory')
report=[]
for slot in mesh.get_editor_property('static_materials'):
    mat=slot.get_editor_property('material_interface')
    entry={'material':mat.get_path_name()}
    while isinstance(mat,u.MaterialInstanceConstant):
        mat=mat.get_editor_property('parent')
    entry['parent']=mat.get_path_name()
    entry['nodes']=[]
    for n in L.get_material_expressions(mat):
        row={'name':n.get_name(),'class':n.get_class().get_name()}
        if isinstance(n,u.MaterialExpressionTextureSample):row['texture']=n.texture.get_path_name() if n.texture else None
        if isinstance(n,u.MaterialExpressionCustom):row['code']=n.get_editor_property('code')
        entry['nodes'].append(row)
    report.append(entry)
(P/'source-material.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('FROST_SOURCE_READ',[(e['material'],e['parent']) for e in report])
