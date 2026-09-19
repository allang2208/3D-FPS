import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumFlow_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;hm=bpy.data.objects['SK_Manny_Arms_Export'];rest=r.data.bones
data=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909/build.json').read_text());component=rest['WPN_SOCKET_Magazine'].matrix_local.inverted()@Matrix(data['source_to_component'])@Matrix.Translation(Vector(data['center']))
groupids={g.index for g in hm.vertex_groups if g.name.endswith('_l') and g.name.startswith(('hand','thumb','index','middle','ring','pinky'))};ids=np.array([v.index for v in hm.data.vertices if sum(g.weight for g in v.groups if g.group in groupids)>.7]);report={}
for clip,end,release,grip in [('reload',126,18,50),('reload_empty',162,14,35)]:
 a=bpy.data.actions['A_M4_DrumFlow_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];hinge=0;stretch=0;depth=0;steps=0;prev={};rows=[];fast=[]
 for k in range(end*2+1):
  t=k/2;s.frame_set(k//2,subframe=(k%2)/2);bpy.context.view_layer.update()
  for side in ['l','r']:
   b=r.pose.bones['lowerarm_'+side];e=(b.parent.matrix.inverted()@b.matrix).to_euler();hinge=max(hinge,math.degrees(max(abs(e.x),abs(e.y))))
   for n in ['lowerarm_'+side,'hand_'+side]:
    bone=r.pose.bones[n];expected=(rest[n].head_local-rest[bone.parent.name].head_local).length;stretch=max(stretch,abs((bone.head-bone.parent.head).length-expected)*100)
    q=bone.matrix_basis.to_quaternion()
    if n in prev:
     angle=math.degrees(prev[n].rotation_difference(q).angle);angle=min(angle,360-angle);steps=max(steps,angle);fast.append((angle,t,n))
    prev[n]=q
  if release<t<grip:continue
  D=r.pose.bones['WPN_SOCKET_Magazine'].matrix@component;ev=hm.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();co=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',co);p=(np.array(D.inverted()@ev.matrix_world)@np.column_stack((co.reshape(-1,3)[ids],np.ones(len(ids)))).T).T[:,:3];ev.to_mesh_clear();q=np.stack((np.sqrt(p[:,0]**2+(p[:,2]+.085)**2)-.070,np.abs(p[:,1])-.0355),axis=1);dist=np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(np.maximum(q[:,0],q[:,1]),0);d=float(max(0,-dist.min())*1000);depth=max(depth,d)
  rows.append({'frame':t,'hand_penetration_mm':d})
 report[clip]={'elbow_off_hinge_deg':hinge,'max_bone_length_error_cm':stretch,'max_half_frame_rotation_step_deg':steps,'fastest_steps':sorted(fast,reverse=True)[:12],'hand_volume_penetration_mm':depth,'visible_contact_samples':rows}
 assert hinge<.05 and stretch<.01,(clip,hinge,stretch)
(O/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({c:{k:v for k,v in d.items() if k!='visible_contact_samples'} for c,d in report.items()},indent=2))

