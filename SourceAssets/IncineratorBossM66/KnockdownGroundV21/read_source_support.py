"""Compare the current skinned body and original reaction support on a flat plane."""
from pathlib import Path
import bpy,json,numpy as np
from mathutils import Matrix
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'KnockdownGroundV21'
report=[]
for version,source in [('V01',BASE/'MeshyRigV01/Authoring/M66_back_completed_v01.blend'),('V17',BASE/'FurnaceBreathV17/Authoring/M66_furnace_breath_v17.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(source));rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body'];scene=bpy.context.scene
 rig.animation_data_create();rig.animation_data.action=None
 for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
 if mesh.data.shape_keys:
  for block in mesh.data.shape_keys.key_blocks:block.value=0.
 bpy.context.view_layer.update()
 ref=np.array([mesh.matrix_world@v.co for v in mesh.data.vertices]);floor=float(ref[:,2].min());scale=380./float(np.ptp(ref[:,2]))
 groups={g.index:g.name for g in mesh.vertex_groups}
 torso=[v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if groups.get(g.group) in ('Bone_000','Bone_001','Bone_006','Bone_007','Bone_005'))>.6]
 with bpy.data.libraries.load(str(BASE/'ReactionsV03/Authoring/M66_reactions_v03.blend')) as (src,dst):dst.actions=['A_M66_Landing_V03','A_M66_GetUp_V03']
 for action,seconds in zip(dst.actions,(.9,3.2)):
  for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
  rig.animation_data.action=action
  if action.slots:rig.animation_data.action_slot=action.slots[0]
  scene.render.fps=60
  for t in (0.,seconds*.25,seconds*.5,seconds*.75,seconds):
   scene.frame_set(round(t*60));bpy.context.view_layer.update();ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
   xyz=np.empty(len(ev.data.vertices)*3);ev.data.vertices.foreach_get('co',xyz);xyz=xyz.reshape(-1,3)
   mat=np.array(ev.matrix_world);xyz=xyz@mat[:3,:3].T+mat[:3,3];low=int(np.argmin(xyz[:,2]))
   report.append(dict(version=version,clip=action.name,seconds=t,scale=scale,ref_floor=floor,
    gap_cm=float((xyz[low,2]-floor)*scale),torso_bottom_cm=float((xyz[torso,2].min()-floor)*scale),
    lowest_source_vertex=low,lowest_weights={groups[g.group]:g.weight for g in mesh.data.vertices[low].groups},
    pelvis=list(rig.pose.bones['Bone_000'].matrix.translation)))
(ROOT/'Records/source-support.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for row in report:print('M66_SOURCE_SUPPORT',row['version'],row['clip'],row['seconds'],round(row['gap_cm'],2),round(row['torso_bottom_cm'],2),row['lowest_weights'],flush=True)
