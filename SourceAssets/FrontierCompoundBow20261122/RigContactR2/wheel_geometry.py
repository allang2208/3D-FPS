"""Local-space visual tracks for the existing Frontier game meshes (Blender units)."""
import math
from mathutils import Vector, Quaternion, Matrix

# Each ellipse was fitted separately to the outline of its original wheel mesh.
OUTLINES={'upper':(-16.416,47.787,7.186,8.187,-.466),
          'lower':(-16.415,-37.296,7.090,8.346,.504)}
GUIDES=[Vector((-13.8,-2.52,9.45)),Vector((-13.3,-3.04,9.45))]
SEAT=Vector((-6.25,5.20,9.45))
BRACE=Vector((-23.62,0.,SEAT.z))
DRAW=BRACE+Vector((-30.,0,0))
SIDES=('upper','lower')
REELS=(3.28,2.78)
ZERO=Vector((0.,0.,0.))

def outline(side):
    x,z,ra,rb,t=OUTLINES[side]
    return (Vector((x,0,z)),Vector((math.cos(t)*ra,0,math.sin(t)*ra)),
            Vector((-math.sin(t)*rb,0,math.cos(t)*rb)))

def rotate_y(angle):
    return Matrix.Rotation(math.radians(angle),4,'Y')

def tangent(center,u,v,target):
    delta=target-center
    x,y=delta.dot(u)/u.length_squared,delta.dot(v)/v.length_squared
    d=max(x*x+y*y,1.000001)
    h=math.sqrt(d-1.)
    return min((center+u*((x-k*y*h)/d)+v*((y+k*x*h)/d) for k in (-1,1)),key=lambda p:p.x)

def local_from_world(rig,bone,point):
    pb=rig.pose.bones[bone]
    rest=pb.bone
    parent=pb.parent
    neutral=parent.matrix @ parent.bone.matrix_local.inverted() @ rest.matrix_local
    return neutral.inverted() @ point

def animate(rig,scene):
    rest=rig.data.bones
    for frame in range(1,34):
        q=(frame-1)/24. if frame<=25 else (33-frame)/8.
        nock=BRACE.lerp(DRAW,q)
        wheel=.5*(q+q*q*(3.-2.*q))
        for side in SIDES:
            for suffix in ('_01','_02','_cam'):
                name=side+suffix
                pb=rig.pose.bones[name]
                rel=rest[name].matrix_local.inverted() @ rest['draw_'+name].matrix_local
                f=wheel if suffix=='_cam' else q
                pb.rotation_mode='QUATERNION'
                # FTransform::Blend uses a normalized hemisphere-corrected linear blend.
                goal=rel.to_quaternion()
                if goal.w<0:goal.negate()
                pb.rotation_quaternion=Quaternion((1.+(goal.w-1.)*f,goal.x*f,goal.y*f,goal.z*f)).normalized()
                pb.keyframe_insert(data_path='rotation_quaternion',frame=frame)
        bpy_update=scene.view_layers[0].update
        bpy_update()
        for side in SIDES:
            cam=rig.pose.bones[side+'_cam']
            tf=cam.matrix @ cam.bone.matrix_local.inverted()
            c,u,v=outline(side);c=tf@c
            u=tf.to_3x3()@u;v=tf.to_3x3()@v
            positions={side+'_tip':tangent(c,u,v,nock)}
            for i,r in enumerate(REELS):
                center=tf@(cam.bone.head_local+Vector((0,GUIDES[i].y,0)))
                positions[side+'_cable'+str(i)]=tangent(center,u.normalized()*r,v.normalized()*r,GUIDES[i])
            for name,point in positions.items():
                pb=rig.pose.bones[name];pb.location=local_from_world(rig,name,point)
                pb.keyframe_insert(data_path='location',frame=frame)
        pb=rig.pose.bones['preview_nock']
        pb.location=local_from_world(rig,'preview_nock',nock)
        pb.keyframe_insert(data_path='location',frame=frame)
    scene.frame_start,scene.frame_end=1,33
    scene.frame_set(1)
