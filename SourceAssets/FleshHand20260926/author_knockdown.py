"""Bake hand-specific airborne, landing and fingertip-supported recovery; no render."""
from pathlib import Path
import json, math
import bpy
from mathutils import Vector, Quaternion

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Knockdown';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LocalRig/FleshHand_Green_WithLODs.blend'))
scene=bpy.context.scene;scene.render.fps=60
rig=next(o for o in scene.objects if o.type=='ARMATURE')
mesh=max((o for o in scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
for o in scene.objects:o.hide_set(False)
inverse={b.name:b.matrix_local.to_3x3().inverted() for b in rig.data.bones}
digits=('index','middle','ring','little')

def turn(name,axis,degrees):
    return Quaternion((inverse[name]@Vector(axis)).normalized(),math.radians(degrees))

def flex(name,degrees):
    bone=rig.data.bones[name]
    axis=(bone.tail_local-bone.head_local).normalized().cross(Vector((0,1,0))).normalized()
    return turn(name,axis,degrees)

def reset():
    for p in rig.pose.bones:
        p.location=(0,0,0);p.scale=(1,1,1);p.rotation_mode='QUATERNION';p.rotation_quaternion=Quaternion()

def curve(t,keys):
    if t<=keys[0][0]:return keys[0][1]
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:
            f=(t-a)/(b-a);f=f*f*(3-2*f);return x+(y-x)*f
    return keys[-1][1]

def hand(tilt,curl,spread,roll=0,phase=0,flutter=0,thumb_support=0):
    rig.pose.bones['wrist'].rotation_quaternion=turn('wrist',(0,1,0),roll)@turn('wrist',(-1,0,0),tilt)
    for k,digit in enumerate(digits):
        rig.pose.bones[digit+'_metacarpal'].rotation_quaternion=turn(digit+'_metacarpal',(0,1,0),(k-1.5)*spread)
        for n,weight in enumerate((.72,1.,.48),1):
            name=digit+'_%02d'%n
            rig.pose.bones[name].rotation_quaternion=flex(name,curl*weight+flutter*math.sin(phase+k*.7+n*.35))
    # Thumb remains outside the fingers and becomes a lateral support on a back get-up.
    rig.pose.bones['thumb_01'].rotation_quaternion=turn('thumb_01',(0,1,-.4),-curl*.25-spread-thumb_support)
    rig.pose.bones['thumb_02'].rotation_quaternion=flex('thumb_02',curl*.35+thumb_support*.3)
    rig.pose.bones['thumb_03'].rotation_quaternion=flex('thumb_03',curl*.2)

def support(tilt):
    bpy.context.view_layer.update()
    evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points=[mesh.matrix_world@v.co for v in evaluated.data.vertices]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    # Recenter the falling body over its existing gameplay capsule. Grounding is
    # authored against the skinned surface, not the palm bone or capsule center.
    a=min(1.,abs(tilt)/62.);a=a*a*(3-2*a)
    offset=Vector((-(lo.x+hi.x)*.5*a,-(lo.y+hi.y)*.5*a,-lo.z))
    # Pose-bone translation uses the bone's rest axes (root Y points up here),
    # not Blender world XYZ. Convert both the object and rest-bone bases.
    rig.pose.bones['root'].location=inverse['root']@(rig.matrix_world.inverted().to_3x3()@offset)
    return [[float(v) for v in lo+offset],[float(v) for v in hi+offset]]

roles=[('KnockupStart',13/60),('KnockupStartBack',13/60),('KnockupAir',.6),('KnockupAirBack',.6),
       ('LandPalm',19/60),('LandBack',23/60),('DownPalm',1.),('DownBack',1.),('GetUpPalm',.95),('GetUpBack',1.2)]
clips={}
for role,duration in roles:
    reset();action=bpy.data.actions.new('A_FleshHand_'+role);action.use_fake_user=True
    rig.animation_data_create();rig.animation_data.action=action
    frames=round(duration*60);scene.frame_start=0;scene.frame_end=frames
    bounds=[]
    for frame in range(frames+1):
        scene.frame_set(frame);reset();t=frame/frames;phase=t*2*math.pi
        back=role.endswith('Back');sign=-1 if back else 1
        roll=0.;thumb=0.;flutter=0.
        if role.startswith('KnockupStart'):
            tilt=sign*curve(t,[(0,0),(.25,12),(1,62)])
            curl=curve(t,[(0,2),(.24,-6),(.68,22),(1,18)])
            spread=curve(t,[(0,.5),(.25,6),(1,3)])
        elif role.startswith('KnockupAir'):
            tilt=sign*(62+3*math.sin(phase));curl=18+2*math.sin(phase);spread=3;flutter=1.2*math.sin(phase)
        elif role.startswith('Land'):
            tilt=sign*curve(t,[(0,62),(.30,88),(.57,80),(1,86)])
            curl=curve(t,[(0,18),(.3,35 if not back else 25),(.6,13),(1,8 if not back else 16)])
            spread=curve(t,[(0,3),(.3,6),(1,3 if not back else 2)])
        elif role.startswith('Down'):
            tilt=sign*86;curl=(16 if back else 8)+.7*math.sin(phase);spread=2 if back else 3
            flutter=.5*math.sin(phase)
        elif not back:
            tilt=curve(t,[(0,86),(.23,80),(.48,57),(.72,24),(1,0)])
            curl=curve(t,[(0,8),(.23,42),(.48,29),(.76,10),(1,2)])
            spread=curve(t,[(0,3),(.23,5),(.7,2),(1,.5)])
            thumb=curve(t,[(0,0),(.2,12),(.6,8),(1,0)])
        else:
            tilt=curve(t,[(0,-86),(.22,-70),(.47,24),(.72,32),(1,0)])
            roll=curve(t,[(0,0),(.22,-46),(.47,-66),(.72,-22),(1,0)])
            curl=curve(t,[(0,16),(.22,22),(.47,42),(.72,24),(1,2)])
            spread=curve(t,[(0,2),(.22,6),(.47,5),(.72,2),(1,.5)])
            thumb=curve(t,[(0,0),(.22,28),(.47,22),(.72,10),(1,0)])
        hand(tilt,curl,spread,roll,phase,flutter,thumb)
        bounds.append(support(max(abs(tilt),abs(roll))))
        for p in rig.pose.bones:
            for prop in ('location','rotation_quaternion','scale'):p.keyframe_insert(prop,frame=frame,group=p.name)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    path=OUT/('A_FleshHand_'+role+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
        bake_anim_step=1,bake_anim_simplify_factor=0,path_mode='AUTO')
    clips[role]={'file':str(path),'duration_seconds':duration,'frames':frames,
                 'loop':role.startswith(('KnockupAir','Down')),'support_bounds_m':bounds}
    print('FLESHHAND_KNOCKDOWN_AUTHORED '+role,flush=True)
reset();rig.animation_data.action=None
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FleshHand_Knockdown.blend'))
(OUT/'authoring.json').write_text(json.dumps({'fps':60,'clips':clips,'palm_outward_axis':[0,1,0],
    'root_motion':False,'world_motion':'CharacterMovement','rendered':False,'runtime_tested':False},indent=2),encoding='utf-8')
print('FLESHHAND_KNOCKDOWN_AUTHORING_COMPLETE',flush=True)
