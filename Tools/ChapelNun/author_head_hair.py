"""Author the Meshy face on Kaitlin's real neck and a separate low-bun strand groom."""
import bpy,bmesh,json,math,random
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/ProductionR1'
O=R/'Authored';O.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
bpy.ops.wm.read_factory_settings(use_empty=True)
native=read(R/'Inputs/native_head.json');src=read(R/'Inputs/meshy_head.json')
ids=sorted({i for t,m in zip(native['triangles'],native['triangle_materials']) if m==0 for i in t})
tree=KDTree(len(ids))
for k,i in enumerate(ids):tree.insert(native['positions'][i],i)
tree.balance()
def weights(p):
 accum={}
 for _,i,dist in tree.find_n(p,4):
  factor=1/max(dist,.03)**2
  for b,w in native['weights'][i]:accum[b]=accum.get(b,0)+w*factor
 pairs=sorted(accum.items(),key=lambda x:-x[1])[:8];total=sum(w for _,w in pairs)
 return {b:w/total for b,w in pairs}
def bm_from(points,faces,uvs,mat=0,skin_weights=None):
 bm=bmesh.new();uv=bm.loops.layers.uv.new('UVMap');dw=bm.verts.layers.deform.new()
 vs=[bm.verts.new(p) for p in points]
 for i,v in enumerate(vs):
  for b,w in (dict(skin_weights[i]) if skin_weights else weights(v.co)).items():v[dw][int(b)]=w
 for t,tex in zip(faces,uvs):
  f=bm.faces.new([vs[i] for i in t]);f.material_index=mat
  for l,xy in zip(f.loops,tex):l[uv].uv=xy
 return bm
# Meshy is -Y forward in Blender; native Kaitlin is +Y forward, in centimetres.
p=np.asarray(src['positions']);p*=15.8;p[:,1]*=-1;p+=np.array([0,1.4,168.0523223876953-0.94961101*15.8])
faces=[t[::-1] for t in src['triangles']];uvs=[t[::-1] for t in src['uv']]
bm=bm_from(p,faces,uvs)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,145.0),plane_no=(0,0,1),clear_inner=True,dist=1e-6)
# The lower neck is retained from the actual native head, including its body interface.
sel=[i for i,m in enumerate(native['triangle_materials']) if m==0]
nfaces=[native['triangles'][i][::-1] for i in sel];nuvs=[[[a,1-b] for a,b in native['uv'][i][::-1]] for i in sel]
nb=bm_from(native['positions'],nfaces,nuvs,1,native['weights'])
bmesh.ops.bisect_plane(nb,geom=list(nb.verts)+list(nb.edges)+list(nb.faces),plane_co=(0,0,144.5),plane_no=(0,0,1),clear_outer=True,dist=1e-6)
bmesh.ops.delete(nb,geom=[v for v in nb.verts if not v.link_faces],context='VERTS')
# Ease only the neck transition; preserve the Meshy face and cranium.
near=[v for v in nb.verts if abs(v.co.z-144.5)<.002]
ring=sorted(near,key=lambda v:math.atan2(v.co.y-1.0,v.co.x))
angles=np.array([math.atan2(v.co.y-1.0,v.co.x) for v in ring])
def contour(theta):
 k=int(np.searchsorted(angles,theta));a=ring[(k-1)%len(ring)].co;b=ring[k%len(ring)].co
 ta=angles[(k-1)%len(ring)];tb=angles[k%len(ring)]
 if tb<ta:tb+=math.tau
 if theta<ta:theta+=math.tau
 return a.lerp(b,(theta-ta)/max(tb-ta,1e-6))
for v in bm.verts:
 if v.co.z<149.0:
  q=contour(math.atan2(v.co.y-1.0,v.co.x));t=max(0,min(1,(149.0-v.co.z)/4));t=t*t*(3-2*t)
  v.co.x=v.co.x*(1-t)+q.x*t;v.co.y=v.co.y*(1-t)+q.y*t
# Merge native neck into the author mesh, preserving its UVs and exact bindings.
uv=bm.loops.layers.uv.active;dw=bm.verts.layers.deform.active
nuv=nb.loops.layers.uv.active;ndw=nb.verts.layers.deform.active;mapping={}
for v in nb.verts:
 out=bm.verts.new(v.co);mapping[v]=out
 for bi,w in v[ndw].items():out[dw][bi]=w
for f in nb.faces:
 out=bm.faces.new([mapping[v] for v in f.verts]);out.material_index=1
 for a,b in zip(out.loops,f.loops):a[uv].uv=b[nuv].uv
nb.free()
upper=sorted([v for v in bm.verts if abs(v.co.z-145)<.002 and any(e.is_boundary for e in v.link_edges)],key=lambda v:math.atan2(v.co.y-1,v.co.x))
lower=sorted([v for v in bm.verts if abs(v.co.z-144.5)<.002 and any(e.is_boundary for e in v.link_edges)],key=lambda v:math.atan2(v.co.y-1,v.co.x))
# Zip the two independently sampled neck rings. They remain separated by 5 mm.
ua=[math.atan2(v.co.y-1,v.co.x) for v in upper];la=[math.atan2(v.co.y-1,v.co.x) for v in lower]
i=j=0
while i<len(upper) or j<len(lower):
 an=ua[(i+1)%len(upper)]+(math.tau if i+1>=len(upper) else 0)
 bn=la[(j+1)%len(lower)]+(math.tau if j+1>=len(lower) else 0)
 if i<len(upper) and (j>=len(lower) or an<=bn):
  verts=[upper[i%len(upper)],upper[(i+1)%len(upper)],lower[j%len(lower)]];i+=1
 else:
  verts=[upper[i%len(upper)],lower[(j+1)%len(lower)],lower[j%len(lower)]];j+=1
 f=bm.faces.new(verts);f.material_index=1
 # Use the adjoining native neck UV to keep the seam within the collar.
 for l in f.loops:
  candidate=min(lower,key=lambda v:(v.co-l.vert.co).length_squared)
  found=next((lp for lp in candidate.link_loops if lp.face.material_index==1 and lp.face!=f),None)
  l[uv].uv=found[uv].uv if found else (.5,.5)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
me=bpy.data.meshes.new('NunHead');bm.to_mesh(me);bm.free()
head=bpy.data.objects.new('SK_NunHead',me);bpy.context.collection.objects.link(head)
# Store the full native face hierarchy; runtime shared body bones drive its neck.
for bone in native['bones']:head.vertex_groups.new(name=bone['name'])
for f in me.polygons:f.use_smooth=True
bpy.context.view_layer.objects.active=head;head.select_set(True)
me.calc_loop_triangles()
d=dict(binding_source=native['source'],skeleton=native['skeleton'],bones=native['bones'],positions=[list(v.co) for v in me.vertices],weights=[[[g.group,g.weight] for g in v.groups] for v in me.vertices],triangles=[],uv=[],normals=[],triangle_materials=[],material_slots=['NunSkin','NativeNeck'])
for t in me.loop_triangles:
 order=list(t.loops)[::-1]
 d['triangles'].append(list(t.vertices)[::-1]);d['uv'].append([[me.uv_layers.active.data[k].uv.x,1-me.uv_layers.active.data[k].uv.y] for k in order]);d['normals'].append([list(me.vertices[me.loops[k].vertex_index].normal) for k in order]);d['triangle_materials'].append(t.material_index)
(O/'head.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
# Groom roots and comb paths use the new cranium surface, not the former head.
bvh=BVHTree.FromPolygons([v.co for v in me.vertices],[tuple(f.vertices) for f in me.polygons],all_triangles=True)
center=Vector((0,0.1,158.9))
def scalp(theta,phi,lift=0):
 direction=Vector((math.sin(phi)*math.sin(theta),math.sin(phi)*math.cos(theta),math.cos(phi)))
 point,normal,index,dist=bvh.ray_cast(center,direction,40)
 if point is None:raise RuntimeError('Cranium projection failed')
 return point+direction*lift
rng=random.Random(151115)
def make_groom(name,count,loose):
 curves=bpy.data.curves.new(name,'CURVE');curves.dimensions='3D';curves.resolution_u=1
 obj=bpy.data.objects.new(name,curves);bpy.context.collection.objects.link(obj);obj['groom_group_id']=0;obj['groom_guide']=0
 for k in range(count):
  theta=rng.uniform(-math.pi,math.pi)
  limit=1.32+.76*(abs(theta)/math.pi)**.70
  phi=math.acos(rng.uniform(math.cos(limit),1))
  root=scalp(theta,phi,.035)
  side=-1 if root.x<-.7 else 1
  endtheta=side*(math.pi-rng.uniform(.02,.23));endphi=rng.uniform(2.02,2.20)
  phase=rng.random()*math.tau;wave=rng.uniform(.01,.045);points=[]
  if loose:
   # Short temple/nape flyaways; strongly rooted with softly free ends.
   theta=side*rng.uniform(.75,2.75);phi=rng.uniform(1.15,1.90);root=scalp(theta,phi,.06)
   length=rng.uniform(2.2,7.0);n=24
   tangent=Vector((side*.28,-.65,-.7)).normalized()
   for j in range(n):
    t=j/(n-1);point=root+tangent*(length*t)+Vector((side*.55*math.sin(t*2),-.5*t*t,.45*math.sin(t*math.pi)))
    # Keep the root zone outside the head.
    if t<.4:
     delta=point-center;hit=scalp(math.atan2(delta.x,delta.y),math.acos(delta.z/delta.length),.06+.08*t)
     point=hit.lerp(point,t/.4)
    point.x+=.055*math.sin(phase+t*7)*t
    points.append(point)
  else:
   n=48;bun=Vector((0,-10.4,150.8));radius=rng.uniform(1.4,3.35);coil_start=side*math.pi*.55+rng.uniform(-.35,.35)
   for j in range(n):
    t=j/(n-1)
    if t<=.66:
     u=t/.66
     # Off-centre part fans around the head and collects at the nape.
     a=theta+(endtheta-theta)*(u*u*(3-2*u));f=phi+(endphi-phi)*u
     lift=.035+.30*math.sin(math.pi*u)+wave*math.sin(phase+u*18)*math.sin(math.pi*u)
     point=scalp(a,f,lift)
    else:
     u=(t-.66)/.34;angle=coil_start+side*u*math.tau*1.25
     coil=bun+Vector((radius*math.sin(angle),-1.45*math.sin(math.pi*u),radius*.70*math.cos(angle)))
     start=scalp(endtheta,endphi,.05)
     blend=min(1,u/.30);blend=blend*blend*(3-2*blend)
     point=start.lerp(coil,blend)
    points.append(point)
  spline=curves.splines.new('POLY');spline.points.add(n-1)
  spline.points.foreach_set('co',[c for pt in points for c in (*pt,1.)])
  for j,pnt in enumerate(spline.points):pnt.radius=.006*(1-.75*(j/(n-1))**3)
 print('NUN_GROOM_AUTHORED',name,count,flush=True)
 return obj
core=make_groom('Nun_LowBun_Core',38000,False)
loose=make_groom('Nun_LowBun_Loose',1400,True)
for obj in (core,loose):
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 bpy.ops.wm.alembic_export(filepath=str(O/(obj.name+'.abc')),start=1,end=1,selected=True,as_background_job=False,export_custom_properties=True,curves_as_mesh=False,global_scale=1.0)
bpy.ops.object.select_all(action='DESELECT');head.select_set(True);bpy.context.view_layer.objects.active=head
# Material previews are packed source textures; no scene rendering is performed.
mat=bpy.data.materials.new('Nun_Skin_Source');mat.use_nodes=True
nt=mat.node_tree;shader=nt.nodes.get('Principled BSDF');tex=nt.nodes.new('ShaderNodeTexImage')
tex.image=bpy.data.images.load(str(P/'SourceAssets/ChapelNun20261115/MeshyHeadR1/Source/NunHead_R1_M00_base_color.png'));tex.image.pack();nt.links.new(tex.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Roughness'].default_value=.52
head.data.materials.append(mat);head.data.materials.append(mat)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Nun_Head_Hair.blend'))
(O/'head_hair_receipt.json').write_text(json.dumps(dict(head='head.json',blend='Nun_Head_Hair.blend',core='Nun_LowBun_Core.abc',loose='Nun_LowBun_Loose.abc',core_strands=38000,loose_strands=1400,original_head_triangles=len(src['triangles']),authored_head_triangles=len(d['triangles']),neck='native interface retained; 144.5-145 cm connection',groom_coordinates='Blender centimetres; Alembic Y-up; import Euler rotation X=-90, unit scale 1',tested=False),indent=2),encoding='utf-8')
print('NUN_HEAD_HAIR_EXPORTED',flush=True)
