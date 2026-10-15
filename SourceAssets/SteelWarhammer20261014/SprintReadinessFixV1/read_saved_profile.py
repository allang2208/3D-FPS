"""Read only the latest PIE profile's hammer/sprint prerequisites."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent
saved=u.GameplayStatics.load_game_from_slot('ColdSteelPlayer_PIE_0_A',0)
state=saved.get_editor_property('profile')
slot=state.get_editor_property('active_weapon_slot')
items=[]
for item in state.get_editor_property('items'):
    if item.get_editor_property('place')==1 and item.get_editor_property('cell')==slot:
        data=json.loads(item.get_editor_property('data'))
        items.append({'instance':item.get_editor_property('instance_id'),'definition':item.get_editor_property('definition'),
                      'fields':{k:data.get(k) for k in ['category','weaponType','isTwoHanded','tool_kind','tool_viewmodel']}})
report={'active_weapon_slot':slot,'active_tool_override':state.get_editor_property('active_production_tool'),
        'active_items':items,'stamina':state.get_editor_property('stamina'),
        'sprint_exhausted':state.get_editor_property('sprint_exhausted'),
        'dash_skill':str(state.get_editor_property('skills').get('dashAttack'))}
(P/'saved_prerequisites.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HAMMER_SPRINT_SAVED_PREREQUISITES '+json.dumps(report))
