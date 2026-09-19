import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'A_M4_Canted_idle.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];s.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None;H=r.pose.bones['hand_l'].matrix.copy();f=json.loads((O/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(f['grip_in_root']);R=Matrix.Rotation(__import__('math').radians(45),4,'X');axis=G.to_3x3()@R.to_3x3()@Vector((0,0,-1));ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};selected={v.index for v in ob.data.vertices if any(g.weight>.2 and groups[g.group].startswith(('index','middle','ring','pinky','thumb')) and groups[g.group].endswith('_l') for g in v.groups)};out=[]
for k in range(11):
 shift=k*.002;m=H.copy();m.translation+=axis*shift;r.pose.bones['hand_l'].matrix=m;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg);mesh=ev.to_mesh();mesh.calc_loop_triangles();faces=[tuple(t.vertices) for t in mesh.loop_triangles if any(i in selected for i in t.vertices)];tree=BVHTree.FromPolygons([ev.matrix_world@v.co for v in mesh.vertices],faces,all_triangles=True);pairs=set()
 for grip in [o for o in s.objects if o.name.startswith('CG_')]:
  e=grip.evaluated_get(dg);gm=e.to_mesh();gm.calc_loop_triangles();b=BVHTree.FromPolygons([e.matrix_world@v.co for v in gm.vertices],[tuple(t.vertices) for t in gm.loop_triangles],all_triangles=True);pairs.update(i for i,j in tree.overlap(b));e.to_mesh_clear()
 ev.to_mesh_clear();out.append({'shift_m':shift,'crossing_triangles':len(pairs)})
(O/'hand_shift_candidates.json').write_text(json.dumps(out,indent=2));print(out)
