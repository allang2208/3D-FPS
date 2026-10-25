"""Hand-over-hand bed scoots: planted palms, elbow loading and body follow-through."""
import copy,json,math,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'SourceAssets/FurnitureRest20261022/BedSupportedV9'
OUT=BASE.parent/'BedHandDriveV10';OUT.mkdir(parents=True,exist_ok=True)
ns={'__file__':str(ROOT/'Tools/FurnitureRest/bed_supported_v9.py')}
exec((ROOT/'Tools/FurnitureRest/bed_supported_v9.py').read_text().rsplit('for kind in kinds:',1)[0],ns)
fk,rot,ik,handrot,ix,ref,bind,blendrot,smooth,sample=[ns[k] for k in ('fk','rot','ik','handrot','ix','ref','bind','blendrot','smooth','sample')]
source=json.loads((BASE/'authored.json').read_text());result=copy.deepcopy(source);changed=[]
configs={n:json.loads((ROOT/'Content/ColdSteelData'/n).read_text(encoding='utf-8-sig')) for n in ('furniture_rest.json','apartment_furniture_rest.json')}
config=copy.deepcopy(configs['furniture_rest.json'])
for k in ('types','clips'):config[k].update(configs['apartment_furniture_rest.json'][k])
config['furniture']+=configs['apartment_furniture_rest.json']['furniture']
routes=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))['clips']
if not (OUT/'baseline_routes.json').exists():(OUT/'baseline_routes.json').write_text(json.dumps({k:routes[k] for k in source['clips']},indent=2))
geometry_index=json.loads((BASE/'Geometry/index.json').read_text())
body=json.loads((BASE/'ReviewSaved/body.json').read_text());points=np.array(body['positions']);ibind=np.linalg.inv(bind)
dom=[body['bone_names'][max(ws,key=lambda x:x[1])[0]] for ws in body['weights']]
hand_ids={s:np.array([j for j,b in enumerate(dom) if b.endswith('_'+s) and b.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_'))])[::2] for s in ('l','r')}
influences={}
for j,ws in enumerate(body['weights']):
    for b,weight in ws:influences.setdefault(ix[body['bone_names'][b]],[]).append((j,weight))
influences={b:(np.array(v)[:,0].astype(int),np.array(v)[:,1,None]) for b,v in influences.items()}
def skin(f):
    m=fk(f)@ibind;v=np.zeros_like(points)
    for b,(ids,weights) in influences.items():v[ids]+=(points[ids]@m[b,:3,:3].T+m[b,:3,3])*weights
    return v
def window(t,a,b):return smooth((t-a)/(b-a))
def unit(v):return v/max(np.linalg.norm(v),1e-8)
grid=np.linspace(0,1,2001);smooth_grid=np.array([smooth(x) for x in grid])
reports={}
only=sys.argv[sys.argv.index('--only')+1] if '--only' in sys.argv else None
if only and (OUT/'authored.json').exists():
    result=json.loads((OUT/'authored.json').read_text());changed=[r for r in result.get('changed_roles',[]) if r.split('.')[1]!=only]
    reports=json.loads((OUT/'choreography.json').read_text())
    for filename in configs:configs[filename]=json.loads((OUT/filename).read_text(encoding='utf-8'))
for kind in sorted({r.split('.')[1] for r in source['clips']}):
    if only and kind!=only:continue
    frames=np.array(source['clips'][f'Rest.{kind}.Enter']['frames']);spec=config['types'][kind]
    yaw0=spec['entry_yaw'];height=spec['surface_height'];lead='l' if yaw0<0 else 'r';trail='r' if lead=='l' else 'l'
    distance=np.linalg.norm(fk(sample(frames,3.8))[ix['pelvis'],:2,3]-fk(sample(frames,2.65))[ix['pelvis'],:2,3])
    steps=3 if distance>65 else 2;pushes=[(2.95+.9*j,3.5+.9*j) for j in range(steps)]
    pivot_end=pushes[-1][1];duration=6.7+.9*(steps-2)
    def progress(t):return sum(window(t,a,b) for a,b in pushes)/steps
    def source_time(t):
        if t<=2.45:return t
        if t<2.85:return 2.45+.2*window(t,2.45,2.85)
        if t<=pivot_end:return 2.65+1.15*float(np.interp(progress(t),smooth_grid,grid))
        if t<pivot_end+.4:return 3.8
        if t<pivot_end+1.65:return 3.8+1.25*window(t,pivot_end+.4,pivot_end+1.65)
        return 5.05+.75*window(t,pivot_end+1.65,duration)
    def turn_for(t):return R.from_euler('z',yaw0*(1-progress(t)),degrees=True).as_matrix()
    def base_pose(t):
        f=sample(frames,source_time(t));w=fk(f);turn=turn_for(t)
        envelope=window(t,2.05,2.65)*(1-window(t,pivot_end+.4,pivot_end+1.))
        load=sum(math.sin(math.pi*window(t,a-.32,a+.2))**2 for a,b in pushes)
        roll=0.
        for j,(a,b) in enumerate(pushes):
            side=lead if j%2==0 else trail;sgn=1 if side=='l' else -1
            roll+=sgn*3*math.sin(math.pi*window(t,a-.5,b+.2))**2
        lean=((16 if kind=='Ward' else 10)+4*load)*envelope
        if kind=='Bunk':lean*=.35;roll*=.55
        for bone,factor in [('spine_01',.35),('spine_02',.55),('spine_03',.75),('spine_04',.9),('spine_05',1),('neck_01',.5),('neck_02',-.1),('head',-.6)]:
            delta=turn@R.from_euler('yx',[roll*factor,lean*factor],degrees=True).as_matrix()@turn.T
            rot(f,ix[bone],delta@w[ix[bone],:3,:3])
        if kind=='Ward' and t>pivot_end:
            # Releasing into the old pose must keep its mattress contacts;
            # otherwise the extra shoulder lean drags the free fingers down.
            for side in ('l','r'):
                hand=ix['hand_'+side]
                ik(f,side,('upperarm','lowerarm','hand'),w[hand,:3,3],w[ix['lowerarm_'+side],:3,3])
                rot(f,hand,w[hand,:3,:3])
        return f
    profile=next(p for p in config['furniture'] if any(s['kind']==kind for s in p['slots']))
    slot=next(s for s in profile['slots'] if s['kind']==kind);scale=np.array(profile.get('scale',[1,1,1]))
    offset=np.array(slot['seat'])*scale;offset[2]-=height
    furniture_turn=R.from_euler('z',slot['yaw']-90,degrees=True).as_matrix()
    geometry=json.loads(Path(geometry_index[profile['mesh']]).read_text());vs=(np.array(geometry['positions'])*scale-offset)@furniture_turn
    triangles=vs[np.array(geometry['triangles'],int)];a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    denominator=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1]);valid=np.abs(denominator)>1e-6
    low=triangles.min(axis=1);high=triangles.max(axis=1)
    candidates=valid&(high[:,2]>height-15)&(low[:,2]<height+22)
    def surface(xy):
        ids=np.flatnonzero(candidates&(low[:,0]<=xy[0]+1e-4)&(high[:,0]>=xy[0]-1e-4)&(low[:,1]<=xy[1]+1e-4)&(high[:,1]>=xy[1]-1e-4))
        if not len(ids):return None
        av,bv,cv=a[ids],b[ids],c[ids]
        aa=((bv[:,1]-cv[:,1])*(xy[0]-cv[:,0])+(cv[:,0]-bv[:,0])*(xy[1]-cv[:,1]))/denominator[ids]
        bb=((cv[:,1]-av[:,1])*(xy[0]-cv[:,0])+(av[:,0]-cv[:,0])*(xy[1]-cv[:,1]))/denominator[ids]
        cc=1-aa-bb;z=aa*av[:,2]+bb*bv[:,2]+cc*cv[:,2]
        mask=(aa>=-1e-5)&(bb>=-1e-5)&(cc>=-1e-5)&(z>height-15)&(z<height+22)
        return float(z[mask].max()) if mask.any() else None
    brace=sample(frames,2.45);finger_bones={s:[i for i,n in enumerate(source['names']) if n.endswith('_'+s) and n.startswith(('thumb','index_','middle','ring','pinky'))] for s in ('l','r')}
    events={s:[] for s in ('l','r')};anchors={};metrics=[]
    for side in ('l','r'):
        w=fk(sample(frames,2.35));anchors[(side,0)]={'point':w[ix['hand_'+side],:3,3].copy(),'rotation':w[ix['hand_'+side],:3,:3].copy()}
    last_support=lead if (steps-1)%2==0 else trail
    release_start={s:pivot_end+(.1 if s==last_support else -.45) for s in ('l','r')}
    # Every new contact is fixed in furniture coordinates. The next hand can
    # travel while this hand continues carrying the body.
    for k in range(1,steps+1):
        side=lead if k%2 else trail;start=2.35 if k==1 else pushes[k-2][0]+.05;finish=start+.5
        next_start=pushes[k][0]+.05 if k<len(pushes) else release_start[side]
        until=min(next_start,release_start[side]);until=max(until,finish+.05)
        if finish>release_start[side]:continue
        events[side].append((start,finish,k))
        times=np.linspace(finish,until,13);samples=[base_pose(t) for t in times];worlds=np.array([fk(f) for f in samples])
        shoulder=worlds[:,ix['upperarm_'+side],:3,3];hips=worlds[:,ix['pelvis'],:3,3]
        length=np.linalg.norm(bind[ix['lowerarm_'+side],:3,3]-bind[ix['upperarm_'+side],:3,3])+np.linalg.norm(bind[ix['hand_'+side],:3,3]-bind[ix['lowerarm_'+side],:3,3])
        sign=1 if side=='l' else -1;turn=turn_for(finish)
        lateral=np.array([(turn_for(t)@np.array([sign,0.,0.]))[:2] for t in times])
        desired=shoulder[len(shoulder)//2,:2]+(turn_for(times[len(times)//2])@np.array([sign*14.,-5.,0.]))[:2]
        offset_z=5.
        def objective(xy):
            z=surface(xy)
            if z is None:return 1e7+float(np.sum((xy-desired)**2))
            target=np.array([*xy,z+offset_z]);dist=np.linalg.norm(shoulder-target,axis=1)
            hipgap=np.linalg.norm(hips[:,:2]-xy,axis=1)
            sidegap=np.sum((xy-hips[:,:2])*lateral,axis=1)
            return float(180*np.sum(np.maximum(dist-length*.96,0)**2)+.025*np.sum((xy-desired)**2)+.8*np.sum(np.maximum(20-hipgap,0)**2)+.5*np.sum(np.maximum(12-sidegap,0)**2)+.15*(dist[0]-length*.87)**2)
        trial=min((desired+[x,y] for x in (-16,-8,0,8,16) for y in (-16,-8,0,8,16)),key=objective)
        fit=minimize(objective,trial,method='Nelder-Mead',options={'maxiter':160,'xatol':.03,'fatol':.01})
        xy=fit.x;target=np.array([*xy,surface(xy)+offset_z]);f=base_pose(finish)
        for bone in finger_bones[side]:f[bone,3:7]=brace[bone,3:7]
        handrot(f,side,turn@np.array([sign*.45,-.89,0]),np.array([0.,0.,-1.]));q=fk(f)[ix['hand_'+side],:3,:3].copy()
        for iteration in range(3):
            for _ in range(2):
                w=fk(f);pole=w[ix['upperarm_'+side],:3,3]+turn@np.array([sign*27.,-10.,0. if kind=='Bunk' else -24.])
                ik(f,side,('upperarm','lowerarm','hand'),target,pole);rot(f,ix['hand_'+side],q)
                v=skin(f)[hand_ids[side]];corrections=[z+.45-p[2] for p in v if (z:=surface(p[:2])) is not None]
                if corrections:target[2]+=max(corrections)
            offset_z=target[2]-surface(xy)
            if iteration<2:
                fit=minimize(objective,xy,method='Nelder-Mead',options={'maxiter':100,'xatol':.03,'fatol':.01})
                xy=fit.x;target=np.array([*xy,surface(xy)+offset_z])
        anchors[(side,k)]={'point':target,'rotation':q}
        metrics.append({'side':side,'reach_start':start,'plant':finish,'hold_until':until,'anchor':target.tolist(),'maximum_reach_ratio':float(np.linalg.norm(shoulder-target,axis=1).max()/length)})
    takes=[];contact_rows=[]
    for j in range(round(duration*30)+1):
        t=j/30;f=base_pose(t);original=f.copy();world=fk(f);turn=turn_for(t);row={'t':t,'source_t':source_time(t),'contacts':{}}
        if t>2.1:
            for side,sign in [('l',1),('r',-1)]:
                hand=ix['hand_'+side];elbow=ix['lowerarm_'+side];current=anchors[(side,0)];target=current['point'].copy();q=current['rotation'];moving=False
                for start,finish,key in events[side]:
                    nxt=anchors[(side,key)]
                    if t<start:break
                    if t<finish:
                        u=window(t,start,finish);target=current['point']*(1-u)+nxt['point']*u
                        target+=np.array([sign*3.,0.,15. if kind=='Bunk' else 11.])*math.sin(math.pi*u)
                        q=blendrot(current['rotation'],nxt['rotation'],u);moving=True;break
                    current=nxt;target=current['point'].copy();q=current['rotation']
                release=window(t,release_start[side],release_start[side]+.55)
                if release>=1:continue
                target=target*(1-release)+world[hand,:3,3]*release
                outward=15. if kind in ('BedKing','Ward','Bunk') else 3.
                arc=turn@np.array([sign*outward,0.,18. if kind=='Ward' else 10.])
                target+=arc*math.sin(math.pi*release);q=blendrot(q,world[hand,:3,:3],release)
                active=window(t,2.1,2.35);target=world[hand,:3,3]*(1-active)+target*active;q=blendrot(world[hand,:3,:3],q,active)
                for bone in finger_bones[side]:f[bone,3:7]=R.from_matrix(blendrot(R.from_quat(brace[bone,3:7]).as_matrix(),R.from_quat(original[bone,3:7]).as_matrix(),release)).as_quat()
                pole=world[ix['upperarm_'+side],:3,3]+turn@np.array([sign*27.,-10.,0. if kind=='Bunk' else -24.])
                pole=pole*(1-release)+world[elbow,:3,3]*release
                ik(f,side,('upperarm','lowerarm','hand'),target,pole);rot(f,hand,q)
                actual=fk(f)[hand,:3,3]
                row['contacts'][side]={'planted':not moving and release==0 and active==1,'target':target.tolist(),'error_cm':float(np.linalg.norm(actual-target))}
        takes.append(f.tolist());contact_rows.append(row)
    takes[0]=source['clips'][f'Rest.{kind}.Enter']['frames'][0];takes[-1]=source['clips'][f'Rest.{kind}.Idle']['frames'][0]
    for phase,pose_frames in [('Enter',takes),('Exit',copy.deepcopy(takes[::-1])+[copy.deepcopy(takes[0]) for _ in range(9)])]:
        role=f'Rest.{kind}.{phase}';camera=[]
        for f in pose_frames:
            h=fk(np.array(f))[ix['head']];eye=h[:3,3]+h[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0,7,6]);camera.append([*eye.tolist(),0.,0.])
        length=(len(pose_frames)-1)/30;result['clips'][role]={'rate':30,'duration':length,'frames':pose_frames}
        configs['apartment_furniture_rest.json' if kind=='ApartmentBed' else 'furniture_rest.json']['clips'][role]={'duration':length,'camera':camera};changed.append(role)
    reports[kind]={'steps':steps,'pushes':pushes,'anchors':metrics,'frames':contact_rows}
    print('HAND_DRIVE_AUTHORED',kind,'steps',steps,'max reach',max(x['maximum_reach_ratio'] for x in metrics),'max contact error',max((r['error_cm'] for row in contact_rows for r in row['contacts'].values() if r['planted']),default=0),flush=True)
result['changed_roles']=changed;(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')))
(OUT/'choreography.json').write_text(json.dumps(reports,indent=2))
for n,cfg in configs.items():(OUT/n).write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
merged=copy.deepcopy(configs['furniture_rest.json'])
for k in ('types','clips'):merged[k].update(configs['apartment_furniture_rest.json'][k])
merged['furniture']+=configs['apartment_furniture_rest.json']['furniture'];(OUT/'review_config.json').write_text(json.dumps(merged,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'Geometry').mkdir(exist_ok=True);(OUT/'Geometry/index.json').write_bytes((BASE/'Geometry/index.json').read_bytes())
(OUT/'ReviewSaved').mkdir(exist_ok=True)
for n in ('body.json','head.json'):(OUT/'ReviewSaved'/n).write_bytes((BASE/'ReviewSaved'/n).read_bytes())
