import bpy,json,numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/RigV01')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/HeQue_source.blend'))
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH');m=mesh.data
p=np.array([v.co[:] for v in m.vertices]);uv=np.array([v.uv[:] for v in m.uv_layers.active.data]);loopv=np.array([l.vertex_index for l in m.loops])
_,weld=np.unique(np.round(p,6),axis=0,return_inverse=True);parent=np.arange(weld.max()+1)
def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
for e in m.edges:
    a,b=(find(weld[v]) for v in e.vertices)
    if a!=b:parent[b]=a
labels=np.array([find(i) for i in weld]);counts=np.unique(labels,return_counts=True)
islands=[]
for id,n in sorted(zip(*counts),key=lambda v:-v[1]):
    q=p[labels==id];islands.append(dict(id=int(id),vertices=int(n),lo=q.min(0).tolist(),hi=q.max(0).tolist(),center=q.mean(0).tolist()))
images={}
for image in bpy.data.images:
    if image.size[0]==0:continue
    images[image.name]={'size':list(image.size),'path':image.filepath}
nodes=mesh.data.materials[0].node_tree.nodes
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
base=bsdf.inputs['Base Color'].links[0].from_node.image
px=np.array(base.pixels[:],np.float32).reshape(base.size[1],base.size[0],4)
xy=np.floor(uv*np.array(base.size[:])).astype(int);xy[:,0]=np.clip(xy[:,0],0,base.size[0]-1);xy[:,1]=np.clip(xy[:,1],0,base.size[1]-1)
rgb=px[xy[:,1],xy[:,0],:3];colors=np.zeros((len(p),3));num=np.zeros(len(p))
np.add.at(colors,loopv,rgb);np.add.at(num,loopv,1);colors/=np.maximum(num[:,None],1)
np.savez_compressed(ROOT/'Records/surface_map.npz',points=p,labels=labels,colors=colors)
(ROOT/'Records/regions.json').write_text(json.dumps({'images':images,'islands':islands[:60]},indent=2),encoding='utf8')
print(json.dumps({'images':images,'islands':islands[:18]},indent=2))
