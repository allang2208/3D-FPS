import unreal as u,json
from pathlib import Path
m=u.load_asset('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
rows=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else ''} for s in m.materials]
(Path(__file__).parent/'svd_slots.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows),flush=True)
