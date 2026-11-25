"""Bake a back-crossed idle on the resident's own tracks and measured coat/palms. All distances are cm."""
from pathlib import Path
import json,sys,math
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
root=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(root/'Tools/VillageTavernKeeper/Idle'))
from retarget_idle import forward_kinematics as fk, rotation, unit, swing

home=root/'SourceAssets/HillsVillageStable';out=home/'StablemasterBackIdleR7'
def read(p):return json.loads(p.read_bytes())
rig=read(home/'StablemasterMeshyR3/Authoring/idle_reference.json')
base=read(home/'StablemasterMeshyR4/standing.json')
palms=read(home/'StablemasterMeshyR4/palms.json')
measure=np.load(out/'tailoring.npz')
names=rig['names'];ix={n:i for i,n in enumerate(names)};parents=rig['parents']
rest=np.asarray(rig['reference']);ref=fk(rest,parents);rate=base['rate'];count=base['frame_count']
tracks={n:[] for n in names}
def axis(angle,vec):return Rotation.from_rotvec(np.deg2rad(angle)*np.asarray(vec))
def axes(finger,palm):
    d=unit(finger);n=unit(palm-d*np.dot(palm,d))
    return np.column_stack((d,n,np.cross(d,n)))
def hand_basis(side,sign,direction,palm_normal):
    cloud=measure[side+'Hand']
    centers=cloud[np.linalg.norm(cloud,axis=1)>5.]
    _,vec=np.linalg.eigh(np.cov(centers.T));n=vec[:,0]
    if n[0]*sign>0:n=-n # palms face the thigh in the reference A pose
    return Rotation.from_matrix(axes(direction,palm_normal)@axes(palms[side+'Hand'],n).T)
def shell_clearance(xyz):
    coat=measure['coat'];tree=cKDTree(coat[:,[0,2]])
    # Sample the actual coat skirt under each glove, including the wider lower hem.
    near=tree.query(xyz[:,[0,2]],k=12)[1]
    return np.min(coat[near,1],axis=1)-xyz[:,1]
hand={}
for side,sign in [('Left',1),('Right',-1)]:
    left=side=='Left'
    r=hand_basis(side,sign,[-.81,-.20,-.55] if left else [.84,-.16,-.52],
                 [0,-1,.14] if left else [0,1,-.14])
    wrist=np.array([6.7 if left else -6.3, -12.5,100.6 if left else 99.9])
    cloud=wrist+r.apply(measure[side+'Hand'])
    shift=np.min(shell_clearance(cloud))-.9
    wrist[1]+=shift;cloud[:,1]+=shift
    hand[side]=(wrist,r,cloud)
# Position the outer palm against the other hand's actual dorsal surface.
inner=hand['Left'][2];outer=hand['Right'][2];tree=cKDTree(inner[:,[0,2]])
dist,idx=tree.query(outer[:,[0,2]],k=12)
overlap=dist<.50
if not np.any(overlap):raise ValueError('The two hands have no contact patch')
gaps=np.where(overlap,inner[idx,1]-outer[:,None,1],np.inf)
offset=min(0.,float(np.min(gaps))-.11)
hand['Right'][0][1]+=offset;outer[:,1]+=offset

def solve_chain(frame,w,n0,n1,n2,goal,pole):
    a,b,c=[ix[n] for n in (n0,n1,n2)]
    p=w[a,:3,3].copy();u=np.linalg.norm(ref[b,:3,3]-ref[a,:3,3]);l=np.linalg.norm(ref[c,:3,3]-ref[b,:3,3])
    d=goal-p;dist=np.clip(np.linalg.norm(d),abs(u-l)+.002,u+l-.002);aim=unit(d)
    projected=pole-aim*np.dot(pole,aim)
    ortho=unit(projected);along=(u*u+dist*dist-l*l)/(2*dist)
    bend=p+aim*along+ortho*np.sqrt(max(0.,u*u-along*along))
    for bone,child,endpoint in [(a,b,bend),(b,c,p+aim*dist)]:
        desired=swing(w[child,:3,3]-w[bone,:3,3],endpoint-w[bone,:3,3])*rotation(w[bone])
        frame[bone,3:7]=(rotation(w[parents[bone]]).inv()*desired).as_quat()
        w=fk(frame,parents)
    return w
for f in range(count):
    phase=math.tau*f/count
    breath=math.sin(2*phase-.35);sway=math.sin(phase+.2)
    frame=rest.copy()
    for n in ['Spine02','Spine01','Spine','neck','Head','LeftShoulder','RightShoulder']:
        keys=base['tracks'][n];frame[ix[n]]=keys[f%len(keys)] if len(keys)>1 else keys[0]
    hip=ix['Hips']
    frame[hip,:3]+=np.array([.65+.40*sway,.18+.09*breath,-.52+.09*breath])
    frame[hip,3:7]=(axis(.45+.26*sway,[0,1,0])*rotation(ref[hip])).as_quat()
    w=fk(frame,parents)
    def rotate_in_world(i,delta):
        global w
        desired=delta*rotation(w[i])
        frame[i,3:7]=(rotation(w[parents[i]]).inv()*desired).as_quat()
        w=fk(frame,parents)
    for n,bias in [('Spine02',.65),('Spine01',.85),('Spine',.65)]:
        rotate_in_world(ix[n],axis(-bias-.24*breath,[1,0,0]))
    rotate_in_world(ix['Head'],axis(.65*math.sin(phase-.6),[0,0,1])*axis(.52+.34*breath,[1,0,0]))
    back=ix['Spine02'];rel=rotation(w[back])*rotation(ref[back]).inv()
    def follow(point):return w[back,:3,3]+rel.apply(point-ref[back,:3,3])
    for side,sign in [('Left',1),('Right',-1)]:
        rotate_in_world(ix[side+'Shoulder'],axis(-sign*(3.3+.35*breath),[0,0,1]))
        wrist,wr,_=hand[side]
        w=solve_chain(frame,w,side+'Arm',side+'ForeArm',side+'Hand',follow(wrist),
                      rel.apply([sign*(5.8+.35*sway),-12.8,-16.5]))
        i=ix[side+'Hand']
        goal=rel*wr*rotation(ref[i])
        # Carry pronation through the forearm. Leaving the full roll on the
        # hand bone would corkscrew the cuff where the palms turn inward.
        fore=ix[side+'ForeArm']
        roll_axis=unit(w[i,:3,3]-w[fore,:3,3])
        dq=(goal*rotation(w[i]).inv()).as_quat()
        angle=2*math.atan2(np.dot(dq[:3],roll_axis),dq[3])
        angle=(angle+math.pi)%(2*math.pi)-math.pi
        rotate_in_world(fore,Rotation.from_rotvec(roll_axis*np.clip(.70*angle,-1.22,1.22)))
        frame[i,3:7]=(rotation(w[fore]).inv()*goal).as_quat();w=fk(frame,parents)
        # Keep both soles and their orientation planted while the pelvis settles over one leg.
        foot=ix[side+'Foot']
        w=solve_chain(frame,w,side+'UpLeg',side+'Leg',side+'Foot',ref[foot,:3,3],
                      ref[ix[side+'Leg'],:3,3]-ref[ix[side+'UpLeg'],:3,3])
        frame[foot,3:7]=(rotation(w[parents[foot]]).inv()*rotation(ref[foot])).as_quat();w=fk(frame,parents)
    for n,i in ix.items():
        key=frame[i].copy()
        if tracks[n] and np.dot(key[3:7],tracks[n][-1][3:7])<0:key[3:7]*=-1
        tracks[n].append(key.tolist())
for n,keys in tracks.items():
    keys.append(keys[0].copy())
    if np.max(np.abs(np.asarray(keys)-keys[0]))<1.e-7:tracks[n]=keys[:1]
(out/'standing.json').write_text(json.dumps(dict(rate=rate,frame_count=count,tracks=tracks),separators=(',',':')))
(out/'authoring.json').write_text(json.dumps(dict(rate=rate,seconds=count/rate,anchors_cm={k:v[0].tolist() for k,v in hand.items()},
    forward_reference='https://cosindra.ai/motionsmith/motions/idle-lean-forward',
    hands_reference='https://3dtexel.com/product/idle-neutral-hands-back-female/',
    base_motion='StablemasterMeshyR4/standing.json',finger_bones=False),indent=2))
