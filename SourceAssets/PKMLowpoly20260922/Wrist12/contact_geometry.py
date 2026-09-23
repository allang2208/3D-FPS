"""Requested local glove/support contact diagnosis; no gameplay execution."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;R=O.parent;report={}
for label,path,action in [('before',R/'HandReload10/PKM_ReloadHands_Editable.blend','PKM_Game_idle'),('after',O/'PKM_WristCandidate.blend','PKM_Game_idle_Wrist12')]:
 bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['PKM_Manny_Rig'];a=bpy.data.actions[action];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
 W=r.pose.bones['WPN_root'].matrix@Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix']);vertices=[];faces=[]
 for ob in s.objects:
  if ob.get('source_part_id',-1) not in [42,68] or ob.name.startswith('New_'):continue
  ev=ob.evaluated_get(deps);me=ev.to_mesh();start=len(vertices);vertices += [W.inverted()@ev.matrix_world@v.co for v in me.vertices];faces += [[start+i for i in p.vertices] for p in me.polygons];ev.to_mesh_clear()
 tree=BVHTree.FromPolygons(vertices,faces);hands=bpy.data.objects['SK_Manny_Arms_Export'];ev=hands.evaluated_get(deps);me=ev.to_mesh();groups={g.index:g.name for g in hands.vertex_groups};data={}
 rest_hand_inv=r.data.bones['hand_l'].matrix_local.inverted()
 for digit in ['palm_pad','hand','thumb','index','middle','ring','pinky']:
  distances=[];near=[]
  for v in hands.data.vertices:
   if digit=='palm_pad':
    local=rest_hand_inv@hands.matrix_world@v.co
    if not (.05<local.x<.095 and local.y>.004 and abs(local.z)<.026):continue
   else:
    weight=sum(g.weight for g in v.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))
    if weight<.7:continue
   p=W.inverted()@ev.matrix_world@me.vertices[v.index].co
   # The palm/phalanges only; do not let receiver edges behind the grip stand
   # in for the intended support surface ahead of the ammunition box.
   if not -.16<p.y<-.025:continue
   closest,normal,face,distance=tree.find_nearest(p)
   if closest is None:continue
   distances.append(distance*1000)
   if distance<.003:near.append({'p':list(p),'surface':list(closest),'signed_mm':(p-closest).dot(normal)*1000})
  distances.sort();data[digit]={'vertices':len(distances),'nearest_mm':distances[0] if distances else None,'p05_mm':distances[int(len(distances)*.05)] if distances else None,'within_3mm':len(near),'contact_samples':near[::max(1,len(near)//12)]}
 ev.to_mesh_clear();report[label]=data
(O/'contact_geometry.json').write_text(json.dumps(report,indent=2));print(json.dumps({label:{d:{k:v for k,v in row.items() if k!='contact_samples'} for d,row in data.items()} for label,data in report.items()}))
