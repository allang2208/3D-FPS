"""Measure the retained factory wrist and authored transition in source space."""
import bpy,json
import numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ActionLayout20261027/M24_ActionLayout_Editable.blend'),use_scripts=False)
ob=bpy.data.objects['M24_base'];m=ob.data
parent=list(range(len(m.vertices)));seen={}
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def join(a,b):parent[root(a)]=root(b)
for v in m.vertices:
 key=tuple(round(x,6) for x in v.co)
 if key in seen:join(v.index,seen[key])
 else:seen[key]=v.index
for e in m.edges:join(*e.vertices)
stock=root(0);rows=[];edges={}
gdir=O.parent/'M24CustomScope20261026/Original/GLTF'
g=json.loads((gdir/'scene.gltf').read_text())
mat=next(x for x in g['materials'] if x['name']=='sniper')['pbrMetallicRoughness']
def texture(key):return gdir/g['images'][g['textures'][mat[key]['index']]['source']]['uri']
image=bpy.data.images.load(str(texture('baseColorTexture')),check_existing=True)
bc=np.array(image.pixels[:]).reshape(image.size[1],image.size[0],4)
mi=bpy.data.images.load(str(texture('metallicRoughnessTexture')),check_existing=True);mi.colorspace_settings.name='Non-Color'
metal=np.array(mi.pixels[:]).reshape(mi.size[1],mi.size[0],4)
def sample(arr,uv):
 h,w=arr.shape[:2];return arr[min(h-1,int((uv[1]%1)*h)),min(w-1,int((uv[0]%1)*w)),:3]
for p in m.polygons:
 if root(p.vertices[0])!=stock:continue
 vs=[m.vertices[i].co for i in p.vertices];remove=min(v.y for v in vs)>=.020
 for a,b in p.edge_keys:
  key=tuple(sorted(tuple(round(x,6) for x in m.vertices[i].co) for i in (a,b)))
  edges.setdefault(key,[]).append(remove)
 if -.04<=p.center.y<=.06 and not remove:
  uv=np.mean([m.uv_layers[0].data[i].uv[:] for i in p.loop_indices],axis=0)
  orm=sample(metal,uv)
  rows.append({'center':list(p.center),'color':sample(bc,uv).tolist(),'metal':[float(orm[2])]*3,'roughness':float(orm[1]),'area':p.area})
boundary=[e for e,v in edges.items() if any(v) and not all(v)]
R={'boundary':boundary,'neck_samples':rows,'source':bpy.data.filepath,'units':'metres Blender, Unreal asset uses cm and inverted Y'}
(O/'source_seam.json').write_text(json.dumps(R,indent=2))
p=np.array([v for e in boundary for v in e]);print('SEAM_BOUNDS',p.min(0).tolist(),p.max(0).tolist(),flush=True)
weights=np.array([x['area'] for x in rows]);weights/=weights.sum()
print('SEAM_COLOR_LINEAR',np.sum(np.array([x['color'] for x in rows])*weights[:,None],axis=0).tolist(),flush=True)
print('SEAM_METAL',np.sum(np.array([x['metal'] for x in rows])*weights[:,None],axis=0).tolist(),flush=True)
