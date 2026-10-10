"""Read the exact grip/tail material inputs needed for production, no writes to UE."""
import unreal as u
import json
from pathlib import Path
P=Path(__file__).resolve().parent
B='/Game/Weapons/ApprenticeStaff20260927/Meshes/SM_Staff_'
keys=['grip_lining_'+x for x in ['false','alloy_grip','pine_grip','sandalwood_grip']]
keys+=['tail_charm_'+x for x in ['ice_soul_pendant','thunder_bell','purification_vine','flame_pendant']]
data={}
for key in keys:
    mesh=u.load_asset(B+key); mats=[]
    for slot in mesh.static_materials:
        mat=slot.material_interface; nodes=[]
        if isinstance(mat,u.Material):
            for n in u.MaterialEditingLibrary.get_material_expressions(mat):
                d={'class':n.get_class().get_name()}
                if isinstance(n,u.MaterialExpressionTextureSample):d['texture']=n.texture.get_path_name() if n.texture else None
                if isinstance(n,u.MaterialExpressionConstant):d['value']=n.r
                if isinstance(n,u.MaterialExpressionConstant3Vector):d['value']=[n.constant.r,n.constant.g,n.constant.b]
                nodes.append(d)
        mats.append({'path':mat.get_path_name(),'nodes':nodes})
    bounds=mesh.get_bounding_box()
    data[key]={'materials':mats,'bounds':[str(bounds.min),str(bounds.max)]}
(P/'inputs.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('STAFF_GRIP_TAIL_INPUTS_WRITTEN')
