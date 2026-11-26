"""Resolve the collar against every visible robe layer and the native neck."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,geometry
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');R=N/'RefinementR4';O=R/'Authored';read=lambda p:json.loads(p.read_text())
head=read(O/'head.json');robe=read(N/'ProductionR1/Inputs/native_robe.json');old=read(R/'Inputs/current_trim.json')
def tree(d,keep):return BVHTree.FromPolygons([Vector(p) for p in d['positions']],[t[::-1] for t,m in zip(d['triangles'],d['triangle_materials']) if keep(m)],all_triangles=True)
supports=[tree(head,lambda m:True),tree(robe,lambda m:m!=9)]
weights_tree=KDTree(len(robe['positions']))
for i,p in enumerate(robe['positions']):weights_tree.insert(p,i)
weights_tree.balance()
def skin(p):
 a={}
 for _,i,d in weights_tree.find_n(p,4):
  for b,w in robe['weights'][i]:a[b]=a.get(b,0)+w/max(.04,d)**2
 q=sorted(a.items(),key=lambda x:-x[1])[:8];s=sum(w for b,w in q);return [[b,w/s] for b,w in q]
A=192;B=24;radius=np.zeros((B+1,A));zs=np.zeros_like(radius)
for j in range(B+1):
 for i in range(A):
  angle=math.tau*i/A;z=143.8-j/B*(5.25+1.5*max(0,math.cos(angle)));direction=Vector((math.sin(angle),math.cos(angle),0));origin=Vector((0,1.3,z));rs=[]
  for s in supports:
   p,n,k,d=s.ray_cast(origin+direction*24,-direction,24)
   if p is not None:rs.append((p-origin).dot(direction))
  if not rs:raise RuntimeError('Missing support')
  radius[j,i]=max(rs)+.50;zs[j,i]=z
# Smooth an outward maximum envelope; no averaging through a supporting layer.
raw=radius.copy()
for _ in range(2):
 padded=np.pad(radius,((1,1),(0,0)),mode='edge')
 radius=np.maximum.reduce([np.roll(padded[1+dy:B+2+dy],dx,axis=1) for dy in (-1,0,1) for dx in (-1,0,1)])
for _ in range(4):
 padded=np.pad(radius,((1,1),(0,0)),mode='edge')
 radius=(radius*4+np.roll(radius,1,1)+np.roll(radius,-1,1)+padded[:-2]+padded[2:])/8
 radius=np.maximum(radius,raw)
ps=[];faces=[];uvs=[]
for j in range(B+1):
 for i in range(A):
  angle=math.tau*i/A;ps.append((radius[j,i]*math.sin(angle),1.3+radius[j,i]*math.cos(angle),zs[j,i]))
for j in range(B):
 for i in range(A):
  k=(i+1)%A;faces.append((j*A+i,j*A+k,(j+1)*A+k,(j+1)*A+i));uvs.append([(i/A,j/B),((i+1)/A,j/B),((i+1)/A,(j+1)/B),(i/A,(j+1)/B)])
if not globals().get('KEEP_AUTHOR_SCENE',False):bpy.ops.wm.read_factory_settings(use_empty=True)
me=bpy.data.meshes.new('NunLinenFinal');me.from_pydata(ps,[],faces);me.update();me.uv_layers.new(name='UVMap')
for f,uv in zip(me.polygons,uvs):
 f.use_smooth=True
 for li,xy in zip(f.loop_indices,uv):me.uv_layers.active.data[li].uv=xy
ob=bpy.data.objects.new('SK_Nun_CollarCross',me);bpy.context.collection.objects.link(ob);ob.select_set(True);bpy.context.view_layer.objects.active=ob
solid=ob.modifiers.new('ContinuousClothThickness','SOLIDIFY');solid.thickness=.12;solid.offset=-1;solid.use_even_offset=True;bpy.ops.object.modifier_apply(modifier=solid.name)
me=ob.data;me.calc_loop_triangles();out={k:old[k] for k in ('bones','skeleton')};out.update(binding_source=robe['source'],material_slots=['IvoryLinen','BlackCord','WornIron'],positions=[list(v.co) for v in me.vertices],weights=[skin(v.co) for v in me.vertices],triangles=[],uv=[],normals=[],triangle_materials=[])
for t in me.loop_triangles:
 order=list(t.loops)[::-1];out['triangles'].append(list(t.vertices)[::-1]);out['uv'].append([[me.uv_layers.active.data[i].uv.x,1-me.uv_layers.active.data[i].uv.y] for i in order]);out['normals'].append([list(me.corner_normals[i].vector) for i in order]);out['triangle_materials'].append(0)
base=len(out['positions']);out['positions']+=old['positions'];out['weights']+=old['weights']
for t,uv,n,m in zip(old['triangles'],old['uv'],old['normals'],old['triangle_materials']):
 if m==0:continue
 out['triangles'].append([i+base for i in t]);out['uv'].append(uv);out['normals'].append(n);out['triangle_materials'].append(m)
(O/'trim.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
report={}
for label,d,keep in [('neck',head,lambda m:True),('robe',robe,lambda m:m!=9)]:
 a=[t for t,m in zip(out['triangles'],out['triangle_materials']) if m==0];b=[t for t,m in zip(d['triangles'],d['triangle_materials']) if keep(m)]
 ta=BVHTree.FromPolygons([Vector(p) for p in out['positions']],a,all_triangles=True);tb=BVHTree.FromPolygons([Vector(p) for p in d['positions']],b,all_triangles=True);pairs=ta.overlap(tb);hits=0
 for ia,ib in pairs:
  av=[Vector(out['positions'][i]) for i in a[ia]];bv=[Vector(d['positions'][i]) for i in b[ib]];intersects=False
  for edges,tri in [(av,bv),(bv,av)]:
   for i,p in enumerate(edges):
    vec=edges[(i+1)%3]-p;dist=vec.length
    if dist<1e-7:continue
    point=geometry.intersect_ray_tri(*tri,vec.normalized(),p,True)
    if point is not None and 1e-5<(point-p).dot(vec.normalized())<dist-1e-5:intersects=True;break
   if intersects:break
  hits+=int(intersects)
 report[label]={'candidate_pairs':len(pairs),'triangle_segment_intersections':hits}
(R/'collar_geometry_final.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('FINAL_COLLAR',json.dumps(report),flush=True)
if globals().get('KEEP_AUTHOR_SCENE',False):bpy.data.objects.remove(ob,do_unlink=True)
