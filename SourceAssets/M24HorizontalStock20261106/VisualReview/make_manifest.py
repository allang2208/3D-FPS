from pathlib import Path
import json
O=Path(__file__).resolve().parent
saved=json.loads((O.parent/'saved.json').read_text())
groups=[]
for kind in ('native','advanced'):
    a=saved['assets'][kind]
    for view,camera,target in [('side',[104,2.5,8.8],[0,2.5,8.8]),('joint',[24,5.0,13.7],[0,2.5,8.5])]:
        groups.append({'name':kind+'_'+view,'camera_cm':camera,'target_cm':target,
            'parts':[{'mesh':a['path'],'before':list(a['materials'].values()),'after':list(a['materials'].values())}]})
(O/'capture_manifest.json').write_text(json.dumps({'after_only':True,'groups':groups},indent=2))
print('M24_CAPTURE_MANIFEST',len(groups))
