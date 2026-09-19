import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;hand=bpy.data.objects['SK_Manny_Arms_Export'];mag=next(o for o in r.children if o.type=='MESH' and 'Magazine' in o.name)
ids=[v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if hand.vertex_groups[g.group].name.endswith('_l') and hand.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>0.7]
def act(a):r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def frame(f):s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
report={}
for clip,lo,hi in [('reload',70,101),('reload_empty',65,89)]:
 a=bpy.data.actions['M4_MAT_'+clip];act(a);rows=[];baseline=None;drift=0
 for k in range(lo*8,hi*8+1):
  f=k/8;frame(f);dep=bpy.context.evaluated_depsgraph_get();inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();wrist=inv@r.pose.bones['hand_l'].head
  if baseline is None:baseline=wrist
  if f<hi-1:drift=max(drift,(wrist-baseline).length*1000)
  ev=mag.evaluated_get(dep);m=ev.to_mesh();vs=[inv@ev.matrix_world@v.co for v in m.vertices];tree=BVHTree.FromPolygons(vs,[list(p.vertices) for p in m.polygons]);ev.to_mesh_clear();bounds=[[min(p[i] for p in vs),max(p[i] for p in vs)] for i in range(3)]
  ev=hand.evaluated_get(dep);m=ev.to_mesh();ps=[inv@ev.matrix_world@m.vertices[i].co for i in ids];ev.to_mesh_clear();depth=0;inside=0
  for p in ps:
   if not(bounds[1][0]<p.y<bounds[1][1] and bounds[2][0]<p.z<bounds[2][1]):continue
   left=tree.ray_cast(Vector((-.1,p.y,p.z)),Vector((1,0,0)),.2)[0];right=tree.ray_cast(Vector((.1,p.y,p.z)),Vector((-1,0,0)),.2)[0]
   if left is not None and right is not None and left.x<p.x<right.x:
    d=min(p.x-left.x,right.x-p.x)*1000;depth=max(depth,d);inside+=d>.3
  rows.append({'frame':f,'inside_envelope_vertices_over_0_3mm':inside,'max_depth_mm':depth})
 report[clip]={'insertion_samples_480hz':len(rows),'locked_wrist_drift_mm':drift,'maximum_envelope_depth_mm':max(p['max_depth_mm'] for p in rows),'samples':rows}
 (O/'polish_validation.json').write_text(json.dumps(report,indent=2))
 assert max(p['max_depth_mm'] for p in rows)<.5,(clip,report[clip]['maximum_envelope_depth_mm'])
new=bpy.data.actions['M4_MAT_reload_empty']
with bpy.data.libraries.load('D:/FPS3D/FPSGAME/SourceAssets/M4HandMATRepair20260910/M4_Hand_MAT_Editable.blend',link=False) as (a,b):b.actions=['M4_MAT_reload_empty']
old=b.actions[0];strike={}
for label,a in [('before',old),('after',new)]:
 act(a);positions=[]
 for k in range(242,269):
  frame(k/2);positions.append((r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_l'].matrix).translation.copy())
 speeds=[(positions[i+1]-positions[i]).length*120 for i in range(len(positions)-1)];strike[label]={'peak_approach_m_s':max(speeds[:18]),'peak_rebound_m_s':max(speeds[18:])}
report['strike']=strike;(O/'polish_validation.json').write_text(json.dumps(report,indent=2));print('POLISH_VALIDATION',json.dumps({k:{n:v for n,v in value.items() if n!='samples'} for k,value in report.items()}))
