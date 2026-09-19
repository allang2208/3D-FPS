import bpy,json,sys,itertools,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));from audit_m4 import apply,render
f=json.loads((O/'canted_refit.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(O/'Canted_Refit.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;rest={b.name:b.matrix_local.copy() for b in r.data.bones};old={b.name:b.matrix.copy() for b in r.pose.bones};G=old['WPN_root']@Matrix(f['grip_in_root']);B=G@Matrix(f['body_in_grip']);ob=bpy.data.objects['SK_Manny_Arms_Export'];ob.data.calc_loop_triangles();groups={g.index:g.name for g in ob.vertex_groups};digits=['index','middle','ring','pinky','thumb']
labels={v.index:max([(g.weight,groups[g.group]) for g in v.groups],default=(0,''))[1] for v in ob.data.vertices};faces=[tuple(t.vertices) for t in ob.data.loop_triangles if any(labels[i].endswith('_l') and labels[i].startswith(tuple(digits)) for i in t.vertices)]
ids={d:[v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(d+'_') and groups[g.group].endswith('_l'))>.85] for d in digits};dg=bpy.context.evaluated_depsgraph_get();e=ob.evaluated_get(dg);m=e.to_mesh();vertices=[e.matrix_world@v.co for v in m.vertices];e.to_mesh_clear();vv=[];ff=[]
for part in [x for x in s.objects if x.name.startswith('CG_')]:
 e=part.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();offset=len(vv);vv.extend(e.matrix_world@v.co for v in m.vertices);ff.extend(tuple(i+offset for i in t.vertices) for t in m.loop_triangles);e.to_mesh_clear()
tree=BVHTree.FromPolygons(vv,ff,all_triangles=True);best=None
for xyz in itertools.product([-12,-8,-4,0,4,8,12],[-12,-8,-4,0,4,8,12],[-20,-15,-10,-5,0,5,10]):
 shift=B.to_3x3()@Vector(xyz)/1000;v=[x+shift for x in vertices];hit=len(BVHTree.FromPolygons(v,faces,all_triangles=True).overlap(tree));near={d:sum(sorted(tree.find_nearest(v[i])[3] for i in ids[d])[:8])/8*1000 for d in digits};score=hit*100000+sum(x*x for x in xyz)+sum(max(0,near[d]-2)**2*8 for d in digits[:4])
 if best is None or score<best[0]:best=(score,xyz,hit,near)
print('SURFACE_BEST',best,flush=True);assert best[2]==0,best
shift=B.to_3x3()@Vector(best[1])/1000;p={n:m.copy() for n,m in old.items()}
for n in p:
 if n=='hand_l' or n.endswith('_l') and n.startswith(tuple(digits)):p[n].translation+=shift
# Re-solve the arm using the measured fixed shoulder and unchanged segment lengths.
from audit_m4 import support
code=(O/'build_akm.py').read_text();exec(code[code.index('def arm('):code.index('def render(')],globals());arm(p,rest,p['hand_l'],1,Vector((0,0,0)))
apply(r,p,rest);f['hand_in_root']=[list(x) for x in p['WPN_root'].inverted()@p['hand_l']];f['surface_slide_body_mm']=list(best[1]);(O/'canted_refit.json').write_text(json.dumps(f,indent=2));(O/'surface_refinement.json').write_text(json.dumps({'shift_body_mm':best[1],'approximate_pairs':best[2],'near_mm':best[3]},indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'Canted_Refit.blend'));render(r,G,'surface')
