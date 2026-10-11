import itertools
from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'arm_clearance.py').read_text(encoding='utf-8'),str(O/'arm_clearance.py'),'exec'))
sets={}
for phase,frames in (('release',range(112,125,2)),('bolt',range(138,163,3))):
    results=[]
    for dx,dy,dz,angle in itertools.product((-3,0,3,6),(-4,-8,-12,-16),(-6,-10,-14),(-45,-30,-15,0,15,30,45)):
        try:costs=[clearance_cost(support_pose(source_rows['empty'][f],(dx,dy,dz),angle,1)) for f in frames]
        except ValueError:continue
        cost=max(costs)+.25*np.mean(costs)+.012*(dx*dx+dy*dy+dz*dz)+.0015*angle*angle
        results.append(dict(offset=[dx,dy,dz],angle=angle,cost=float(cost)))
    results.sort(key=lambda r:r['cost']);sets[phase]=results[:20]
    print('PHASE',phase,json.dumps(results[:3]),flush=True)

def correct(p,f,end,a,b):
    t=smooth((f-122)/16);off=Vector(a['offset']).lerp(Vector(b['offset']),t);angle=a['angle']*(1-t)+b['angle']*t
    return support_pose(p,off,angle,envelope(f,end))

candidates=[]
for a,b in itertools.product(sets['release'],sets['bolt']):
    try:
        for branch in ('normal','empty'):
            rows=source_rows[branch];end=len(rows)-1
            for f,p in enumerate(rows):correct(p,f,end,a,b)
    except ValueError:continue
    candidates.append(dict(release=a,bolt=b,cost=a['cost']+b['cost']))
candidates.sort(key=lambda r:r['cost'])
if not candidates:raise RuntimeError('No coherent reachable pair')
chosen=candidates[0];(O/'phase_fit.json').write_text(json.dumps(dict(chosen=chosen,phases=sets),indent=2),encoding='utf-8')
out={};report=[]
for branch,rows in source_rows.items():
    if branch=='cycle':out[branch]=rows;continue
    out[branch]=[]
    for f,p in enumerate(rows):
        q=correct(p,f,len(rows)-1,chosen['release'],chosen['bolt']);out[branch].append(q)
        if f>=88:
            a=cloth_points(p);b=cloth_points(q)
            report.append(dict(branch=branch,frame=f,before=coverage(a,proximal),after=coverage(b,proximal),before_upper=coverage(a,upper),after_upper=coverage(b,upper)))
(O/'candidate_poses.json').write_text(json.dumps({b:[{n:[list(r) for r in m] for n,m in p.items()} for p in ps] for b,ps in out.items()},separators=(',',':')),encoding='utf-8')
(O/'clearance.json').write_text(json.dumps(dict(parameters=chosen,rows=report),indent=2),encoding='utf-8')
print('PHASE_FIT_CHOSEN',json.dumps(chosen),flush=True)
