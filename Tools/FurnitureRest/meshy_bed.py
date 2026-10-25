"""Fit the user's complete sleep take to the ordinary bed, preserving its timing."""
import copy,json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
from scipy.signal import savgol_filter
from scipy.interpolate import PchipInterpolator

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'SourceAssets/FurnitureRest20261022/MeshySitLieBed37120261024'
OUT=ROOT/'SourceAssets/FurnitureRest20261022/MeshyBed20261024'
OUT.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
donor=read(SRC/'retargeted.json');take=next(v for k,v in donor['clips'].items() if k.endswith('_sleep'))
raw=read(SRC/'source_world.json');raw_ix={n:i for i,n in enumerate(raw['names'])}
seating=read(OUT.parent/'ChairReuse20261024/authored.json')
ns={'__file__':str(ROOT/'Tools/FurnitureRest/refine.py')}
exec((ROOT/'Tools/FurnitureRest/refine.py').read_text().split('specs=')[0],ns)
fk,rot,ix,bind=ns['fk'],ns['rot'],ns['ix'],ns['bind']
ref=np.array(donor['reference'])
support_file=OUT/'support_fit.json'
support_data=read(support_file) if support_file.exists() else {'times':[0.,9.],'root_z':[0.,0.],'neck_degrees':[0.,0.]}
root_support=PchipInterpolator(support_data['times'],support_data['root_z'])
neck_support=PchipInterpolator(support_data['times'],support_data['neck_degrees'])
def smooth(t):
    t=np.clip(t,0,1);return t*t*t*(t*(6*t-15)+10)
def unit(v):return v/max(np.linalg.norm(v),1e-9)
def basis(direction,normal):
    y=unit(direction);z=unit(normal-y*(normal@y));return np.column_stack((np.cross(y,z),y,z))
def blend(a,b,t):
    f=a*(1-t)+b*t;q=b[:,3:7].copy();q[(a[:,3:7]*q).sum(axis=1)<0]*=-1
    f[:,3:7]=a[:,3:7]*(1-t)+q*t;f[:,3:7]/=np.linalg.norm(f[:,3:7],axis=1)[:,None];return f

config=read(ROOT/'Content/ColdSteelData/furniture_rest.json')
profile=next(p for p in config['furniture'] if p['slots'][0]['kind']=='Bed' and 'RefinementV2' in p['mesh'])
geo_root=OUT.parent/'RefineV2/Geometry';geo_index=read(geo_root/'index.json')
geo=read(geo_root/geo_index[profile['mesh']]);vertices=np.array(geo['positions']);triangles=vertices[np.array(geo['triangles'],int)]
xy=triangles[:,0,:2];edge1=triangles[:,1,:2]-xy;edge2=triangles[:,2,:2]-xy
den=edge1[:,0]*edge2[:,1]-edge1[:,1]*edge2[:,0];valid=abs(den)>1e-8
def surface(x,y):
    q=np.array([x,y])-xy
    u=np.divide(q[:,0]*edge2[:,1]-q[:,1]*edge2[:,0],den,out=np.zeros_like(den),where=valid)
    v=np.divide(edge1[:,0]*q[:,1]-edge1[:,1]*q[:,0],den,out=np.zeros_like(den),where=valid)
    mask=valid&(u>=0)&(v>=0)&(u+v<=1)
    z=triangles[:,0,2]+u*(triangles[:,1,2]-triangles[:,0,2])+v*(triangles[:,2,2]-triangles[:,0,2])
    return float(z[mask].max()) if mask.any() else 0.

def solve(f,side,chain,target,end_rotation,max_reach=None):
    a,b,c=[ix[n+'_'+side] for n in chain];w=fk(f);h,k,e=w[[a,b,c],:3,3]
    upper,lower=k-h,e-k;l1,l2=np.linalg.norm(upper),np.linalg.norm(lower)
    old_axis=unit(e-h);old_bend=unit(upper-old_axis*(upper@old_axis));axis=unit(target-h)
    bend=ns['between'](old_axis,axis)@old_bend
    reach_limit=(l1+l2)*max_reach if max_reach else l1+l2-.2
    distance=np.clip(np.linalg.norm(target-h),abs(l1-l2)+.05,reach_limit)
    along=(l1*l1+distance*distance-l2*l2)/(2*distance)
    knee=h+axis*along+bend*math.sqrt(max(0.,l1*l1-along*along));end=h+axis*distance
    old_normal=unit(np.cross(upper,lower));normal=unit(np.cross(knee-h,end-knee))
    rot(f,a,basis(knee-h,normal)@basis(upper,old_normal).T@w[a,:3,:3])
    rot(f,b,basis(end-knee,normal)@basis(lower,old_normal).T@w[b,:3,:3]);rot(f,c,end_rotation)

def feet_clear(f,goals,progress,preparation=None):
    for side in ('l','r'):
        position,rotation=goals[side];position=position.copy();lift=progress[side]
        prepare=float(smooth((150.-position[1])/24.)) if preparation is None else preparation
        if preparation is not None:
            position[1]=max(position[1],126.+20.*(1-prepare))
        position[2]=max(position[2],9.+42.*prepare)
        if preparation is None:position[2]=max(position[2],51.+25.*lift)
        if position[1]<126.:
            position[1]=126.*(1-lift)+position[1]*lift
            position[2]=max(position[2],51.+25.*lift)
        # Ankle goals include the native sole depth, including when crossing
        # the projecting foot frame before reaching the mattress.
        top=surface(position[0],position[1])
        if top>0:position[2]=max(position[2],top+10.)
        solve(f,side,('thigh','calf','foot'),position,rotation)

def head_support(f,time):
    angle=float(neck_support(time))
    if angle<1e-5:return
    w=fk(f)
    for name,factor in [('neck_01',1.),('neck_02',1.),('head',.55)]:
        rot(f,ix[name],R.from_euler('x',-angle*factor,degrees=True).as_matrix()@w[ix[name],:3,:3])

prefix=[]
for j,frame in enumerate(seating['clips']['Rest.Chair55.Enter']['frames']):
    t=j/30;f=np.array(frame);w=fk(f)
    shift=np.array([-32.,73.+24.*(1-smooth(t/1.15)),12.*smooth(t/1.15)])
    f[ix['pelvis'],:3]+=shift
    f[ix['pelvis'],2]+=float(root_support(t))
    goals={s:(w[ix['foot_'+s],:3,3]+[shift[0],shift[1],0.],w[ix['foot_'+s],:3,:3]) for s in ('l','r')}
    # Keep the approach feet low until the hips reach the mattress; then
    # lift them around the foot frame as the seated body moves inward.
    feet_clear(f,goals,dict(l=0.,r=0.),float(smooth((t-.55)/.85)))
    for side in ('l','r'):
        current=fk(f);hand=ix['hand_'+side]
        target=current[hand,:3,3]+[0.,0.,1.4*float(smooth((t-.7)/1.6))]
        solve(f,side,('upperarm','lowerarm','hand'),target,current[hand,:3,:3])
    head_support(f,t)
    prefix.append(f)

# The old generic seated-hand IK contains an elbow-plane flip. Reconstruct
# this short entry from its two native endpoints on a continuous bend circle.
start_world,end_world=fk(prefix[0]),fk(prefix[-1])
for j,f in enumerate(prefix):
    t=j/30
    for side,sign in [('l',1),('r',-1)]:
        a,b,c=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
        w=fk(f);shoulder=w[a,:3,3]
        l1=np.linalg.norm(start_world[b,:3,3]-start_world[a,:3,3]);l2=np.linalg.norm(start_world[c,:3,3]-start_world[b,:3,3])
        reach=float(smooth((t-(.68 if side=='l' else .8))/(1.68 if side=='l' else 1.7)))
        knee_clear=float(smooth(t/.25)*(1-smooth((t-.85)/.5)))
        natural=shoulder+unit(np.array([sign*(.195+.10*knee_clear),.045,-1.]))*(l1+l2)*(.977 if side=='l' else .973)
        resting=f[ix['pelvis'],:3]+end_world[c,:3,3]-end_world[ix['pelvis'],:3,3]
        target=natural*(1-reach)+resting*reach+np.array([sign*5.5,1.,4.])*math.sin(math.pi*reach)
        axis=unit(target-shoulder);distance=min(np.linalg.norm(target-shoulder),l1+l2-.15)
        references=[]
        for ref_world in (start_world,end_world):
            upper=ref_world[b,:3,3]-ref_world[a,:3,3];lower=ref_world[c,:3,3]-ref_world[b,:3,3]
            ref_axis=unit(upper+lower);ref_bend=unit(upper-ref_axis*(upper@ref_axis));normal=unit(np.cross(upper,lower))
            references.append((ns['between'](ref_axis,axis)@ref_bend,basis(upper,normal).T@ref_world[a,:3,:3],basis(lower,normal).T@ref_world[b,:3,:3]))
        theta=math.atan2(axis@np.cross(references[0][0],references[1][0]),references[0][0]@references[1][0])
        bend=R.from_rotvec(axis*theta*reach).as_matrix()@references[0][0]
        along=(l1*l1+distance*distance-l2*l2)/(2*distance)
        knee=shoulder+axis*along+bend*math.sqrt(max(0.,l1*l1-along*along));wrist=shoulder+axis*distance
        normal=unit(np.cross(knee-shoulder,wrist-knee))
        upper_c=Slerp([0,1],R.from_matrix([references[0][1],references[1][1]]))(reach).as_matrix()
        lower_c=Slerp([0,1],R.from_matrix([references[0][2],references[1][2]]))(reach).as_matrix()
        rot(f,a,basis(knee-shoulder,normal)@upper_c);rot(f,b,basis(wrist-knee,normal)@lower_c)
        hand_rotation=Slerp([0,1],R.from_matrix([start_world[c,:3,:3],end_world[c,:3,:3]]))(float(smooth(reach))).as_matrix()
        rot(f,c,hand_rotation)

base_frames=np.array(take['frames']);raw_frames=np.array(raw['clips']['sleep']['frames'])
# The export's first left-wrist sample differs by 18 degrees from the next
# frame. Join to the first moving pose while keeping the take's time span.
base_frames[0]=base_frames[1].copy()
offset=prefix[-1][ix['pelvis'],:3]-base_frames[0,ix['pelvis'],:3]
offset[2]-=float(root_support(2.8))
torso_bones=[ix[n] for n in ('spine_01','spine_02','spine_03','spine_04','spine_05','neck_01','neck_02','head','clavicle_l','clavicle_r')]
rest_fingers=np.array(seating['clips']['Rest.Chair52.Idle']['frames'][0])
raw_angles=[];hand_targets=[];base_world=[]
for j,frame in enumerate(base_frames):
    f=frame.copy();f[ix['pelvis'],:3]+=offset;w=fk(f);base_world.append(w)
    contact=float(smooth((j/30-.60)/.70));goals={}
    for s in ('l','r'):
        p=raw_frames[j,raw_ix['hand_'+s],:3,3]*[100.,-100.,100.]
        x,y=p[0]+offset[0],p[1]+offset[1]-18.
        goals[s]=np.array([x,y,surface(x,y)+(p[2]-50.)+4.])
        release=float(smooth((j/30-3.3)/1.0))
        native=w[ix['hand_'+s],:3,3]
        resting=np.array([native[0],native[1]-4.,surface(native[0],native[1]-4.)+5.])
        goals[s]=goals[s]*(1-release)+resting*release+[0.,0.,2.*math.sin(math.pi*release)]
    pivot=w[ix['spine_01'],:3,3]
    chest=w[ix['spine_05'],:3,3]-w[ix['pelvis'],:3,3]
    lean=math.degrees(math.atan2(-chest[1],chest[2]))
    limit=max(0.,min(35.,88.-lean));chosen=0.;best=1e9
    for angle in np.linspace(0,limit,max(2,round(limit*2)+1)):
        turn=R.from_euler('x',angle,degrees=True).as_matrix();reach=[]
        for s in ('l','r'):
            a,b,c=[ix[n+'_'+s] for n in ('upperarm','lowerarm','hand')]
            shoulder=pivot+turn@(w[a,:3,3]-pivot);natural=pivot+turn@(w[c,:3,3]-pivot)
            target=natural*(1-contact)+goals[s]*contact
            length=np.linalg.norm(w[b,:3,3]-w[a,:3,3])+np.linalg.norm(w[c,:3,3]-w[b,:3,3])
            reach.append(np.linalg.norm(target-shoulder)/length)
        if max(reach)<best:best=max(reach);chosen=angle
        if max(reach)<=.955:break
    raw_angles.append(chosen*contact);hand_targets.append(goals)
angles=np.clip(savgol_filter(np.array(raw_angles),31,2),0.,35.)
for j in range(1,len(angles)):angles[j]=min(angles[j],angles[j-1]+2.)
for j in range(len(angles)-2,-1,-1):angles[j]=min(angles[j],angles[j+1]+2.)
core=[];diagnostics=[]
for j,frame in enumerate(base_frames):
    t=j/30;f=frame.copy();f[ix['pelvis'],:3]+=offset;w=base_world[j]
    f[ix['pelvis'],2]+=float(root_support(3.2+t))
    contact=float(smooth((t-.60)/.70));angle=max(0.,float(angles[j]));turn=R.from_euler('x',angle,degrees=True).as_matrix()
    for bone in torso_bones:rot(f,bone,turn@w[bone,:3,:3])
    for side in ('l','r'):
        now=fk(f);hand=ix['hand_'+side]
        target=now[hand,:3,3]*(1-contact)+hand_targets[j][side]*contact
        solve(f,side,('upperarm','lowerarm','hand'),target,w[hand,:3,:3],max_reach=.965)
        for digit in ('thumb','index','middle','ring','pinky'):
            for joint in (1,2,3):f[ix[f'{digit}_{joint:02d}_{side}'],3:7]=rest_fingers[ix[f'{digit}_{joint:02d}_{side}'],3:7]
    goals={};progress={}
    for side in ('l','r'):
        foot=ix['foot_'+side];target=w[foot,:3,3].copy();target[2]+=9.
        goals[side]=(target,w[foot,:3,:3])
        progress[side]=float(smooth((t-(1.1 if side=='l' else 1.067))/(1.10 if side=='l' else .95)))
    feet_clear(f,goals,progress)
    head_support(f,3.2+t)
    core.append(f);diagnostics.append({'source_time':t,'additional_torso_degrees':angle,'hand_contact':contact,'leg_lift':progress})

bridge=[blend(prefix[-1],core[0],float(smooth(i/12))) for i in range(1,13)]
enter=prefix+bridge+core[1:]
idle=[]
for i in range(121):
    f=enter[-1].copy();w=fk(f);angle=.12*math.sin(math.pi*i/120)**2
    for n in ('spine_03','spine_04','spine_05'):rot(f,ix[n],R.from_euler('x',angle,degrees=True).as_matrix()@w[ix[n],:3,:3])
    idle.append(f)
leave=[f.copy() for f in enter[::-1]]+[enter[0].copy() for _ in range(9)]
data={k:donor[k] for k in ('mesh','skeleton','names','parents','reference')};data['clips']={}
metadata={}
for phase,frames in [('Enter',enter),('Idle',idle),('Exit',leave)]:
    duration=(len(frames)-1)/30;role='Rest.Bed.'+phase;camera=[]
    data['clips'][role]={'duration':duration,'rate':30,'frames':np.array(frames).tolist()}
    for f in frames:
        head=fk(f)[ix['head']];eye=head[:3,3]+head[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0.,7.,6.]);camera.append([*eye.tolist(),0.,0.])
    metadata[role]={'duration':duration,'camera':camera}
types={'Bed':{**config['types']['Bed'],'entry_offset':[-32.,167.,0.],'entry_yaw':0.}}
config['types'].update(types);config['clips'].update(metadata)
(OUT/'authored.json').write_text(json.dumps(data,separators=(',',':')))
(OUT/'clip_metadata.json').write_text(json.dumps(metadata,separators=(',',':')))
(OUT/'type_updates.json').write_text(json.dumps(types,indent=2))
(OUT/'review_config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'fitting.json').write_text(json.dumps({'source_take':take['asset'],'source_duration':take['duration'],
    'offset':offset.tolist(),'seating_seconds':2.8,'bridge_seconds':.4,'samples':diagnostics},indent=2))
body=read(ROOT/'Content/ColdSteelData/player_body.json');roles=list(data['clips']);snapshot=OUT/'baseline_routes.json'
if not snapshot.exists():snapshot.write_text(json.dumps({'default':{r:body['clips'][r] for r in roles},'variants':{
    n:{'mesh':v['body_mesh'],'clips':{r:v['clips'][r] for r in roles}} for n,v in body.get('body_variants',{}).items() if v.get('ready')}},indent=2))
print('MESHY_BED_AUTHORED',[(k,v['duration']) for k,v in data['clips'].items()], 'torso',min(angles),max(angles),flush=True)
