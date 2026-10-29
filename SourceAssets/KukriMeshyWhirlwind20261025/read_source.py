"""Sample the user-provided Meshy GLB without importing or modifying its rig."""
import hashlib
import json
import struct
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

OUT=Path(__file__).resolve().parent
ORIGINAL=Path(r'C:/Users/allan/Downloads/Meshy_AI_Gray_Full_Body_Manneq_All_Animations (1).glb')


def read():
    raw=ORIGINAL.read_bytes()
    copy=OUT/'Meshy_Gray_Mannequin_All_Animations.glb'
    if not copy.exists():copy.write_bytes(raw)
    elif hashlib.sha256(copy.read_bytes()).digest()!=hashlib.sha256(raw).digest():
        raise RuntimeError('Preserved source differs from current download')
    chunks={};pos=12
    while pos<len(raw):
        length,kind=struct.unpack_from('<II',raw,pos);pos+=8
        chunks[kind]=raw[pos:pos+length];pos+=length
    doc=json.loads(chunks[0x4e4f534a]);buf=chunks[0x004e4942]
    def accessor(i):
        a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']]
        types={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}
        width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        dtype=np.dtype(types[a['componentType']]);offset=v.get('byteOffset',0)+a.get('byteOffset',0)
        stride=v.get('byteStride',dtype.itemsize*width)
        return np.ndarray((a['count'],width),dtype=dtype,buffer=buf,offset=offset,strides=(stride,dtype.itemsize)).copy()
    nodes=doc['nodes'];parents={c:i for i,n in enumerate(nodes) for c in n.get('children',[])}
    ref=np.asarray([n.get('translation',[0.,0.,0.])+n.get('rotation',[0.,0.,0.,1.])+n.get('scale',[1.,1.,1.]) for n in nodes])
    order=[]
    def visit(i):
        if i in order:return
        if i in parents:visit(parents[i])
        order.append(i)
    for i in range(len(nodes)):visit(i)
    def world(local):
        p=local[...,:3].copy();q=local[...,3:7].copy();s=local[...,7:].copy()
        for i in order:
            if i not in parents:continue
            parent=parents[i]
            p[:,i]=p[:,parent]+R.from_quat(q[:,parent]).apply(local[:,i,:3]*s[:,parent])
            q[:,i]=(R.from_quat(q[:,parent])*R.from_quat(local[:,i,3:7])).as_quat()
            s[:,i]*=s[:,parent]
        return np.concatenate([p,q,s],axis=-1)
    animation=next(a for a in doc['animations'] if a['name']=='Axe_Spin_Attack')
    length=max(float(accessor(s['input'])[-1,0]) for s in animation['samplers'])
    times=np.linspace(0.,length,round(length*120)+1)
    local=np.repeat(ref[None],len(times),axis=0)
    for channel in animation['channels']:
        sampler=animation['samplers'][channel['sampler']]
        if sampler.get('interpolation','LINEAR')!='LINEAR':raise RuntimeError('Unsupported source interpolation')
        t=accessor(sampler['input'])[:,0];v=accessor(sampler['output']);i=channel['target']['node'];path=channel['target']['path']
        st=np.clip(times,t[0],t[-1])
        if path=='rotation':local[:,i,3:7]=Slerp(t,R.from_quat(v))(st).as_quat()
        else:
            offset=0 if path=='translation' else 7
            local[:,i,offset:offset+3]=np.column_stack([np.interp(st,t,v[:,axis]) for axis in range(3)])
    bind=world(ref[None])[0];frames=world(local)
    # glTF right-handed Y-up to this project's body coordinates (X left, Y front,
    # Z up). Reflections conjugate rotation matrices; never reflect quaternions.
    conversion=np.array([[1.,0.,0.],[0.,0.,1.],[0.,1.,0.]])
    def convert(a):
        out=a.copy();out[...,:3]=a[...,:3]@conversion.T
        out[...,3:7]=R.from_matrix(conversion@R.from_quat(a[...,3:7].reshape(-1,4)).as_matrix()@conversion.T).as_quat().reshape(a.shape[:-1]+(4,))
        return out
    bind=convert(bind);frames=convert(frames)
    names=[n.get('name',str(i)) for i,n in enumerate(nodes)];ix={n:i for i,n in enumerate(names)}
    # Source forward comes from its actual face marker, not a filename convention.
    forward=bind[ix['headfront'],:3]-bind[ix['head'],:3];forward[2]=0.;forward/=np.linalg.norm(forward)
    left=bind[ix['upperarm_l'],:3]-bind[ix['upperarm_r'],:3]
    source=dict(original=str(ORIGINAL),sha256=hashlib.sha256(raw).hexdigest(),clip=animation['name'],
        duration=length,rate=120,names=names,parents=[parents.get(i,-1) for i in range(len(nodes))],
        reference_world=bind.tolist(),frames=frames.tolist(),forward=forward.tolist(),
        provenance='User-provided Meshy export; no redistribution license inferred',all_clips=[a['name'] for a in doc['animations']])
    (OUT/'source.json').write_text(json.dumps(source,separators=(',',':')))
    hip=ix['pelvis'];heading=(R.from_quat(frames[:,hip,3:7])*R.from_quat(bind[hip,3:7]).inv()).apply(np.tile(forward,(len(frames),1)))
    yaw=np.unwrap(np.arctan2(-heading[:,0],heading[:,1]))
    print('SOURCE',animation['name'],length,'forward',forward.round(3),'left vector',left.round(3))
    for k in range(0,len(frames),12):
        print(round(times[k],3),'yaw',round(float(np.degrees(yaw[k])),1),
            'hip',frames[k,hip,:3].round(3).tolist(),
            'hand offsets',{s:(frames[k,ix['hand_'+s],:3]-frames[k,hip,:3]).round(3).tolist() for s in 'lr'})


if __name__=='__main__':read()
