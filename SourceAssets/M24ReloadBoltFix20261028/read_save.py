import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent
s=u.GameplayStatics.load_game_from_slot('ColdSteelPlayer_PIE_0_B',0)
p=s.get_editor_property('profile');slot=p.get_editor_property('active_weapon_slot')
rows=[]
for item in p.get_editor_property('items'):
 definition=item.get_editor_property('definition');place=item.get_editor_property('place');cell=item.get_editor_property('cell')
 if place==1 or definition=='ue_m24':rows.append({n:str(item.get_editor_property(n)) for n in ('definition','place','cell','data','magazine')})
result={'active_slot':slot,'equipment':rows};(O/'saved_equipment.json').write_text(json.dumps(result,indent=2));print('M24_SAVED_EQUIPMENT',json.dumps(result),flush=True)
