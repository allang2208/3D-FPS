"""Side-feed contacts on native M249/V9 arms, with shared foregrip deltas."""
import sys,pickle,json,gzip
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'Repair10'))
from motion import *
d=pickle.load(open(r/'native.pkl','rb'));g=pickle.load(open(r/'grasp.pkl','rb'));cfg=json.loads((r/'model_recipe.json').read_text())
canted_fix=json.loads((r/'canted_index_fix.json').read_text()) if (r/'canted_index_fix.json').exists() else None
names=d['names'];parents={n:names[p] if p>=0 else None for n,p in zip(names,d['parents'])};B={n:matrix(v) for n,v in zip(names,d['bind'])}
gn=g['names'];gp={n:gn[p] if p>=0 else None for n,p in zip(gn,g['parents'])};GB={n:matrix(v) for n,v in zip(gn,g['bind'])};gl={n:matrix(v) for n,v in zip(gn,g['local'])};gw=compose(gn,gp,gl)
def rel(world,n):
    a=np.linalg.inv(world['WPN_root'])@world[n];a[:3,3]*=100;a[:3,:3]=rot(a);return a
def local_at(path,t):
    c=d['clips'][path];a=np.asarray(c['frames']);times=np.minimum(np.arange(len(a))/c['fps'],c['duration'])
    return {n:matrix(sample(a[:,i],times,t)) for i,n in enumerate(names)}
idle_path=next(k for k in d['clips'] if k.split('.')[0].endswith('_idle'))
empty_path=next(k for k in d['clips'] if k.split('.')[0].endswith('_reload_empty'))
def layer(local,family,path,t):
    out={n:a.copy() for n,a in local.items()};c=next((c for c in d['profiles'][family]['clips'] if c['base']==path),None)
    if c:
        for track in c['tracks']:
            n=track['bone'];v=sample(np.asarray(track['values']).reshape(-1,10),track['times'],t)
            out[n][:3,3]+=v[:3];out[n][:3,:3]=R.from_quat(v[3:7]).as_matrix()@rot(out[n])*(np.linalg.norm(out[n][:3,:3],axis=0)+v[7:])
    if family=='canted' and canted_fix:out[canted_fix['bone']][:3,3]+=np.array(canted_fix['local_delta'])
    return out
idle_local=layer(local_at(idle_path,0),'base',idle_path,0);idle_world=compose(names,parents,idle_local)
holdlocals={family:layer(local_at(idle_path,0),family,idle_path,0) for family in d['profiles']}
holds={family:rel(compose(names,parents,ls),'hand_l') for family,ls in holdlocals.items()}
holdworlds={family:compose(names,parents,ls) for family,ls in holdlocals.items()}
grasp=np.linalg.inv(gw['WPN_SOCKET_Magazine'])@gw['hand_l'];grasp[:3,3]*=100;grasp[:3,:3]=rot(grasp)
contact=np.array(cfg['donor_mag_to_root'])@grasp;mount=np.array(cfg['idle_mag_frame'])
digits={side:[n for n in names if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))] for side in ('l','r')}
donor_fingers={}
for n in digits['l']:
    bt=np.linalg.inv(B[parents[n]])@B[n];bd=np.linalg.inv(GB[gp[n]])@GB[n]
    a=idle_local[n].copy();a[:3,:3]=rot(bt)@rot(bd).T@rot(gl[n])*np.linalg.norm(a[:3,:3],axis=0);donor_fingers[n]=a
fit=json.loads((r/'grasp_fit.json').read_text())
contact[:3,3]+=np.array(fit['offset_cm'])
contact[:3,:3]=R.from_rotvec(fit['palm_rotvec']).as_matrix()@contact[:3,:3]
for n,angle in fit['finger_hinge_z'].items():donor_fingers[n][:3,:3]=turn([0,0,1],angle)@donor_fingers[n][:3,:3]
open_fingers={}
for n in digits['l']:
    a=idle_local[n].copy();b=np.linalg.inv(B[parents[n]])@B[n];a[:3,:3]=rot(b)*np.linalg.norm(a[:3,:3],axis=0);open_fingers[n]=a
unhook_fingers={n:(open_fingers[n].copy() if '_02_' in n or '_03_' in n else donor_fingers[n].copy()) for n in digits['l']}

twist_state={}
twist_log={}
pole_state={}
pole_plan=pickle.load(open(r/'pole_plan.pkl','rb')) if (r/'pole_plan.pkl').exists() else {}
roll_plan=pickle.load(open(r/'roll_plan.pkl','rb')) if (r/'roll_plan.pkl').exists() else {}
def solve(world,local,side,pos,rotation,fingers=None,source_time=0.,family='base'):
    out={n:a.copy() for n,a in world.items()};s='_'+side
    a,e,h=[world[n+s][:3,3].copy() for n in ('upperarm','lowerarm','hand')]
    axis=unit(pos-a);dist=np.linalg.norm(pos-a);la=np.linalg.norm(e-a);lb=np.linalg.norm(h-e)
    if dist>la+lb-.08:
        shift=axis*(dist-(la+lb-.08));a+=shift;e+=shift;dist=la+lb-.08
        out['clavicle'+s][:3,3]+=shift
    along=(la*la-lb*lb+dist*dist)/(2*max(dist,.01));pole=unit(e-a-axis*((e-a)@axis))
    if side=='l':
        # Choose the elbow on its physical two-bone circle from the native
        # straight-wrist direction. Projecting the old elbow alone flips when
        # the wrist crosses that plane during extraction.
        bind_axis=unit(B['hand_l'][:3,3]-B['lowerarm_l'][:3,3])
        wrist_axis=rotation@rot(B['hand_l']).T@bind_axis
        preferred=-wrist_axis+axis*(wrist_axis@axis);preferred=unit(preferred)
        idleaxis=unit(h-a);idlepole=unit(e-a-idleaxis*((e-a)@idleaxis));reference=swing(idleaxis,axis)@idlepole
        yaw=np.arctan2(axis@np.cross(reference,preferred),np.clip(reference@preferred,-1,1))
        previous=pole_state.get(family,yaw);yaw=previous+np.arctan2(np.sin(yaw-previous),np.cos(yaw-previous));pole_state[family]=yaw
        amount=ease(source_time/.30)*(1-ease((source_time-3.30)/.40))
        pole=turn(axis,yaw*amount)@reference
        if role+'_'+family in pole_plan:
            pole=pole_plan[role+'_'+family][round(source_time*120)].copy();pole=unit(pole-axis*(pole@axis))
    elbow=a+axis*along+pole*np.sqrt(max(0,la*la-along*along))
    olda,olde,oldh=[world[n+s][:3,3] for n in ('upperarm','lowerarm','hand')]
    du=swing(olde-olda,elbow-a);dl=swing(oldh-olde,pos-elbow)
    if side=='l':
        # Transport both segments through the actual elbow hinge, updating
        # upper-arm auxiliaries together; palm roll belongs to the forearm.
        oldnormal=unit(np.cross(olde-olda,oldh-olde));normal=unit(np.cross(elbow-a,pos-elbow))
        du=frame(elbow-a,normal)@frame(olde-olda,oldnormal).T
        dl=frame(pos-elbow,normal)@frame(oldh-olde,oldnormal).T
    for prefix,origin,neworigin,delta in (('upperarm',olda,a,du),('lowerarm',olde,elbow,dl)):
        for suffix in ('','_twist_01','_twist_02'):
            n=prefix+suffix+s
            if n in out:out[n][:3,:3]=delta@world[n][:3,:3];out[n][:3,3]=neworigin+delta@(world[n][:3,3]-origin)
    axis=unit(pos-elbow);q=R.from_matrix(rotation@(dl@rot(world['hand'+s])).T).as_quat();q[:3]=axis*(q[:3]@axis);q/=max(np.linalg.norm(q),1.e-12);rv=R.from_quat(q).as_rotvec()
    if side=='l':
        phi=float(rv@axis);previous=twist_state.get(family,0.)
        phi=previous+np.arctan2(np.sin(phi-previous),np.cos(phi-previous))
        twist_state[family]=phi;twist_log.setdefault(family,[]).append([source_time,float(phi)])
        forearm=np.clip(phi,-np.radians(110),np.radians(110));extra=phi-forearm
        if role+'_'+family in roll_plan:
            extra=float(roll_plan[role+'_'+family][round(source_time*120)]);forearm=phi-extra
        # Excess roll is shared by both sides of the elbow, rather than
        # concentrating a half-turn into the distal forearm helpers.
        for prefix,origin,boneaxis in (('upperarm',a,unit(elbow-a)),('lowerarm',elbow,axis)):
            delta=turn(boneaxis,extra)
            for suffix in ('','_twist_01','_twist_02'):
                n=prefix+suffix+s
                if n in out:out[n][:3,:3]=delta@out[n][:3,:3];out[n][:3,3]=origin+delta@(out[n][:3,3]-origin)
        rv=axis*forearm
    for suffix,w in (('_twist_01',1.),('_twist_02',.5)):
        n='lowerarm'+suffix+s
        if n in out:
            t=R.from_rotvec(rv*w).as_matrix();out[n][:3,:3]=t@out[n][:3,:3];out[n][:3,3]=elbow+t@(out[n][:3,3]-elbow)
    out['hand'+s][:3,:3]=rotation*np.linalg.norm(world['hand'+s][:3,:3],axis=0);out['hand'+s][:3,3]=pos
    for n in digits[side]:out[n]=out[parents[n]]@(fingers.get(n,local[n]) if fingers else local[n])
    if 'ik_hand'+s in out:out['ik_hand'+s]=out['hand'+s]@np.linalg.inv(world['hand'+s])@world['ik_hand'+s]
    return out

def key(t,points):
    for (ta,a),(tb,b) in zip(points,points[1:]):
        if t<=tb:return np.array(a)+(np.array(b)-a)*ease((t-ta)/(tb-ta))
    return np.array(points[-1][1])
# Magazine travel and left-hand contact are authored in one root frame.
# First clear the socket along its own axis; only then move down to pickup.
out_axis=-np.array(cfg['donor_mag_to_root'])[:3,2]
def mag_offset(t):
    a=np.eye(4)
    a[:3,3]=key(t,[(0,[0,0,0]),(.72,[0,0,0]),(.85,(out_axis*7.5).tolist()),
        (1.05,[9,10,-25]),(1.45,[9,10,-25]),(1.84,[10,8,-8]),
        (2.08,(out_axis*8).tolist()),(2.22,(out_axis*8).tolist()),
        (2.55,[0,0,0]),(2.63,(out_axis*.20).tolist()),(2.70,[0,0,0])])
    return a

spatial_paths={}
def travel(hold,returning,t):
    key=(tuple(hold[:3,3]),returning)
    if key not in spatial_paths:
        above=contact[:3,3]+[0,0,10.];outer=np.array([contact[0,3]+16.,hold[1,3]+8.,contact[2,3]+10.]);below=hold[:3,3]+[25,8,-2]
        end=contact[:3,3]+[0,0,.25]
        pts=np.array([contact[:3,3],above,outer,below,hold[:3,3]] if returning else [hold[:3,3],below,outer,above,end])
        knots=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))];knots/=knots[-1];curve=PchipInterpolator(knots,pts,axis=0);s=np.linspace(0,1,2049);p=curve(s);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];arc/=arc[-1];spatial_paths[key]=(curve,s,arc)
    u=np.clip((t-(2.78 if returning else .04))/(.92 if returning else .56),0,1);a=.15
    distance=(.5*u*u/a if u<a else u-.5*a if u<=1-a else 1-a-.5*(1-u)**2/a)/(1-a)
    curve,s,arc=spatial_paths[key];return curve(np.interp(distance,arc,s))

def palm_path(t,hold,moving_contact):
    # Both magazine variants retain this exact upper hand seat. Approach from
    # outside, visibly wrap before extraction, then leave below the long shell.
    if .60<=t<=2.78:
        a=moving_contact.copy();a[2,3]+=.25*(1-ease((t-.60)/.10));return a
    returning=t>=2.78
    a=mix(contact,hold,ease((t-3.08)/.52)) if returning else mix(hold,contact,ease((t-.18)/.36))
    a[:3,3]=travel(hold,returning,t);return a

def impulse(t,at,width):
    x=(t-at)/width
    return np.sin(np.pi*x)*np.exp(-2*x) if 0<x<1 else 0.
def in_world(root,pose):
    a=np.eye(4);a[:3,3]=root[:3,3]+rot(root)@pose[:3,3];a[:3,:3]=rot(root)@rot(pose)*100;return a
def encode(a):
    q=R.from_matrix(rot(a)).as_quat()
    if q[3]<0:q=-q
    return [*a[:3,3],*q,*np.linalg.norm(a[:3,:3],axis=0)]
selected=[n for n in names if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky','ik_hand'))]
profiles={family:[] for family in holds}
outdir=r/'Motion';outdir.mkdir(exist_ok=True)
for empty in (False,True):
    twist_state.clear()
    pole_state.clear()
    role='reload_empty' if empty else 'reload';duration=5.0 if empty else 3.8;fps=120
    frames=[];family_frames={family:[] for family in holds};times=np.arange(round(duration*fps)+1)/fps
    for t in times:
        local={n:a.copy() for n,a in idle_local.items()};world=compose(names,parents,local)
        # Whole-weapon anticipation and insertion reaction. The right palm
        # remains receiver-bound; the shoulder/elbow are solved anatomically.
        w=ease(t/.38)*(1-ease((t-(4.3 if empty else 3.15))/(.7 if empty else .65)))
        root=world['WPN_root'].copy();root[:3,:3]=root[:3,:3]@R.from_euler('xyz',[0,-5*w,-2*w],degrees=True).as_matrix();root[:3,3]+=rot(world['WPN_root'])@np.array([-.6*w,0,-.5*w])
        pull=impulse(t,.72,.24);seat=impulse(t,2.55,.20)+.6*impulse(t,2.70,.18)
        root[:3,3]+=rot(root)@np.array([-.22*pull+.15*seat,0.,-.12*pull+.12*seat])
        root[:3,:3]=root[:3,:3]@R.from_euler('xyz',[0.,.55*pull-.45*seat,.20*pull],degrees=True).as_matrix()
        world['WPN_root']=root
        for n in names:
            if n!='WPN_root' and parents[n] in world and (n.startswith(('WPN_','PKM_','New_'))):world[n]=world[parents[n]]@local[n]
        relative=mag_offset(t)@mount;world['WPN_SOCKET_Magazine']=in_world(root,relative)
        right=rel(idle_world,'hand_r');right_fingers=None
        if empty and t>=2.85:
            # The native M249 charge and return are reused in the same gun
            # frame. They start after insertion, with the feed cover closed.
            src=min(6.6,t+1.95);sl=layer(local_at(empty_path,src),'base',empty_path,src);sw=compose(names,parents,sl)
            amount=ease((t-2.85)/.25);right=mix(right,rel(sw,'hand_r'),amount)
            right_fingers={n:mix(local[n],sl[n],amount) for n in digits['r']}
            for n in ('PKM_Charge','WPN_ChargingHandle','WPN_bolt','PKM_InnerCarrier'):
                target=in_world(root,rel(sw,n));world[n]=mix(world[n],target,amount)
        rt=in_world(root,right);world=solve(world,local,'r',rt[:3,3],rot(rt),right_fingers)
        contact_now=mag_offset(t)@contact
        for family,hold in holds.items():
            palm=palm_path(t,hold,contact_now)
            if t<.32:fingers={n:mix(holdlocals[family][n],open_fingers[n],ease((t-.22)/.10)) for n in digits['l']}
            elif t<.46:fingers={n:mix(open_fingers[n],unhook_fingers[n],ease((t-.32)/.14)) for n in digits['l']}
            elif t<.60:fingers={n:a.copy() for n,a in unhook_fingers.items()}
            elif t<.70:fingers={n:mix(unhook_fingers[n],donor_fingers[n],ease((t-.60)/.10)) for n in digits['l']}
            elif t<=2.70:fingers={n:a.copy() for n,a in donor_fingers.items()}
            elif t<2.80:fingers={n:mix(donor_fingers[n],unhook_fingers[n],ease((t-2.70)/.10)) for n in digits['l']}
            elif t<2.98:fingers={n:a.copy() for n,a in unhook_fingers.items()}
            elif t<3.12:fingers={n:mix(unhook_fingers[n],open_fingers[n],ease((t-2.98)/.14)) for n in digits['l']}
            else:fingers={n:mix(open_fingers[n],holdlocals[family][n],ease((t-3.38)/.24)) for n in digits['l']}
            familyworld={n:a.copy() for n,a in world.items()}
            for n in selected:familyworld[n]=holdworlds[family][n].copy()
            target=in_world(root,palm);fw=solve(familyworld,local,'l',target[:3,3],rot(target),fingers,source_time=t,family=family)
            fl={n:np.linalg.inv(fw[parents[n]])@fw[n] if parents[n] else fw[n] for n in (names if family=='base' else selected)}
            if family=='base':frames.append(fl)
            family_frames[family].append(fl)
    path='/Game/Weapons/M249/SideMagazine20261108/Animations/A_M249_side_'+role
    tracks={n:[encode(f[n]) for f in frames] for n in names}
    with gzip.open(outdir/(role+'.json.gz'),'wt') as f:json.dump(dict(source=idle_path,asset=path,fps=fps,duration=duration,tracks=tracks),f,separators=(',',':'))
    for family,rows in family_frames.items():
        delta=[]
        for n in selected:
            values=[]
            for base,posed in zip(frames,rows):
                a,b=posed[n],base[n];q=R.from_matrix(rot(a)@rot(b).T).as_quat()
                if q[3]<0:q=-q
                values.append([*(a[:3,3]-b[:3,3]),*q,*(np.linalg.norm(a[:3,:3],axis=0)-np.linalg.norm(b[:3,:3],axis=0))])
            a=np.array(values)
            if np.max(np.abs(a-[0,0,0,0,0,0,1,0,0,0]))>1.e-6:delta.append(dict(bone=n,times=times.tolist(),values=a.ravel().tolist()))
        profiles[family].append(dict(base=path,duration=duration,tracks=delta))
    print('M249_SIDE_RELOAD_AUTHORED',role,len(frames),flush=True)
for family,newclips in profiles.items():
    if family=='canted' and canted_fix:
        import copy
        for source in d['profiles'][family]['clips']:
            if '/SideMagazine20261108/' in source['base']:continue
            row=copy.deepcopy(source);track=next((v for v in row['tracks'] if v['bone']==canted_fix['bone']),None)
            if track is None:
                track=dict(bone=canted_fix['bone'],times=[0.],values=[0,0,0,0,0,0,1,0,0,0]);row['tracks'].append(track)
            values=np.asarray(track['values'],dtype=float).reshape(-1,10);values[:,:3]+=np.array(canted_fix['local_delta']);track['values']=values.ravel().tolist();newclips.append(row)
    # Append only the new actions when installing; existing rows are retained
    # directly as UE structs so retained clips and future fields survive.
    with gzip.open(r/(family+'.json.gz'),'wt') as f:json.dump(dict(family=family,clips=newclips),f,separators=(',',':'))
(r/'motion_recipe.json').write_text(json.dumps(dict(normal=3.8,empty=5.,contact_root=contact.tolist(),source_grasp=g['path'],grip_families=list(holds),charge_source=empty_path,charge_source_offset=1.95,left_hand_extraction=True,left_hand_insertion=True,alignment_pause=[2.08,2.22],contact_seconds=[.60,.72,2.55,2.70],fps=120,runtime_tested=False),indent=2))
(r/'twist_log.json').write_text(json.dumps(twist_log))
