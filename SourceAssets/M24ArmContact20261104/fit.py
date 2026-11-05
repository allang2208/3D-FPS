from pathlib import Path
__file__=str(Path(__file__).parent/'common.py')
exec(compile(Path(__file__).read_text(),'contact authoring setup','exec'))
result=json.loads((TASKOUT/'grip_anchors.json').read_text())
resume=json.loads((TASKOUT/'resume_parameters.json').read_text())
for family in ('mag10','base'):
    result.setdefault(family,{})
    for stage,frames in [('old',[18]),('new',[38])]:
        if stage in result[family]:continue
        if stage=='new' or family=='base':
            # The same magazine shell uses the same established hand contact on
            # withdrawal and insertion; solve only the residual arm-skin change.
            old=result[family]['old'] if stage=='new' else result['mag10']['old'];a=anchors[family][stage]
            a['relative']=Matrix(old['mag_to_hand'])
            for n,q in old['digits'].items():
                p,_,sc=a['local'][n].decompose()
                a['local'][n]=Matrix.LocRotScale(p,Quaternion(q),sc)
            resume[family+'/'+stage]=[0.]*22
        frames=[ContactFrame(family,f,stage) for f in frames];x=np.array(resume.get(family+'/'+stage,[0.]*22));history=[]
        for iteration in range(55):
            allJ=[];allR=[];allC=[];need=[];details=[];arms=[]
            for fr in frames:
                fr.witnesses={};fr.planes={}
                p,cons,mins,hits=fr.contacts(x);res,terms,info=fr.features(p)
                deriv=[]
                for k in range(22):
                    y=x.copy();y[k]+=.04;deriv.append((fr.points(y)-p)/.04)
                allJ.extend([[float(n@dp[i])*1000*w for dp in deriv] for i,n,w in terms]);allR.extend(res)
                allC.extend([[float(n@dp[i])*1000 for dp in deriv] for i,n,v in cons]);need.extend(v*1000 for i,n,v in cons)
                details.append({'frame':fr.f,'clearance_mm':mins,'crossings':hits,'pads_mm':info})
                arms.append({'v':list((fr.H-fr.S)*1000),'basis':np.array(fr.basis).tolist(),'limit':((fr.A+fr.B)*.964+.065)*1000})
            reg=np.diag([.03]*3+[.04]*3+[.018]*8+[.04]*4+[.025]*4);allJ.extend(reg.tolist());allR.extend(reg@x)
            score=float(np.square(allR).sum());history.append({'x':x.tolist(),'score':score,'frames':details})
            print('CONTACT_FIT',family,stage,iteration,round(score,2),details[0]['pads_mm'],[d['crossings'] for d in details],flush=True)
            (TASKOUT/f'{family}_{stage}_iterations.json').write_text(json.dumps(history,indent=2))
            payload={'J':allJ,'r':list(allR),'C':allC,'need':need,'x':x.tolist(),'arms':arms}
            z=subprocess.run(['C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe',str(TASKOUT/'step.py')],input=json.dumps(payload),text=True,capture_output=True,check=True)
            step=json.loads(z.stdout)
            if np.linalg.norm(step['step'])<.01:break
            x+=np.array(step['step'])
        valid=[h for h in history if all(min(v['clearance_mm'].values())>.05 and not any(v['crossings'].values()) for v in h['frames'])]
        if not valid:
            (TASKOUT/f'{family}_{stage}_fit_history.json').write_text(json.dumps(history,indent=2));raise RuntimeError('No clear grip anchor '+family+'/'+stage)
        chosen=min(valid,key=lambda h:h['score']);fr=frames[0];row=fr.pose(np.array(chosen['x']))
        result[family][stage]={'parameters':chosen['x'],'mag_to_hand':[list(v) for v in row['WPN_Magazine'].inverted()@row['hand_l']],
         'digits':{n:list((row[parents[n]].inverted()@row[n]).to_quaternion()) for n in digits},'authoring_contact':chosen['frames'],'history':history}
        (TASKOUT/'grip_anchors.json').write_text(json.dumps(result,indent=2))
print('CONTACT_ANCHORS_COMPLETE',flush=True)
