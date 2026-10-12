import bpy,bmesh,json,sys,gzip
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;sys.path.insert(0,str(O.parent/'HK416CommonAttachments20260930'))
import reargrip_interfaces as R
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/super90.fbx'),use_anim=False)
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
bm=bmesh.new();bm.from_mesh(ob.data);bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table()
# The current native grip is a separate manufacturing island. Weld only seam duplicates in this temporary extraction.
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bm.faces.ensure_lookup_table()
seed=next(f for f in bm.faces if all(-.2381<v.co.y<-.158 and -.9046<v.co.z<-.788 for v in f.verts) and f.calc_center_median().z<-.89)
keep={seed};stack=[seed]
while stack:
 for v in stack.pop().verts:
  for f in v.link_faces:
   if f not in keep:keep.add(f);stack.append(f)
if len(keep)!=3880:raise RuntimeError('Unexpected native grip island '+str(len(keep)))
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f not in keep],context='FACES');bm.to_mesh(ob.data);bm.free()
for x in list(bpy.context.scene.objects):
 if x!=ob:bpy.data.objects.remove(x,do_unlink=True)
ob.name='Hand_grip_low';bpy.ops.wm.save_as_mainfile(filepath=str(O/'Inputs/native_grip.blend'))
sections={}
for z in [-.795,-.800,-.805,-.81,-.82,-.84,-.86,-.88,-.90]:
 pts=R.section(ob.data,z,32);sections[str(z)]={'center':[sum(p[j] for p in pts)/len(pts) for j in range(3)],'bounds':[[min(p[j] for p in pts) for j in range(3)],[max(p[j] for p in pts) for j in range(3)]]}
(O/'native_sections.json').write_text(json.dumps(sections,indent=2));print('NATIVE_GRIP_EXTRACTED',sections)
# Select the corresponding source triangles by exact native vertex positions, not material-wide hiding.
points={tuple(round(c*100,4) for c in (v.co.x,-v.co.y,v.co.z)) for v in ob.data.vertices}
with gzip.open(O/'Inputs/native_geometry.json.gz','rt') as f:d=json.load(f)
ids=[i for i,t in enumerate(d['triangles']) if all(tuple(round(c,4) for c in d['positions'][j]) in points for j in t)]
# FBX round-trip precision can exceed 1 micron; use a small nearest-neighbour manufacturing tolerance.
if len(ids)!=3880:
 from mathutils.kdtree import KDTree
 kd=KDTree(len(ob.data.vertices))
 for i,v in enumerate(ob.data.vertices):kd.insert((v.co.x*100,-v.co.y*100,v.co.z*100),i)
 kd.balance();inside=[kd.find(p)[2]<.001 for p in d['positions']]
 ids=[i for i,t in enumerate(d['triangles']) if all(inside[j] for j in t)]
if len(ids)!=3880:raise RuntimeError('Native source grip mapping '+str(len(ids)))
(O/'factory_triangles.json').write_text(json.dumps(ids));print('FACTORY_TRIANGLES',len(ids))
