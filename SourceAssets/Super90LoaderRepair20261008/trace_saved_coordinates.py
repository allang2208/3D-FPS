"""Locate whether the reported failure occurs in source motion or FBX import."""
import json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;author=O.parent/'Super90Speedloader20261007/author_speedloader.py'
s={'__file__':str(author)}
exec(compile((O/'Before/Source/author_speedloader.py').read_text().split('def local_rows(')[0],str(author),'exec'),s)
data=json.loads((O/'saved_motion_r3.json').read_text());out=[]
for kind,clip in data['clips'].items():
    count=int(kind[-1]);empty=kind.startswith('empty')
    for row in clip['rows']:
        world={}
        for n in s['names']:world[n]=world.get(s['parents'][n],Matrix.Identity(4))@s['uemat'](row['local'][n])
        actual={n:s['evaluation_to_author']@s['Ci']@world[n]@s['Ki'][n] for n in s['names']}
        expected=s['pose'](row['frame'],count,empty)[0]
        bones=('upperarm_l','lowerarm_l','hand_l','WPN_root','WPN_Shell')
        out.append({'clip':kind,'mode':row['mode'],'frame':row['frame'],
          'position_error_cm':{n:100*(actual[n].translation-expected[n].translation).length for n in bones},
          'scale':{n:list(actual[n].to_scale()) for n in bones}})
(O/'saved_coordinate_trace_r3.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
for mode in ('SOURCE','COMPRESSED'):
    print(mode, 'max coordinate difference cm',max(v for r in out if r['mode']==mode for v in r['position_error_cm'].values()),flush=True)
