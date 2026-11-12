"""Clear the box by a smooth elbow-joint arc; keep the new hand pose and all lengths."""
from fit_hold import *
cache=pickle.load(open(root/'candidate.pkl','rb'));payload=json.load(gzip.open(root/'prism.json.gz','rt'));report={}
for path,c in d['clips'].items():
    if not path.endswith(('A_M249_reload','A_M249_reload_empty')):continue
    old=cache['prism',path];t=np.array(c['times']);window=ease(t/.07)*(1-ease((t-.28)/.25));active=np.flatnonzero(window>1e-8)
    baseline=np.array([box_clearance(old[k]) for k in active]);target=baseline+np.maximum(.45-baseline,0)*window[active];options=[]
    for deg in range(-36,37,3):
        new=old.copy()
        for k in active:new[k]=elbow_pose(old[k],[0,0,0,np.radians(deg)*window[k],0,0,0])
        margin=np.array([box_clearance(new[k]) for k in active]);deficit=float(np.maximum(target-margin-.03,0).max())
        options.append((deficit*1e5+abs(deg),deg,new,float(margin.min())))
    score,deg,new,minimum=min(options,key=lambda x:x[0])
    if score>100:raise RuntimeError('No joint-only clear elbow arc '+path)
    row=next(x for x in payload['clips'] if x['base']==path);a=encode(old,parents);b=encode(new,parents)
    for i in arm+[ha]:
        change=R.from_quat(b[:,i,3:7])*R.from_quat(a[:,i,3:7]).inv();original=next(x for x in row['tracks'] if x['bone']==names[i]);ts=np.unique(np.r_[t,original['times']]);corr=np.zeros((len(t),10));corr[:,3:7]=change.as_quat();add=sample(corr.ravel(),t,ts);v=sample(original['values'],original['times'],ts)
        v[:,3:7]=(R.from_quat(add[:,3:7])*R.from_quat(v[:,3:7])).as_quat()
        for k in range(1,len(v)):
            if v[k-1,3:7]@v[k,3:7]<0:v[k,3:7]*=-1
        original.update(times=ts.tolist(),values=v.ravel().tolist())
    reconstructed=compose(layer(np.array(c['frames']),path,payload,names,t),parents)
    hand_error=float(abs(reconstructed[:,ha]-old[:,ha]).max())
    position_error=float(np.linalg.norm(reconstructed[:,ha,:3,3]-old[:,ha,:3,3],axis=1).max())
    rotation_error=float(np.degrees((R.from_matrix(rot(reconstructed[:,ha]))*R.from_matrix(rot(old[:,ha])).inv()).magnitude()).max())
    if position_error>.001 or rotation_error>.03:raise RuntimeError('Encoded wrist compensation failed '+path+' position_cm='+str(position_error)+' rotation_deg='+str(rotation_error))
    report[path]=dict(pole_degrees=deg,minimum_lbs_margin_cm=minimum,hand_world_matrix_error=hand_error,hand_position_error_cm=position_error,hand_rotation_error_degrees=rotation_error,source_window_seconds=[0,.53])
    print('PRISM_ELBOW_ARC',report[path],flush=True)
with gzip.open(root/'prism.json.gz','wt') as f:json.dump(payload,f,separators=(',',':'))
(root/'prism_entry_arc.json').write_text(json.dumps(report,indent=2))
