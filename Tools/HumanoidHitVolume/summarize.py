import json
import sys
from pathlib import Path
p=Path(sys.argv[1]) if len(sys.argv)>1 else Path('SourceAssets/HumanoidHitVolume20261018/baseline.json')
if not p.exists():
    print('report not available');raise SystemExit(0)
d=json.loads(p.read_bytes())
print('complete',d.get('complete'),'monsters',len(d['monsters']))
for r in d['monsters']:
    print(r['id'],r.get('error',''),'PA',r.get('physics_asset'),'deferred',r.get('defer_kinematic_bone_update'))
    print(' bodies',[(x['bone'],x['trace_flag'],x['shapes'],x['reference_bounds']['size']) for x in r.get('head_bodies',[])])
    for pose in r.get('poses',[]):
        v=pose.get('views',[])
        sums={k:sum(x[k] for x in v) for k in ('visible_head_rays','complex_head_hits','simple_head_hits','complex_misses','complex_other_hits','head_hits_outside_mesh')}
        print(' ',pose['pose'],pose.get('error',''),sums,'coverage',round(sums['complex_head_hits']/max(1,sums['visible_head_rays'])*100,2),
              'drift',pose.get('head_body_position_error_before_forced_sync_cm'),pose.get('head_body_rotation_error_before_forced_sync_deg'),
              'head',pose.get('visible_head_bounds',{}).get('size'))
