"""Targeted authoring checks for the reported arm defect and preserved contacts."""
from surface import *
manifest=json.loads((O/'Inputs/manifest.json').read_text())
clip=motion['clips']['quick_melee'];data=np.load(O/'poses.npz')
before,after=data['before'],data['after'];h=ids['hand_r'];u=ids['upperarm_r'];l=ids['lowerarm_r']
result={'families':{},'runtime_tested':False,'visual_accepted':False,
    'surface':'Installed V9 + exact JC payload, including blue-glove coverage','frames':len(before)}
for family in ('base','angled','vertical','canted','prism'):
    orig=json.loads((O/'Inputs'/('svch_'+family+'.json')).read_text())
    dest=O/'SavedReadback'/(family+'.json')
    new=json.loads((dest if dest.exists() else O/'Profiles'/(family+'.json')).read_text())
    original=[c for c in orig['clips'] if c['base']!=clip['path']];updated=[c for c in new['clips'] if c['base']!=clip['path']]
    assert original==updated
    lengths=palms=gun=digits=scale=0.
    for i in range(len(clip['times'])):
        a=pose('quick_melee',i,orig);b=pose('quick_melee',i,new)
        palms=max(palms,float(np.max(abs(a[h]-b[h]))));gun=max(gun,float(np.max(abs(a[ids['WPN_root']]-b[ids['WPN_root']]))))
        for j,n in enumerate(names):
            if n.startswith(('thumb','index','middle','ring','pinky')) and n.endswith('_r'):digits=max(digits,float(np.max(abs(a[j]-b[j]))))
        for j,k in [(u,l),(l,h)]:lengths=max(lengths,abs(np.linalg.norm(a[j,:3,3]-a[k,:3,3])-np.linalg.norm(b[j,:3,3]-b[k,:3,3])))
        scale=max(scale,float(np.max(abs(np.linalg.norm(a[:,:3,:3],axis=1)-np.linalg.norm(b[:,:3,:3],axis=1)))))
    print(family,'saved float-key errors',dict(palm=palms,gun=gun,digits=digits,lengths_cm=lengths,scale=scale),flush=True)
    # The profile stores times/quaternions as float32. Sampling the saved keys
    # at the author's double-precision times adds <0.001 cm matrix error on
    # the accelerated entry; bone lengths and scales have tighter bounds.
    assert max(palms,gun,digits)<.001 and lengths<.00002 and scale<.000001
    result['families'][family]={'other_actions_identical':True,'palm_matrix_error':palms,'gun_matrix_error':gun,
        'right_finger_matrix_error':digits,'bone_length_error_cm':lengths,'scale_error':scale,'read_saved_profile':dest.exists()}
for name in ['upperarm_r','lowerarm_r','hand_r']:
    result[name]={}
    for label,p in [('rejected',before),('revision',after)]:
        steps=np.linalg.norm(np.diff(p[:,ids[name],:3,3],axis=0),axis=1)
        result[name][label]={'maximum_step_cm_at_120Hz':float(steps.max()),'frame':int(steps.argmax()+1)}
from scipy.spatial.transform import Rotation
refL=rigid(ref[l])[:3,:3];rel=refL.T@rigid(ref[h])[:3,:3];ax=refL.T@unit(ref[h,:3,3]-ref[l,:3,3])
for label,p in [('rejected',before),('revision',after)]:
    rolls=[]
    for f in p:
        q=R.from_matrix(rigid(f[l])[:3,:3].T@rigid(f[h])[:3,:3]@rel.T).as_quat()
        if q[3]<0:q=-q
        rolls.append(2*np.arctan2(q[:3]@ax,q[3]))
    result[label+'_forearm_roll_deg']=[float(x) for x in np.degrees(np.unwrap(rolls))[[0,20,40,68,108]]]
(O/'pose-contract.json').write_text(json.dumps(result,indent=2))
print('SVCH quick-melee contacts, fingers, lengths, scales and non-target actions preserved in five families',flush=True)
