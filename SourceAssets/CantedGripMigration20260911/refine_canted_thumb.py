import bpy,json,itertools,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
src=(O/'refine_canted_surface.py').read_text().split('for xyz in')[0];exec(compile(src,str(O/'thumb_generated.py'),'exec'))
self_faces={d:[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in set(ids[d]) for i in t.vertices)] for d in digits};base={b.name:b.matrix_basis.copy() for b in r.pose.bones};best=None
for a,b in itertools.product([-8,-4,0,4,8],repeat=2):
 for n,m in base.items():r.pose.bones[n].matrix_basis=m
 r.pose.bones['thumb_01_l'].matrix_basis=base['thumb_01_l']@Quaternion((0,1,0),math.radians(a)).to_matrix().to_4x4();r.pose.bones['thumb_02_l'].matrix_basis=base['thumb_02_l']@Quaternion((0,0,1),math.radians(b)).to_matrix().to_4x4();bpy.context.view_layer.update();e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@x.co for x in m.vertices];ht=BVHTree.FromPolygons(v,faces,all_triangles=True);thumb=BVHTree.FromPolygons(v,self_faces['thumb'],all_triangles=True);hit=len(ht.overlap(tree));sh=sum(len(thumb.overlap(BVHTree.FromPolygons(v,self_faces[d],all_triangles=True))) for d in digits[:4]);score=(hit+sh)*10000+a*a+b*b
 if best is None or score<best[0]:best=(score,a,b,hit,sh)
 e.to_mesh_clear()
print('THUMB_BEST',best,flush=True);assert best[3]==0 and best[4]==0,best
for n,m in base.items():r.pose.bones[n].matrix_basis=m
for n,axis,angle in [('thumb_01_l',(0,1,0),best[1]),('thumb_02_l',(0,0,1),best[2])]:r.pose.bones[n].matrix_basis=base[n]@Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()
bpy.context.view_layer.update();f['basis']={n:[list(x) for x in r.pose.bones[n].matrix_basis] for n in f['basis']};f['thumb_refinement_deg']=[best[1],best[2]];(O/'canted_refit.json').write_text(json.dumps(f,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'Canted_Refit.blend'));render(r,G,'final_fit')
