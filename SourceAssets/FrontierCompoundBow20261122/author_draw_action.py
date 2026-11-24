"""Keep the editable Blender action in sync with the in-game draw presentation."""
from pathlib import Path
import bpy
from mathutils import Quaternion

POSES = ((1,0.),(13,.45),(26,1.),(36,1.),(39,0.))

def draw_at(frame):
    for (left,a),(right,b) in zip(POSES,POSES[1:]):
        if frame <= right:
            return a+(b-a)*(frame-left)/(right-left)
    return POSES[-1][1]

def animate(rig,scene):
    scene.frame_start,scene.frame_end = POSES[0][0],POSES[-1][0]
    for frame in range(scene.frame_start,scene.frame_end+1):
        phase=draw_at(frame)
        wheel=(phase+phase*phase*(3.-2.*phase))*.5
        for side in ('upper','lower'):
            hub=rig.data.bones[side+'_cam'].head_local
            for suffix in ('_01','_02','_cam','_tip'):
                pb=rig.pose.bones[side+suffix]
                bone=pb.bone
                goal=rig.data.bones['draw_'+pb.name]
                t=wheel if suffix in ('_cam','_tip') else phase
                change=bone.matrix_local.inverted() @ goal.matrix_local
                pb.rotation_mode='QUATERNION'
                pb.rotation_quaternion=Quaternion().slerp(change.to_quaternion(),t)
                pb.location=change.translation*t
                if suffix=='_tip':
                    start=bone.head_local-hub
                    end=goal.head_local-hub
                    arc=start.normalized().rotation_difference(end.normalized())
                    direction=Quaternion().slerp(arc,t) @ start.normalized()
                    point=hub+direction*((1.-t)*start.length+t*end.length)
                    pb.location=bone.matrix_local.inverted() @ point
                pb.keyframe_insert(data_path='rotation_quaternion',frame=frame)
                pb.keyframe_insert(data_path='location',frame=frame)
            string=scene.objects['MainString_'+side]
            shape=string.data.shape_keys.key_blocks['Draw']
            shape.value=phase
            shape.keyframe_insert(data_path='value',frame=frame)
    scene.frame_set(scene.frame_start)

if __name__ == '__main__':
    master=Path(__file__).resolve().parent/'FrontierCompoundBow.blend'
    bpy.ops.wm.open_mainfile(filepath=str(master))
    bpy.context.preferences.filepaths.save_version=0
    animate(bpy.context.scene.objects['Armature'],bpy.context.scene)
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
