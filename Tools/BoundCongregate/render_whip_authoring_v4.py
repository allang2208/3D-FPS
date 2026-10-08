"""Offline authoring preview while the user's editor holds the native DLL.

This is not the UE pose review. Uses the same direction bake and frame mapping.
"""
from pathlib import Path
import bpy,numpy as np,math
from mathutils import Vector,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/TentacleWhipV4')
setup=(Path('D:/FPS3D/FPSGAME/Tools/BoundCongregate/render_whip_v4.py').read_text()).split('poses=json.loads')[0]
exec(setup)
cam.location=(7,-4,3.5);data.ortho_scale=10.;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
raw=np.load(ROOT/'whip_baked_pose.npz');anchor=int(raw['anchor']);count=57-anchor
poses=raw['poses'];last=len(poses)-1
bones=[rig.pose.bones[f'attack_tentacle_{i:02}'] for i in range(57)]
rest=[pb.bone.matrix_local.copy() for pb in bones]
root=rest[anchor].translation.copy();aim=Vector((0,-3.4,.96));to_aim=aim-root
direction=Vector((to_aim.x,to_aim.y,0)).normalized();up=Vector((0,0,1));across=up.cross(direction)
contact=Vector(poses[-1,-1]);yaw=math.atan2(contact.y,contact.x)
pitch=max(-.5,min(.5,math.atan2(to_aim.z,to_aim.xy.length)-math.atan2(contact.z,contact.xy.length)))
def frame(p):
    along=p[0]*math.cos(yaw)+p[1]*math.sin(yaw);side=-p[0]*math.sin(yaw)+p[1]*math.cos(yaw)
    return direction*(along*math.cos(pitch)-p[2]*math.sin(pitch))+across*side+up*(along*math.sin(pitch)+p[2]*math.cos(pitch))
def segment(sample,i):
    j=i-anchor;old=(rest[i].translation-rest[i-1].translation).normalized();d=frame(sample[j]-sample[j-1]).normalized()
    b=max(0,min(1,(j-1)/6));b=b*b*(3-2*b)
    return Quaternion().slerp(old.rotation_difference(d),b)@old
for iteration in range(5):
    end=Vector()
    for i in range(anchor+1,57):end+=segment(poses[-1],i)*(rest[i].translation-rest[i-1].translation).length
    yaw+=math.atan2(end.dot(across),end.dot(direction))
    pitch=max(-.9,min(.9,pitch+math.atan2(to_aim.z,to_aim.xy.length)-math.atan2(end.z,end.xy.length)))
for fraction in [0.,.25,.5,.75,1.]:
    for pb in rig.pose.bones:pb.matrix_basis.identity()
    goals=[m.translation.copy() for m in rest]
    sample=poses[round(fraction*last)]
    for i in range(anchor+1,57):goals[i]=goals[i-1]+segment(sample,i)*(rest[i].translation-rest[i-1].translation).length
    transport=Quaternion();matrices=[]
    for i in range(anchor,57):
        a=i if i<56 else 55;b=a+1
        old=(rest[b].translation-rest[a].translation).normalized();new=(goals[b]-goals[a]).normalized()
        transport=(transport@old).rotation_difference(new)@transport
        m=(transport@rest[i].to_quaternion()).to_matrix().to_4x4();m.translation=goals[i];matrices.append(m)
    for i,m in enumerate(matrices,anchor):
        parent_pose=rest[i-1] if i==anchor else matrices[i-anchor-1]
        local_rest=rest[i-1].inverted()@rest[i]
        bones[i].matrix_basis=local_rest.inverted()@parent_pose.inverted()@m
    bpy.context.view_layer.update();scene.render.filepath=str(ROOT/f'authoring_phase_{round(fraction*100):03}.png');bpy.ops.render.render(write_still=True)
