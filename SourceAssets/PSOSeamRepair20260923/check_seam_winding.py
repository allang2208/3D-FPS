"""Inspect collar-to-body boundary closure and winding without editing source."""
import bpy,bmesh,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'SVDMatteDetail20260923/SVD_base_Editable.blend'))
rig=bpy.data.objects['SK_M4_Infima'];root=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted()
bm=bmesh.new();tag=bm.faces.layers.int.new('mechanical_collar')
for name in ['SM_SVD_ScopeBody','SM_SVD_ScopeMount','SM_SVD_ScopeLens']:
 ob=bpy.data.objects[name];X=root@ob.matrix_world;verts=[bm.verts.new(X@v.co) for v in ob.data.vertices]
 for p in ob.data.polygons:
  f=bm.faces.new([verts[i] for i in p.vertices]);f[tag]=int(name.endswith('Lens') and 'ScopeBody' in ob.data.materials[p.material_index].name)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=2e-6);bm.normal_update()
edges={e for f in bm.faces if f[tag] for e in f.edges};boundary=[e for e in edges if e.is_boundary]
seams=[e for e in edges if any(f[tag] for f in e.link_faces) and any(not f[tag] for f in e.link_faces)]
result={'collar_triangles':sum(bool(f[tag]) for f in bm.faces),'collar_boundary_edges':len(boundary),
 'joined_body_edges':len(seams),'joined_edges_with_inconsistent_winding':sum(not e.is_contiguous for e in seams),
 'nonmanifold_collar_edges':sum(not e.is_manifold for e in edges)}
pending=set(boundary);groups=[]
while pending:
 e=pending.pop();es={e};vs=set(e.verts);stack=list(e.verts)
 while stack:
  for e in stack.pop().link_edges:
   if e in pending:
    pending.remove(e);es.add(e)
    for v in e.verts:
     if v not in vs:vs.add(v);stack.append(v)
 groups.append({'edges':len(es),'min':[min(v.co[i] for v in vs) for i in range(3)],'max':[max(v.co[i] for v in vs) for i in range(3)]})
result['boundary_loops']=groups
# The two unjoined inner rims sit inside overlapping housings. Probe the
# exterior radially around those joints to distinguish inner rims from holes.
bvh=BVHTree.FromBMesh(bm);misses=[];radii=[]
for center in [-.0227647,.04464885]:
 for step in range(-8,9):
  # Avoid casting exactly in the annular face plane (coplanar ray ambiguity).
  y=center+step*.00025+.0000313
  for j in range(32):
   theta=j*math.tau/32;direction=Vector((math.cos(theta),0,math.sin(theta)))
   origin=Vector((.0000366,y,.1023703))+direction*.06
   hit,normal,index,distance=bvh.ray_cast(origin,-direction,.05)
   if hit is None:misses.append([y,j])
   else:radii.append(.06-distance)
result['inner_rim_exterior_probe']={'rays':1088,'joint_half_width_m':.002,'plane_offset_m':.0000313,'misses':misses,'min_hit_radius_m':min(radii)}
(O/'seam_winding_checks.json').write_text(json.dumps(result,indent=2));print('PSO_SEAM_WINDING',result,flush=True)
bm.free()
