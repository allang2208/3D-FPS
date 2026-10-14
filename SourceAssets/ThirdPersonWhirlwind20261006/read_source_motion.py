"""Read existing KayKit source tracks for third-person whirlwind design. No render/asset writes."""
import json, struct, math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'SourceAssets/ThirdPersonSwordFree20261005/KayKit/KayKit_Character_Animations_1.1/Animations/gltf/Rig_Medium/Rig_Medium_CombatMelee.glb'
raw=source.read_bytes();chunks=[];pos=12
while pos<len(raw):
    length,kind=struct.unpack_from('<II',raw,pos);pos+=8
    chunks.append((kind,raw[pos:pos+length]));pos+=length
d=json.loads(next(b for t,b in chunks if t==0x4e4f534a))
binary=next(b for t,b in chunks if t==0x004e4942)
def accessor(i):
    a=d['accessors'][i];v=d['bufferViews'][a['bufferView']]
    count={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
    return np.ndarray((a['count'],count),dtype='<f4',buffer=binary,
        offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',count*4),4)).copy()
def rotation(q):
    x,y,z,w=q/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
nodes=d['nodes'];byname={n.get('name'):i for i,n in enumerate(nodes)}
parent={c:i for i,n in enumerate(nodes) for c in n.get('children',[])}
def pose(channels,t):
    loc=[dict(translation=n.get('translation',[0,0,0]),rotation=n.get('rotation',[0,0,0,1]),scale=n.get('scale',[1,1,1])) for n in nodes]
    for ni,path,times,values in channels:
        ix=max(0,min(len(times)-2,int(np.searchsorted(times,t,side='right')-1)))
        if len(times)==1:value=values[0]
        else:
            f=np.clip((t-times[ix])/max(1e-8,times[ix+1]-times[ix]),0,1)
            a,b=values[ix],values[ix+1]
            if path=='rotation' and np.dot(a,b)<0:b=-b
            value=a*(1-f)+b*f
        loc[ni][path]=value
    world={}
    def build(i):
        if i not in world:
            v=loc[i];m=np.eye(4);m[:3,:3]=rotation(np.array(v['rotation']))@np.diag(v['scale']);m[:3,3]=v['translation']
            world[i]=build(parent[i])@m if i in parent else m
        return world[i]
    return {name:build(i) for name,i in byname.items()}
bind=pose([],0)
out={}
for anim in d['animations']:
    if anim['name'] not in ['Melee_2H_Attack_Spin','Melee_2H_Attack_Spinning']:continue
    channels=[]
    for c in anim['channels']:
        s=anim['samplers'][c['sampler']]
        if s.get('interpolation','LINEAR') not in ['LINEAR','STEP']:raise RuntimeError('Unsupported interpolation')
        channels.append((c['target']['node'],c['target']['path'],accessor(s['input']).ravel(),accessor(s['output'])))
    duration=max(float(c[2][-1]) for c in channels)
    times=np.linspace(0,duration,round(duration*60)+1)
    poses=[pose(channels,t) for t in times]
    heading={}
    for name in ['root','hips','chest','head']:
        angles=[]
        for p in poses:
            delta=p[name][:3,:3]@np.linalg.inv(bind[name][:3,:3])
            forward=delta@np.array([0,0,1]);angles.append(math.atan2(forward[0],forward[2]))
        heading[name]=np.degrees(np.unwrap(angles))
    samples=[]
    for ix in np.linspace(0,len(times)-1,13).round().astype(int):
        p=poses[ix]
        samples.append(dict(time=round(float(times[ix]),3),yaw={n:round(float(a[ix]),1) for n,a in heading.items()},
                            points_cm={n:[round(float(v)*100,2) for v in p[n][:3,3]] for n in ['hips','hand.r','hand.l','foot.r','foot.l']}))
    out[anim['name']]=dict(duration=duration,heading_range={n:[round(float(min(a)),1),round(float(max(a)),1)] for n,a in heading.items()},
                           end_delta_cm={n:round(float(np.linalg.norm(poses[-1][n][:3,3]-poses[0][n][:3,3])*100),3) for n in ['hips','hand.r','hand.l','foot.r','foot.l']},samples=samples)
    out[anim['name']]['foot_root_relative_range_cm']={}
    for name in ['foot.r','foot.l']:
        positions=np.array([(np.linalg.inv(p['root'])@p[name])[:3,3] for p in poses])
        out[anim['name']]['foot_root_relative_range_cm'][name]=[round(float(v)*100,3) for v in np.ptp(positions,axis=0)]
    print(anim['name'],json.dumps({k:v for k,v in out[anim['name']].items() if k!='samples'}))
(Path(__file__).parent/'source-motion.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
