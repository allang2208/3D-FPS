"""Continue the original Meshy neck below its cut, retaining its own PBR UVs/normals."""
import bpy,json,math,bisect
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
P=Path('D:/FPS3D/FPSGAME');N=P/'SourceAssets/ChapelNun20261115';R=N/'RefinementR4';O=R/'Authored'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
d=read(O/'head.json');native=read(N/'ProductionR1/Inputs/native_head.json');old=read(N/'OriginalMeshyFaceR3/Authored/head.json')
ring_ids={i for t,m in zip(old['triangles'],old['triangle_materials']) if m==1 for i in t if abs(old['positions'][i][2]-144.5)<.002}
ring=sorted([Vector(old['positions'][i]) for i in ring_ids],key=lambda p:math.atan2(p.y-1,p.x));angles=[math.atan2(p.y-1,p.x) for p in ring]
ids=sorted({i for t,m in zip(native['triangles'],native['triangle_materials']) if m==0 for i in t});tree=KDTree(len(ids))
for i,vi in enumerate(ids):tree.insert(native['positions'][vi],vi)
tree.balance()
def weights(p):
 acc={}
 for _,i,dist in tree.find_n(p,4):
  for b,w in native['weights'][i]:acc[b]=acc.get(b,0)+w/max(dist,.03)**2
 pairs=sorted(acc.items(),key=lambda x:-x[1])[:8];total=sum(w for b,w in pairs);return [[b,w/total] for b,w in pairs]
def fit(p):
 p=p.copy();theta=math.atan2(p.y-1,p.x);k=bisect.bisect_left(angles,theta);a=ring[(k-1)%len(ring)];b=ring[k%len(ring)];ta=angles[(k-1)%len(ring)];tb=angles[k%len(ring)]
 if tb<ta:tb+=math.tau
 if theta<ta:theta+=math.tau
 q=a.lerp(b,(theta-ta)/max(1e-6,tb-ta));t=max(0,min(1,(149-p.z)/4));t=t*t*(3-2*t);p.x=p.x*(1-t)+q.x*t;p.y=p.y*(1-t)+q.y*t;return p
before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(N/'MeshyHeadR1/Source/NunHead_R1_glb.glb'))
ob=next(o for o in bpy.data.objects if o not in before and o.type=='MESH');bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
me=ob.data;me.calc_loop_triangles();offset=168.0523223876953-.94961101*15.8
rows=[(t,uv,n,m) for t,uv,n,m in zip(d['triangles'],d['uv'],d['normals'],d['triangle_materials']) if m!=1]
d.update(triangles=[x[0] for x in rows],uv=[x[1] for x in rows],normals=[x[2] for x in rows],triangle_materials=[x[3] for x in rows]);added=0;lookup={}
for face in me.loop_triangles:
 poly=[]
 for li in face.loops:
  v=me.vertices[me.loops[li].vertex_index];n=me.corner_normals[li].vector;uv=me.uv_layers.active.data[li].uv
  poly.append((Vector((v.co.x*15.8,-v.co.y*15.8+1.4,v.co.z*15.8+offset)),Vector((n.x,-n.y,n.z)),Vector((uv.x,1-uv.y))))
 for bound,above in ((139.1,True),(145.,False)):
  clipped=[]
  for i,cur in enumerate(poly):
   prev=poly[i-1];inside=cur[0].z>=bound if above else cur[0].z<=bound;was=prev[0].z>=bound if above else prev[0].z<=bound
   if inside!=was:
    t=(bound-prev[0].z)/(cur[0].z-prev[0].z);clipped.append((prev[0].lerp(cur[0],t),prev[1].lerp(cur[1],t).normalized(),prev[2].lerp(cur[2],t)))
   if inside:clipped.append(cur)
  poly=clipped
  if not poly:break
 for i in range(1,len(poly)-1):
  corners=[poly[0],poly[i],poly[i+1]];tri=[]
  for p,n,uv in corners:
   p=fit(p);key=tuple(round(v,7) for v in p)
   if key not in lookup:lookup[key]=len(d['positions']);d['positions'].append(list(p));d['weights'].append(weights(p))
   tri.append(lookup[key])
  d['triangles'].append(tri);d['normals'].append([list(n) for p,n,uv in corners]);d['uv'].append([list(uv) for p,n,uv in corners]);d['triangle_materials'].append(1);added+=1
for ob in list(bpy.data.objects):
 if ob not in before:bpy.data.objects.remove(ob,do_unlink=True)
d['material_slots'][1]='MeshyOriginalNeck';(O/'head.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
(R/'neck_source.json').write_text(json.dumps({'source':'Original Meshy GLB','added_triangles':added,'visible_face_unchanged':True,'material':'Original Meshy PBR, including original normal map','native_lower_shoulder_skin_removed':True},indent=2),encoding='utf-8')
print('ORIGINAL_NECK_CONTINUED',added,flush=True)
