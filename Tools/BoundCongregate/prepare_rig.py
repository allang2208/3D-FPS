"""Anatomical rig recipe and surface-aware weights, in the supplied GLB frame."""
from pathlib import Path
import json, struct
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from PIL import Image

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
b=(ROOT/'Original/Meshy_AI_Fleshmaw_Leviathan_1006141038_texture.glb').read_bytes()
n=struct.unpack_from('<I',b,12)[0];glb=json.loads(b[20:20+n]);binary=b[28+n:]
images=[]
for im in glb['images']:
    view=glb['bufferViews'][im['bufferView']];start=view.get('byteOffset',0)
    p=ROOT/'Textures'/(im['name']+'.png');p.write_bytes(binary[start:start+view['byteLength']])
    images.append({'name':im['name'],'size':Image.open(p).size,'path':str(p)})
report=json.loads((ROOT/'Assessment/source_report.json').read_text());report['images']=images
report['suitability']='Usable textured source. Static mesh requires species-specific skinning, motions and runtime assets.'
report['ground_limbs']=10;report['reduction_performed']=False
(ROOT/'Assessment/source_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')

legs=[
('L1',[[-.18,-.34,-.16],[-.24,-.55,-.21],[-.20,-.76,-.47],[-.21,-.87,-.505]]),
('L2',[[-.30,-.20,-.12],[-.47,-.40,-.14],[-.48,-.55,-.465],[-.49,-.62,-.51]]),
('L3',[[-.36,.12,-.12],[-.63,.17,-.13],[-.65,.29,-.47],[-.69,.36,-.515]]),
('L4',[[-.28,.31,-.12],[-.48,.43,-.19],[-.43,.61,-.47],[-.43,.69,-.51]]),
('L5',[[-.15,.40,-.17],[-.22,.55,-.19],[-.27,.78,-.48],[-.26,.87,-.505]]),
('R1',[[.17,-.34,-.18],[.31,-.41,-.20],[.28,-.55,-.47],[.27,-.63,-.51]]),
('R2',[[.32,-.22,-.11],[.50,-.28,-.13],[.48,-.35,-.47],[.50,-.43,-.51]]),
('R3',[[.35,.04,-.10],[.51,.05,-.13],[.55,.14,-.47],[.58,.19,-.51]]),
('R4',[[.33,.20,-.10],[.59,.29,-.07],[.61,.37,-.47],[.67,.40,-.51]]),
('R5',[[.20,.39,-.16],[.31,.50,-.20],[.47,.45,-.47],[.52,.48,-.51]])]
bones=[]
def add(name,a,b,parent='body',deform=True):
    bones.append(dict(name=name,head=a,tail=b,parent=parent,deform=deform))
add('root',[0,0,-.532125],[0,0,-.432125],None,False)
add('body',[0,0,-.17],[0,0,.10],'root')
add('body_front',[0,-.15,-.17],[0,-.37,-.10])
add('body_rear',[0,.15,-.17],[0,.39,-.10])
add('maw',[.015,-.36,-.02],[.04,-.50,-.26],'body_front')
add('jaw_L',[-.065,-.405,-.055],[-.015,-.51,-.29],'maw')
add('jaw_R',[.145,-.40,-.065],[.10,-.52,-.29],'maw')
for name,points in legs:
    parent='body_front' if points[0][1]<0 else 'body_rear'
    for i,part in enumerate(['upper','lower','foot']):
        bn=f'leg_{name}_{part}';add(bn,points[i],points[i+1],parent);parent=bn
def chain(name,points,parent='body'):
    for i,(a,b) in enumerate(zip(points,points[1:])):
        bn=f'{name}_{i:02d}';add(bn,a,b,parent);parent=bn
chain('curl',[[.26,.09,.07],[.35,.09,.27],[.23,.08,.46],[.03,.07,.50],[-.15,.07,.43],[-.19,.06,.34],[-.13,.03,.32]])
chain('feeler',[[-.13,.03,.32],[-.07,-.12,.25],[-.10,-.32,.06],[-.10,-.49,-.17],[0,-.52,-.34],[.08,-.56,-.43],[-.03,-.59,-.47],[.09,-.59,-.51]],'curl_05')
chain('scent',[[-.22,-.1,.09],[-.26,-.14,.25],[-.31,-.22,.29],[-.31,-.28,.25]])
chain('grasp',[[-.36,-.08,-.0],[-.43,-.16,.10],[-.51,-.20,.03],[-.54,-.23,-.07]])
data=np.load(ROOT/'Assessment/output.npz');p=data['vertices'];tri=data['triangles']
v,inv=np.unique(np.round(p,5),axis=0,return_inverse=True);t=inv[tri]
edges=np.unique(np.sort(np.concatenate([t[:,:2],t[:,1:],t[:,[0,2]]]),axis=1),axis=0)
length=np.maximum(1e-6,np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1))
g=coo_matrix((np.tile(length,2),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(len(v),len(v))).tocsr()
deform=[b for b in bones if b['deform']];eu=[];dist=[]
for bone in deform:
    a=np.array(bone['head']);axis=np.array(bone['tail'])-a
    f=np.clip((v-a)@axis/(axis@axis),0,1);d=np.linalg.norm(v-a-f[:,None]*axis,axis=1)
    eu.append(d)
    # Surface seeds stay local to each segment; geodesic propagation follows the
    # connected donor limb instead of leaking straight across adjacent limbs.
    seeds=np.argsort(d)[:32]
    gd=dijkstra(g,directed=False,indices=seeds,min_only=True)
    dist.append(gd+max(.005,float(d[seeds].mean())*.30))
    print('WEIGHT',bone['name'],flush=True)
dist=np.array(dist).T;eu=np.array(eu).T
bad=~np.isfinite(dist).any(1);dist[bad]=eu[bad]
dist=np.nan_to_num(dist,posinf=1e5)
weights=np.exp(-(dist-dist.min(1,keepdims=True))/.024)
weights/=weights.sum(1,keepdims=True)
# Smooth only over actual surface adjacency, retaining UV/material seams.
adj=g.copy();adj.data[:]=1;degree=np.asarray(adj.sum(1)).ravel();degree=np.maximum(degree,1)
for _ in range(10):weights=.45*weights+.55*(adj@weights)/degree[:,None]
ids=np.argsort(weights,axis=1)[:,-4:];vals=np.take_along_axis(weights,ids,axis=1);vals/=vals.sum(1,keepdims=True)
np.savez_compressed(ROOT/'Authoring/skin_weights.npz',indices=ids[inv],weights=vals[inv],names=np.array([b['name'] for b in deform]))
recipe=dict(scale=2.25,ground_z=-.532125,bones=bones,legs=[dict(name=n,points=p,phase=(i%2)*.5) for i,(n,p) in enumerate(legs)],
    axis='Blender -Y forward, Z up; FBX exported -Y/Z then UE import yields +X forward',
    walk_cycle=1.8,stride_m=.48,stance=.70,
    materials=images,source=str(ROOT/'Authoring/Source_Imported.blend'))
(ROOT/'Authoring/rig_recipe.json').write_text(json.dumps(recipe,indent=2),encoding='utf8')
