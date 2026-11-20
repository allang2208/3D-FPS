"""Task-owned native combat-shirt geometry helpers; centimetres, UE rest pose."""
import json,copy,ast
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR1'
DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR1'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
def unit(v):return np.asarray(v)/max(float(np.linalg.norm(v)),1e-12)
def subset(d,mask):
    out=copy.deepcopy(d);faces=np.asarray(d['triangles'])[mask];ids=np.unique(faces);remap={int(v):i for i,v in enumerate(ids)}
    out['positions']=[d['positions'][i] for i in ids];out['weights']=[d['weights'][i] for i in ids];out['triangles']=[[remap[int(v)] for v in f] for f in faces]
    for k in ['uv','normals','triangle_materials']:out[k]=[v for v,keep in zip(d[k],mask) if keep]
    return out
def merge(a,b):
    offset=len(a['positions']);boneids={v['name']:v['index'] for v in a['bones']};other={v['index']:boneids[v['name']] for v in b['bones']}
    matmap={}
    for i,path in enumerate(b['materials']):
        if path not in a['materials']:a['materials'].append(path);a['material_slots'].append(b['material_slots'][i])
        matmap[i]=a['materials'].index(path)
    a['positions']+=b['positions'];a['weights']+=[[[other[bi],w] for bi,w in ws] for ws in b['weights']]
    a['triangles']+=[[vi+offset for vi in face] for face in b['triangles']]
    a['triangle_materials']+=[matmap[i] for i in b['triangle_materials']]
    a['uv']+=b['uv'];a['normals']+=b['normals'];return a
def smooth_transport(d,original):
    tree=ast.parse((P/'Tools/ModernTacticalSet/derive.py').read_text(encoding='utf-8'))
    ns={'np':np};exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='transport_normals'],type_ignores=[]),'native_normal_transport','exec'),ns)
    old=np.asarray(d['normals']).reshape(-1,3);ns['transport_normals'](d,np.asarray(original))
    keys=np.column_stack([np.asarray(d['triangles']).reshape(-1),np.round(old,4)]);_,ix=np.unique(keys,axis=0,return_inverse=True)
    n=np.asarray(d['normals']).reshape(-1,3);acc=np.zeros((int(ix.max())+1,3));np.add.at(acc,ix,n);acc/=np.maximum(np.linalg.norm(acc,axis=1,keepdims=True),1e-12)
    d['normals']=acc[ix].reshape(-1,3,3).tolist()
