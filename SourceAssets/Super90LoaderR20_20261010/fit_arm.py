import itertools
from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'arm_clearance.py').read_text(encoding='utf-8'),str(O/'arm_clearance.py'),'exec'))
fit=[]
for branch in ('normal','empty'):
    end=len(source_rows[branch])-1
    for f in range(89,end):
        p=source_rows[branch][f];fit.append((p,envelope(f,end)))
print('FIT_START',len(fit),'proximal',len(proximal),'station range',float(station[upper].min()),float(station[upper].max()),flush=True)
results=[]
for dx,dy,dz,angle in itertools.product((0,3,6),(-8,-12,-16,-20),(-6,-10,-14),(-20,0,20)):
    try:costs=[clearance_cost(support_pose(p,(dx,dy,dz),angle,w)) for p,w in fit]
    except ValueError:continue
    cost=max(costs)+.2*np.mean(costs)+.015*(dx*dx+dy*dy+dz*dz)+.001*angle*angle
    results.append(dict(offset=[dx,dy,dz],angle=angle,cost=float(cost),maximum=float(max(costs))))
results.sort(key=lambda r:r['cost']);(O/'fit.json').write_text(json.dumps(results[:25],indent=2),encoding='utf-8')
print('FIT_RESULTS',json.dumps(results[:5]),flush=True)
if not results:raise RuntimeError('No reachable support pose')
chosen=results[0];out={};report=[]
for branch,rows in source_rows.items():
    if branch=='cycle':out[branch]=rows;continue
    out[branch]=[]
    for f,p in enumerate(rows):
        q=support_pose(p,chosen['offset'],chosen['angle'],envelope(f,len(rows)-1));out[branch].append(q)
        if f>=88:
            a=cloth_points(p);b=cloth_points(q)
            report.append(dict(branch=branch,frame=f,before=coverage(a,proximal),after=coverage(b,proximal),before_upper=coverage(a,upper),after_upper=coverage(b,upper)))
(O/'candidate_poses.json').write_text(json.dumps({b:[{n:[list(r) for r in m] for n,m in p.items()} for p in ps] for b,ps in out.items()},separators=(',',':')),encoding='utf-8')
(O/'clearance.json').write_text(json.dumps(dict(parameters=chosen,rows=report),indent=2),encoding='utf-8')
