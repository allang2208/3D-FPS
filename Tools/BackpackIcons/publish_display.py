"""Install only the inventory display leaf using the shared configuration writer."""
import json,runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackIcons20261025/FrontR1'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
saved=read(R/'display_saved.json');plan=read(R/'plan.json')
if not saved['completed']:raise RuntimeError('Finish saving display assets')
path=P/'Content/ColdSteelData/player_body.json';before=path.read_bytes();cfg=json.loads(before.decode('utf-8-sig'));owned=[]
for row in saved['items']:
 if not row['saved']:raise RuntimeError('Unsaved display '+row['id'])
 key=row['id'];cfg['outfits'][key]['inventory_static_mesh']=row['asset'];owned.append(('outfits',key,'inventory_static_mesh'))
 for rig,variant in cfg.get('body_variants',{}).items():
  if key in variant.get('outfits',{}):variant['outfits'][key]['inventory_static_mesh']=row['asset'];owned.append(('body_variants',rig,'outfits',key,'inventory_static_mesh'))
result=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit'](path,before,cfg,owned_paths=owned,producer=__file__)
(R/'display_published.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('BACKPACK_DISPLAY_REFERENCES_SAVED',len(owned),flush=True)
