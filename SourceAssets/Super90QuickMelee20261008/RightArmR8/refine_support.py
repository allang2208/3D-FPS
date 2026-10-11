"""Finish body-side shoulder/elbow clearance without changing the fitted grasp."""
from pathlib import Path
O=Path(__file__).parent
exec((O/'author_motion.py').read_text().split('result=copy.deepcopy(D)')[0])
auth=json.loads((O/'BeforeSupportRefinement/authored_poses.json').read_text())
result=json.loads((O/'BeforeSupportRefinement/animation_patch.json').read_text())
reports={};allposes={};locals_by_family={}
for family in ['base',*D['profiles']]:
    source,local=decode(family)
    fitted=np.array(json.loads((O/('fit_parameters_'+family+'.json')).read_text()))
    poses=[{n:np.array(m) for n,m in p.items()} for p in auth[family]]
    frames=sorted(set([*range(0,len(times),3),27,40,49,len(times)-1]));keys=[]
    for f in frames:
        w=blend[f];p=source[f];gp=poses[f];gi=np.linalg.inv(p['WPN_root']@ri['WPN_root'])
        if w<.10 or min(clearance(skinned(gp),gi))>=.006:
            keys.append(np.zeros(4));continue
        def residual(x):
            q=solve_arm(p,gp,fitted[f,3]+x[3],w,x[:3])
            gap=clearance(skinned(q),gi)
            return np.r_[np.sort(np.maximum(0,.010-gap))[-15:]/.0015,x[:3]/.045,x[3]/.60]
        seeds=[np.array([a,b,c,d])*w for a in [0,-.05] for b in [0,.06] for c in [0,-.04,-.08] for d in [-.8,0,.8]]
        seed=min(seeds,key=lambda x:np.linalg.norm(residual(x)))
        fit=least_squares(residual,seed,bounds=(np.array([-.10,0,-.08,-.8])*w,np.array([0,.12,0,.8])*w),max_nfev=90,ftol=1e-4,xtol=1e-4,gtol=1e-4)
        keys.append(fit.x)
    controls=PchipInterpolator(np.array(frames)/D['fps'],np.array(keys),axis=0)(times)
    controls=gaussian_filter1d(controls,1.5,axis=0)*blend[:,None]
    rows=[];reports[family]=[];output={n:[] for n in WRITE}
    for f,(p,gp) in enumerate(zip(source,poses)):
        x=controls[f]
        q=solve_arm(p,gp,fitted[f,3]+x[3],blend[f],x[:3]) if blend[f]>1e-8 else p
        packed=encode(q)
        for n in WRITE:output[n].append(packed[n])
        rows.append({n:m.tolist() for n,m in q.items()})
        gap=float(1000*min(clearance(skinned(q),np.linalg.inv(p['WPN_root']@ri['WPN_root']))))
        reports[family].append(dict(frame=f,shoulder_offset_camera_cm=(100*x[:3]).tolist(),pole_extra_degrees=float(np.degrees(x[3])),stock_clearance_mm=gap))
    allposes[family]=rows
    for n in WRITE:local[n]=np.array(output[n])
    locals_by_family[family]=local
    print('R8_SUPPORT_FINISHED',family,flush=True)
base=locals_by_family['base']
result['base_tracks']=[track(t['bone'],base[t['bone']]) if t['bone'] in WRITE else t for t in result['base_tracks']]
zero=np.array([0,0,0,0,0,0,1,0,0,0])
for family in D['profiles']:
    local=locals_by_family[family];tracks=[t for t in result['profiles'][family]['clip']['tracks'] if t['bone'] not in WRITE]
    for n in WRITE:
        q=(R.from_quat(local[n][:,3:7])*R.from_quat(base[n][:,3:7]).inv()).as_quat();q[q[:,3]<0]*=-1
        delta=np.c_[local[n][:,:3]-base[n][:,:3],q,local[n][:,7:]-base[n][:,7:]]
        if np.max(np.abs(delta-zero))>1e-7:tracks.append(track(n,delta))
    result['profiles'][family]['clip']['tracks']=tracks
(O/'animation_patch.json').write_text(json.dumps(result,separators=(',',':')))
(O/'authored_poses.json').write_text(json.dumps(allposes,separators=(',',':')))
(O/'support_refinement.json').write_text(json.dumps(reports,separators=(',',':')))
print('R8_SUPPORT_REFINEMENT_DONE',flush=True)
