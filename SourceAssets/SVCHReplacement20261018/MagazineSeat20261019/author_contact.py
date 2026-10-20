"""Move magazine contact with the fitted shell; preserve V9 shape and left bolt."""
from arm_math import *
import copy

ref=matrices(weapon['reference']);mi=ids['WPN_SOCKET_Magazine']
correction=np.array(json.loads((O/'seat_calibration.json').read_text())['correction_bind_component_cm'])
ui,li,hi,ci=[ids[n] for n in ('upperarm_l','lowerarm_l','hand_l','clavicle_l')]
changed=[i for i,n in enumerate(names) if n=='clavicle_l' or n=='hand_l' or (n.endswith('_l') and n.startswith(('upperarm','lowerarm')))]

def basis(axis,normal):
    x=unit(axis);z=unit(normal-x*(normal@x));return np.column_stack((x,np.cross(z,x),z))

def fit(p,offset):
    out=p.copy();A,E,H=[p[j,:3,3] for j in (ui,li,hi)];T=H+offset
    l1=np.linalg.norm(E-A);l2=np.linalg.norm(H-E);axis=unit(T-A);d=np.linalg.norm(T-A)
    follow=max(0,d-(l1+l2)*.96);S=A+axis*follow;d=np.linalg.norm(T-S)
    # Preserve the forearm's existing direction as far as the fixed-length
    # elbow circle permits. Do not solve this by bending the wrist alone.
    desired=T-unit(H-E)*l2
    pole=unit(desired-S-axis*((desired-S)@axis));along=(l1*l1-l2*l2+d*d)/(2*d)
    elbow=S+axis*along+pole*np.sqrt(max(0,l1*l1-along*along))
    n0=np.cross(E-A,H-E);n1=np.cross(elbow-S,T-elbow)
    du=basis(elbow-S,n1)@basis(E-A,n0).T;dl=basis(T-elbow,n1)@basis(H-E,n0).T
    out[ci,:3,3]+=S-A
    for j,n in enumerate(names):
        if n.endswith('_l') and n.startswith('upperarm'):
            out[j,:3,3]=S+du@(p[j,:3,3]-A);out[j,:3,:3]=du@p[j,:3,:3]
        elif n.endswith('_l') and n.startswith('lowerarm'):
            out[j,:3,3]=elbow+dl@(p[j,:3,3]-E);out[j,:3,:3]=dl@p[j,:3,:3]
    out[hi,:3,3]=T
    # Preserve near-wrist alignment of the same palm. Only distribute the
    # extra axial rotation through the native forearm's existing helper frames.
    fo=R.from_matrix(rigid(p[li])[:3,:3]);fn=R.from_matrix(rigid(out[li])[:3,:3]);ho=R.from_matrix(rigid(p[hi])[:3,:3])
    delta=((fn.inv()*ho)*(fo.inv()*ho).inv()).as_quat()
    if delta[3]<0:delta=-delta
    local_axis=fo.inv().apply(unit(H-E));roll=2*np.arctan2(delta[:3]@local_axis,delta[3])
    for n,share in [('lowerarm_twist_01_l',1.),('lowerarm_twist_02_l',.5)]:
        j=ids[n];rot=fn*R.from_rotvec(local_axis*roll*share)*fn.inv();out[j,:3,:3]=rot.as_matrix()@out[j,:3,:3]
    return out,float(follow)

out=copy.deepcopy(profile);report={'source_profile_sha256':json.loads((O/'Inputs/manifest.json').read_text())['profile']['sha256'],'clips':{},'V9_modified':False,'right_hand_modified':False,'mechanical_tracks_modified':False,'left_bolt_contact_modified':False}
for role in ('reload','reload_empty'):
    c=motion['clips'][role];dst=next(x for x in out['clips'] if x['base']==c['path']);src=next(x for x in profile['clips'] if x['base']==c['path']);values={j:[] for j in changed};maxshift=0;maxfollow=0;maxlength=0
    release=(248,292) if role=='reload_empty' else (255,302)
    for i,t in enumerate(c['times']):
        p=pose(role,i);w=float(ease(0,20,i)*(1-ease(*release,i)))
        if w>0:
            deform=p[mi]@np.linalg.inv(ref[mi]);x=deform@correction@np.linalg.inv(deform)
            shift=(transform(x,p[hi,:3,3])-p[hi,:3,3])*w
            q,follow=fit(p,shift);maxshift=max(maxshift,float(np.linalg.norm(shift)));maxfollow=max(maxfollow,follow)
            for a,b in [(ui,li),(li,hi)]:maxlength=max(maxlength,abs(np.linalg.norm(q[b,:3,3]-q[a,:3,3])-np.linalg.norm(p[b,:3,3]-p[a,:3,3])))
        else:q=p
        raw=np.asarray(c['frames'][i])
        for j in changed:
            if not w:
                track=next((tr for tr in src['tracks'] if tr['bone']==names[j]),None)
                v=sample(t,track) if track else np.array([0,0,0,0,0,0,1,0,0,0],float)
            else:
                local=relative(q[parents[j]],q[j]);scale=np.linalg.norm(local[:3,:3],axis=0)
                v=np.r_[local[:3,3]-raw[j,:3],(R.from_matrix(local[:3,:3]/scale)*R.from_quat(raw[j,3:7]).inv()).as_quat(),scale-raw[j,7:10]]
            if values[j] and values[j][-1][3:7]@v[3:7]<0:v[3:7]*=-1
            values[j].append(v)
    dst['tracks']=[tr for tr in dst['tracks'] if ids[tr['bone']] not in changed]+[{'bone':names[j],'times':c['times'],'values':np.round(values[j],10).ravel().tolist()} for j in changed]
    report['clips'][role]={'max_hand_translation_cm':maxshift,'max_shoulder_follow_cm':maxfollow,'max_bone_length_error_cm':float(maxlength),'release_frames':list(release)}
(O/'profile_magazine_seat.json').write_text(json.dumps(out,separators=(',',':')))
(O/'contact_recipe.json').write_text(json.dumps(report,indent=2));print('SVCH_MAGAZINE_CONTACT_AUTHORED',json.dumps(report),flush=True)
