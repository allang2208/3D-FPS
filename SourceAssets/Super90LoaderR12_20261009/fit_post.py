"""Fit the rotating pusher grip to a readable, anatomically reachable stroke."""
from pathlib import Path
O=Path(__file__).parent
g={'__file__':str(O/'r12_core.py')}
for part in ('r12_core.py','skin_arm.py','r12_motion.py'):
    exec(compile((O/part).read_text(),str(O/part),'exec'),g)
globals().update({k:v for k,v in g.items() if not k.startswith('__')})
rows=[]
for psi in range(-180,181,30):
    LAYOUT['post_psi']=psi;pose_cache.clear()
    frames=[pose(f,7,True)[0] for f in range(87,115)]
    stats=[p['_stats']['left'] for p in frames]
    score=sum((s['skin_pronation_degrees']/100)**2+(s['shoulder_shift_cm']/10)**2 for s in stats)/len(stats)
    for p in frames:
        u,v,depth=screen(p['hand_l'].translation)
        score+=max(0,abs(u)-.8)*3+max(0,abs(v)-.85)*2+max(0,17-depth)
    row=dict(psi=psi,score=score,twist=[round(s['skin_pronation_degrees']) for s in stats[::9]],shift=max(s['shoulder_shift_cm'] for s in stats))
    rows.append(row)
print('POST_FIT',json.dumps(sorted(rows,key=lambda r:r['score']),indent=2),flush=True)
