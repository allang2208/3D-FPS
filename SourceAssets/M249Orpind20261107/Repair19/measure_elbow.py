from pathlib import Path
exec(compile((Path(__file__).parent/'dense_bvh.py').read_text().split('for key,data in cache.items():')[0],__file__,'exec'))
scores={}
for trial in pickle.load(open(r/'elbow_trials.pkl','rb')):
    w=trial['world'];xf=w@ib;p=np.zeros_like(v)
    for b,js,pts in groups:p[js]+=pts@xf[b,:3,:].T
    count=0
    for bone,parts in [('WPN_root',('SM_M249_SidePort','Receiver')),('WPN_SOCKET_Magazine',('SM_m249_side_mag_30','SM_m249_side_mag_45'))]:
        m=w[ix[bone]];rot=m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0);local=(p-m[:3,3])@rot;hand=BVHTree.FromPolygons(local.tolist(),ff.tolist(),all_triangles=True)
        count+=sum(len(hand.overlap(trees[name])) for name in parts)
    key=(trial['family'],trial['phase'],trial['degrees']);scores[key]=scores.get(key,0)+count
out={}
for family in ('base','vertical','canted','prism','angled'):
    out[family]={}
    for phase in ('approach','return'):
        candidates=[(abs(degrees),hits,degrees) for (f,ph,degrees),hits in scores.items() if f==family and ph==phase and hits==0]
        if not candidates:raise RuntimeError('No clear elbow '+family+' '+phase)
        out[family][phase]=min(candidates)[2]
(r/'elbow_clearance.json').write_text(json.dumps(out,indent=2));print('ELBOW_CLEARANCE',out,flush=True)
