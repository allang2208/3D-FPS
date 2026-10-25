"""Fit the approved side-entry choreography to each remaining interactive bed type."""
import copy,json,math,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/FurnitureRest20261022/BedFamilyReuse20261024';OUT.mkdir(parents=True,exist_ok=True)
BASE=OUT.parent/'ApartmentFastRest20261024R2'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
source=read(BASE/'ReviewSaved/saved_poses.json');timing=read(BASE/'authored.json')['native_retime']['samples']['Rest.ApartmentBed.Enter']
ns={'__file__':str(ROOT/'Tools/FurnitureRest/meshy_bed.py')}
exec((ROOT/'Tools/FurnitureRest/meshy_bed.py').read_text().split('prefix=[]')[0],ns)
fk,ix,bind,rot,solve,smooth,blend,unit,basis=[ns[n] for n in ('fk','ix','bind','rot','solve','smooth','blend','unit','basis')]
config=read(ROOT/'Content/ColdSteelData/furniture_rest.json');body=read(ROOT/'Content/ColdSteelData/player_body.json')
legacy=read(OUT.parent/'BedHandDriveV10/authored.json')
ordinary=read(OUT.parent/'MeshyBedSupportedHands20261024/authored.json')
core_names=['pelvis','spine_01','spine_02','spine_03','spine_04','spine_05','neck_01','neck_02','head']
core_ids=[ix[n] for n in core_names]
body_geo=read(BASE/'ReviewSaved/body.json');body_points=np.asarray(body_geo['positions']);inverse_bind=np.linalg.inv(bind);foot_skin={}
for side in ('l','r'):
    ids=[]
    for vertex,weights in enumerate(body_geo['weights']):
        bone=ix[body_geo['bone_names'][max(weights,key=lambda item:item[1])[0]]]
        while bone>=0 and bone!=ix['foot_'+side]:bone=source['parents'][bone]
        if bone>=0:ids.append(vertex)
    influences={}
    for local,vertex in enumerate(ids):
        for bone,weight in body_geo['weights'][vertex]:influences.setdefault(ix[body_geo['bone_names'][bone]],[]).append((local,weight))
    foot_skin[side]=(body_points[ids],{bone:(np.asarray(rows)[:,0].astype(int),np.asarray(rows)[:,1,None]) for bone,rows in influences.items()})
def foot_vertices(f,side):
    points,influences=foot_skin[side];matrices=fk(f)@inverse_bind;result=np.zeros_like(points)
    for bone,(ids,weights) in influences.items():result[ids]+=(points[ids]@matrices[bone,:3,:3].T+matrices[bone,:3,3])*weights
    return result
params={
    'Bed':{'seat_x':-67.,'rest_x':-30.,'rest_y':-10.},
    'BedKing':{'seat_x':80.,'rest_x':40.,'rest_y':-10.},
    'Hospital':{'seat_x':43.,'rest_x':0.,'rest_y':16.},
    'Ward':{'seat_x':58.,'rest_x':0.,'rest_y':20.},
    'Bunk':{'seat_x':-35.,'rest_x':0.,'rest_y':6.,'duck_degrees':62.},
}
if (OUT/'fit_parameters.json').exists():params=read(OUT/'fit_parameters.json')
else:(OUT/'fit_parameters.json').write_text(json.dumps(params,indent=2))
inventory={k:[p for p in config['furniture'] if any(s['kind']==k for s in p['slots'])] for k in params}
if set(params)!={k for k,v in config['types'].items() if v.get('lying')}:raise RuntimeError('Interactive bed inventory changed.')
geo_base=OUT.parent/'BedSupportedV9/Geometry';old_index=read(geo_base/'index.json');index={}
(OUT/'Geometry').mkdir(exist_ok=True);(OUT/'ReviewSaved').mkdir(exist_ok=True)
for name in ('body.json','head.json'):shutil.copy2(BASE/'ReviewSaved'/name,OUT/'ReviewSaved'/name)
surfaces={}
for kind,models in inventory.items():
    tables=[];height=config['types'][kind]['surface_height']
    for profile in models:
        slot=next(s for s in profile['slots'] if s['kind']==kind);scale=np.asarray(profile.get('scale',[1,1,1]));offset=np.asarray(slot['seat'],float)*scale;offset[2]-=height
        turn=R.from_euler('z',slot['yaw']-90,degrees=True).as_matrix();g=read(geo_base/old_index[profile['mesh']])
        name=str(len(index))+'.json';(OUT/'Geometry'/name).write_text(json.dumps(g,separators=(',',':')));index[profile['mesh']]=name
        v=(np.asarray(g['positions'])*scale-offset)@turn;tri=v[np.asarray(g['triangles'],int)]
        a,b,c=tri[:,0],tri[:,1],tri[:,2];den=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1])
        mask=(abs(den)>1e-8)&(tri.max(axis=1)[:,2]>height-20)&(tri.min(axis=1)[:,2]<height+30)
        tables.append((a[mask],b[mask],c[mask],den[mask]))
    surfaces[kind]=tables
def surface(kind,x,y):
    height=config['types'][kind]['surface_height'];values=[]
    for a,b,c,den in surfaces[kind]:
        u=((b[:,1]-c[:,1])*(x-c[:,0])+(c[:,0]-b[:,0])*(y-c[:,1]))/den
        v=((c[:,1]-a[:,1])*(x-c[:,0])+(a[:,0]-c[:,0])*(y-c[:,1]))/den
        z=u*a[:,2]+v*b[:,2]+(1-u-v)*c[:,2];mask=(u>=0)&(v>=0)&(u+v<=1)&(z>height-20)&(z<height+30)
        if mask.any():values.append(float(z[mask].max()))
    return max(values) if values else None

def elbow_clearance(f,kind,side):
    """Rotate the elbow bend plane above a raised blanket, keeping the palm fixed."""
    w=fk(f);a,b,c=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')];h,k,e=w[[a,b,c],:3,3]
    lift=0.
    for u in (0.,.25,.5,.65):
        point=k*(1-u)+e*u;top=surface(kind,*point[:2])
        if top is not None:lift=max(lift,(top+5.0-point[2])/(1-u))
    if lift<=0:return
    axis=unit(e-h);center=h+axis*((k-h)@axis);bend=k-center
    desired=bend+np.array([0.,0.,min(lift,8.)]);desired-=axis*(desired@axis)
    angle=math.atan2(axis@np.cross(bend,desired),bend@desired);angle=float(np.clip(angle,-math.pi/4,math.pi/4))
    elbow=center+R.from_rotvec(axis*angle).as_matrix()@bend
    oldnormal=unit(np.cross(k-h,e-k));normal=unit(np.cross(elbow-h,e-elbow))
    rot(f,a,basis(elbow-h,normal)@basis(k-h,oldnormal).T@w[a,:3,:3])
    rot(f,b,basis(e-elbow,normal)@basis(e-k,oldnormal).T@w[b,:3,:3]);rot(f,c,w[c,:3,:3])

mirror=np.diag([-1.,1.,1.]);pairs=[ix.get(n[:-2]+('_r' if n.endswith('_l') else '_l'),i) if n.endswith(('_l','_r')) else i for i,n in enumerate(source['names'])]
def mirrored(f):
    w=fk(f);out=f.copy();wr=np.asarray([mirror@w[j,:3,:3]@bind[j,:3,:3].T@mirror@bind[i,:3,:3] for i,j in enumerate(pairs)])
    out[ix['pelvis'],0]*=-1
    for i,p in enumerate(source['parents']):out[i,3:7]=R.from_matrix(wr[p].T@wr[i] if p>=0 else wr[i]).as_quat()
    return out
entry=np.asarray(source['clips']['Rest.ApartmentBed.Enter']['frames']);idle=np.asarray(source['clips']['Rest.ApartmentBed.Idle']['frames'])
mirrored_entry=[mirrored(f) for f in entry];mirrored_idle=[mirrored(f) for f in idle]
result={k:source[k] for k in ('mesh','skeleton','names','parents','reference')};result['clips']={};metadata={};type_updates={}
for kind,p in params.items():
    right=p['seat_x']>0;sign=-1. if right else 1.;height=config['types'][kind]['surface_height'];dz=height-67.
    donor_entry=mirrored_entry if right else entry;donor_idle=mirrored_idle if right else idle
    final=fk(donor_idle[0])[ix['pelvis'],:3,3];seat_dx=p['seat_x']-(-91.*sign);rest_dx=p['rest_x']-final[0];dy=p['rest_y']-final[1]
    if kind=='BedKing':calibrated=mirrored(np.asarray(ordinary['clips']['Rest.Bed.Idle']['frames'][0]))
    else:calibrated=np.asarray((ordinary if kind=='Bed' else legacy)['clips'][f'Rest.{kind}.Idle']['frames'][0])
    core_delta=R.from_quat(calibrated[core_ids,3:7])*R.from_quat(np.asarray(donor_idle[0])[core_ids,3:7]).inv()
    rest_z_delta=float(calibrated[ix['pelvis'],2]-final[2]-dz)+p.get('root_z',0.)
    contact_windows={s:[] for s in ('l','r')}
    donor_world=np.asarray([fk(f) for f in donor_entry])
    for side in ('l','r'):
        path=donor_world[:,ix['hand_'+side],:3,3];still=np.linalg.norm(np.diff(path,axis=0),axis=1)<.07;start=None
        for j,planted in enumerate([*still,False]):
            eligible=planted and .65<=j/30<=1.95 and 58.<path[j,2]<90.
            if eligible and start is None:start=j
            if not eligible and start is not None:
                if j-start>=3:
                    a,b=start/30,j/30;anchor=path[start:j+1].mean(axis=0)+[rest_dx if b>1.2 else seat_dx,dy,dz]
                    contact_windows[side].append((a,b,anchor))
                start=None
    def fit(original,t,source_t,resting=False):
        f=np.array(original).copy();pivot=1. if resting else float(smooth((source_t-1.65)/1.35))
        lift=1. if resting else float(smooth((t-.30)/.45))
        f[ix['pelvis'],:3]+=[seat_dx*(1-pivot)+rest_dx*pivot,dy,dz*lift]
        w=fk(f);goals={s:(w[ix['hand_'+s],:3,3].copy(),w[ix['hand_'+s],:3,:3].copy()) for s in ('l','r')}
        feet={s:(w[ix['foot_'+s],:3,3].copy(),w[ix['foot_'+s],:3,:3].copy()) for s in ('l','r')}
        if not resting:
            for side in ('l','r'):
                for a,b,anchor in contact_windows[side]:
                    weight=float(smooth((t-a+.12)/.12)*(1-smooth((t-b)/.12)))
                    if weight>0:goals[side]=(goals[side][0]*(1-weight)+anchor*weight,goals[side][1])
        if kind=='Bunk' and not resting:
            across=w[ix['thigh_l'],:3,3]-w[ix['thigh_r'],:3,3];across/=np.linalg.norm(across)
            spread=float(smooth((t-.23)/.12)*(1-smooth((t-.60)/.20)))
            for side,sgn in [('l',1.),('r',-1.)]:
                goal,q=goals[side];lateral=float((goal-w[ix['pelvis'],:3,3])@across)*sgn
                goals[side]=(goal+across*sgn*max(0.,28.-lateral)*spread,q)
        settle=1. if resting else float(smooth((t-p.get('settle_start',1.90))/p.get('settle_duration',1.20)))
        f[ix['pelvis'],2]+=rest_z_delta*settle+p.get('seat_lift',0.)*lift*(1-settle)
        if not resting:f[ix['pelvis'],2]+=p.get('edge_lift',0.)*float(smooth((t-.45)/.10)*(1-smooth((t-.62)/.15)))
        sculpted=f.copy();sculpted[core_ids,3:7]=(core_delta*R.from_quat(f[core_ids,3:7])).as_quat()
        f[core_ids,3:7]=blend(f,sculpted,settle)[core_ids,3:7]
        w=fk(f)
        if kind=='Bunk' and not resting:
            duck=float(smooth((t-.18)/.30)*(1-smooth((t-2.25)/.5)))
            # Lower the hips before the head crosses below the upper bunk.
            # Retain the original feet and palms as support targets.
            crouch=duck*float(1-smooth((t-.65)/.45))
            f[ix['pelvis'],2]-=max(0.,f[ix['pelvis'],2]-(height+10.))*crouch
            across=w[ix['thigh_l'],:3,3]-w[ix['thigh_r'],:3,3];yaw=math.atan2(across[1],across[0]);turn=R.from_euler('z',yaw).as_matrix()
            for bone,factor in [('pelvis',.38),('spine_01',.60),('spine_02',.75),('spine_03',.86),('spine_04',.94),('spine_05',1.),('neck_01',1.),('neck_02',1.),('head',1.)]:
                b=ix[bone];up=turn.T@w[b,:3,:3]@bind[b,:3,:3].T@np.array([0.,0.,1.]);pitch=math.degrees(math.atan2(-up[1],up[2]));extra=max(0.,p['duck_degrees']*factor-pitch)*duck
                rot(f,b,turn@R.from_euler('x',extra,degrees=True).as_matrix()@turn.T@w[b,:3,:3])
        if p.get('neck_degrees'):
            amount=1. if resting else float(smooth((t-2.55)/.65));current=fk(f)
            for bone in ('neck_01','neck_02'):rot(f,ix[bone],R.from_euler('x',p['neck_degrees']*amount,degrees=True).as_matrix()@current[ix[bone],:3,:3])
            rot(f,ix['head'],current[ix['head'],:3,:3])
        for side in ('l','r'):
            goal,q=feet[side];goal[2]=max(goal[2],9.0);contact=1. if resting else float(smooth((t-.85)/.35))
            goal[1]-=p.get('foot_retract',0.)*contact;top=surface(kind,*goal[:2])
            if p.get('foot_pitch'):
                amount=1. if resting else float(smooth((t-p.get('foot_pitch_start',1.2))/.65))
                cw=fk(f);across=cw[ix['thigh_l'],:3,3]-cw[ix['thigh_r'],:3,3];turn=R.from_euler('z',math.atan2(across[1],across[0])).as_matrix()
                q=turn@R.from_euler('x',p['foot_pitch']*amount,degrees=True).as_matrix()@turn.T@q
            if top is not None and contact>0:
                goal[2]+=max(0.,top+p.get('foot_clearance',10.8)-goal[2])*contact
            if kind=='Bunk' or p.get('foot_pitch') or np.linalg.norm(goal-fk(f)[ix['foot_'+side],:3,3])>1e-5:solve(f,side,('thigh','calf','foot'),goal,q)
            if p.get('foot_end_limit') and contact>0:
                for _ in range(2):
                    excess=float(foot_vertices(f,side)[:,1].max()-p['foot_end_limit'])
                    if excess<=.02:break
                    goal[1]-=excess*contact;solve(f,side,('thigh','calf','foot'),goal,q)
            goal,q=goals[side];top=surface(kind,*goal[:2])
            if side=='l' and p.get('left_hand_outset'):
                amount=1. if resting else float(smooth((t-1.85)/.30))
                goal[0]+=p['left_hand_outset']*amount;top=surface(kind,*goal[:2])
            if top is not None and height-8<goal[2]<height+15:goal[2]=max(goal[2],top+p.get('hand_clearance',5.5))
            if kind=='Bunk' or np.linalg.norm(goal-fk(f)[ix['hand_'+side],:3,3])>1e-5:solve(f,side,('upperarm','lowerarm','hand'),goal,q)
            if kind=='Ward':elbow_clearance(f,kind,side)
        return f
    entered=[fit(f,j/30,timing[j]) for j,f in enumerate(donor_entry)]
    resting=[fit(f,3.3,6.7,True) for f in donor_idle];entered[-1]=resting[0].copy()
    leaving=[f.copy() for f in entered[::-1]]+[entered[0].copy() for _ in range(3)]
    for phase,frames in [('Enter',entered),('Idle',resting),('Exit',leaving)]:
        role=f'Rest.{kind}.{phase}';duration=(len(frames)-1)/30;camera=[]
        for f in frames:
            h=fk(f)[ix['head']];eye=h[:3,3]+h[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0.,7.,6.]);camera.append([*eye.tolist(),0.,0.])
        result['clips'][role]={'duration':duration,'rate':30,'frames':np.asarray(frames).tolist()};metadata[role]={'duration':duration,'camera':camera}
    spec=copy.deepcopy(config['types'][kind]);spec.update(entry_yaw=-90. if right else 90.,entry_offset=[-200.*sign+seat_dx,dy,0.])
    type_updates[kind]=spec
    print('BED_FAMILY_AUTHORED',kind,len(inventory[kind]),'models',spec['entry_offset'],flush=True)
result['changed_roles']=list(result['clips']);roles=result['changed_roles']
baseline={'default':{r:body['clips'][r] for r in roles},'variants':{n:{'mesh':v['body_mesh'],'clips':{r:v['clips'][r] for r in roles}} for n,v in body['body_variants'].items() if v.get('ready')}}
for name,value in [('baseline_routes.json',baseline),('baseline.json',{'furniture':config})]:
    if not (OUT/name).exists():(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
review=copy.deepcopy(config);review['types'].update(type_updates);review['clips'].update(metadata)
for name,value in [('authored.json',result),('clip_metadata.json',metadata),('type_updates.json',type_updates),('review_config.json',review),('inventory.json',{'types':list(params),'models':inventory,'source_entry':source['clips']['Rest.ApartmentBed.Enter']['asset'],'entry_seconds':3.3,'exit_seconds':3.4})]:
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
(OUT/'Geometry/index.json').write_text(json.dumps(index,indent=2))
print('BED_FAMILY_PREPARED',len(roles),'roles',sum(map(len,inventory.values())),'models')
