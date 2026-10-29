"""Skin current hash-matched Jason body and garment captures using leader poses."""
import hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
s=importlib.util.spec_from_file_location('author',OUT/'author.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
version=sys.argv[1] if len(sys.argv)>1 else 'after'
body=a.c.Body(a.base.rig.DATA['jason']);origin=OUT if version=='after' else ROOT/'SourceAssets/KukriDualWhirlwind20261026'
source=json.loads((origin/'jason-actions.json').read_text());parts=[np.asarray(source['clips'][r]['frames']) for r in a.ROLES]
frames=np.concatenate([parts[0],parts[1][1:],parts[2][1:]])
times=[.5,.58,.67,.95,1.21,1.4,1.55];frames=np.array([frames[min(len(frames)-1,round(t*120))] for t in times]);p,q=body.world(frames)
cfg=json.loads((ROOT/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
captures=ROOT/'SourceAssets/GarmentWaist20261023/Read'

def read(file):
    d=json.loads(file.read_text());path=ROOT/'Content'/(d['source'].split('.')[0].removeprefix('/Game/')+'.uasset')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=d['asset_sha256']:raise RuntimeError('Capture changed: '+str(file))
    return d

def skin(d):
    vertices=np.asarray(d['positions']);weights=d['weights'];width=max(map(len,weights))
    wi=np.zeros((len(weights),width),int);wv=np.zeros((len(weights),width))
    for k,row in enumerate(weights):
        for j,(name,w) in enumerate(row.items()):wi[k,j]=body.ix[name];wv[k,j]=w
    reference=np.zeros((len(body.names),3));inv=np.tile(np.eye(3),(len(body.names),1,1))
    for name,b in d['bones'].items():
        if name in body.ix:
            i=body.ix[name];reference[i]=b['position'];inv[i]=np.linalg.inv(np.asarray(b['axes']).T)
    local=np.einsum('nvij,nvj->nvi',inv[wi],vertices[:,None,:]-reference[wi])
    out=[]
    for k in range(len(frames)):
        rot=R.from_quat(q[k]).as_matrix()
        out.append(np.sum((np.einsum('nvij,nvj->nvi',rot[wi],local)+p[k,wi])*wv[:,:,None],axis=1))
    return np.asarray(out,dtype=np.float32)

native=read(captures/'NativeBase.json');native_vertices=skin(native);proof=[]
for name in ('ue_st6_sleeves','ue_field_sweater_charcoal','ue_chainmail_shirt'):
    garment=read(captures/name/'Jason.json');recipe=cfg['items'][name]
    if recipe['rig_meshes']['Jason']!=garment['source']:raise RuntimeError('Recipe changed '+name)
    cover=recipe.get('rig_world_covers',{}).get('Jason',recipe.get('world_covers',[0,1,3,7,8,9,10,14]))
    visible=~np.isin(np.asarray(native['triangle_materials']),cover+[6])
    np.savez_compressed(OUT/f'outfit-{version}-{name}.npz',body=native_vertices,
        body_triangles=np.asarray(native['triangles'])[visible],cloth=skin(garment),cloth_triangles=garment['triangles'],times=times)
    proof.append({'item':name,'body':native['source'],'body_sha256':native['asset_sha256'],'garment':garment['source'],'garment_sha256':garment['asset_sha256'],'hidden_body_materials':cover})
    print('OUTFIT_PREPARED',version,name,flush=True)
(OUT/f'outfit-{version}-sources.json').write_text(json.dumps(proof,indent=2))
