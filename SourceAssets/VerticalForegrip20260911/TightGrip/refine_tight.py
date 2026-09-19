import bpy,json,math,itertools
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
data=json.loads((O/'fit_final.json').read_text());G=Matrix(data['grip_matrix'])
hand=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in hand.vertex_groups}
dg=bpy.context.evaluated_depsgraph_get();verts=[];faces=[];grip_tree=None
for ob in s.objects:
 if ob.type!='MESH' or ob==hand or (ob.parent!=r and not ob.name.startswith('VG_')):continue
 e=ob.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();vv=[e.matrix_world@v.co for v in m.vertices]
 ff=[tuple(t.vertices) for t in m.loop_triangles if all((vv[i]-G.translation).length<.15 for i in t.vertices)]
 if ob.name.startswith('VG_'):
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


# First seat the palm, then fit all phalanges with positive proximal flexion.
base=r.pose.bones['hand_l'].matrix.copy();best=None
for x,y,z in itertools.product([-.008,-.004,0,.004,.008],[-.008,-.004,0,.004,.008],[-.003,0,.003]):
 H=base.copy();H.translation+=G.to_3x3()@Vector((x,y,z));r.pose.bones['hand_l'].matrix=H
 readings={d:measure(d) for d in ['index','middle','ring','pinky','thumb','palm']}
 score=sum(v[0] for v in readings.values())*100+sum(v[1] for v in readings.values())*1500+Vector((x,y,z)).length*20
 if best is None or score<best[0]:best=(score,H.copy(),readings)
r.pose.bones['hand_l'].matrix=best[1];bpy.context.view_layer.update();data['hand_in_root']=[list(row) for row in r.pose.bones['WPN_root'].matrix.inverted()@best[1]];print('WHOLE_HAND',best[2],flush=True)
segment_ids={d:[[v.index for v in hand.data.vertices if any(groups[g.group]==f'{d}_{j:02}_l' and g.weight>.45 for g in v.groups)][::3] for j in [1,2,3]] for d in ['index','middle','ring','pinky']}
def segment_distance(d):
 bpy.context.view_layer.update();e=hand.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();vv=[e.matrix_world@v.co for v in m.vertices]
 distances=[]
 for ids in segment_ids[d]:
  a=sorted(grip_tree.find_nearest(vv[i])[3] for i in ids);distances.append(sum(a[:6])/max(1,len(a[:6])))
 e.to_mesh_clear();return sum(distances)/3
report={}
for d in ['index','middle','ring','pinky']:
 best=None
 for mcp,pip,dip in itertools.product(range(0,76,15),range(20,91,10),range(0,61,15)):
  for j,ang in enumerate([mcp,pip,dip],1):r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(ang))
  count,near,enclosed=measure(d);distance=segment_distance(d) if count==0 else near
  score=count*100+distance*3000+abs(mcp-40)*.005+abs(pip-65)*.005+abs(dip-30)*.005+(0 if enclosed else 1)
  if best is None or score<best[0]:best=(score,mcp,pip,dip,count,distance)
 for j,ang in enumerate(best[1:4],1):r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(ang))
 report[d]=best;print(d,best,flush=True)
# Thumb opposes near the upper grip, instead of pointing down between the fingers.
b=r.pose.bones['thumb_01_l'];native=b.rotation_quaternion.copy();best=None
for x,y,z in itertools.product(range(-45,46,15),repeat=3):
 b.rotation_quaternion=native@Quaternion((1,0,0),math.radians(x))@Quaternion((0,1,0),math.radians(y))@Quaternion((0,0,1),math.radians(z))
 count,near,_=measure('thumb');point=G.inverted()@r.pose.bones['thumb_03_l'].head
 score=count*100+near*1000+(point-Vector((-.017,-.002,-.037))).length*1500+(abs(x)+abs(y)+abs(z))*.002
 if best is None or score<best[0]:best=(score,b.rotation_quaternion.copy(),count,near,[x,y,z])
b.rotation_quaternion=best[1];report['thumb']=[best[2],best[3],best[4]]
for b in r.pose.bones:
 if b.name.startswith(('index','middle','ring','pinky','thumb')):data['basis'][b.name]=[list(row) for row in b.matrix_basis]
report['surfaces']={d:measure(d) for d in ['index','middle','ring','pinky','thumb','palm']}
(O/'fit_final.json').write_text(json.dumps(data,indent=2));(O/'contact_final.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'))
