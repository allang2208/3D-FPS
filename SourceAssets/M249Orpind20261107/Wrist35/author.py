"""Rotate shoulder/elbow only; retain every source local offset/scale and palm."""
from pathlib import Path
here=Path(__file__).resolve().parent
exec(compile((here/'fit_visibility_actual.py').read_text().split('payload=json.load')[0],str(here/'fit_visibility_actual.py'),'exec'))
payload=json.load(gzip.open(outdir/'prism-before.json.gz','rt'));original_payload=json.loads(json.dumps(payload))
from scipy.interpolate import PchipInterpolator
box_arcs=json.loads((outdir/'box_arc.json').read_text())
fit=json.loads((outdir/'visibility_fit.json').read_text());parameters=np.array(next(v for k,v in fit.items() if k.endswith('_empty'))['parameters'])
report={};poses={}
for path,c in d['clips'].items():
    if not path.endswith(('A_M249_reload','A_M249_reload_empty')):continue
    t=np.array(c['times']);base=np.array(c['frames']);oldlocal=layer(base,path,payload,names,t);old=compose(oldlocal,parents)
    empty=path.endswith('_empty');start,full,back,end=(1.25,1.75,4.85,5.25) if empty else (1.9,2.45,5.95,6.45)
    win=ease((t-start)/(full-start))*(1-ease((t-back)/(end-back)));new=old.copy()
    arc=box_arcs[path];keys=np.array([start]+[x['time'] for x in arc]+[end]);values=np.array([parameters]+[x['parameters'] for x in arc]+[parameters])
    curve=PchipInterpolator(keys,values,axis=0)
    for k in np.flatnonzero(win>1e-8):new[k]=elbow_pose(old[k],curve(t[k])*win[k])
    row=next(x for x in payload['clips'] if x['base']==path);a=encode(old,parents);b=encode(new,parents)
    for i in [cl]+arm+[ha]:
        change=R.from_quat(b[:,i,3:7])*R.from_quat(a[:,i,3:7]).inv()
        track=next(x for x in row['tracks'] if x['bone']==names[i]);ts=np.unique(np.r_[t,track['times']])
        corr=np.zeros((len(t),10));corr[:,3:7]=change.as_quat();add=sample(corr.ravel(),t,ts);v=sample(track['values'],track['times'],ts)
        v[:,3:7]=(R.from_quat(add[:,3:7])*R.from_quat(v[:,3:7])).as_quat()
        for k in range(1,len(v)):
            if v[k-1,3:7]@v[k,3:7]<0:v[k,3:7]*=-1
        track.update(times=ts.tolist(),values=v.ravel().tolist())
    final_local=layer(base,path,payload,names,t);final=compose(final_local,parents);cam=camera(path,t)
    hand_error=float(np.linalg.norm(final[:,ha,:3,3]-old[:,ha,:3,3],axis=1).max())
    angle_error=float(np.degrees((R.from_matrix(rot(final[:,ha]))*R.from_matrix(rot(old[:,ha])).inv()).magnitude()).max())
    offset_error=float(abs(final_local[:,:,[0,1,2,7,8,9]]-oldlocal[:,:,[0,1,2,7,8,9]]).max())
    if hand_error>.001 or angle_error>.03 or offset_error>1e-8:
        worst=int(np.argmax(np.linalg.norm(final[:,ha,:3,3]-old[:,ha,:3,3],axis=1)))
        raise RuntimeError('Joint-only invariant failed '+path+' '+str((hand_error,angle_error,offset_error,float(t[worst]))))
    rows=[]
    for k in np.flatnonzero(win>1e-8):
        rows.append(dict(time=float(t[k]),weight=float(win[k]),margin_before=float(clearance(old[k],cam[k]).min()),margin_after=float(clearance(final[k],cam[k]).min()),wrist_before=float(np.degrees(wrist(old[k]))),wrist_after=float(np.degrees(wrist(final[k]))),box_before=box_clearance(old[k]),box_after=box_clearance(final[k])))
    report[path]=dict(hand_position_error_cm=hand_error,hand_rotation_error_degrees=angle_error,local_offset_scale_error=offset_error,window=[start,full,back,end],rows=rows)
    poses[path]=dict(times=t,before=old,after=final,cameras=cam)
    print(path,hand_error,angle_error,offset_error,flush=True)
with gzip.open(outdir/'prism.json.gz','wt') as f:json.dump(payload,f,separators=(',',':'))
(outdir/'joint_only_report.json').write_text(json.dumps(report,indent=2))
pickle.dump(poses,open(outdir/'preview_poses.pkl','wb'))
