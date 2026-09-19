import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector,Quaternion
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
from studio import setup,aim
bpy.ops.wm.open_mainfile(filepath=str(root/'handbrain_rig_complete.blend'))
rig=bpy.data.objects['SK_HandBrain'];cam=setup()
aim(cam,(3,-7,2.6))
def rotate(name,axis,angle):
    p=rig.pose.bones[name];q=p.bone.matrix_local.to_quaternion()
    p.rotation_mode='QUATERNION';p.rotation_quaternion=q.inverted()@Quaternion(axis,angle)@q
for label,scale,angle in [('rest_hidden',.08,0),('extended',1,0),('slam',1,math.radians(23))]:
    rig.pose.bones['arm_mount'].scale=(scale,)*3
    rig.pose.bones['fan_mount'].scale=(scale,)*3
    rotate('arm_mount',(0,1,0),angle)
    bpy.context.view_layer.update()
    bpy.context.scene.render.filepath=str(root/f'rig_check_{label}.png');bpy.ops.render.render(write_still=True)
checks={}
for name in ['HandBrain_Body','HandBrain_AttackArm','HandBrain_CrownHands']:
    o=bpy.data.objects[name]
    checks[name]={'unweighted':sum(not v.groups for v in o.data.vertices),'max_weights':max(len(v.groups) for v in o.data.vertices),'max_weight_sum_error':max(abs(sum(g.weight for g in v.groups)-1) for v in o.data.vertices)}
(root/'rig_weight_check.json').write_text(json.dumps(checks,indent=2))
