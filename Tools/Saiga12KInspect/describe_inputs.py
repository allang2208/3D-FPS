import json
from pathlib import Path
import numpy as np
from pose_math import matrix,world,apply,role
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KInspect20261018')
d=json.loads((O/'Inputs/runtime-source.json').read_text())
parents={b['name']:d['bones'][b['parent']]['name'] if b['parent']>=0 else None for b in d['bones']}
def describe(local):
    w=world(local,parents);inv=np.linalg.inv(w['WPN_root'])
    return {n:np.round((inv@w[n])[:3,3]*100,2).tolist() for n in ('upperarm_l','lowerarm_l','hand_l','thumb_03_l','index_03_l','pinky_03_l')}
print('EDITOR',d['editor']);print('DURATION',d['duration'],'FRAMES',len(d['frames']))
for i in np.linspace(0,len(d['frames'])-1,9).astype(int):
    f=d['frames'][i];print('INSPECT',f['time'],describe({n:matrix(v) for n,v in f['local'].items()}))
idle={n:matrix(v) for n,v in d['idle'].items()}
print('BASE IDLE',describe(idle))
for family,profile in d['profiles'].items():
    inspect=role(profile,'inspect')
    print('FAMILY',family,'inspect',None if not inspect else {'base':inspect['base'],'retained':inspect['retained'],'tracks':len(inspect['tracks'])})
    c=role(profile,'idle');print('IDLE',family,'retained',c['retained'],describe(apply(idle,c,0)))
