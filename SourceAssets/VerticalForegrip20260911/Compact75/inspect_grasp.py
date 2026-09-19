import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
fit=json.loads((O/'fit_final.json').read_text());G=Matrix(fit['grip_matrix']);inv=G.inverted();dg=bpy.context.evaluated_depsgraph_get()
grip=next(o for o in s.objects if o.name.startswith('VG_'));e=grip.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();gv=[inv@e.matrix_world@v.co for v in m.vertices];tree=BVHTree.FromPolygons(gv,[tuple(t.vertices) for t in m.loop_triangles],all_triangles=True);e.to_mesh_clear()
ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};e=ob.evaluated_get(dg);m=e.to_mesh();vv=[inv@e.matrix_world@v.co for v in m.vertices]
report={}
for d in ['index','middle','ring','pinky','thumb','hand']:
 ids=[v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(d) and groups[g.group].endswith('_l'))>.5]
 pen=[]
 for i in ids:
  loc,n,j,dist=tree.find_nearest(vv[i])
  if (vv[i]-loc).dot(n)<-1e-6:pen.append(dist)
 report[d]={'inside_vertices':len(pen),'max_penetration_m':max(pen,default=0)}
for d in ['index','middle']:
 joints=[inv@r.pose.bones[f'{d}_{j:02}_l'].head for j in [1,2,3]]+[inv@r.pose.bones[f'{d}_03_l'].tail]
 z=sum(p.z for p in joints)/4;section=[v for v in gv if abs(v.z-z)<.002]
 if section:
  lo=Vector([min(v[i] for v in section) for i in range(3)]);hi=Vector([max(v[i] for v in section) for i in range(3)]);center=(lo+hi)/2
  report[d]['section_center']=list(center);report[d]['section_bounds']=[list(lo),list(hi)];report[d]['joint_loop']=[list(p) for p in joints]
e.to_mesh_clear();(O/'grasp_inspection.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
# Render the fitted hand from three actual model viewpoints.
for ob in s.objects:ob.hide_render=not(ob.name.startswith('VG_') or (ob.type=='MESH' and ob.parent==r))
focus=G@Vector((0,0,-.045))
for loc in [(-.6,-.2,.9),(.8,.6,.7)]:
 d=bpy.data.lights.new('GraspReview','AREA');d.energy=70;d.size=1;o=bpy.data.objects.new('GraspReview',d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('GraspReview');cam=bpy.data.objects.new('GraspReview',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=.26;d.clip_start=.001
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=900;s.render.resolution_y=720;s.render.resolution_percentage=100
for label,off in [('palm',(.4,-.12,.02)),('back',(-.4,-.12,.04)),('front',(0,.4,-.02))]:
 cam.location=focus+Vector(off);cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/('grasp_review_'+label+'.png'));bpy.ops.render.render(write_still=True)
