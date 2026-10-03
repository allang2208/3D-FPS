"""Read the supplied GLB anatomy for authoring; preserve the original input."""
from pathlib import Path
import json, struct, shutil
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from PIL import Image
import io

ROOT=Path(__file__).resolve().parent
SOURCE=Path(r'C:/Users/allan/Downloads/Meshy_AI_M_10_Mawcrawler_1003020804_texture.glb')
ROOT.mkdir(parents=True,exist_ok=True)
if not (ROOT/'M10_Meshy_original.glb').exists(): shutil.copy2(SOURCE,ROOT/'M10_Meshy_original.glb')
raw=SOURCE.read_bytes(); length,kind=struct.unpack_from('<II',raw,12)
doc=json.loads(raw[20:20+length]); pos=20+length
blen,bkind=struct.unpack_from('<II',raw,pos); binary=raw[pos+8:pos+8+blen]
def access(i):
    a=doc['accessors'][i]; b=doc['bufferViews'][a['bufferView']]
    dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']]
    width={'SCALAR':1,'VEC2':2,'VEC3':3}[a['type']]
    return np.frombuffer(binary,dtype=dtype,count=a['count']*width,offset=b.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,width).copy()
primitive=doc['meshes'][0]['primitives'][0]
original=access(primitive['attributes']['POSITION']); uv=access(primitive['attributes']['TEXCOORD_0']); faces=access(primitive['indices']).reshape(-1,3)
# glTF +Z is read as candidate forward +X. Final forward is selected from the mouth geometry.
v=original[:,[2,0,1]].astype(np.float64)
factor=4.2/np.ptp(v[:,0]); v[:,0]-=(v[:,0].max()+v[:,0].min())/2;v[:,1]-=(v[:,1].max()+v[:,1].min())/2;v[:,2]-=v[:,2].min();v*=factor
textures=[]
for i,info in enumerate(doc['images']):
    b=doc['bufferViews'][info['bufferView']]; data=binary[b.get('byteOffset',0):b.get('byteOffset',0)+b['byteLength']]
    im=Image.open(io.BytesIO(data)); name=['BaseColor','MetallicRoughness','NormalGL'][i]
    im.save(ROOT/(name+'.png'));textures.append({'name':name,'size':im.size})
color=np.asarray(Image.open(ROOT/'BaseColor.png').convert('RGB'))
pixel=color[np.clip(((1-uv[:,1])*color.shape[0]).astype(int),0,color.shape[0]-1),np.clip((uv[:,0]*color.shape[1]).astype(int),0,color.shape[1]-1)]
unique,inv=np.unique(np.round(v,6),axis=0,return_inverse=True)
edges=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]); edges=np.sort(inv[edges],axis=1);edges=np.unique(edges,axis=0)
regions={}
for cut in (.12,.22,.35,.48):
    selected=np.flatnonzero(unique[:,2]<cut)
    lookup=np.full(len(unique),-1);lookup[selected]=np.arange(len(selected))
    es=edges[(lookup[edges]>=0).all(axis=1)]; local=lookup[es]
    graph=coo_matrix((np.ones(len(local)),(local[:,0],local[:,1])),shape=(len(selected),len(selected)))
    count,labels=connected_components(graph,directed=False)
    groups=[]
    for label in range(count):
        ids=selected[labels==label]
        if len(ids)<80:continue
        p=unique[ids];groups.append({'count':len(ids),'center':p.mean(axis=0).round(4).tolist(),'min':p.min(axis=0).round(4).tolist(),'max':p.max(axis=0).round(4).tolist()})
    regions[str(cut)]=sorted(groups,key=lambda x:-x['count'])[:24]
end_colors={}
for sign in (-1,1):
    ids=(v[:,0]*sign>1.65)&(abs(v[:,1])<.8)
    end_colors[str(sign)]={'vertices':int(ids.sum()),'rgb_mean':pixel[ids].mean(axis=0).round(1).tolist(),'dark_fraction':float((pixel[ids].mean(axis=1)<65).mean())}
report={'vertices':len(v),'triangles':len(faces),'source_has_skin':bool(doc.get('skins')),'source_bounds':{'min':original.min(axis=0).tolist(),'max':original.max(axis=0).tolist()},'scale_to_meters':factor,'authoring_bounds_m':{'min':v.min(axis=0).tolist(),'max':v.max(axis=0).tolist()},'textures':textures,'end_colors':end_colors,'lower_surface_regions':regions}
(ROOT/'source_anatomy.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
np.savez_compressed(ROOT/'source_geometry.npz',vertices=v,original=original,uv=uv,faces=faces,unique=unique,inverse=inv,edges=edges)
print(json.dumps(report,indent=2),flush=True)
