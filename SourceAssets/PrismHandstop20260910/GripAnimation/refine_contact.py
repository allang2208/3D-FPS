import bpy,json,math,itertools
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Prism_Pose.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
data=json.loads((O/'fit_final.json').read_text());G=Matrix(data['grip_matrix'])
hand=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in hand.vertex_groups}
dg=bpy.context.evaluated_depsgraph_get();verts=[];faces=[];grip_tree=None
for ob in s.objects:
 if ob.type!='MESH' or ob==hand or (ob.parent!=r and not ob.name.startswith('PH_')):continue
 e=ob.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();vv=[e.matrix_world@v.co for v in m.vertices]
 ff=[tuple(t.vertices) for t in m.loop_triangles if all((vv[i]-G.translation).length<.15 for i in t.vertices)]
 if ob.name.startswith('PH_'):
  grip_tree=BVHTree.FromPolygons(vv,ff,all_triangles=True);grip_local=[G.inverted()@v for v in vv]
 offset=len(verts);verts.extend(vv);faces.extend([tuple(i+offset for i in f) for f in ff]);e.to_mesh_clear()
tree=BVHTree.FromPolygons(verts,faces,all_triangles=True);assert grip_tree
digit_ids={d:{v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(d) and groups[g.group].endswith('_l'))>.5} for d in ['index','middle','ring','pinky','thumb']}
digit_ids['palm']={v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if groups[g.group]=='hand_l' or groups[g.group].endswith('_metacarpal_l'))>.7}
def measure(d):
 bpy.context.view_layer.update();e=hand.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();vv=[e.matrix_world@v.co for v in m.vertices]
 ff=[tuple(t.vertices) for t in m.loop_triangles if any(i in digit_ids[d] for i in t.vertices)]
 ht=BVHTree.FromPolygons(vv,ff,all_triangles=True);hits=len(set(i for i,j in ht.overlap(tree)))
 distances=sorted(grip_tree.find_nearest(vv[i])[3] for i in digit_ids[d]);near=sum(distances[:8])/8
 enclosed=True
 if d in ['index','middle']:
  inv=G.inverted();z=(inv@r.pose.bones[d+'_01_l'].head).z
  section=[p for p in grip_local if abs(p.z-z)<.003]
  if section:
   center=((min(p.x for p in section)+max(p.x for p in section))/2,(min(p.y for p in section)+max(p.y for p in section))/2)
   points=sorted(set((p.x,p.y) for i in digit_ids[d] for p in [inv@vv[i]]))
   def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
   hull=[]
   for p in points:
    while len(hull)>1 and cross(hull[-2],hull[-1],p)<=0:hull.pop()
    hull.append(p)
   upper=[]
   for p in reversed(points):
    while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
    upper.append(p)
   hull=hull[:-1]+upper[:-1];enclosed=all(cross(hull[i],hull[(i+1)%len(hull)],center)>=0 for i in range(len(hull)))
 e.to_mesh_clear();return hits,near,enclosed
report={}
for d in ['index','middle','ring','pinky']:
 best=None
 for mcp,pip,dip in itertools.product([-30,-20,-10,0],[45,55,65,75,85],[10,20,30,40]):
  for j,ang in [(1,mcp),(2,pip),(3,dip)]:r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(ang))
  hits,near,enclosed=measure(d)
  # Collisions dominate; retain a natural tight wrap rather than contorting the wrist.
  score=hits*3+near*300+abs(mcp+10)*.03+abs(pip-65)*.015+abs(dip-30)*.015+(0 if enclosed else 3000)
  if best is None or score<best[0]:best=(score,mcp,pip,dip,hits,near)
 for j,ang in enumerate(best[1:4],1):r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(ang))
 report[d]={'angles':best[1:4],'crossing_triangles':best[4],'nearest_surface_m':best[5]}
 print(d,report[d],flush=True)
b=r.pose.bones['thumb_01_l'];native=b.rotation_quaternion.copy();best=None
for x,y,z in itertools.product([-20,-10,0,10,20],[-30,-15,0,15,30],[-30,-15,0,15,30]):
 b.rotation_quaternion=native@Quaternion((1,0,0),math.radians(x))@Quaternion((0,1,0),math.radians(y))@Quaternion((0,0,1),math.radians(z))
 hits,near,_=measure('thumb');score=hits*3+near*300+(abs(x)+abs(y)+abs(z))*.01
 if best is None or score<best[0]:best=(score,b.rotation_quaternion.copy(),hits,near,[x,y,z])
b.rotation_quaternion=best[1];bpy.context.view_layer.update()
report['thumb']={'delta':best[4],'crossing_triangles':best[2],'nearest_surface_m':best[3]}
# Refine palm clearance as a rigid whole-hand change; never move finger joints.
for iteration in range(2):
 base=r.pose.bones['hand_l'].matrix.copy();best=None
 for x,y,z in itertools.product([-.003,0,.003],repeat=3):
  H=base.copy();H.translation+=G.to_3x3()@Vector((x,y,z));r.pose.bones['hand_l'].matrix=H
  readings={d:measure(d) for d in ['index','middle','ring','pinky','thumb','palm']}
  score=sum(v[0] for v in readings.values())*3+sum(readings[d][1] for d in ['index','middle','thumb','palm'])*500+Vector((x,y,z)).length*100+sum(0 if readings[d][2] else 3000 for d in ['index','middle'])
  if best is None or score<best[0]:best=(score,H.copy(),readings)
 r.pose.bones['hand_l'].matrix=best[1];bpy.context.view_layer.update()
data['hand_in_root']=[list(row) for row in r.pose.bones['WPN_root'].matrix.inverted()@best[1]]
# Re-close around the new palm location. A clearance-only translation can leave
# the fingers floating, so measure the final surfaces again after closure.
for d in ['index','middle','ring','pinky']:
 best=None
 for mcp,pip,dip in itertools.product([-30,-20,-10,0],[45,55,65,75,85],[10,20,30,40]):
  for j,ang in [(1,mcp),(2,pip),(3,dip)]:r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(ang))
  hits,near,enclosed=measure(d);score=hits*10+near*(3000 if d in ['index','middle'] else 150)+abs(mcp+10)*.02+abs(pip-65)*.01+abs(dip-30)*.01+(0 if enclosed else 3000)
  if best is None or score<best[0]:best=(score,mcp,pip,dip)
 for j,ang in enumerate(best[1:],1):r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(ang))
 report[d]['final_angles']=best[1:]
b=r.pose.bones['thumb_01_l'];best=None
for x,y,z in itertools.product([-30,-15,0,15,30],[-30,-15,0,15,30],[-30,-15,0,15,30]):
 b.rotation_quaternion=native@Quaternion((1,0,0),math.radians(x))@Quaternion((0,1,0),math.radians(y))@Quaternion((0,0,1),math.radians(z))
 hits,near,_=measure('thumb');score=hits*10+near*3000+(abs(x)+abs(y)+abs(z))*.005
 if best is None or score<best[0]:best=(score,b.rotation_quaternion.copy(),[x,y,z])
b.rotation_quaternion=best[1];report['thumb']['final_delta']=best[2]
report['final_surfaces']={d:{'crossing_triangles':v[0],'nearest_surface_m':v[1],'encloses_grip_section':v[2] if d in ['index','middle'] else None} for d in ['index','middle','ring','pinky','thumb','palm'] for v in [measure(d)]}
# A small nearest distance alone does not prove grasping. Record the full
# finger loop in attachment coordinates for cross-section and visual review.
report['finger_loops']={d:[list(G.inverted()@r.pose.bones[f'{d}_{j:02}_l'].head) for j in [1,2,3]]+[list(G.inverted()@r.pose.bones[f'{d}_03_l'].tail)] for d in ['index','middle','ring','pinky']}
for b in r.pose.bones:
 if b.name.startswith(('index','middle','ring','pinky','thumb')):data['basis'][b.name]=[list(row) for row in b.matrix_basis]
data['contact']=report;(O/'fit_final.json').write_text(json.dumps(data,indent=2))
(O/'contact_fit.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Prism_Fitted.blend'))
print('PRISM_CONTACT_FIT_PASS',report,flush=True)
