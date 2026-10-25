"""Continuous, asymmetric bed entry; reference: C-MHAD Figure 6, not copied motion."""
import copy,json,math,shutil
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R,Slerp

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/FurnitureRest20261022/ApartmentLegTransfer20261024R2'
BASE=OUT.parent/'MeshyApartmentBed20261024'
OUT.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
ns={'__file__':str(ROOT/'Tools/FurnitureRest/meshy_bed.py')}
exec((ROOT/'Tools/FurnitureRest/meshy_bed.py').read_text().split('prefix=[]')[0],ns)
fk,rot,ix,bind,unit,basis,smooth,blend,solve=[ns[k] for k in ('fk','rot','ix','bind','unit','basis','smooth','blend','solve')]
source=read(BASE/'authored.json');old=np.asarray(source['clips']['Rest.ApartmentBed.Enter']['frames'])
def sample(t):
    v=np.clip(t*30,0,len(old)-1);j=min(int(v),len(old)-2)
    return blend(old[j],old[j+1],v-j)
def mixrot(a,b,t):return Slerp([0,1],R.from_matrix([a,b]))(float(t)).as_matrix()
seat=fk(sample(1.8));calibration={}
for s in ('l','r'):
    a,b,c=[ix[n+'_'+s] for n in ('thigh','calf','foot')]
    h,k,e=seat[[a,b,c],:3,3];u,v=k-h,e-k;n=unit(np.cross(u,v))
    calibration[s]=(np.linalg.norm(u),np.linalg.norm(v),basis(u,n).T@seat[a,:3,:3],basis(v,n).T@seat[b,:3,:3],unit(u-unit(e-h)*(u@unit(e-h))))
def leg(f,s,target,pole,end_rotation):
    a,b,c=[ix[n+'_'+s] for n in ('thigh','calf','foot')];h=fk(f)[a,:3,3]
    l1,l2,cu,cl,_=calibration[s];axis=unit(target-h);d=np.clip(np.linalg.norm(target-h),abs(l1-l2)+.05,l1+l2-.35)
    bend=unit(pole-axis*(pole@axis));along=(l1*l1+d*d-l2*l2)/(2*d)
    k=h+axis*along+bend*math.sqrt(max(0.,l1*l1-along*along));e=h+axis*d;n=unit(np.cross(k-h,e-k))
    rot(f,a,basis(k-h,n)@cu);rot(f,b,basis(e-k,n)@cl);rot(f,c,end_rotation)

retime=PchipInterpolator([0,1.2,1.75,2.1,2.45,3.0],[0,1.8,2.8,3.45,4.15,4.5])
def transfer(t):
    f=sample(float(retime(t)))
    if t<=1.2:return f
    support=fk(f)
    across=unit((support[ix['thigh_l'],:3,3]-support[ix['thigh_r'],:3,3])*[1,1,0])
    source_yaw=math.atan2(across[1],across[0])
    pivot=float(smooth((t-1.65)/1.35))
    turn_delta=R.from_euler('z',math.pi/2*(1-pivot)-source_yaw).as_matrix()
    f[ix['pelvis'],0]=-91.+51.*pivot
    rot(f,ix['pelvis'],turn_delta@support[ix['pelvis'],:3,:3])
    f[ix['pelvis'],2]+=3.2*float(smooth((t-1.2)/.2)*(1-smooth((t-1.75)/.45)))
    for s in ('l','r'):
        hand=ix['hand_'+s];solve(f,s,('upperarm','lowerarm','hand'),support[hand,:3,3],support[hand,:3,:3])
    w=fk(f);across=unit((w[ix['thigh_l'],:3,3]-w[ix['thigh_r'],:3,3])*[1,1,0])
    yaw=math.atan2(across[1],across[0]);turn=R.from_euler('z',yaw).as_matrix();relative=R.from_euler('z',yaw-math.pi/2).as_matrix()
    for s,sign,delay in [('l',1,0.),('r',-1,.14)]:
        rise=float(smooth((t-1.2-delay)/.56));extend=float(smooth((t-2.25-delay)/.75))
        forward=39.+20.*math.sin(math.pi*rise)+(19. if s=='l' else -5.)*extend
        target=w[ix['pelvis'],:3,3]+turn@np.array([sign*13.,forward,0.])
        target[2]=seat[ix['foot_'+s],2,3]*(1-rise)+(86.-(6. if s=='l' else -1.)*extend)*rise
        angle=math.radians(20.+60.*rise)
        pole=unit(relative@calibration[s][4]*(1-rise)+turn@np.array([0.,math.cos(angle),math.sin(angle)])*rise)
        foot=mixrot(relative@seat[ix['foot_'+s],:3,:3],turn@R.from_euler('x',12.,degrees=True).as_matrix()@bind[ix['foot_'+s],:3,:3],rise)
        # Preserve the retimed reference before the delayed foot starts lifting.
        original=f.copy();leg(f,s,target,pole,foot)
        amount=float(smooth((t-1.2-delay)/.18))
        for n in ('thigh','calf','foot'):
            b=ix[n+'_'+s];f[b]=blend(original,f,amount)[b]
    return f

join_start=transfer(3.0);join_end=sample(8.1);enter=[]
for j in range(202):
    t=j/30
    if t<=3.:f=transfer(t)
    elif t<3.6:f=blend(join_start,join_end,float(smooth((t-3.)/.6)))
    else:f=sample(8.1+(t-3.6)*(11.-8.1)/(6.7-3.6))
    enter.append(f)
idle=np.asarray(source['clips']['Rest.ApartmentBed.Idle']['frames'])
enter[-1]=idle[0].copy()
exit_frames=[f.copy() for f in enter[::-1]]+[enter[0].copy() for _ in range(9)]
data={k:source[k] for k in ('mesh','skeleton','names','parents','reference')};data['clips']={};metadata={}
data['changed_roles']=['Rest.ApartmentBed.Enter','Rest.ApartmentBed.Exit']
for phase,frames in [('Enter',enter),('Idle',idle),('Exit',exit_frames)]:
    role='Rest.ApartmentBed.'+phase;duration=(len(frames)-1)/30;camera=[]
    for f in frames:
        h=fk(f)[ix['head']];eye=h[:3,3]+h[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0.,7.,6.]);camera.append([*eye.tolist(),0.,0.])
    data['clips'][role]={'duration':duration,'rate':30,'frames':np.asarray(frames).tolist()}
    if role in data['changed_roles']:metadata[role]={'duration':duration,'camera':camera}
apartment=read(ROOT/'Content/ColdSteelData/apartment_furniture_rest.json');main=read(ROOT/'Content/ColdSteelData/furniture_rest.json')
candidate=copy.deepcopy(apartment);candidate['clips'].update(metadata)
review=copy.deepcopy(main);review['types'].update(candidate['types']);review['clips'].update(candidate['clips']);review['furniture'].extend(reversed(candidate['furniture']))
body=read(ROOT/'Content/ColdSteelData/player_body.json');roles=data['changed_roles']
snapshots={'baseline.json':{'apartment':apartment},'baseline_routes.json':{'default':{r:body['clips'][r] for r in roles},'variants':{n:{'mesh':v['body_mesh'],'clips':{r:v['clips'][r] for r in roles}} for n,v in body['body_variants'].items() if v.get('ready')}}}
for name,value in snapshots.items():
    if not (OUT/name).exists():(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
for name,value in [('authored.json',data),('clip_metadata.json',metadata),('review_config.json',review),('apartment_candidate.json',candidate)]:
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
shutil.copytree(BASE/'Geometry',OUT/'Geometry',dirs_exist_ok=True);(OUT/'ReviewSaved').mkdir(exist_ok=True)
for name in ('body.json','head.json'):shutil.copy2(BASE/'ReviewSaved'/name,OUT/'ReviewSaved'/name)
(OUT/'References').mkdir(exist_ok=True)
(OUT/'References/reference.json').write_text(json.dumps({'source':'https://personal.utdallas.edu/~kehtar/C-MHAD.html','paper':'https://www.mdpi.com/1424-8220/20/10/2905','observed':'Published Figure 6 video-frame sequences, rows c/f; full AVI located but not played.','local_reference':'../ApartmentLegTransfer20261024/References/c-mhad-transitions.png','application':'Original authored curves: overlap knee flexion, continuous pelvic turn and supported torso descent; no dataset motion imported.','duration_before':11.,'duration_after':6.7},indent=2),encoding='utf-8')
print('APARTMENT_LEG_TRANSFER_AUTHORED',[(k,v['duration']) for k,v in data['clips'].items()],flush=True)
