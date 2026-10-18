from pathlib import Path
O=Path(__file__).parent
exec((O/'review_thumb_skin.py').read_text().split("datasets={")[0])
datasets={s:thumb_data(s) for s in ['l','r']};graph=json.loads((O/'graph_before.json').read_text());report=[]
def correct(world,limit):
    local=world.copy()
    for i,p in enumerate(parents):
        if p>=0:local[i]=np.linalg.inv(world[p])@world[i]
    for seg in [2,3]:
        i=ix[f'thumb_{seg:02}_l'];child=ix['thumb_03_l'] if seg==2 else -1
        axis=ref[ix['thumb_03_l'],:3].copy();axis/=np.linalg.norm(axis)
        before=Q.from_matrix(local[i,:3,:3]);delta=Q.from_quat(ref[i,3:7]).inv()*before;q=delta.as_quat();q=q if q[3]>=0 else -q
        angle=2*np.arctan2(q[:3]@axis,q[3]);corr=Q.from_rotvec(axis*(np.clip(angle,-limit,limit)-angle));local[i,:3,:3]=(before*corr).as_matrix()
        if child>=0:local[child,:3,:3]=(corr.inv()*Q.from_matrix(local[child,:3,:3])).as_matrix()
        for h,n in enumerate(names):
            if parents[h]==i and '_half_' in n:
                d=Q.from_quat(ref[i,3:7]).inv()*Q.from_matrix(local[i,:3,:3]);local[h,:3,:3]=(Q.from_rotvec(-d.as_rotvec()*.5)*Q.from_quat(ref[h,3:7])).as_matrix()
    result=local.copy()
    for i,p in enumerate(parents):
        if p>=0:result[i]=result[p]@result[i]
    return result
for row in graph['cases']:
    if row['case']!='unarmed' or row['food']=='roasted_large_lamb':continue
    before=after=0;error=0
    for s in row['samples']:
        if s['weight']<.01:continue
        w=mat(np.array(s['world']));v=correct(w,np.deg2rad(8));before=max(before,skin_metrics(w,'l')[0]);after=max(after,skin_metrics(v,'l')[0]);error=max(error,float(np.linalg.norm(w[ix['thumb_03_l'],:3,3]-v[ix['thumb_03_l'],:3,3])))
    report.append({'food':row['food'],'before':before,'after':after,'distal_joint_shift_cm':error})
print(report)
(O/'thumb_hinge_fit.json').write_text(json.dumps(report,indent=2))
