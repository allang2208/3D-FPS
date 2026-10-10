"""Save integer circumferential repeats so the existing wrapped UV seam stays closed."""
from pathlib import Path
import json,unreal as u
P=Path(__file__).resolve().parent
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('PIE preserved')
specs=json.loads((P/'surfaces.json').read_text(encoding='utf-8'))
paths=['/Game/Weapons/ApprenticeStaff20260927/GripTailRefinement20261009/Materials/MI_StaffGripCraft_'+k for k,s in specs.items() if not s['metallic']]
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in paths):raise RuntimeError('Unsaved grip instance preserved')
saved=[]
for key,s in specs.items():
    if s['metallic']:continue
    mi=u.load_asset('/Game/Weapons/ApprenticeStaff20260927/GripTailRefinement20261009/Materials/MI_StaffGripCraft_'+key)
    u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi,'GrainScale',u.LinearColor(*s['uv_scale'],1))
    u.MaterialEditingLibrary.update_material_instance(mi)
    if not u.EditorAssetLibrary.save_loaded_asset(mi,False):raise RuntimeError('Cannot save '+mi.get_path_name())
    saved.append(mi.get_path_name())
receipt=json.loads((P/'install-receipt.json').read_text(encoding='utf-8'))
receipt['final_grip_surfaces']=specs;receipt['saved_assets'].extend(saved)
(P/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('STAFF_GRIP_SEAM_SAFE_SCALES_SAVED')
