"""Requested scoped diagnosis: source, native retarget, authored V17 and sole slip."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
BASE=Path(__file__).resolve().parents[1];P=BASE/'V18CoupledLocomotion'
for f in ['Records','Motion','Authoring']:(P/f).mkdir(parents=True,exist_ok=True)
native=json.loads((BASE/'RecoveryInputs/RampageBiped/Motion/native_walk.json').read_text())
source=json.loads((BASE/'RecoveryInputs/RampageBiped/Source/rampage_biped_source.json').read_text())
final=json.loads((BASE/'RecoveryInputs/RampageBiped/Motion/rampage_keys.json').read_text())
def mat(v):return Matrix.LocRotScale(Vector(v['p']),Quaternion((v['q'][3],*v['q'][:3])),Vector(v['s']))
ref={n:mat(v) for n,v in native['reference'].items()};parents={n:p if p in ref else None for n,p in native['parents'].items()}
def depth(n):return 1+depth(parents[n]) if parents[n] else 0
order=sorted(ref,key=depth);root=order[0]
raw=[{n:mat(v) for n,v in row.items()} for row in native['frames']]
neutral=[{n:ref[root]@p[root].inverted()@m for n,m in p.items()} for p in raw]
authored=[]
for i in range(final['frames']):
    pose={}
    for n in order:pose[n]=pose[parents[n]]@mat(final['keys'][n][i]) if parents[n] else mat(final['keys'][n][i])
    authored.append(pose)
src=[{n:mat(v) for n,v in row.items()} for row in source['frames']]
source_names={'root':'root','hip':'pelvis','chest':'spine_03','head':'head','ls':'upperarm_l','rs':'upperarm_r','lh':'thigh_l','rh':'thigh_r','le':'lowerarm_l','re':'lowerarm_r','lw':'hand_l','rw':'hand_r','lk':'calf_l','rk':'calf_r','lf':'foot_l','rf':'foot_r'}
target_names={'root':root,'hip':'Bone_001','chest':'Bone_002','head':'Bone_016','ls':'Bone_022','rs':'Bone_027','lh':'Bone_010','rh':'Bone_015','le':'Bone_021','re':'Bone_026','lw':'Bone_020','rw':'Bone_025','lk':'Bone_009','rk':'Bone_014','lf':'Bone_008','rf':'Bone_013'}
def stats(values):
    a=np.array(values);return {'min':float(a.min()),'max':float(a.max()),'range':float(np.ptp(a)),'mean':float(a.mean())}
def vector_range(values):return np.ptp(np.array(values),axis=0).tolist()
def motion_stats(poses,names):
    pos=lambda p,n:p[names[n]].translation
    pitch=[];twist=[];knee={'L':[],'R':[]}
    for p in poses:
        v=pos(p,'chest')-pos(p,'hip');pitch.append(math.degrees(math.atan2(math.hypot(v.x,v.y),v.z)))
        s=pos(p,'rs')-pos(p,'ls');h=pos(p,'rh')-pos(p,'lh')
        twist.append(math.degrees(math.atan2(s.x*h.y-s.y*h.x,s.x*h.x+s.y*h.y)))
        for side,a,b,c in [('L','lh','lk','lf'),('R','rh','rk','rf')]:
            x=pos(p,b)-pos(p,a);y=pos(p,c)-pos(p,b);knee[side].append(math.degrees(x.angle(y)))
    rotations=[p[names['root']].to_quaternion() for p in poses]
    return {'root_xyz_range_cm':vector_range([pos(p,'root') for p in poses]),
        'root_rotation_excursion_deg':max(math.degrees(rotations[0].rotation_difference(q).angle) for q in rotations),
        'pelvis_xyz_range_cm':vector_range([pos(p,'hip') for p in poses]),
        'chest_pitch_deg':stats(pitch),'shoulder_pelvis_twist_deg':stats(twist),
        'right_hand_relative_chest_range_cm':vector_range([pos(p,'rw')-pos(p,'chest') for p in poses]),
        'knee_flexion_deg':{s:stats(v) for s,v in knee.items()}}
report={'source':motion_stats(src,source_names),'native':motion_stats(raw,target_names),
    'root_neutralized':motion_stats(neutral,target_names),'v17':motion_stats(authored,target_names)}
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V14BareBodyHand/Authoring/NightWarden_BareBody_HandRepair_V14.blend'))
body=bpy.data.objects['NW14_CompleteBody_HandRepair'];groups={g.index:g.name for g in body.vertex_groups}
C=Matrix(((0,-100,0,0),(-100,0,0,0),(0,0,100,0),(0,0,0,1)));inv={n:m.inverted() for n,m in ref.items()}
soles={}
for side,family in [('L',{'Bone_008','Bone_007','Bone_006'}),('R',{'Bone_013','Bone_012','Bone_011'})]:
    rows=[]
    for v in body.data.vertices:
        w={groups[g.group]:g.weight for g in v.groups if groups[g.group] in ref and g.weight>1e-6}
        if sum(w.get(n,0.) for n in family)>.6:rows.append((C@(body.matrix_world@v.co),w))
    cutoff=np.percentile([p.z for p,w in rows],10)+.8
    rows=[(p,w) for p,w in rows if p.z<=cutoff];soles[side]=rows
def skin(rows,pose):
    transforms={n:pose[n]@inv[n] for n in ref}
    return np.array([sum(((transforms[n]@p)*(v/sum(w.values())) for n,v in w.items()),Vector()) for p,w in rows])
speed=json.loads((BASE/'RecoveryInputs/RampageBiped/Records/motion_manifest.json').read_text())['nominal_speed_cm_s']
foot_data={}
for side,rows in soles.items():
    points=np.array([skin(rows,p) for p in authored]);ground=points[:,:,2].min(axis=1)
    centroid=points.mean(axis=1);centroid[:,0]+=np.arange(len(authored))/60*speed
    velocity=np.linalg.norm(np.gradient(centroid,1/60,axis=0)[:,:2],axis=1)
    contact=ground<1.1;contact[:2]=False;contact[-2:]=False
    foot_data[side]={'sole_vertices':len(rows),'support_frames':np.where(contact)[0].tolist(),
        'height_cm':stats(ground),'stance_centroid_world_speed_cm_s':stats(velocity[contact]),
        'forward_displacement_during_longest_stance_cm':None}
    best=[];run=[]
    for i,v in enumerate(contact):
        if v:run.append(i)
        else:
            if len(run)>len(best):best=run
            run=[]
    if len(run)>len(best):best=run
    if best:foot_data[side]['forward_displacement_during_longest_stance_cm']=float(centroid[best[-1],0]-centroid[best[0],0])
report['v17_feet']=foot_data
report['v17_nominal_speed_cm_s']=speed
(P/'Records/diagnosis_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NW18_DIAGNOSIS '+json.dumps(report),flush=True)
