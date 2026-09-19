"""ASH-only curved shell extension; factory feed, grip and floorplate retained."""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
O=Path(__file__).parent;S=O.parent;report={};gun='ASH12'
sys.path.insert(0,str(S/'ExtMagPattern20260919'));from export_tangents import export
bpy.ops.wm.open_mainfile(filepath=str(S/'ASH12Surface20260919/ASH12_Surface_Editable.blend'))
gun=bpy.data.objects['ASH12_Export'];F=Matrix(json.loads((O/'source_measurements.json').read_text())['matrix']);inv=F.inverted()
# Shared circle center from the two actual shell silhouettes (exclude throat/base).
rows=json.loads((O/'sections.json').read_text());a=[];b=[]
for z,front,back in rows:
 for side,x in enumerate((front,back)):
  a.append([2*x,2*z,float(side==0),float(side==1)]);b.append(x*x+z*z)
cx,cz,c0,c1=np.linalg.lstsq(a,b,rcond=None)[0];R=float((math.sqrt(c0+cx*cx+cz*cz)+math.sqrt(c1+cx*cx+cz*cz))/2)
cut=0.;extension=.075;period=.025;theta=math.asin((-.165-cz)/R)
# This magazine is on the positive-X side of the fitted center; increasing s runs down.
def unroll(p):
 v=F@p;t=math.atan2(v.z-cz,v.x-cx)
 return Vector((v.y,math.hypot(v.x-cx,v.z-cz)-R,(theta-t)*R))
def roll(q):
 t=theta-q.z/R;r=R+q.y
 return inv@Vector((cx+r*math.cos(t),q.x,cz+r*math.sin(t)))
slots=[i for i,m in enumerate(gun.data.materials) if 'Magazine' in m.name]
mesh=gun.data.copy();ob=bpy.data.objects.new('SM_ASH12_ExtMag30',mesh);bpy.context.collection.objects.link(ob)
bm=bmesh.new();bm.from_mesh(mesh);nl=bm.loops.layers.float_vector.new('FactoryCornerNormal')
for f in bm.faces:
 for l,i in zip(f.loops,mesh.polygons[f.index].loop_indices):l[nl]=mesh.corner_normals[i].vector
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index not in slots],context='FACES')
for f in bm.faces:f.material_index=slots.index(f.material_index)
materials=[gun.data.materials[i] for i in slots];mesh.materials.clear()
for m in materials:mesh.materials.append(m)
bm.to_mesh(mesh);bm.free();mesh.update()
gun='ASH12'
# Keep an untouched editable factory copy in the source file.
factory=ob.copy();factory.data=mesh.copy();factory.name='Factory_ASH12_Magazine';bpy.context.collection.objects.link(factory);factory.hide_render=True;factory.hide_set(True)
mesh.calc_loop_triangles();tris=list(mesh.loop_triangles);

qpts=[unroll(v.co) for v in mesh.vertices];uvs=[x.uv.copy() for x in mesh.uv_layers.active.data]
tree=BVHTree.FromPolygons(qpts,[tuple(t.vertices) for t in tris],all_triangles=True)
def uv_at(q):
 point,n,i,d=tree.find_nearest(q);t=tris[i]
 return barycentric_transform(point,*[qpts[v] for v in t.vertices],*[Vector((*uvs[l],0)) for l in t.loops]).xy
bm=bmesh.new();bm.from_mesh(mesh);uv=bm.loops.layers.uv.active;nl=bm.loops.layers.float_vector.get('FactoryCornerNormal')
for v in bm.verts:v.co=unroll(v.co)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,cut),plane_no=(0,0,1),dist=1e-7)
lower={f for f in bm.faces if f.calc_center_median().z>cut+1e-8}
edges=[e for e in bm.edges if all(abs(v.co.z-cut)<2e-6 for v in e.verts) and any(f in lower for f in e.link_faces) and any(f not in lower for f in e.link_faces)]
records=[]
for e in edges:
 f=next(f for f in e.link_faces if f not in lower);l=next(l for l in f.loops if l.edge==e);records.append((l.vert,l.link_loop_next.vert))
ring={v for a,b in records for v in (a,b)};endring={v:bm.verts.new(v.co+Vector((0,0,extension))) for v in ring}
# Moving lower pieces is a rigid rotation along the source curve, not a stretch.
turn=inv.to_3x3()@Matrix.Rotation(extension/R,3,'Y')@F.to_3x3()
for f in lower:
 for l in f.loops:l[nl]=turn@l[nl]
for v in {v for f in lower for v in f.verts}-ring:v.co.z+=extension
for f in list(lower):
 if not any(v in ring for v in f.verts):continue
 verts=[endring.get(l.vert,l.vert) for l in f.loops];data=[(l[uv].uv.copy(),l[nl].copy()) for l in f.loops];mat=f.material_index;bm.faces.remove(f);nf=bm.faces.new(verts);nf.material_index=mat;nf.smooth=True
 for l,(t,n) in zip(nf.loops,data):l[uv].uv=t;l[nl]=n
steps=60;rings=[{v:v for v in ring}]
for k in range(1,steps):rings.append({v:bm.verts.new(v.co+Vector((0,0,extension*k/steps))) for v in ring})
rings.append(endring)
for k in range(steps):
 for a,b in records:
  f=bm.faces.new((rings[k][b],rings[k][a],rings[k+1][a],rings[k+1][b]));f.smooth=True;f.material_index=0
  repeat=math.floor(extension*(k+.5)/steps/period)
  for l in f.loops:
   q=l.vert.co.copy();q.z=cut-period+(q.z-cut-repeat*period);l[uv].uv=uv_at(q)
for v in bm.verts:v.co=roll(v.co)
bmesh.ops.triangulate(bm,faces=list(bm.faces));norms=[l[nl].copy() for f in bm.faces for l in f.loops];bm.to_mesh(mesh);bm.free();mesh.update()
for p in mesh.polygons:p.use_smooth=True
mesh.set_sharp_from_angle(angle=math.radians(65));mesh.normals_split_custom_set([(0,0,0)]*len(mesh.loops));mesh.update()
derived=[n.vector.copy() for n in mesh.corner_normals]
for i,n in enumerate(norms):
 if n.length>.5:derived[i]=n.normalized()
mesh.normals_split_custom_set(derived);mesh.update()

# Refine only the texture transition strips so weights do not stretch across
# large source triangles. Interpolate normals and UV0 through each cut.
seams=[cut+k*period for k in range(round(extension/period)+1)];width=.004
bm=bmesh.new();bm.from_mesh(mesh);nl=bm.loops.layers.float_vector.new('SavedNormal')
for f in bm.faces:
 for l,i in zip(f.loops,mesh.polygons[f.index].loop_indices):l[nl]=mesh.corner_normals[i].vector
for v in bm.verts:v.co=unroll(v.co)
for seam in seams:
 for d in [-width,-.002,-.001,0,.001,.002,width]:bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,seam+d),plane_no=(0,0,1),dist=1e-7)
for v in bm.verts:v.co=roll(v.co)
bmesh.ops.triangulate(bm,faces=list(bm.faces));norm=[l[nl].normalized() for f in bm.faces for l in f.loops];bm.to_mesh(mesh);bm.free();mesh.update();mesh.normals_split_custom_set(norm)
mesh.calc_loop_triangles();mesh.calc_tangents(uvmap='UVMap');tris=list(mesh.loop_triangles);qpts=[unroll(v.co) for v in mesh.vertices];uv0=[l.uv.copy() for l in mesh.uv_layers[0].data]
trees={}
for seam in seams:
 for side in [-1,1]:
  ids=[i for i,t in enumerate(tris) if side*(sum(qpts[v].z for v in t.vertices)/3-seam)>1e-7 and abs(sum(qpts[v].z for v in t.vertices)/3-seam)<width*2 and t.material_index==0]
  trees[seam,side]=(BVHTree.FromPolygons(qpts,[tuple(tris[i].vertices) for i in ids],all_triangles=True),ids)
alt=[];packs=[[] for _ in range(5)];identity=Matrix.Identity(3)
loopface={i:p for p in mesh.polygons for i in p.loop_indices}
def basis(li):
 l=mesh.loops[li];n=mesh.corner_normals[li].vector;t=l.tangent.copy()
 if t.length<.1:t=n.cross(Vector((0,1,0)))
 if t.length<.1:t=n.cross(Vector((1,0,0)))
 t.normalize();b=n.cross(t)*(l.bitangent_sign or 1)
 return Matrix((t,b,n)).transposed()
bases=[basis(i) for i in range(len(mesh.loops))]
for li,l in enumerate(mesh.loops):
 q=qpts[l.vertex_index];seam=min(seams,key=lambda s:abs(q.z-s));dist=abs(q.z-seam);weight=0.;value=uv0[li];rotation=identity
 if dist<width and loopface[li].material_index==0:
  face=loopface[li];fs=sum(qpts[v].z for v in face.vertices)/len(face.vertices);side=1 if fs>=seam else -1
  target=q.copy();target.z=seam-side*max(dist,.00002);tree,ids=trees[seam,-side];hit=tree.find_nearest(target)
  if hit[0] is not None:
   point,n,idx,d=hit;tri=tris[ids[idx]];coords=[qpts[v] for v in tri.vertices]
   weights=barycentric_transform(point,*coords,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
   value=sum((uv0[i]*w for i,w in zip(tri.loops,weights)),Vector((0,0)))
   other=sum((bases[i]*w for i,w in zip(tri.loops,weights)),Matrix(((0,0,0),(0,0,0),(0,0,0))))
   turn=inv.to_3x3()@Matrix.Rotation((q.z-point.z)/R,3,'Y')@F.to_3x3();rotation=bases[li].transposed()@turn@other
   x=dist/width;weight=.5*(1-x*x*(3-2*x))
 alt.append(tuple(value));v=[weight]+[rotation[i][j] for i in range(3) for j in range(3)]
 # UE FBX import flips V on every UV channel, including packed data.
 # Pre-encode the matrix components so its imported numeric values survive.
 for k in range(5):packs[k].append((v[2*k],1-v[2*k+1]))
for name,values in [('SeamUV',alt)]+[('SeamBasis'+str(i),x) for i,x in enumerate(packs)]:
 layer=mesh.uv_layers.new(name=name)
 for l,v in zip(layer.data,values):l.uv=v
mesh.uv_layers.active_index=0;mesh.uv_layers[0].active_render=True
# ASH magazine slots have no receiver polymer/bolt/bore regional masks.
# New BMesh faces default to white, which otherwise activates the dark bore.
region=mesh.color_attributes.get('SurfaceRegions')
if region:
 for color in region.data:color.color=(0,0,0,1)
 mesh.color_attributes.active_color=region
report.setdefault(gun,{}).update({'seams_m':seams,'blend_halfwidth_mm':width*1000,'normal_blend':'alternate tangent frame rotated into UV0 frame; matrix in UV2-6'})

for other in list(bpy.context.scene.objects):
 if other not in (ob,factory):bpy.data.objects.remove(other,do_unlink=True)
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
export(mesh,O/(ob.name+'.fbx'))
for im in list(bpy.data.images):
 if im.source=='FILE' and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).exists():
  im.filepath=im.filepath.replace('fbx\\cdm','cdm').replace('fbx/cdm','cdm')
bpy.data.orphans_purge(do_recursive=True);bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'ASH12_ExtMag30_Editable.blend'))
report['ASH12'].update(dict(extension_cm=extension*100,capacity=30,center=[float(cx),float(cz)],radius_cm=R*100,source='ASH12Surface20260919/ASH12_Surface_Editable.blend',cut_z_m=-.165,frame=list(map(list,F)),materials=[m.name for m in mesh.materials],vertices=len(mesh.vertices),tested=False))
(O/'authoring.json').write_text(json.dumps(report,indent=2))
print('ASH12_EXTMAG_AUTHORED',flush=True)
