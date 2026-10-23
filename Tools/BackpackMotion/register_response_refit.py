"""Keep the corrected mountain/knit fit in the motion authoring manifest."""
import hashlib
import json
from pathlib import Path

R=Path('D:/FPS3D/FPSGAME/SourceAssets/BackpackMotion20261022')


def apply(plan):
    root=R/'MountainSweaterR2'
    if not (root/'fit_delta.json').exists():return
    fit=json.loads((root/'fit_delta.json').read_text())
    row=next(r for r in plan['variants'] if r['kind']=='mountain' and r['profile']=='knit_sweater')
    for key,name in [('source','authored.json'),('mask','mask.json')]:
        path=root/name;row[key]=str(path);row[key+'_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    row.update(input_asset=fit['input_asset'],asset=fit['asset'],new_geometry=False,fit_delta=str(root/'fit_delta.json'))


if __name__=='__main__':
    path=R/'manifest.json';plan=json.loads(path.read_text());apply(plan)
    path.write_text(json.dumps(plan,indent=2),encoding='utf-8')
