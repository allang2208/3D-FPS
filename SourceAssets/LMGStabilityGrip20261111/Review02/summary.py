"""Summarize the actual role/case and presentation captures used in review."""
import json,sys
from pathlib import Path
from collections import Counter
r=Path(sys.argv[1])
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
rows=read(r/'host.json')['cases']
remote=[s for s in rows if s['owner']=='client']
out=dict(passed=read(r/'receipt.json')['passed'], unique_owner_cases=len({(s['case'],s['owner']) for s in rows}), save_reloads_passed=sum(s['profile_save_reload'] for s in rows), authority_matches=sum(s.get('authority_stats_match',False) for s in remote), wrong_owner_frames=sum(s['wrong_equipment_frames'] for s in rows), wrong_authority_frames=sum(s.get('remote_wrong_equipment_frames',0) for s in remote), max_regrip_boundary_cm=max(s['return_boundary_cm'] for s in rows), roles={}, stats={})
for s in rows:
    out['stats'][(s['definition']+' '+s['variant'])]=[s['recoil_ratio'],s['stability_ratio'],s['ads_duration_ratio'],s['ads_seconds_added']]
for owner in ['host','client']:
    v=r/owner/'Visual'
    counts={}
    for kind in ['Owner','Close','Remote']:
        seq=[json.loads(line) for line in (v/(kind.lower()+'.jsonl')).read_text().splitlines()]
        files=[a for a in seq if (v/kind/a['image']).is_file()]
        counts[kind]=len(files)
        if kind=='Remote':
            groups={}
            for a in files:
                if a.get('profile'): groups.setdefault(a['weapon_instance'],[]).append(a)
            relevant=[a for a in groups.values() if any(z['action'] in (2,3) for z in a)]
            counts['remote_loadouts']=len(relevant)
            counts['remote_finished_idle']=sum(a[-1]['action']==0 and not a[-1]['aiming'] for a in relevant)
        else:
            counts[kind+'_stages_by_case']={str(i):dict(Counter(a['stage'] for a in files if a['case']==i)) for i in range(8)}
    out['roles'][owner]=counts
(r/'summary.json').write_text(json.dumps(out,indent=2))
print({k:v for k,v in out.items() if k!='roles'})
for name,v in out['roles'].items():print(name,{k:n for k,n in v.items() if 'stages' not in k})
