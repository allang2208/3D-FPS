"""Targeted wrist/contact/bone-length continuity checks before publishing."""
import json,gzip,pickle
from pose import *
d=pickle.load(open(r/'current.pkl','rb'));names=d['names'];ix={n:i for i,n in enumerate(names)};B=matrix(d['bind']);parents=d['parents'];report={};fail=[]
d['profiles']['bipod']=json.loads((r/'extra_inputs.json').read_text())['bipod']
for family,profile in d['profiles'].items():
    newprofile=json.load(gzip.open(r/(family+'.json.gz'),'rt'))
    for path,c in d['clips'].items():
        oldclip=next((x for x in profile['clips'] if x['base']==path),None)
        if not oldclip:continue
        t=np.array(c['times']);base=np.array(c['frames']);old=compose(layer(base,path,profile,names,t),parents);new=compose(layer(base,path,newprofile,names,t),parents)
        if not np.isfinite(new).all():fail.append('nonfinite '+path)
        ma,mb=metrics(old,B,names),metrics(new,B,names)
        errors=[]
        for p,q in [('clavicle_l','upperarm_l'),('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')]:
            before=np.linalg.norm(old[:,ix[q],:3,3]-old[:,ix[p],:3,3],axis=1);after=np.linalg.norm(new[:,ix[q],:3,3]-new[:,ix[p],:3,3],axis=1);errors.append(float(abs(after-before).max()))
        if max(errors)>1e-4:fail.append('bone length '+family+'/'+path)
        # Contact matrices and every non-left-arm bone remain unchanged; only
        # cover-to-belt free travel rotates the hand as documented.
        free=np.zeros(len(t),bool)
        if path.endswith('A_M249_reload'):free=(t>.72)&(t<1.60)
        if path.endswith('A_M249_reload_empty'):free=(t>.70)&(t<1.56)
        hand_error=float(abs(new[~free,ix['hand_l']]-old[~free,ix['hand_l']]).max())
        mount=family in ('vertical','prism')
        if not mount and hand_error>1e-3:fail.append('contact '+family+'/'+path)
        if mount:
            hand_delta=np.linalg.norm(new[:,ix['hand_l'],:3,3]-old[:,ix['hand_l'],:3,3],axis=1)
            if hand_delta.max()>3.001:fail.append('mount translation '+family+'/'+path)
            rotation_error=R.from_matrix(rot(new[~free,ix['hand_l']])@rot(old[~free,ix['hand_l']]).transpose(0,2,1)).magnitude().max()
            if rotation_error>1e-4:fail.append('grasp rotation '+family+'/'+path)
            if path.endswith('A_M249_idle'):
                expected=rot(old[:,ix['WPN_root']])@np.array([0.,3.,0.])
                if np.max(abs(new[:,ix['hand_l'],:3,3]-old[:,ix['hand_l'],:3,3]-expected))>1e-3:fail.append('mount match '+family)
            if path.endswith(('A_M249_reload','A_M249_reload_empty')):
                # Left opens the cover/removes the spent belt; the RIGHT hand
                # swaps the box, feeds and closes while left supports the gun.
                # Those right-hand/mechanical bones are checked in `others`.
                contacts=[.65] if path.endswith('_empty') else [.65,1.65]
                for contact in contacts:
                    k=np.argmin(abs(t-contact))
                    if hand_delta[k]>1e-3:fail.append('mechanical contact '+family+'/'+str(contact))
        others=[i for i,n in enumerate(names) if not(n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky','ik_hand')))]
        other_error=float(abs(new[:,others]-old[:,others]).max())
        if other_error>1e-4:fail.append('unowned '+family+'/'+path)
        steps={}
        for bone in ('upperarm_l','lowerarm_l','lowerarm_twist_01_l','hand_l'):
            i=ix[bone];qa=R.from_matrix(rot(old[:,i]));qb=R.from_matrix(rot(new[:,i]));da=np.degrees((qa[:-1].inv()*qa[1:]).magnitude());db=np.degrees((qb[:-1].inv()*qb[1:]).magnitude())
            steps[bone]=dict(before=float(da.max()),after=float(db.max()),at=float(t[db.argmax()]))
        report[family+'/'+path.split('.')[-1]]=dict(wrist_before=float(ma['wrist_swing'].max()),wrist_after=float(mb['wrist_swing'].max()),bone_length_error_cm=max(errors),contact_matrix_error=hand_error,unowned_matrix_error=other_error,steps=steps)
(r/'payload_review.json').write_text(json.dumps(dict(failures=fail,cases=report),indent=2))
print('PAYLOAD_REVIEW',len(report),'cases',len(fail),'failures',flush=True)
if fail:raise RuntimeError(str(fail[:8]))
