"""Summarize production/build receipts without launching any acceptance checks."""
import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KMagazine20261017'
def read(name):return json.loads((O/'Receipts'/name).read_text(encoding='utf-8-sig'))
r={'weapon':'ue_saiga12k','option':'saiga12k_ext12','capacity':{'factory':8,'extended':12},'crosshair':'shared four-arc shotgun crosshair; duckbill ellipse retained','assets':read('assets.json'),'icon':read('icon.json'),'builds':read('build.json'),'authoring':read('authoring.json'),'icon_generation':'Icons/generation.json','runtime_tested':False,'editor_reopened_by_this_task':False,'editor_close':read('editor-close.json'),'incidental_build_fix':'FPSUDSHillsAtmosphere.cpp: PreviousFog->FogInscatteringColor renamed to current UE5.8 FogInscatteringLuminance; directional counterpart had already been corrected in shared workspace.'}
r['complete']=r['assets']['complete'] and len(r['builds'])==2 and all(x['exit_code']==0 for x in r['builds'])
(O/'Receipts/delivery.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print('SAIGA_EXT12_DELIVERY_RECORDED',r['complete'])
