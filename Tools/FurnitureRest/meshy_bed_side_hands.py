"""Keep the seated hands relaxed beside the hips before the bed-support reach."""
import copy,hashlib,json,math,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'SourceAssets/FurnitureRest20261022/MeshyBed20261024'
OUT=BASE.parent/'MeshyBedSideHands20261024'
OUT.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
ns={'__file__':str(ROOT/'Tools/FurnitureRest/meshy_bed.py')}
exec((ROOT/'Tools/FurnitureRest/meshy_bed.py').read_text().split('prefix=[]')[0],ns)
fk,rot,ix,unit,basis,smooth=[ns[n] for n in ('fk','rot','ix','unit','basis','smooth')]
between=ns['ns']['between']
data=copy.deepcopy(read(BASE/'authored.json'))
data['changed_roles']=['Rest.Bed.Enter','Rest.Bed.Exit']
frames=np.asarray(data['clips']['Rest.Bed.Enter']['frames'])
initial=fk(frames[0]);result=[];paths=[]
def turn(a,b,t):return Slerp([0,1],R.from_matrix([a,b]))(float(np.clip(t,0,1))).as_matrix()
geometry=read(BASE/'ReviewSaved/body.json');points=np.asarray(geometry['positions'])
inverse_bind=np.linalg.inv(fk(np.asarray(data['reference'])))
hand_skin={}
for side in ('l','r'):
    selected=[i for i,ws in enumerate(geometry['weights']) if
        geometry['bone_names'][max(ws,key=lambda p:p[1])[0]].startswith(('hand_','thumb_','index_','middle_','ring_','pinky_')) and
        geometry['bone_names'][max(ws,key=lambda p:p[1])[0]].endswith('_'+side)][::3]
    influences={}
    for output,index in enumerate(selected):
        for bone,weight in geometry['weights'][index]:
            influences.setdefault(ix[geometry['bone_names'][bone]],[]).append((output,weight))
    hand_skin[side]=(points[selected],{b:(np.asarray(rows)[:,0].astype(int),np.asarray(rows)[:,1,None]) for b,rows in influences.items()})
def hand_points(f,side):
    p,influences=hand_skin[side];mat=fk(f)@inverse_bind;v=np.zeros_like(p)
    for bone,(ids,weights) in influences.items():v[ids]+=(p[ids]@mat[bone,:3,:3].T+mat[bone,:3,3])*weights
    return v

for j,original in enumerate(frames):
    t=j/30;f=original.copy();world=fk(original);row={'time':t,'hands':{}}
    for side,sign in [('l',1),('r',-1)]:
        delay=0. if side=='l' else .08
        weight=float(smooth((t-.45-delay)/.60)*(1-smooth((t-3.45-delay)/.95)))
        if weight<1e-8:continue
        a,b,c=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
        shoulder=world[a,:3,3]
        length1=np.linalg.norm(initial[b,:3,3]-initial[a,:3,3])
        length2=np.linalg.norm(initial[c,:3,3]-initial[b,:3,3])
        knee_clear=float(1-smooth((t-.9)/.5))
        relaxed=shoulder+unit(np.array([sign*(.205+.04*knee_clear),.025,-1.]))*(length1+length2)*.966
        seated=float(smooth((t-.85)/.65))
        beside=world[ix['pelvis'],:3,3]+np.array([sign*28.,2.,0.])
        horizontal=beside[:2]-shoulder[:2]
        beside[2]=shoulder[2]-math.sqrt(max(1.,((length1+length2)*.966)**2-horizontal@horizontal))
        relaxed=relaxed*(1-seated)+beside*seated
        target=world[c,:3,3]*(1-weight)+relaxed*weight
        axis=unit(target-shoulder);distance=min(np.linalg.norm(target-shoulder),(length1+length2)*.985)
        references=[]
        for pose in (world,initial):
            upper=pose[b,:3,3]-pose[a,:3,3];lower=pose[c,:3,3]-pose[b,:3,3]
            old_axis=unit(upper+lower);bend=unit(upper-old_axis*(upper@old_axis))
            normal=unit(np.cross(upper,lower))
            references.append((between(old_axis,axis)@bend,basis(upper,normal).T@pose[a,:3,:3],basis(lower,normal).T@pose[b,:3,:3]))
        angle=math.atan2(axis@np.cross(references[0][0],references[1][0]),references[0][0]@references[1][0])
        bend=R.from_rotvec(axis*angle*weight).as_matrix()@references[0][0]
        along=(length1**2+distance**2-length2**2)/(2*distance)
        elbow=shoulder+axis*along+bend*math.sqrt(max(0.,length1**2-along**2))
        wrist=shoulder+axis*distance;normal=unit(np.cross(elbow-shoulder,wrist-elbow))
        rot(f,a,basis(elbow-shoulder,normal)@turn(references[0][1],references[1][1],weight))
        rot(f,b,basis(wrist-elbow,normal)@turn(references[0][2],references[1][2],weight))
        rot(f,c,turn(world[c,:3,:3],initial[c,:3,:3],weight))
        for digit in ('thumb','index','middle','ring','pinky'):
            for joint in (1,2,3):
                bone=ix[f'{digit}_{joint:02d}_{side}']
                f[bone,3:7]=R.from_matrix(turn(R.from_quat(original[bone,3:7]).as_matrix(),R.from_quat(frames[0,bone,3:7]).as_matrix(),weight)).as_quat()
        clearance=0.
        for _ in range(2):
            vertices=hand_points(f,side)
            low=vertices[np.argsort(vertices[:,2])[:12]]
            gap=min(float(p[2]-ns['surface'](p[0],p[1])) for p in low)
            lift=max(0.,.4-gap)
            if lift<.01:break
            current=fk(f);ns['solve'](f,side,('upperarm','lowerarm','hand'),current[c,:3,3]+[0.,0.,lift],current[c,:3,:3])
            clearance+=lift
        row['hands'][side]={'side_weight':weight,'target':target.tolist(),'mattress_clearance_lift_cm':clearance}
    result.append(f);paths.append(row)

data['clips']['Rest.Bed.Enter']['frames']=np.asarray(result).tolist()
leave=np.asarray(data['clips']['Rest.Bed.Exit']['frames'])
leave[:len(result)]=np.asarray(result)[::-1]
data['clips']['Rest.Bed.Exit']['frames']=leave.tolist()
body=read(ROOT/'Content/ColdSteelData/player_body.json');roles=data['changed_roles']
snapshot=OUT/'baseline_routes.json'
if not snapshot.exists():
    snapshot.write_text(json.dumps({'default':{r:body['clips'][r] for r in roles},'variants':{
        n:{'mesh':v['body_mesh'],'clips':{r:v['clips'][r] for r in roles}}
        for n,v in body.get('body_variants',{}).items() if v.get('ready')}},indent=2))
cfg=read(ROOT/'Content/ColdSteelData/furniture_rest.json')
(OUT/'authored.json').write_text(json.dumps(data,separators=(',',':')))
(OUT/'clip_metadata.json').write_text(json.dumps({r:cfg['clips'][r] for r in roles},separators=(',',':')))
(OUT/'review_config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'hand_paths.json').write_text(json.dumps(paths,indent=2))
(OUT/'source_revision.json').write_text(json.dumps({'source':str(BASE/'authored.json'),
    'sha256':hashlib.sha256((BASE/'authored.json').read_bytes()).hexdigest(),
    'changed_roles':roles,'modified_channels':'upperarm, lowerarm, hand and finger rotations only',
    'source_time_range_seconds':[.45,4.48],'timing_body_head_legs_and_idle_unchanged':True},indent=2))
(OUT/'ReviewSaved').mkdir(exist_ok=True)
for name in ('body.json','head.json'):
    if not (OUT/'ReviewSaved'/name).exists():shutil.copyfile(BASE/'ReviewSaved'/name,OUT/'ReviewSaved'/name)
print('MESHY_BED_SIDE_HANDS_AUTHORED',len(result),flush=True)
