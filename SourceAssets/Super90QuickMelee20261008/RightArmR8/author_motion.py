"""R8: small grip reorientation, preserved finger contacts, supported right wrist."""
from support_geometry import *
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import minimize_scalar
from scipy.spatial import cKDTree
body_tree=cKDTree(body)

fingers=['thumb','index','middle','ring','pinky']
finger_bones=[f'{finger}_{j:02d}_r' for finger in fingers for j in (1,2,3)]
WRITE[:]=[n+'_r' for n in ('clavicle','upperarm','lowerarm','lowerarm_aux','lowerarm_twist_02','lowerarm_twist_01','hand')]+finger_bones
pivot=np.array([0.,-.188,-.851])

def rigid_grip(p,vector):
    gun=p['WPN_root']@ri['WPN_root'];local=np.eye(4)
    local[:3,:3]=R.from_rotvec(vector).as_matrix();local[:3,3]=pivot-local[:3,:3]@pivot
    delta=gun@local@np.linalg.inv(gun);q={n:m.copy() for n,m in p.items()}
    for n in names:
        if n=='hand_r' or (n.endswith('_r') and any(n.startswith(f+'_') for f in fingers)):
            q[n]=delta@p[n]
    return q

def fit_motion(source):
    frames=sorted(set([*range(0,len(times),6),27,40,49,len(times)-1]))
    parameters={};probe=np.array([-.545,-.167,.210,-.357]);previous=probe.copy()
    anchor=49
    visit=[anchor,*reversed([f for f in frames if f<anchor]),*[f for f in frames if f>anchor]]
    for f in visit:
        if f==min(x for x in frames if x>anchor):previous=parameters[anchor].copy()
        p=source[f];w=blend[f]
        if w<1e-8:parameters[f]=np.zeros(4);previous=np.zeros(4);continue
        gi=np.linalg.inv(p['WPN_root']@ri['WPN_root'])
        def residual(x):
            q=solve_arm(p,rigid_grip(p,x[:3]*w),x[3]*w,w)
            gaps=clearance(skinned(q),gi)
            hd=(rot(q['hand_r'])*rot(rest['hand_r']).inv()).as_matrix()
            bend=np.arccos(np.clip(unit(q['hand_r'][:3,3]-q['lowerarm_r'][:3,3])@unit(hd@rf),-1,1))
            return np.r_[np.sort(np.maximum(0,.008-gaps))[-15:]/.0015,
                x[:3]/.8,x[3]/.8,max(0,bend-np.radians(20))/.2,
                (x-previous)/.55,max(0,np.linalg.norm(x[:3])-.85)/.08]
        seeds=[previous,probe]
        fits=[least_squares(residual,x,bounds=([-.95,-.95,-.95,-1.2],[.95,.95,.95,1.2]),
                max_nfev=70,ftol=1e-4,xtol=1e-4,gtol=1e-4) for x in seeds]
        fit=min(fits,key=lambda a:np.linalg.norm(a.fun));previous=fit.x;parameters[f]=fit.x
    fitted=PchipInterpolator(np.array(frames)/D['fps'],np.array([parameters[f] for f in frames]),axis=0)(times)
    return gaussian_filter1d(fitted,2,axis=0)*blend[:,None]

def hand_motion(source,parameters):
    vectors=parameters[:,:3]
    output=[]
    for i,p in enumerate(source):
        q={n:m.copy() for n,m in p.items()}
        gun=p['WPN_root']@ri['WPN_root'];local=np.eye(4)
        local[:3,:3]=R.from_rotvec(vectors[i]).as_matrix();local[:3,3]=pivot-local[:3,:3]@pivot
        delta=gun@local@np.linalg.inv(gun)
        for n in names:
            if n=='hand_r' or (n.endswith('_r') and any(n.startswith(f+'_') for f in fingers)):
                q[n]=delta@p[n]
        if blend[i]>1e-8:
            for finger in fingers:
                ns=[f'{finger}_{j:02d}_r' for j in (1,2,3)]
                lm=[np.linalg.inv(p[parents[n]])@p[n] for n in ns]
                parent=q[parents[ns[0]]]
                tiprest=rest[ns[2]][:3,3]+.70*(rest[ns[2]][:3,3]-rest[ns[1]][:3,3])
                tip=ri[ns[2]]@np.r_[tiprest,1.]
                # A regrip may slide around the grip surface. Do not force the old
                # fingertip location at the cost of a contorted finger chain.
                oldtip=(p[ns[2]]@tip)[:3]
                newtip=(q[ns[2]]@tip)[:3]
                oldlocal=(np.linalg.inv(gun)@np.r_[oldtip,1.])[:3]
                newlocal=(np.linalg.inv(gun)@np.r_[newtip,1.])[:3]
                olddistance=body_tree.query(oldlocal)[0]
                distance,nearest=body_tree.query(newlocal)
                targetlocal=body[nearest]+unit(newlocal-body[nearest])*np.clip(olddistance,.005,.012)
                targettip=(gun@np.r_[targetlocal,1.])[:3]
                target03=q[ns[2]][:3,3].copy();target02=q[ns[1]][:3,3].copy()
                def chain(x):
                    rows=[];m=parent
                    for j in range(3):
                        l=lm[j].copy();l[:3,:3]=lm[j][:3,:3]@R.from_rotvec(x[j*3:j*3+3]).as_matrix()
                        m=m@l;rows.append(m)
                    return rows
                def residual(x):
                    rows=chain(x)
                    return np.r_[((rows[2]@tip)[:3]-targettip)/.0035,
                        (rows[2][:3,3]-target03)/.010,
                        (rows[1][:3,3]-target02)/.020,x/.30]
                fit=least_squares(residual,np.zeros(9),bounds=(-.85,.85),max_nfev=24,ftol=1e-5,xtol=1e-5,gtol=1e-5)
                for n,m in zip(ns,chain(fit.x)):q[n]=m
        output.append(q)
    return output,vectors

def solve_arm(original,gripped,angle,w,shift=np.zeros(3),pole_world=None):
    p={n:m.copy() for n,m in gripped.items()}
    a0,e0,h0=[original[n][:3,3] for n in ('upperarm_r','lowerarm_r','hand_r')]
    h=p['hand_r'][:3,3];la,lb=np.linalg.norm(e0-a0),np.linalg.norm(h0-e0)
    a=a0+np.linalg.inv(CL)@shift;axis=unit(h-a);distance=np.linalg.norm(h-a)
    if distance>(la+lb)*.965:
        a+=axis*(distance-(la+lb)*.965);distance=(la+lb)*.965
    pole=unit(e0-a0-axis*((e0-a0)@axis));pole=turn(axis,angle)@pole
    if pole_world is not None:pole=unit(pole_world-axis*(pole_world@axis))
    along=(la*la-lb*lb+distance*distance)/(2*distance)
    e=a+axis*along+pole*np.sqrt(max(la*la-along*along,0.))
    upper,fore=e-a,h-e;hinge=unit(np.cross(upper,fore))
    du=basis(upper,hinge)@FU.T
    hd=(rot(p['hand_r'])*rot(rest['hand_r']).inv()).as_matrix()
    neutral=unit(hd@rf);fd=unit(fore);dot=np.clip(neutral@fd,-1,1)
    df=turn(np.cross(neutral,fd),np.arccos(dot))@hd
    for stem in ('upperarm','lowerarm','lowerarm_aux','lowerarm_twist_02','lowerarm_twist_01'):
        n=stem+'_r'
        if stem=='upperarm':driver,position=du,a
        else:
            offset=rest[n][:3,3]-rest['lowerarm_r'][:3,3];s=offset@rf/(rf@rf)
            position=e+s*fore+df@(offset-s*rf)
            driver=mix(du,df,{'lowerarm_aux':.5,'lowerarm_twist_02':.88}.get(stem,1.))
            if stem in ('lowerarm_twist_02','lowerarm_twist_01'):
                amount=.30 if stem=='lowerarm_twist_02' else .80
                driver=mix(driver,hd,amount)
                wp=h+hd@(rest[n][:3,3]-rest['hand_r'][:3,3])
                position=position*(1-amount)+wp*amount
        target=driver@rot(rest[n]).as_matrix()
        p[n][:3,:3]=mix(rot(original[n]).as_matrix(),target,w)*np.linalg.norm(original[n][:3,:3],axis=0)
        p[n][:3,3]=original[n][:3,3]*(1-w)+position*w
    p['clavicle_r'][:3,3]+=w*(a-a0)
    return p

def solve(family):
    source,local=decode(family)
    parameters=fit_motion(source)
    (O/('fit_parameters_'+family+'.json')).write_text(json.dumps(parameters.tolist()))
    print('R8_CONTACT_CLEARANCE_FIT',family,flush=True)
    gripped,rv=hand_motion(source,parameters)
    angles=parameters[:,3]
    print('R8_HAND_FIT',family,flush=True)
    output={n:[] for n in WRITE};report=[];poses=[]
    for i,p in enumerate(source):
        corrected=solve_arm(p,gripped[i],angles[i],blend[i]) if blend[i]>1e-8 else p
        packed=encode(corrected)
        for n in WRITE:output[n].append(packed[n])
        poses.append({n:m.tolist() for n,m in corrected.items()})
        def bend(row):
            hd=(rot(row['hand_r'])*rot(rest['hand_r']).inv()).as_matrix()
            return float(np.degrees(np.arccos(np.clip(unit(row['hand_r'][:3,3]-row['lowerarm_r'][:3,3])@unit(hd@rf),-1,1))))
        report.append(dict(time=float(times[i]),before_wrist_bend=bend(p),after_wrist_bend=bend(corrected),
            palm_turn_degrees=float(np.degrees(np.linalg.norm(rv[i]))),elbow_pole_degrees=float(np.degrees(angles[i])),
            shoulder_cm=(100*(CL@corrected['upperarm_r'][:3,3]+CO)).tolist(),
            elbow_cm=(100*(CL@corrected['lowerarm_r'][:3,3]+CO)).tolist()))
    for n in WRITE:local[n]=np.array(output[n])
    print('R8_RIGHT_ARM_AUTHORED',family,flush=True)
    return local,report,poses

result=copy.deepcopy(D);result.update(revision='Super90QuickMelee-RightArmR8-20261010',write_bones=WRITE,runtime_tested=False,
    contact_time=1/6,ownership_curve=json.loads((O.parent/'VerticalFoldR7/animation_patch.json').read_text())['ownership_curve'])
base,report,poses=solve('base');reports={'base':report};allposes={'base':poses}
result['base_tracks']=[track(t['bone'],base[t['bone']]) if t['bone'] in WRITE else t for t in D['base_tracks']]
zero=np.array([0,0,0,0,0,0,1,0,0,0])
for family in D['profiles']:
    local,report,poses=solve(family);reports[family]=report;allposes[family]=poses
    tracks=[t for t in D['profiles'][family]['clip']['tracks'] if t['bone'] not in WRITE]
    for n in WRITE:
        q=(R.from_quat(local[n][:,3:7])*R.from_quat(base[n][:,3:7]).inv()).as_quat();q[q[:,3]<0]*=-1
        delta=np.c_[local[n][:,:3]-base[n][:,:3],q,local[n][:,7:]-base[n][:,7:]]
        if np.max(np.abs(delta-zero))>1e-7:tracks.append(track(n,delta))
    result['profiles'][family]['clip']['tracks']=tracks
(O/'animation_patch.json').write_text(json.dumps(result,separators=(',',':')))
(O/'authoring_controls.json').write_text(json.dumps(reports,separators=(',',':')))
(O/'authored_poses.json').write_text(json.dumps(allposes,separators=(',',':')))
print('SUPER90_RIGHT_ARM_R8_AUTHORED',flush=True)
