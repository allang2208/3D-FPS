"""Summarize the opt-in UE fixture's observed state, without changing assets."""
import json, sys, math
from pathlib import Path
root=Path(sys.argv[1])
def rows(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()] if path.exists() else []
report={'run':str(root),'peers':{}}
for role in ('host','early','late'):
    surface=rows(root/role/'surface.jsonl'); bodies=rows(root/role/'bodies.jsonl')
    r={'captures':[{k:v for k,v in row.items() if k!='world_pose'} for row in surface if 'capture' in row]}
    r['corpse_samples']=len(bodies)
    r['unfrozen_settled_without_support']=[{'time':b['time'],'actor':b['actor'],'closest_cm':min((x['actual_surface_distance_cm'] for x in b['bodies'] if x['collision']),default=None)} for b in bodies if b['settled'] and not b['support'] and not b['frozen']]
    r['fastest_bodies']=[{'time':b['time'],'actor':b['actor'],'support':b['support'],'settled':b['settled'],'bodies':sorted(b['bodies'],key=lambda x:max(x['linear']/10,x['angular']/.3),reverse=True)[:2]} for b in bodies[-8:]]
    report['peers'][role]=r
host=[r for r in rows(root/'host'/'surface.jsonl') if r.get('capture')=='frozen']
report['frozen_peer_errors']={}
if host:
    h=host[-1]['world_pose']
    for role in ('early','late'):
        cs=[r for r in rows(root/role/'surface.jsonl') if r.get('capture')=='frozen']
        if not cs: continue
        c=cs[-1]['world_pose'];pos=angle=0
        for bone,a in h.items():
            b=c[bone];pos=max(pos,math.dist(a[:3],b[:3]));dot=min(1,abs(sum(x*y for x,y in zip(a[3:],b[3:]))))
            angle=max(angle,2*math.degrees(math.acos(dot)))
        report['frozen_peer_errors'][role]={'position_cm':pos,'angle_deg':angle}
(root/'analysis.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(report,indent=2,ensure_ascii=False))
