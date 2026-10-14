"""Read source animation trajectories for candidate selection; no UE import/render."""
import json
import math
import struct
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent

def read_glb(path, selection, bone_names):
    b = path.read_bytes()
    n = struct.unpack_from('<I', b, 12)[0]
    d = json.loads(b[20:20+n])
    binary = b[28+n:]
    def access(i):
        a = d['accessors'][i]; v = d['bufferViews'][a['bufferView']]
        size = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[a['type']]
        return np.ndarray((a['count'], size), dtype='<f4', buffer=binary,
                          offset=v.get('byteOffset', 0)+a.get('byteOffset', 0),
                          strides=(v.get('byteStride', size*4), 4)).copy()
    nodes = d['nodes']; ids = {n.get('name'): i for i, n in enumerate(nodes)}
    parents = {c: i for i, n in enumerate(nodes) for c in n.get('children', [])}
    def matrix(q):
        x,y,z,w = q/np.linalg.norm(q)
        return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                         [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                         [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
    out = {}
    for a in d['animations']:
        if a['name'] not in selection:
            continue
        channels = []
        for c in a['channels']:
            s = a['samplers'][c['sampler']]
            channels.append((c['target']['node'], c['target']['path'], access(s['input']).ravel(), access(s['output'])))
        duration = max(float(c[2][-1]) for c in channels)
        samples = []
        for t in np.linspace(0, duration, round(duration*60)+1):
            local = [dict(translation=n.get('translation',[0,0,0]), rotation=n.get('rotation',[0,0,0,1]), scale=n.get('scale',[1,1,1])) for n in nodes]
            for ni, prop, times, values in channels:
                k = int(np.clip(np.searchsorted(times,t,side='right')-1,0,len(times)-2))
                u = np.clip((t-times[k])/max(1e-8,times[k+1]-times[k]),0,1)
                v1,v2 = values[k],values[k+1]
                if prop=='rotation' and np.dot(v1,v2)<0: v2=-v2
                local[ni][prop] = v1*(1-u)+v2*u
            world = {}
            def fk(i):
                if i not in world:
                    p = local[i]; m = np.eye(4)
                    m[:3,:3] = matrix(np.array(p['rotation']))@np.diag(p['scale'])
                    m[:3,3] = p['translation']
                    world[i] = fk(parents[i])@m if i in parents else m
                return world[i]
            sample = {'time': round(float(t),4)}
            for label, bone in bone_names.items():
                sample[label] = np.round(fk(ids[bone])[:3,3]*100,3).tolist()
            sample['hands_apart_cm'] = round(float(np.linalg.norm(np.array(sample['right'])-sample['left'])),2)
            samples.append(sample)
        out[a['name']] = {'duration': duration, 'samples': samples}
        compact = [samples[i] for i in np.linspace(0,len(samples)-1,17).round().astype(int)]
        print(a['name'], 'duration', round(duration,3), 'hand_distance_range',
              [min(s['hands_apart_cm'] for s in samples),max(s['hands_apart_cm'] for s in samples)])
        print(json.dumps([{k:s[k] for k in ('time','right','left','hands_apart_cm')} for s in compact]))
    return out

ual = read_glb(OUT/'UAL2_Standard.glb', ['Sword_Dash','Sword_Heavy_Combo','Sword_Regular_C'],
               dict(right='hand_r',left='hand_l',head='Head',hips='pelvis',right_foot='foot_r',left_foot='foot_l'))
large = read_glb(ROOT/'SourceAssets/ThirdPersonSwordFree20261005/KayKit/KayKit_Character_Animations_1.1/Animations/gltf/Rig_Large/Rig_Large_CombatMelee.glb',
                 ['Melee_2H_Attack','Melee_2H_Slam'],
                 dict(right='wrist.r',left='wrist.l',head='head',hips='hips',right_foot='foot.r',left_foot='foot.l'))
(OUT/'source-trajectories.json').write_text(json.dumps({'UAL2':ual,'KayKit_Large':large},indent=2),encoding='utf-8')
