"""Explicitly restore the accepted shared baseline, not a per-player equip API."""
import json
import time
from pathlib import Path
import unreal as u

OUT=Path(__file__).parent
SOURCE='/Game/Weapons/M4InfimaV3'
parents={
    'MI_Manny_01':'/Game/Characters/ArmsSkinSleeveCandidate/M_Manny_Sleeve_01',
    'MI_Manny_02':'/Game/Characters/ArmsGloveCuff3cmCandidate/M_Manny_RolledCuff3cm_02',
}
loaded=[(u.load_asset(SOURCE+'/'+name),u.load_asset(path)) for name,path in parents.items()]
assert all(mi and parent for mi,parent in loaded),'Restore dependencies before applying the baseline.'
rows=[]
for mi,parent in loaded:
    previous=mi.parent.get_path_name() if mi.parent else None
    mi.modify()
    u.MaterialEditingLibrary.set_material_instance_parent(mi,parent)
    if mi.get_name()=='MI_Manny_02':
        u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,'SkinScatterStrength',.18)
        u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,'GloveCuffStart',.8899122968)
        for name,value in [('SkinScatterStrength',.18),('GloveCuffStart',.8899122968)]:
            assert abs(u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi,name)-value)<.0001
    u.MaterialEditingLibrary.update_material_instance(mi)
    for attempt in range(10):
        if u.EditorAssetLibrary.save_loaded_asset(mi,False):break
        time.sleep(1)
    else:raise RuntimeError('Material remains occupied: '+mi.get_path_name())
    rows.append({'instance':mi.get_path_name(),'previous_parent':previous,'parent':mi.parent.get_path_name()})
(OUT/'applied_report.json').write_text(json.dumps(rows,indent=2))
u.log('HAND_APPEARANCE_STANDARD_APPLY_PASS')
