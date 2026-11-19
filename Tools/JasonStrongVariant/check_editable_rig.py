"""Check the updated editable Blender rig against the saved UE mesh."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117/R2_LongLegs')
REVIEW=OUT/'AnatomyReview'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Jason_StrongTall_R2.blend'))
data=json.loads((REVIEW/'derived_saved_mesh.json').read_text())
head=json.loads((OUT/'head_source.json').read_text())
rig=bpy.data.objects['Jason_NativeSkeleton']
body=bpy.data.objects['Jason_StrongTall_R2']
face=bpy.data.objects['Jason_UnchangedHead']
report={}
report['bone_names_match']=set(rig.data.bones.keys())=={b['name'] for b in data['bones']}
report['max_joint_position_error_cm']=max((rig.data.bones[b['name']].head_local-Vector(b['position'])*.01).length*100 for b in data['bones'])
errors=[]
for b in data['bones']:
    expected=np.array([-np.array(b['axes'][1]),b['axes'][0],b['axes'][2]]).T
    actual=np.array(rig.data.bones[b['name']].matrix_local.to_3x3())
    errors.append(float(np.abs(expected-actual).max()))
report['max_bone_basis_error_after_axis_convention_conversion']=max(errors)

def evaluated_positions(ob):
    evaluated=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me=evaluated.to_mesh();p=np.array([v.co[:] for v in me.vertices]);evaluated.to_mesh_clear();return p

p=evaluated_positions(body)
report['body_rest_max_position_error_cm']=float(np.linalg.norm(p*100-np.array(data['positions']),axis=1).max())
h=evaluated_positions(face)
report['head_rest_max_position_error_cm']=float(np.linalg.norm(h*100-np.array(head['positions']),axis=1).max())
# A 95-degree knee bend must match native-matrix LBS, including twist children.
joint='calf_l';axis=Vector((1,0,0));angle=math.radians(-95)
pb=rig.pose.bones[joint];pb.rotation_mode='QUATERNION'
pb.rotation_quaternion=Quaternion(pb.bone.matrix_local.to_3x3().inverted()@axis,angle)
rig.hide_set(False);bpy.context.view_layer.update()
posed=evaluated_positions(body)*100
bones=data['bones'];bone_index={b['name']:b['index'] for b in bones}
affected=set([bone_index[joint]])
for b in bones:
    if b['parent'] in affected:affected.add(b['index'])
center=np.array(bones[bone_index[joint]]['position'])
r=np.array(Quaternion(axis,angle).to_matrix())
positions=np.array(data['positions']);rotated=(positions-center)@r.T+center
weights=np.array([sum(w for i,w in ws if i in affected) for ws in data['weights']])
expected=positions+(rotated-positions)*weights[:,None]
report['knee_pose_vs_native_lbs_max_position_error_cm']=float(np.linalg.norm(posed-expected,axis=1).max())
(REVIEW/'editable_rig_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('JASON_EDITABLE_RIG_CHECK '+json.dumps(report),flush=True)
# Inspection is in memory only. Keep the source .blend in its neutral pose.
