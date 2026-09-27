"""Retain every original skin UV channel, vertex color and material in the cut companion."""
import json,sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/ModularOutfit'));ns={}
exec((P/'Tools/ModularOutfit/author_coupled_fingerless.py').read_text().split('manifest=[];skin_manifest=[]')[0],ns)
R=ns['R'];OUT=ns['OUT'];manifest=[]
for row in ns['read'](ns['REVIEW']/'mesh-manifest.json'):
    name=row['profile'];base=ns['welded_source'](ns['read'](ns['REVIEW']/(name+'_skin.json')));skin=ns['exposed_skin'](base)
    skin.update(profile=name,source=base['path'],family='FingerlessHuntV2_ExposedSkin')
    target=OUT/(name+'_review.json');temp=target.with_suffix('.writing');temp.write_text(json.dumps(skin,separators=(',',':')));temp.replace(target)
    manifest.append(dict(profile=name,source=base['path'],vertices=len(skin['positions']),triangles=len(skin['triangles'])))
    print('FINGERLESS_SKIN_COORDS',name,flush=True)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
