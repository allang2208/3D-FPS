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

report={}
for d in ['index','middle','ring','pinky']:
 best=None
 for mcp,pip,dip in itertools.product(range(-40,41,10),range(30,101,10),range(0,71,10)):
  for j,ang in enumerate([mcp,pip,dip],1):r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(ang))
  hits,near,enclosed=measure(d)
  score=hits*100+near*1800+abs(mcp)*.006+abs(pip-65)*.006+abs(dip-30)*.006+(0 if enclosed else 1)
  if best is None or score<best[0]:best=(score,mcp,pip,dip,hits,near)
 for j,ang in enumerate(best[1:4],1):r.pose.bones[f'{d}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(ang))
 report[d]=best;print(d,best,flush=True)
for b in r.pose.bones:
 if b.name.startswith(('index','middle','ring','pinky','thumb')):data['basis'][b.name]=[list(row) for row in b.matrix_basis]
report['surfaces']={d:measure(d) for d in ['index','middle','ring','pinky','thumb','palm']}
(O/'fit_final.json').write_text(json.dumps(data,indent=2));(O/'contact_final.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'))
