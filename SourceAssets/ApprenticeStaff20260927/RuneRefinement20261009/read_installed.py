"""Read current rune authoring inputs; no world or asset changes."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/Weapons/ApprenticeStaff20260927'
report={'meshes':[],'materials':{}}
for key in ['eagle_eye_rune','crit_rune','storm_rune']:
    mesh=u.load_asset(BASE+'/Meshes/SM_Staff_shaft_rune_'+key)
    if not mesh:raise RuntimeError('Missing rune '+key)
    mats=[]
    for slot in mesh.static_materials:
        mat=slot.material_interface
        mats.append(mat.get_path_name() if mat else '')
        if mat and isinstance(mat,u.Material):
            constants=[]
            for exp in u.MaterialEditingLibrary.get_material_expressions(mat):
                if isinstance(exp,u.MaterialExpressionConstant3Vector):
                    c=exp.get_editor_property('constant');constants.append([c.r,c.g,c.b])
            report['materials'][mat.get_path_name()]=constants
    report['meshes'].append(dict(key=key,path=mesh.get_path_name(),materials=mats))
(ROOT/'installed-inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
