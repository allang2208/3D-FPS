"""Confirm the authored delta and measure the full lift, including the release."""
from cover import *

rows={}
for family in FAMILIES:
    old=json.load(gzip.open(profile_input(family),'rt'))
    new=json.load(gzip.open(HERE/(family+'.json.gz'),'rt'))
    assert len(old['clips'])==len(new['clips'])
    for a,b in zip(old['clips'],new['clips']):
        path=a['base']
        if not path.endswith(('.A_M249_reload','.A_M249_reload_empty')):
            assert a==b,(family,path)
            continue
        assert {k:v for k,v in a.items() if k!='tracks'}=={k:v for k,v in b.items() if k!='tracks'}
        owned={G.names[i] for i in OWNED}
        assert [tr for tr in a['tracks'] if tr['bone'] not in owned]==[tr for tr in b['tracks'] if tr['bone'] not in owned]
        for tr in b['tracks']:
            if tr['bone'] not in owned:continue
            original=next((v for v in a['tracks'] if v['bone']==tr['bone']),None)
            tt=np.array(tr['times'])
            if original:
                expected=G.sample(original['values'],original['times'],tt)
            else:
                expected=np.tile([0,0,0,0,0,0,1,0,0,0.],(len(tt),1))
            actual=np.array(tr['values']).reshape(-1,10)
            assert np.max(abs(actual[:,[0,1,2,7,8,9]]-expected[:,[0,1,2,7,8,9]]))<1e-7
            outside=(tt<=REGION[0])|(tt>=REGION[1])
            assert np.min(abs(np.sum(actual[outside,3:7]*expected[outside,3:7],axis=1)))>.999999
        src=G.d['clips'][path];t=np.array(src['times']);base=np.array(src['frames'])
        i=np.flatnonzero((t>=REGION[0])&(t<=REGION[1]))
        def metrics(profile):
            local=G.layer(base,path,profile,G.names,t)
            w=G.compose(local,G.parents)[i]
            q=local[i][:,OWNED,3:7]
            dq=R.from_quat(q[1:].reshape(-1,4))*R.from_quat(q[:-1].reshape(-1,4)).inv()
            m=G.metrics(w,G.B,G.names)
            return dict(peak_joint_step_deg=float(np.max(np.degrees(dq.magnitude()))),
                        elbow_step_cm=float(np.linalg.norm(np.diff(w[:,E,:3,3],axis=0),axis=1).max()),
                        wrist_step_cm=float(np.linalg.norm(np.diff(w[:,H,:3,3],axis=0),axis=1).max()),
                        max_wrist_residual_roll_deg=float(abs(m['wrist_residual_twist']).max()))
        rows[family+'/'+path.split('.')[-1]]=dict(before=metrics(old),after=metrics(new))
(HERE/'scope.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=1))
