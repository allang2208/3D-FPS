"""Restore the complete Meshy head; fit only the lower neck hidden by the collar."""
import bpy,json,struct,math,bisect,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
P=Path('D:/FPS3D/FPSGAME');N=P/'SourceAssets/ChapelNun20261115';R=N/'FaceOriginalRestoreR6';O=R/'Authored';O.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
raw=(N/'MeshyHeadR1/Source/NunHead_R1_glb.glb').read_bytes();js=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+js]);base=28+js
def accessor(i):
 a=gltf['accessors'][i];v=gltf['bufferViews'][a['bufferView']];k={'VEC3':3,'VEC2':2,'SCALAR':1}[a['type']];dt='<f4' if a['componentType']==5126 else '<u4';offset=base+v.get('byteOffset',0)+a.get('byteOffset',0)
 return np.ndarray((a['count'],k),dtype=dt,buffer=raw,offset=offset,strides=(v.get('byteStride',k*4),4)).copy()
pr=gltf['meshes'][0]['primitives'][0];rawp=accessor(pr['attributes']['POSITION']);uv=accessor(pr['attributes']['TEXCOORD_0']);norm=accessor(pr['attributes']['NORMAL'])[:,[0,2,1]];tris=accessor(pr['indices']).reshape(-1,3)
pos=rawp[:,[0,2,1]].astype(float)*15.8+np.array([0,1.4,168.0523223876953-.94961101*15.8])
old=read(N/'RefinementR4/Authored/head.json');native=read(N/'ProductionR1/Inputs/native_head.json');oldnative=read(N/'OriginalMeshyFaceR3/Authored/head.json')
ringids={v for t,m in zip(oldnative['triangles'],oldnative['triangle_materials']) if m==1 for v in t if abs(oldnative['positions'][v][2]-144.5)<.002}
ring=sorted([Vector(oldnative['positions'][v]) for v in ringids],key=lambda p:math.atan2(p.y-1,p.x));angles=[math.atan2(p.y-1,p.x) for p in ring]
tree=KDTree(len(native['positions']))
for i,p in enumerate(native['positions']):tree.insert(p,i)
tree.balance()
def weights(p):
 acc={}
 for _,i,d in tree.find_n(p,4):
  for b,w in native['weights'][i]:acc[b]=acc.get(b,0)+w/max(.03,d)**2
 pairs=sorted(acc.items(),key=lambda x:-x[1])[:8];total=sum(w for b,w in pairs);return [[b,w/total] for b,w in pairs]
def fit(p):
 p=Vector(p)
 if p.z>=142.5:return p
 theta=math.atan2(p.y-1,p.x);k=bisect.bisect_left(angles,theta);ta=angles[(k-1)%len(ring)];tb=angles[k%len(ring)]
 if tb<ta:tb+=math.tau
 if theta<ta:theta+=math.tau
 q=ring[(k-1)%len(ring)].lerp(ring[k%len(ring)],(theta-ta)/max(1e-6,tb-ta));t=max(0,min(1,(142.5-p.z)/3.4));t=t*t*(3-2*t)
 p.x=p.x*(1-t)+q.x*t;p.y=p.y*(1-t)+q.y*t;return p
# Retain the established facial weights wherever the original geometry already matched.
oldtree=KDTree(len(old['positions']))
for i,p in enumerate(old['positions']):oldtree.insert(p,i)
oldtree.balance()
d={k:old[k] for k in ('binding_source','skeleton','bones','material_slots')};d.update(positions=[],weights=[],triangles=[],uv=[],normals=[],triangle_materials=[])
lookup={};kept=0;fitted=0;max_delta=0
for t in tris:
 polygon=[(Vector(pos[i]),Vector(norm[i]),Vector(uv[i])) for i in t]
 clipped=[]
 for i,cur in enumerate(polygon):
  prev=polygon[i-1];inside=cur[0].z>=139.1;was=prev[0].z>=139.1
  if inside!=was:
   s=(139.1-prev[0].z)/(cur[0].z-prev[0].z);clipped.append((prev[0].lerp(cur[0],s),prev[1].lerp(cur[1],s).normalized(),prev[2].lerp(cur[2],s)))
  if inside:clipped.append(cur)
 for k in range(1,len(clipped)-1):
  corners=[clipped[0],clipped[k],clipped[k+1]];face=[]
  for p,n,tex in corners:
   q=fit(p);key=tuple(round(x,7) for x in (*p,*tex,*n))
   if key not in lookup:
    lookup[key]=len(d['positions']);d['positions'].append(list(q));_,oi,dist=oldtree.find(q)
    d['weights'].append(old['weights'][oi] if q.z>=149 and dist<.0001 else weights(q))
    if p.z>=142.5:kept+=1;max_delta=max(max_delta,(q-p).length)
    else:fitted+=1
   face.append(lookup[key])
  c=sum((p for p,n,tex in corners),Vector())/3
  eye=((abs(c.x)-3.05)/1.7)**2+((c.z-157.43)/.78)**2<1 and c.y>6.1
  lip=(c.x/2.7)**2+((c.z-150.72)/.9)**2<1 and c.y>7.8
  d['triangles'].append(face);d['uv'].append([list(tex) for p,n,tex in corners]);d['normals'].append([list(n) for p,n,tex in corners]);d['triangle_materials'].append(2 if eye or lip else 1 if c.z<145 else 0)
(O/'head.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
report={'source_glb_sha256':hashlib.sha256(raw).hexdigest(),'preserved_above_z_cm':142.5,'preserved_vertices':kept,'preserved_max_displacement_cm':max_delta,'fitted_lower_neck_vertices':fitted,'fit_range_z_cm':[139.1,142.5],'triangles':len(d['triangles']),'original_lip_microgeometry_preserved':True,'original_face_normals_uv_preserved':True}
(R/'restoration.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('FULL_MESHY_FACE_RESTORED',json.dumps(report),flush=True)
# The collar follows the restored neck; it no longer forces the face into its radius.
(R/'Inputs').mkdir(exist_ok=True);(R/'Inputs/current_trim.json').write_bytes((N/'RefinementR4/Inputs/current_trim.json').read_bytes())
code=(P/'Tools/ChapelNun/repair_collar_envelope.py').read_text().replace("R=N/'RefinementR4'","R=N/'FaceOriginalRestoreR6'")
exec(compile(code,'<restored face collar>','exec'))
