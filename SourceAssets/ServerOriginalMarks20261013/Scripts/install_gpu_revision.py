"""Install the new GPU package without replacing any existing package."""
from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
report=json.loads((ROOT/'Receipts/installation.json').read_text('utf-8'))
imported=json.loads((ROOT/'Receipts/ue-import.json').read_text('utf-8'))
gpu=next(m for m in imported['meshes'] if m['item_id']=='search_graphics_card')
relative=Path(gpu['path'].split('.',1)[0].removeprefix('/Game/')+'.uasset')
source=ROOT/'UEImportHost/Content'/relative;target=PROJECT/'Content'/relative
target.parent.mkdir(parents=True,exist_ok=True)
with source.open('rb') as incoming,target.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing)
(ROOT/'Receipts/installation-surface.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report['packages']=[p for p in report['packages'] if 'SM_Search_TripleFanGPU_' not in p['path']]
report['packages'].append(dict(path=str(target),bytes=target.stat().st_size))
report['gpu_tangent_frame']=gpu['tangent_frame']
(ROOT/'Receipts/installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('GPU_PACKAGE_INSTALLED',target)
