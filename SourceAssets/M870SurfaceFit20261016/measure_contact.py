import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M870_SurfaceFit_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;a=json.loads((O/'authoring.json').read_text())
act=bpy.data.actions[a['clips']['idle']['action']];r.animation_data.action=act;r.animation_data.action_slot=act.slots[0];s.frame_set(0)
canon=r.data.bones['WPN_root'].matrix_local@r.pose.bones['WPN_root'].matrix.inverted();dep=bpy.context.evaluated_depsgraph_get()
def mesh(name):
 ob=bpy.data.objects[name];ev=ob.evaluated_get(dep);m=ev.to_mesh();v=[canon@r.matrix_world.inverted()@ev.matrix_world@p.co for p in m.vertices];f=[list(p.vertices) for p in m.polygons];ev.to_mesh_clear();return ob,v,f
ob,pv,pf=mesh('M870_pump');tree=BVHTree.FromPolygons(pv,pf)
hv,hp,hf=mesh('M870_V7');names={g.index:g.name for g in hv.vertex_groups}
def left(n):return n.endswith('_l') and n.startswith(('hand','thumb','index','middle','ring','pinky'))
ids=[i for i,v in enumerate(hv.data.vertices) if sum(g.weight for g in v.groups if left(names[g.group]))>.995]
direction=Vector((1,.173,.281)).normalized()
def inside(p):
 count=0;o=p.copy()
 for _ in range(20):
  hit,normal,index,d=tree.ray_cast(o,direction,2.)
  if hit is None:break
  count+=1;o=hit+direction*.000001
 return count%2==1
deep=[];near=[];digits={}
for i in ids:
 p=hp[i];hit,normal,ix,d=tree.find_nearest(p)
 if d<.012 and inside(p):deep.append((d*1000,i))
 if d<.0015:near.append(i)
 dominant=max(hv.data.vertices[i].groups,key=lambda g:g.weight);part=names[dominant.group].split('_')[0]
 entry=digits.setdefault(part,{'minimum_gap_mm':1000.,'contact_vertices':0});entry['minimum_gap_mm']=min(entry['minimum_gap_mm'],d*1000)
 if d<.0015:entry['contact_vertices']+=1
rs=[math.hypot(p.x,p.z+.7594) for p in pv if .16<p.y<.29]
out={'foreend_radius_max_mm':max(rs)*1000,'left_hand_vertices':len(ids),'inside_vertices':len(deep),'max_depth_mm':max((d for d,i in deep),default=0),'near_contact_vertices':len(near),'digits':digits,'worst':sorted(deep,reverse=True)[:10]}
(O/'actual_contact.json').write_text(json.dumps(out,indent=2));print(out)
