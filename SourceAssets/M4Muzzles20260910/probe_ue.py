import unreal,json
from pathlib import Path
out=Path(__file__).parent
m=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
data={'materials':[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name() if s.material_interface else None} for s in m.materials]}
for row in data['materials']:
 mat=unreal.load_asset(row['asset']) if row['asset'] else None
 if mat:
  try:row['textures']=[t.get_path_name() for t in unreal.MaterialEditingLibrary.get_used_textures(mat)]
  except Exception:pass
(out/'ue-rifle-materials.json').write_text(json.dumps(data,indent=2))
unreal.log('MUZZLE_PROBE_PASS')
