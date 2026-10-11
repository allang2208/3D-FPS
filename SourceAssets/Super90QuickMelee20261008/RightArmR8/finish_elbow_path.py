"""Continuous anatomical elbow-plane curves; prevent stock-avoidance branch flips."""
from pathlib import Path
O=Path(__file__).parent
exec((O/'author_motion.py').read_text().split('result=copy.deepcopy(D)')[0])
auth=json.loads((O/'authored_poses.json').read_text());result=json.loads((O/'animation_patch.json').read_text())
allposes={};locals_by_family={};diagnostic={}
knots=[0,12,18,27,40,49,60,82,105,115,120,144,168,192,216]
right=np.linalg.inv(CL)@np.array([0.,1.,0.])
for family in ['base',*D['profiles']]:
    source,local=decode(family);fitted=np.array(json.loads((O/('fit_parameters_'+family+'.json')).read_text()))
    poses=[{n:np.array(m) for n,m in row.items()} for row in auth[family]]
    for f in [27,115]:
        p=source[f];gp=poses[f];gi=np.linalg.inv(p['WPN_root']@ri['WPN_root'])
        if min(clearance(skinned(gp),gi))<.006:
            def residual(x):
                q=solve_arm(p,gp,fitted[f,3]+x[3],1.,x[:3]);gap=clearance(skinned(q),gi)
                return np.r_[np.sort(np.maximum(0,.010-gap))[-15:]/.0015,x[:3]/.04,x[3]/.5]
            seeds=[np.array([a,b,c,d]) for a in [0,-.05,-.1] for b in [0,.06,.12] for c in [0,-.04,-.08] for d in [-.8,0,.8]]
            seed=min(seeds,key=lambda x:np.linalg.norm(residual(x)))
            fit=least_squares(residual,seed,bounds=([-.10,0,-.08,-.8],[0,.12,0,.8]),max_nfev=120)
            poses[f]=solve_arm(p,gp,fitted[f,3]+fit.x[3],1.,fit.x[:3])
    angles=[];shoulders=[]
    for f in knots:
        p=poses[f];a,e,h=[p[n][:3,3] for n in ['upperarm_r','lowerarm_r','hand_r']]
        axis=unit(h-a);u=unit(right-axis*(right@axis));v=np.cross(axis,u)
        pole=unit(e-a-axis*((e-a)@axis));angles.append(np.arctan2(pole@v,pole@u));shoulders.append(a)
    angles=np.unwrap(angles)
    curve=PchipInterpolator(np.array(knots)/D['fps'],angles)(times)
    ashoulder=PchipInterpolator(np.array(knots)/D['fps'],np.array(shoulders),axis=0)(times)
    rows=[];out={n:[] for n in WRITE}
    for f,(p,gp) in enumerate(zip(source,poses)):
        a=ashoulder[f];h=gp['hand_r'][:3,3];axis=unit(h-a);u=unit(right-axis*(right@axis));v=np.cross(axis,u)
        pole=np.cos(curve[f])*u+np.sin(curve[f])*v
        shift=CL@(a-p['upperarm_r'][:3,3])
        q=solve_arm(p,gp,0.,blend[f],shift,pole) if blend[f]>1e-8 else p
        packed=encode(q)
        for n in WRITE:out[n].append(packed[n])
        rows.append({n:m.tolist() for n,m in q.items()})
    for n in WRITE:local[n]=np.array(out[n])
    locals_by_family[family]=local;allposes[family]=rows
    diagnostic[family]=dict(knots=knots,elbow_plane_degrees=np.degrees(angles).tolist(),shoulder_author_m=np.array(shoulders).tolist())
    print('R8_CONTINUOUS_ELBOW_AUTHORED',family,flush=True)
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
(O/'elbow_path_controls.json').write_text(json.dumps(diagnostic,indent=2))
print('R8_CONTINUOUS_ELBOW_DONE',flush=True)
