import json,runpy
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'
receipt=json.loads((R/'SkinCoverage/asset-receipt.json').read_text())
if not receipt['complete'] or len(receipt['profiles'])!=22:raise RuntimeError('Incomplete exposed-skin family')
for path in receipt['profiles'].values():
    if not u.EditorAssetLibrary.does_asset_exist(path):raise RuntimeError('Missing '+path)
runpy.run_path(str(P/'Tools/ModularOutfit/publish_fingerless_hunt_v2.py'))
cfgpath=P/'Content/ColdSteelData/modular_outfits.json';cfg=json.loads(cfgpath.read_text(encoding='utf-8-sig'))
cfg['items']['ue_field_gloves']['skin_meshes']=receipt['profiles'];cfg['items']['ue_field_gloves']['glove_in_base']=True
cuff='/Game/Characters/ModularOutfit20260924/FingerlessHuntV2/PKM/SK_PKM_FingerlessCuff.SK_PKM_FingerlessCuff'
if cfg['items']['ue_field_gloves'].get('sleeve_meshes',{}).get('PKM')==cuff:
    del cfg['items']['ue_field_gloves']['sleeve_meshes']['PKM']
    if not cfg['items']['ue_field_gloves']['sleeve_meshes']:del cfg['items']['ue_field_gloves']['sleeve_meshes']
cfgpath.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(R/'coupled-published.json').write_text(json.dumps(dict(item='ue_field_gloves',skin_companions=22,shared_opening_seams=True,original_naked_skin_changed=False),indent=2))
print('COUPLED_FINGERLESS_PUBLISHED',22,flush=True)
