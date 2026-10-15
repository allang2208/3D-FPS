"""Read native grasp frames and sword motion keys needed to author the thrust."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P.parents[2]
sys.path.insert(0,str(R/'SourceAssets/RuneSword20260913/StrideThrustV16'))
from thrust_motion import poses
sword={str(t):{'grip':list(poses(t)[0].translation),'axis':list(poses(t)[1].to_quaternion()@Vector((0,0,1)))} for t in (0,.24,.4,.58,.94,1.25)}
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend'))
r=bpy.data.objects['SK_RusticPickaxe_Rig'];r.animation_data.action=bpy.data.actions['A_Warhammer_Slash1'];r.animation_data.action_slot=r.animation_data.action.slots[0]
bpy.context.scene.frame_set(0)
names=['WPN_root']+[n+'_'+s for s in ('l','r') for n in ('clavicle','upperarm','lowerarm','hand')]
idle={n:{'p':list(r.pose.bones[n].matrix.translation),'q':list(r.pose.bones[n].matrix.to_quaternion())} for n in names}
grips={s:[list(row) for row in r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_'+s].matrix] for s in ('l','r')}
out={'sword':sword,'idle':idle,'grips':grips}
native_rest={b.name:b.matrix_local.copy() for b in r.data.bones}
out['native_idle_arm_frames']={}
for side in ('l','r'):
    un,fn,hn=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    fore=(r.pose.bones[hn].matrix.translation-r.pose.bones[fn].matrix.translation).normalized()
    neutral=r.pose.bones[hn].matrix.to_quaternion()@native_rest[hn].to_quaternion().inverted()@(native_rest[hn].translation-native_rest[fn].translation).normalized()
    out['native_idle_arm_frames'][side]={'wrist_axis_degrees':fore.angle(neutral)*180/3.141592653589793}
bpy.ops.wm.open_mainfile(filepath=str(R/'SourceAssets/ThrustElbowRepair20260923/Standard/Thrust_ElbowSupport_Editable.blend'))
donor=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
out['corrected_sword']={'rig':donor.name,'matrix':[list(row) for row in donor.matrix_world],'poses':{}}
for t in (0.,.4,.58,.94,1.25):
    bpy.context.scene.frame_set(round(t*480))
    out['corrected_sword']['poses'][str(t)]={n:list(donor.pose.bones[n].matrix.translation) for n in names}
(P/'author_inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
