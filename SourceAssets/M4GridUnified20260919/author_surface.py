"""Rebuild only the added grille as a sampled factory surface, not warped triangles."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
O=Path(__file__).parent;S=O.parent;sys.path.insert(0,str(S/'ExtMagPattern20260919'));from export_tangents import export
bpy.ops.wm.open_mainfile(filepath=str(S/'ExtMagRebuild20260919/M4_ExtMag_Editable.blend'));src=bpy.data.objects['Factory_M4'];mesh=src.data.copy();ob=bpy.data.objects.new('SM_M4_ExtMag40_Grid',mesh);bpy.context.collection.objects.link(ob)
for o in list(bpy.context.scene.objects):
 if o!=ob:bpy.data.objects.remove(o,do_unlink=True)
ob.hide_render=False;ob.hide_set(False)
cfg=json.loads((S/'ExtMagPattern20260919/parameters.json').read_text())['M4'];cy,cz=cfg['center_yz'];R=cfg['radius_cm']/100;xc=(min(v.co.x for v in mesh.vertices)+max(v.co.x for v in mesh.vertices))/2;top=max((v.co for v in mesh.vertices),key=lambda p:p.z);tt=math.atan2(top.z-cz,top.y-cy);cut=.1115;period=.0125;extension=.0625

def unroll(p):
 t=math.atan2(p.z-cz,p.y-cy);return Vector((p.x-xc,math.hypot(p.y-cy,p.z-cz)-R,math.atan2(math.sin(t-tt),math.cos(t-tt))*R))
def roll(q):
 t=tt+q.z/R;r=R+q.y;return Vector((q.x+xc,cy+r*math.cos(t),cz+r*math.sin(t)))
mesh.calc_loop_triangles();tris=list(mesh.loop_triangles);qp=[unroll(v.co) for v in mesh.vertices];uv0=[l.uv.copy() for l in mesh.uv_layers[0].data];cn=[n.vector.copy() for n in mesh.corner_normals];tree=BVHTree.FromPolygons(qp,[tuple(t.vertices) for t in tris],all_triangles=True)
outer_ids=[]
for i,tr in enumerate(tris):
 a,b,c=[qp[v] for v in tr.vertices];n=(b-a).cross(c-a);center=(a+b+c)/3
 if n.x*center.x+n.y*center.y>0:outer_ids.append(i)
outer_tree=BVHTree.FromPolygons(qp,[tuple(tris[i].vertices) for i in outer_ids],all_triangles=True)
def sample_axis(q,s,axis):
 target=q.copy();target.z=s;direction=Vector((0,0,0));direction[axis]=1 if q[axis]>=0 else -1
 point,n,idx,dist=outer_tree.ray_cast(target+direction*.01,-direction,.02)
 if point is None or (point.xy-target.xy).length>.004:point,n,idx,dist=outer_tree.find_nearest(target)
 i=outer_ids[idx]
 tr=tris[i];w=barycentric_transform(point,*[qp[v] for v in tr.vertices],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
 uv=sum((uv0[l]*f for l,f in zip(tr.loops,w)),Vector((0,0)));normal=sum((cn[l]*f for l,f in zip(tr.loops,w)),Vector()).normalized()
 return point.xy,uv,normal
bm=bmesh.new();bm.from_mesh(mesh);uv=bm.loops.layers.uv.active;nl=bm.loops.layers.float_vector.new('SourceNormal')
for f in bm.faces:
 for l,i in zip(f.loops,mesh.polygons[f.index].loop_indices):l[nl]=cn[i]
for v in bm.verts:v.co=unroll(v.co)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,cut),plane_no=(0,0,1),dist=1e-7)
def cutedges():return [e for e in bm.edges if all(abs(v.co.z-cut)<2e-6 for v in e.verts) and len(e.link_faces)==2]
# Dense perimeter preserves narrow longitudinal ribs; respect actual loop order.
for edge in list(cutedges()):
 a,b=edge.verts;count=max(1,math.ceil((a.co-b.co).length/.001));current=a
 for k in range(1,count):
  e=next(e for e in current.link_edges if e.other_vert(current)==b);_,current=bmesh.utils.edge_split(e,current,1/(count-k+1))
lower={f for f in bm.faces if f.calc_center_median().z>cut+1e-8};records=[]
for edge in cutedges():
 f=next((f for f in edge.link_faces if f not in lower),None)
 if not f:continue
 l=next(l for l in f.loops if l.edge==edge);records.append((l.vert,l.link_loop_next.vert))
ring={v for a,b in records for v in (a,b)};endring={v:bm.verts.new(v.co+Vector((0,0,extension))) for v in ring}
turn=Matrix.Rotation(extension/R,3,'X')
for f in lower:
 for l in f.loops:l[nl]=turn@l[nl]
for v in {v for f in lower for v in f.verts}-ring:v.co.z+=extension
for f in list(lower):
 if not any(v in ring for v in f.verts):continue
 vs=[endring.get(l.vert,l.vert) for l in f.loops];data=[(l[uv].uv.copy(),l[nl].copy()) for l in f.loops];bm.faces.remove(f);nf=bm.faces.new(vs);nf.smooth=True
 for l,(u,n) in zip(nf.loops,data):l[uv].uv=u;l[nl]=n
# Identify entire contour loops, never switch shell identity at a groove corner.
adj={v:set() for v in ring}
for a,b in records:adj[a].add(b);adj[b].add(a)
unseen=set(ring);groups=[]
while unseen:
 seed=unseen.pop();stack=[seed];group={seed}
 while stack:
  for v in adj[stack.pop()]:
   if v in unseen:unseen.remove(v);group.add(v);stack.append(v)
 groups.append(group)
outer_group=max(groups,key=lambda g:(max(v.co.x for v in g)-min(v.co.x for v in g))*(max(v.co.y for v in g)-min(v.co.y for v in g)))
print('SHELL_BOUNDS',[(len(g),g==outer_group,[[min(v.co[k] for v in g),max(v.co[k] for v in g)] for k in (0,1)]) for g in groups],flush=True)
params={}
for v in ring:
 inner=v not in outer_group
 point,n,i,d=tree.find_nearest(v.co)
 axis=0 if abs(n.x)>=abs(n.y) else 1
 try:a=sample_axis(v.co,cut-period,axis)[0];b=sample_axis(v.co,cut,axis)[0]
 except RuntimeError:
  axis=1-axis;a=sample_axis(v.co,cut-period,axis)[0];b=sample_axis(v.co,cut,axis)[0]
 params[v]=(v.co.copy(),inner,axis,a,b)
steps_per_period=24;steps=steps_per_period*5;rings=[{v:v for v in ring}];values={}
for k in range(steps+1):
 t=(k%steps_per_period)/steps_per_period
 # Upper edge of each new unit comes from the same quiet source phase.
 donor=cut-period+t*period
 rmap=endring if k==steps else rings[0] if k==0 else {}
 for v,(q0,inside,axis,a,b) in params.items():
  h,u,n=sample_axis(q0,donor,axis);smooth=t*t*(3-2*t);q=q0.copy();q.z=cut+k*extension/steps
  if not inside:
   delta=h-((1-smooth)*a+smooth*b);q.x+=delta.x;q.y+=delta.y
  if k not in (0,steps):rmap[v]=bm.verts.new(q)
  n=Matrix.Rotation((cut+k*extension/steps-donor)/R,3,'X')@n;values[k,v]=(u,n)
 if k>0:rings.append(rmap)
for k in range(steps):
 for a,b in records:
  face=bm.faces.new((rings[k][b],rings[k][a],rings[k+1][a],rings[k+1][b]));face.smooth=True
  for l,(j,v) in zip(face.loops,((k,b),(k,a),(k+1,a),(k+1,b))):l[uv].uv,l[nl]=values[j,v]
for v in bm.verts:v.co=roll(v.co)
# Remove sub-millimetre sampling steps along bevels while preserving the factory
# seam loops, grille period, broad faces and original floorplate.
polish=[v for v in bm.verts if cut+.001<unroll(v.co).z<cut+extension-.001]
for _ in range(3):bmesh.ops.smooth_vert(bm,verts=polish,factor=.22,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bmesh.ops.triangulate(bm,faces=list(bm.faces));norm=[l[nl].normalized() for f in bm.faces for l in f.loops];bm.to_mesh(mesh);bm.free();mesh.update();mesh.normals_split_custom_set(norm)
# New dense sampling defines smooth quads without the old triangulation warp.
# Derive their actual normals instead of reusing a different source tangent plane.
mesh.normals_split_custom_set([(0,0,0)]*len(mesh.loops));mesh.update();geonorm=[n.vector.copy() for n in mesh.corner_normals]
for i,l in enumerate(mesh.loops):
 s=unroll(mesh.vertices[l.vertex_index].co).z
 if cut<s<cut+extension:
  w=min(1,(s-cut)/.001,(cut+extension-s)/.001);norm[i]=norm[i].lerp(geonorm[i],w).normalized()
mesh.normals_split_custom_set(norm)
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_ExtMag_Remodel_Editable.blend'))
cfg.update(cut_s_cm=cut*100,period_cm=period*100,extension_cm=extension*100,method='Factory grille ray-resampling; same groove profile and corner normals; separate inner shell')
(O/'parameters.json').write_text(json.dumps({'M4':cfg},indent=2));print('GRID_RESAMPLED',len(mesh.vertices),flush=True)
