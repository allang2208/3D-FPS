"""Offline pose study: use torso contact as well as the extremity minimum."""
import bpy,json,numpy as np
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');OUT=BASE/'KnockdownGroundV21'
src=(BASE/'ReactionsV03/author_reactions.py').read_text('utf-8').split('\ncontracts=[]\n')[0]
src=src.replace("exec((BASE/'LocomotionV02/author_locomotion.py').read_text(encoding='utf-8').split('contracts=[]')[0])", "exec((BASE/'LocomotionV02/author_locomotion.py').read_text(encoding='utf-8').split('contracts=[]')[0].replace(\"ROOT.parent/'MeshyRigV01/Authoring/M66_back_completed_v01.blend'\",\"ROOT.parent/'FurnaceBreathV17/Authoring/M66_furnace_breath_v17.blend'\"))")
src=src.replace("ROOT=BASE/'ReactionsV03'","ROOT=BASE/'KnockdownGroundV21'")
src=src.replace('tilt=-1.16*collapse;roll=-.42*collapse','tilt=-DOWN_PITCH*collapse;roll=DOWN_ROLL*collapse')
exec(compile(src,'M66_support_study','exec'))
groups={g.index:g.name for g in mesh.vertex_groups}
body_names={'Bone_000','Bone_001','Bone_006','Bone_007','Bone_005'}
body=[v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if groups.get(g.group) in body_names or groups.get(g.group,'').startswith('M66_Sac'))>.6]
feet_ids=[v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if groups.get(g.group) in ('Bone_010','Bone_015'))>.6]
big_hand=[v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if groups.get(g.group) in ('Bone_037','Bone_036','Bone_041','Bone_045','Bone_049','Bone_053'))>.6]
rows=[]
for DOWN_PITCH in (1.35,1.55,1.75,1.95):
 for DOWN_ROLL in (-.35,-.70,-1.05,-1.40):
  rig.animation_data.action=None;make_pose('Landing',.9,.9);bpy.context.view_layer.update()
  ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());a=np.array([ev.matrix_world@v.co for v in ev.data.vertices])
  rows.append(dict(pitch=DOWN_PITCH,roll=DOWN_ROLL,surface_cm=float((a[:,2].min()-floor_z)*100),body_cm=float((a[body,2].min()-floor_z)*100),feet_cm=float((a[feet_ids,2].min()-floor_z)*100),hand_cm=float((a[big_hand,2].min()-floor_z)*100)))
(OUT/'Records/support-candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
for row in sorted(rows,key=lambda r:r['body_cm']):print('SUPPORT_CANDIDATE',row,flush=True)
