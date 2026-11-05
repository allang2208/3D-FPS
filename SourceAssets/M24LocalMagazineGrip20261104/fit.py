"""Author four local grip anchors against the native magazine and receiver."""
from pathlib import Path
__file__=str(Path(__file__).parent/'common.py')
exec(compile(Path(__file__).read_text(),'local-grip helpers','exec'))
result={}
for family in ('base','mag10'):
    result[family]={}
    for stage,frames in [('old',[18,22,24]),('new',[34,38,40])]:
        contexts=[LocalGripFrame(family,f,stage) for f in frames]
        x=np.zeros(6);history=[]
        for iteration in range(24):
            allJ=[];allR=[];allC=[];need=[];arms=[];details=[]
            for fr in contexts:
                p,cons,mins,hits=fr.contacts(x);res,terms,info=fr.features(p)
                derivatives=[]
                for k in range(6):
                    y=x.copy();y[k]+=.025;derivatives.append((fr.points(y)-p)/.025)
                allJ.extend([[float(n@dp[i])*1000*w for dp in derivatives] for i,n,w in terms]);allR.extend(res)
                allC.extend([[float(n@dp[i])*1000 for dp in derivatives] for i,n,d in cons]);need.extend(d*1000 for i,n,d in cons)
                arms.append({'v':list((fr.H-fr.S)*1000),'basis':np.array(fr.basis).tolist(),'limit':(fr.A+fr.B-.0005)*1000})
                details.append({'frame':fr.f,'clearance_mm':mins,'crossings':hits,'front_patch_mm':info})
            reg=np.diag([.15]*3+[.18]*3);allJ.extend(reg.tolist());allR.extend(reg@x)
            score=float(np.square(allR).sum())
            history.append({'x':x.tolist(),'score':score,'frames':details})
            print('LOCAL_GRIP_FIT',family,stage,iteration,round(score,2),[(d['frame'],d['clearance_mm'],d['crossings']) for d in details],flush=True)
            payload={'J':allJ,'r':list(allR),'C':allC,'need':need,'x':x.tolist(),'translation_limit':20.,'rotation_limit':18.,'arms':arms}
            z=subprocess.run(['C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe',str(TASKOUT.parent/'M24SurfaceGrip20261103/step.py')],input=json.dumps(payload),text=True,capture_output=True,check=True)
            step=json.loads(z.stdout)
            if np.linalg.norm(step['step'])<.015:break
            x+=np.array(step['step'])
        feasible=[h for h in history if all(min(d['clearance_mm'].values())>=.05 and not any(d['crossings'].values()) for d in h['frames'])]
        if not feasible:
            (TASKOUT/f'{family}_{stage}_unfinished.json').write_text(json.dumps(history,indent=2));raise RuntimeError('Grip authoring has no clear anchor: '+family+'/'+stage)
        chosen=min(feasible,key=lambda h:h['score'])
        fr=contexts[1];row=fr.pose(np.array(chosen['x']))
        result[family][stage]={'parameters':chosen['x'],'mag_to_hand':[list(v) for v in row['WPN_Magazine'].inverted()@row['hand_l']],
            'digits':{n:list(q) for n,q in anchors[family][stage]['digits'].items()},'authoring_contact':chosen['frames'],'history':history}
        (TASKOUT/'grip_anchors.json').write_text(json.dumps(result,indent=2))
print('M24_LOCAL_GRIP_ANCHORS_AUTHORED',flush=True)
