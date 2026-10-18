"""Read candidate/production data and measure full skin, not joint-point proxies."""
from pathlib import Path
exec(compile(Path(__file__).with_name('fit_grasp.py').read_text().split('report={}')[0],str(Path(__file__).with_name('fit_grasp.py')),'exec'))
before=json.loads((OUT/'before_motion.json').read_text())
after=json.loads((OUT/'fitted.json').read_text())
report={'scope':'Offline native-equivalent two-bone IK, original Traversal V7 skin, original lamb surface; no UE runtime, PIE or network test','phases':{},'motion':{}}
fullids={s:np.array([i for i,w in enumerate(R.skin['weights']) if sum(v for n,v in w.items() if R.below(n,'hand_'+s))>.05]) for s in ['l','r']}
for label,motion in [('before',before),('after',after)]:
    report['phases'][label]={}
    for t in [.55,1,1.65,2.75,3.75,4.65,4.9,5.3,5.6]:
        points,obj,goal,info=R.solve(motion,t);invobj=np.array(obj.inverted());points=(np.column_stack((points,np.ones(len(points))))@invobj.T)[:,:3]
        row={}
        for s in ['l','r']:
            ids=fullids[s];dist=[];norm=[]
            for p in points[ids]:
                near,normal,_,d=food.find_nearest(Vector(p));dist.append(-d if d<3 and inside(p) else d);norm.append(list(normal))
            dist=np.array(dist);lookup={i:j for j,i in enumerate(ids)};contacts={};contactnorm={}
            for digit in ['thumb','index','middle','ring','pinky']:
                ix=np.array([lookup[i] for i in ids if R.skin['weights'][i].get(digit+'_03_'+s,0)>.7])
                nearest=ix[np.argsort(np.abs(dist[ix]))[:max(6,len(ix)//10)]]
                contacts[digit]={'nearest_cm':float(np.abs(dist[ix]).min()),'closest_10pct_mean_cm':float(np.abs(dist[nearest]).mean())}
                n=Vector(np.mean(np.array(norm)[nearest],axis=0)).normalized();contactnorm[digit]=n
            row[s]={'wrist_swing_deg':info[s]['wrist_swing_deg'],'wrist_flex_deg':info[s]['wrist_flex_deg'],'wrist_deviation_deg':info[s]['wrist_deviation_deg'],'full_hand_vertices':len(ids),'inside_over_0_5mm':int(np.sum(dist<-.05)),'max_depth_cm':max(0,-float(dist.min())),'contacts':contacts,'thumb_vs_finger_surface_normal_dot':{d:contactnorm['thumb'].dot(contactnorm[d]) for d in ['index','middle','ring','pinky']}}
        report['phases'][label][str(t)]=row
    swings=[];steps=[];rotsteps=[];prior=None;bone_error=0
    for t in np.linspace(.55,5.625,306):
        _,obj,goal,info=R.solve(motion,float(t),False)
        swings.append(max(info[s]['wrist_swing_deg'] for s in ['l','r']))
        if prior:
            steps.append(max((goal['hand_'+s].translation-prior['hand_'+s].translation).length for s in ['l','r']))
            rotsteps.append(max(math.degrees(goal['hand_'+s].to_quaternion().rotation_difference(prior['hand_'+s].to_quaternion()).angle) for s in ['l','r']))
        for s in ['l','r']:
            for n in R.order:
                if R.below(n,'hand_'+s) and n!='hand_'+s:
                    bone_error=max(bone_error,abs((goal[n].translation-goal[R.parent[n]].translation).length-(R.rest[n].translation-R.rest[R.parent[n]].translation).length))
        prior=goal
    report['motion'][label]={'samples':306,'max_wrist_swing_deg':max(swings),'max_wrist_translation_per_60hz_step_cm':max(steps),'max_wrist_rotation_per_60hz_step_deg':max(rotsteps),'max_hand_bone_length_error_cm':bone_error}
report['unchanged_contract']={k:before[k]==after[k] for k in ['times','keys','object_rotation','grip_in_object','right_grip_in_object','bite_in_object']}
(OUT/'surface_and_motion_review.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'motion':report['motion'],'contract':report['unchanged_contract'],'present_after':report['phases']['after']['2.75']},indent=2),flush=True)
