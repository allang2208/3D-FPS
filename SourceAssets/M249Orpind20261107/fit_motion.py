"""Fit game animation in the installed rig's native bind space, preserving source finger curls and phase timing."""
import gzip
import json
import sys
import pickle
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parent
D=ROOT/"MotionInput"
OUT=ROOT/"Motion"
OUT.mkdir(exist_ok=True)
def read(p):
    with gzip.open(p,"rt",encoding="utf8") as f:return json.load(f)
def matrix(v):
    a=np.asarray(v)
    m=np.zeros((*a.shape[:-1],4,4));m[...,3,3]=1
    m[...,:3,:3]=Rotation.from_quat(a[...,3:7]).as_matrix()*a[...,None,7:10]
    m[...,:3,3]=a[...,:3]
    return m
def keys(m):
    p=m[:,:3,3];sc=np.linalg.norm(m[:,:3,:3],axis=1)
    q=Rotation.from_matrix(m[:,:3,:3]/sc[:,None,:]).as_quat()
    q*=np.cumprod(np.r_[1,np.where((q[1:]*q[:-1]).sum(1)<0,-1,1)])[:,None]
    a=np.concatenate([p,q,sc],axis=1)
    if np.allclose(a,a[:1],atol=1e-7,rtol=0):a=a[:1]
    return a.round(8).tolist()
def trans(p):
    m=np.eye(4);m[:3,3]=p;return m
def norm(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-9)
def swing(v,w):
    a,b=norm(v),norm(w)
    q=np.c_[np.cross(a,b),1+(a*b).sum(1)]
    return Rotation.from_quat(q).as_matrix()
def mount(x,y,z):return np.array([5.45+y,x-28.6,z-5.3])
r=json.loads((D/"rig.json").read_text());B={n:matrix(t) for n,t in r["bind"].items()};parent=r["parents"]
idle=read(D/"idle.json.gz")
I={n:matrix(row) for n,row in zip(idle["bones"],idle["frames"][0])}
root="WPN_root"
rest_from_idle=B[root]@np.linalg.inv(I[root])
def grip(side):
    a,b=[(rest_from_idle@I[f"middle_{j}_{side}"])[:3,3] for j in ("01","03")]
    # The phalanges run around the far surface. Pull their midpoint towards the wrist to locate the grip axis.
    wrist=(rest_from_idle@I["hand_"+side])[:3,3]
    c=(a+b)/2
    return c+.25*(wrist-c)
grip_delta={"r":mount(16,.18,-8.8)-grip("r"),"l":mount(-14.4,.22,-9.7)-grip("l")}
def diff(n,point):return point-B[n][:3,3]
offsets={"PKM_Cover":diff("PKM_Cover",mount(-2.75,.13,6.0)),
         "PKM_Tray":diff("PKM_Tray",mount(-2.0,.1,4.2)),
         "PKM_Box":diff("PKM_Box",mount(1.7,-.35,-8.6)),
         "PKM_Charge":diff("PKM_Charge",mount(1.0,2.65,1.05))}
offsets["New_PKM_Box"]=offsets["PKM_Box"]
offsets["PKM_Trigger"]=diff("PKM_Trigger",mount(10,.2,-3.4))
sightpoints={"WPN_FrontSight":mount(12.59,.14,9.775),"WPN_RearSight":mount(20.70,.14,9.775),
             "WPN_SOCKET_Muzzle":mount(-50.25,.47,3.85),"WPN_SOCKET_Eject":mount(.25,3.0,1.4),
             "WPN_SOCKET_Magazine":mount(1.7,-.35,-8.6)}
sys.path.insert(0,str(ROOT/"Repair05"))
from rail_contract import sights
sightpoints.update({n:mount(*p) for n,p in sights().items()})
A=trans(mount(1.45,-2.25,3.55))@np.diag([-.72,.72,.72,1])@trans(-B["PKM_Belt_00"][:3,3])
def smooth(t,a,b):
    t=np.clip((t-a)/(b-a),0,1)
    return t*t*(3-2*t)
def mix(a,b,w):return a+(b-a)*w[:,None]

hand_fit=json.loads((ROOT/"ReloadReview/belt_hand_fit.json").read_text())
sys.path.insert(0,str(ROOT/"ReloadReview"))
from strand_fit import as_matrix
sys.path.insert(0,str(ROOT/"Repair03"))
from arm_refinement import solve
sys.path.insert(0,str(ROOT/"Repair06"))
from motion_clearance import hand_route,drape
native=pickle.load(open(ROOT/"Repair02/donor_rig.pkl","rb"))
surface=pickle.load(open(ROOT.parents[1]/"Saved/M249ReloadReview/geometry.pkl","rb"))
verts=np.asarray(surface["vertices"])
skin_names=surface["names"]
dominant=np.asarray([surface["used"].index(max(row,key=lambda w:w[1])[0]) for row in surface["weights"]])
pad_centers={side:{digit:np.r_[verts[dominant==skin_names.index(digit+"_03_"+side)].mean(0),1.]
                  for digit in ("index","thumb")} for side in ("l","r")}
tip_center=np.r_[verts[dominant==skin_names.index("PKM_Belt_00")].mean(0),1.]
new_tip_center=np.r_[verts[dominant==skin_names.index("New_PKM_Belt_00")].mean(0),1.]
belt_centers={n:np.r_[verts[dominant==skin_names.index(n)].mean(0),1.] for n in skin_names if "_Belt_" in n and "Link" not in n and int(n[-2:])<9}
for f in sorted(D.glob("*.json.gz")):
    role=f.name.split(".")[0]
    if sys.argv[1:] and role not in sys.argv[1:]:continue
    if role=='quick_melee':
        # Repair08 preserves this gun's final grip and bakes its runtime handoff.
        # Reapplying the donor shoulder/wrist fit would restore the rejected twist.
        import shutil
        shutil.copyfile(ROOT/'Repair08/quick_melee.json.gz',OUT/(role+'.json.gz'))
        print('M249_FITTED',role,'Repair08 continuous right arm')
        continue
    src=read(f)
    full=pickle.load(open(ROOT/"Repair02"/("donor_"+role+".pkl"),"rb"))
    rows=np.array(full["frames"])
    P={n:matrix(rows[:,i]) for i,n in enumerate(native["names"]) if n in B}
    G=P[root]@np.linalg.inv(B[root]);Gi=np.linalg.inv(G)
    pose={n:Gi@v for n,v in P.items()}
    changed={}
    for n,delta in offsets.items():
        xf=trans(delta)
        changed[n]=xf@pose[n]@np.linalg.inv(B[n])@np.linalg.inv(xf)@B[n]
    if role=='reload_empty':
        times=np.linspace(0,src['duration'],len(rows))
        travel=9.0*smooth(times,5.13,5.36)*(1.-smooth(times,5.48,5.82))
        changed['PKM_Charge']=np.broadcast_to(B['PKM_Charge'],(len(rows),4,4)).copy()
        changed['PKM_Charge'][:,:3,3]+=travel[:,None]*np.array([0.,1.,0.])
    for n in pose:
        if "_Belt_" not in n:continue
        carrier="New_PKM_Box" if n.startswith("New_") else "PKM_Box"
        old=pose[carrier]@np.linalg.inv(B[carrier])
        target=changed[carrier]@np.linalg.inv(B[carrier])
        # Preserve the travelling box frame and adapt the curved strip relative to its mouth.
        changed[n]=target@A@np.linalg.inv(old)@pose[n]@np.linalg.inv(B[n])@np.linalg.inv(A)@B[n]
    for n,p in sightpoints.items():
        changed[n]=pose[n].copy();changed[n][:,:3,3]=p
    if role in hand_fit:
        with np.load(ROOT/"ReloadReview"/(role+"_strand.npz")) as strand:
            for n in strand.files:
                carrier="New_PKM_Box" if n.startswith("New_") else "PKM_Box"
                xf=changed[carrier]@np.linalg.inv(B[carrier])
                changed[n]=xf@as_matrix(strand[n])@np.linalg.inv(xf)@changed[n]
    if role.startswith("reload"):
        drape(changed,B,belt_centers,np.linspace(0,src["duration"],len(rows)),role=="reload_empty")
    for side in ("l","r"):
        anchor=np.broadcast_to(grip_delta[side],(len(rows),3)).copy()
        t=np.linspace(0,src["duration"],len(rows))
        if role.startswith("reload"):
            skip=.9 if role=="reload_empty" else 0
            open_w=smooth(t,.20,.53)*(1-smooth(t,.96,1.32))
            belt_w=smooth(t,1.0,1.43)*(1-smooth(t,1.95,2.30)) if not skip else np.zeros_like(t)
            box_w=smooth(t,2.23-skip,2.54-skip)*(1-smooth(t,4.38-skip,4.60-skip))
            seat_w=smooth(t,4.35-skip,4.67-skip)*(1-smooth(t,5.13-skip,5.36-skip))
            close_w=smooth(t,5.12-skip,5.40-skip)*(1-smooth(t,5.78-skip,6.02-skip))
            charge_w=smooth(t,4.99,5.18)*(1-smooth(t,5.86,6.15)) if skip else np.zeros_like(t)
            for target,weight in ([(offsets["PKM_Cover"],open_w),(mount(1.45,-5.2,2.0)-B["PKM_Belt_00"][:3,3],belt_w)] if side=="l" else
                [(offsets["PKM_Box"],box_w),(mount(1.45,-3.8,3.2)-B["PKM_Belt_00"][:3,3],seat_w),(offsets["PKM_Cover"],close_w),(offsets["PKM_Charge"],charge_w)]):
                anchor=mix(anchor,target,weight)
        # Two-bone reach with the authored elbow plane, wrist orientation and finger tracks.
        upper,lower,hand=["%s_%s"%(n,side) for n in ("upperarm","lowerarm","hand")]
        S,E,H=[pose[n][:,:3,3] for n in (upper,lower,hand)]
        target=pose[hand].copy()
        target[:,:3,3] += anchor
        pad=np.mean([(pose[digit+"_03_"+side]@np.linalg.inv(B[digit+"_03_"+side])@point)[:,:3]
                     for digit,point in pad_centers[side].items()],axis=0)
        pivot=(np.linalg.inv(pose[hand])@np.c_[pad,np.ones(len(pad))][...,None])[:,:,0]
        working=np.zeros(len(rows));wrist_limit=np.full(len(rows),40.)
        if role.startswith("reload"):
            is_left=side=="l"
            tip="PKM_Belt_00" if is_left else "New_PKM_Belt_00"
            ref_tip=tip_center if is_left else new_tip_center
            tip_position=(changed[tip]@np.linalg.inv(B[tip])@ref_tip)[:,:3]
            contact=H+tip_position-pad+np.array([0.,0.,.8])
            contact_w=(smooth(t,1.10,1.38)*(1-smooth(t,1.96,2.30))) if is_left and not skip else (
                smooth(t,4.30-skip,4.50-skip)*(1-smooth(t,5.12-skip,5.40-skip)) if not is_left else np.zeros_like(t))
            target[:,:3,3]=mix(target[:,:3,3],contact,contact_w)
            working=smooth(t,.12,.40)*(1-smooth(t,1.45 if skip else 2.35,1.75 if skip else 2.65)) if is_left else smooth(t,2.15-skip,2.40-skip)*(1-smooth(t,6.10 if skip else 5.95,6.32 if skip else 6.22))
            wrist_limit-=10.*contact_w
            if skip and not is_left:
                knob=mount(.66,2.85,.04)
                handle=(changed['PKM_Charge']@np.linalg.inv(B['PKM_Charge'])@np.r_[knob,1])[:,:3]
                engage=smooth(t,4.96,5.13)*(1-smooth(t,5.82,6.10))
                target[:,:3,3]=mix(target[:,:3,3],H+handle-pad+np.array([.7,0.,0.]),engage)
                wrist_limit-=8.*engage
        if role.startswith("reload") and side=="l":
            hand_route(target,t,bool(skip))
            wrist_limit=np.minimum(wrist_limit,32.)
        changed.update(solve(side,pose,B,target,pivot,working,wrist_limit))
    local={}
    if role.startswith("reload"):
        home=np.load(ROOT/"Repair03/idle_world.npz")
        t=np.linspace(0,src["duration"],len(rows))
        settle=smooth(t,src["duration"]-.22,src["duration"])
        for n in list(changed):
            if not n.startswith(("upperarm","lowerarm","hand")):continue
            m=changed[n]
            scale=np.linalg.norm(m[:,:3,:3],axis=1)
            rotation=m[:,:3,:3]/scale[:,None,:]
            end=home[n][0]
            endrot=end[:3,:3]/np.linalg.norm(end[:3,:3],axis=0)
            delta=Rotation.from_matrix(np.swapaxes(rotation,1,2)@endrot).as_rotvec()
            m[:,:3,:3]=(rotation@Rotation.from_rotvec(delta*settle[:,None]).as_matrix())*scale[:,None,:]
            m[:,:3,3]=mix(m[:,:3,3],end[:3,3],settle)
    for n,tgt in changed.items():
        p=parent[n]
        base=changed[p] if p in changed else pose[p]
        local[n]=keys(np.linalg.inv(base)@tgt)
    with gzip.open(OUT/(role+".json.gz"),"wt",encoding="utf8",compresslevel=4) as handle:
        json.dump({"source":src["source"],"tracks":local},handle,separators=(",",":"))
    if role in ("idle","reload","reload_empty"):
        world={}
        for n in P:
            p=parent[n]
            old_local=np.linalg.inv(pose[p])@pose[n] if p in pose else pose[n]
            if n in changed:
                basis=changed[p] if p in changed else pose[p]
                target_local=np.linalg.inv(basis)@changed[n]
            else:target_local=old_local
            world[n]=world[p]@target_local if p in world else target_local
        np.savez_compressed(ROOT/"Repair06"/(role+"_authored_world.npz"),**world)
    print("M249_FITTED",role,len(rows),len(local))
