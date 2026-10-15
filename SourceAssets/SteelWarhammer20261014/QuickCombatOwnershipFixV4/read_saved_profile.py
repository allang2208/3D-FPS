"""Read only the saved equipment context relevant to quick-combat routing."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent
saved=u.GameplayStatics.load_game_from_slot('ColdSteelPlayer_PIE_0_A',0)
state=saved.get_editor_property('profile')
out={'active_slot':state.get_editor_property('active_weapon_slot'),'active_tool':state.get_editor_property('active_production_tool'),'equipment':[]}
for item in state.get_editor_property('items'):
    if item.get_editor_property('place')!=1:continue
    out['equipment'].append({k:str(item.get_editor_property(k)) for k in ('definition','instance_id','cell','data')})
(P/'user_equipment.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'active_slot':out['active_slot'],'active_tool':out['active_tool'],'equipment':[{k:i[k] for k in ('definition','cell')} for i in out['equipment']]}))
