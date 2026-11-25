"""Transfer stable motions in the two rigs' common glTF (+Z forward, +Y up) frame."""
from pathlib import Path
import json
import struct
import zipfile

import numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp

SOURCE = Path(__file__).resolve().parents[4] / 'SourceAssets/HillsVillageStable/HorsesR7'
OUT = SOURCE / 'Exchange'
OUT.mkdir(exist_ok=True)


class Horse:
    def __init__(self, data):
        length = struct.unpack_from('<I', data, 12)[0]
        self.doc = json.loads(data[20:20 + length])
        self.bin = bytearray(data[28 + length:28 + length + self.doc['buffers'][0]['byteLength']])
        self.nodes = self.doc['nodes']
        self.index = {node['name']: i for i,node in enumerate(self.nodes)}
        self.parent = {child: i for i,node in enumerate(self.nodes) for child in node.get('children', [])}
        self.clips = {clip['name'].split('|')[-1]: clip for clip in self.doc['animations']}

    def accessor(self, index):
        acc = self.doc['accessors'][index]
        bv = self.doc['bufferViews'][acc['bufferView']]
        width = {'SCALAR':1,'VEC3':3,'VEC4':4}[acc['type']]
        offset = bv.get('byteOffset',0) + acc.get('byteOffset',0)
        assert acc['componentType'] == 5126
        return np.ndarray((acc['count'],width), '<f4', self.bin, offset,
                          (bv.get('byteStride',4*width),4)).copy()

    def sample(self, clip, frames=None):
        samplers = clip['samplers']
        duration = max(float(self.accessor(s['input'])[-1,0]) for s in samplers)
        times = np.linspace(0, duration, round(duration*30)+1) if frames is None else frames*duration
        tracks = {}
        for ch in clip['channels']:
            samp = samplers[ch['sampler']]
            t = self.accessor(samp['input'])[:,0]
            values = self.accessor(samp['output'])
            key = ch['target']['path']
            at = np.clip(times,t[0],t[-1])
            if len(t)==1 or samp.get('interpolation')=='STEP':
                value = values[np.searchsorted(t,at,side='right')-1]
            elif key=='rotation':
                value = Slerp(t,Rot.from_quat(values))(at).as_quat()
            else:
                value = np.stack([np.interp(at,t,v) for v in values.T],axis=-1)
            tracks[ch['target']['node'],key] = value
        return times,tracks

    def local(self,i,key,tracks,count):
        defaults={'rotation':[0,0,0,1],'translation':[0,0,0],'scale':[1,1,1]}
        return tracks.get((i,key),np.broadcast_to(self.nodes[i].get(key,defaults[key]),(count,len(defaults[key]))))

    def world_rot(self,i,tracks,count):
        r=Rot.from_quat(self.local(i,'rotation',tracks,count))
        return self.world_rot(self.parent[i],tracks,count)*r if i in self.parent else r

    def world_pos(self,i,tracks,count):
        p=self.local(i,'translation',tracks,count)
        if i not in self.parent:
            return p
        parent=self.parent[i]
        # Target Warhorse has unit-scale ancestors.
        return self.world_pos(parent,tracks,count)+self.world_rot(parent,tracks,count).apply(p)

    def append(self,a,kind):
        a=np.asarray(a,dtype='<f4')
        self.bin.extend(b'\0'*(-len(self.bin)%4))
        v=len(self.doc['bufferViews'])
        self.doc['bufferViews'].append(dict(buffer=0,byteOffset=len(self.bin),byteLength=a.nbytes))
        self.bin.extend(a.tobytes())
        acc=dict(bufferView=v,componentType=5126,count=len(a),type=kind)
        if kind=='SCALAR':
            acc.update(min=[float(a[0])],max=[float(a[-1])])
        self.doc['accessors'].append(acc)
        return len(self.doc['accessors'])-1

    def save_clip(self,name,times,tracks):
        clip=dict(name=name,samplers=[],channels=[])
        timeline=self.append(times,'SCALAR')
        for (node,path),data in tracks.items():
            if path=='rotation':
                data=Rot.from_quat(data).as_quat()
                for i in range(1,len(data)):
                    if np.dot(data[i-1],data[i]) < 0: data[i]*=-1
            idx=len(clip['samplers'])
            clip['channels'].append(dict(sampler=idx,target=dict(node=node,path=path)))
            clip['samplers'].append(dict(input=timeline,output=self.append(data,'VEC4' if path=='rotation' else 'VEC3'),
                                         interpolation='LINEAR'))
        self.doc['animations'].append(clip)

    def write(self,path):
        self.doc['buffers'][0]['byteLength']=len(self.bin)
        header=json.dumps(self.doc,separators=(',',':')).encode()
        header+=b' '*(-len(header)%4)
        self.bin.extend(b'\0'*(-len(self.bin)%4))
        path.write_bytes(struct.pack('<4sIIII',b'glTF',2,28+len(header)+len(self.bin),len(header),0x4E4F534A)
                         +header+struct.pack('<II',len(self.bin),0x004E4942)+self.bin)


if __name__ == '__main__':
    with zipfile.ZipFile(SOURCE/'Originals/WarhorseLite.zip') as original:
        target=Horse(original.read('Warhorse_Lite/Warhorse_Lite.glb'))
        (SOURCE/'Originals/Warhorse-LICENSE.txt').write_bytes(original.read('Warhorse_Lite/LICENSE.txt'))
    donor=Horse((SOURCE/'Originals/QuaterniusHorse.glb').read_bytes())
    for img in target.doc['images']:
        view=target.doc['bufferViews'][img['bufferView']]
        offset=view.get('byteOffset',0)
        ext='.png' if img['mimeType']=='image/png' else '.jpg'
        (OUT/(img['name']+ext)).write_bytes(target.bin[offset:offset+view['byteLength']])

    # Each entry spans an anatomical chain. The relative source rotation is transferred
    # in rest-world axes, independent of the different local bone rolls and proportions.
    chains=[('neck_01','Neck1','Torso2'),('neck_02','Neck2','Neck1'),('neck_03','Neck3','Neck2'),
            ('head','Head','Neck3'),('ear_L','Ear3.L','Head'),('ear_R','Ear3.R','Head'),
            ('tail_01','Tail2','Back'),('tail_02','Tail3','Tail2'),('tail_03','Tail4','Tail3'),
            ('tail_04','Tail5','Tail4'),('tail_05','Tail7','Tail5')]
    for source,name in [('Eating','Q_Feed'),('Idle','Q_Idle'),('Idle_2','Q_IdleLook'),
                        ('Idle_Headlow','Q_HeadLow'),('Walk','Q_LeadWalk')]:
        times,src=donor.sample(donor.clips[source])
        count=len(times)
        # Native lower-body motion maintains hoof contacts and animates the saddle and stirrups.
        base='walk_loop' if source=='Walk' else 'idle_loop'
        _,dst=target.sample(target.clips[base],times/times[-1])
        for dest,bone,parent in chains:
            ti=target.index[dest]; si=donor.index[bone]; pi=donor.index[parent]
            sr=donor.world_rot(si,{},1); pr=donor.world_rot(pi,{},1)
            relative=donor.world_rot(pi,src,count).inv()*donor.world_rot(si,src,count)
            delta=pr*relative*sr.inv()
            tr=target.world_rot(ti,{},1)
            local_rest=Rot.from_quat(target.local(ti,'rotation',{},1))
            dst[ti,'rotation']=(local_rest*tr.inv()*delta*tr).as_quat()
        if source=='Eating':
            neck=target.index['neck_01']
            pivot=target.world_pos(neck,dst,count)
            mouth=target.world_pos(target.index['mouth_socket'],dst,count)
            offset=mouth-pivot
            # Set the bite height to the existing stable manger; retain the source nod and lateral motion.
            height=.89+.045*np.tanh((mouth[:,1]-.89)/.25)
            angle=np.arctan2(offset[:,1],offset[:,2])-np.arcsin(np.clip((height-pivot[:,1])/np.hypot(offset[:,1],offset[:,2]),-.99,.99))
            parent_rot=target.world_rot(target.parent[neck],dst,count)
            dst[neck,'rotation']=(parent_rot.inv()*Rot.from_euler('x',angle[:,None])*parent_rot*Rot.from_quat(dst[neck,'rotation'])).as_quat()
            jaw=target.index['jaw']
            chew=1.8*(1-np.cos(2*np.pi*7*times/times[-1]))
            dst[jaw,'rotation']=(Rot.from_quat(dst[jaw,'rotation'])*Rot.from_euler('x',chew[:,None],degrees=True)).as_quat()
        target.save_clip(name,times,dst)
    target.write(OUT/'Warhorse_Stable.glb')
