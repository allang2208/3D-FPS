"""Six-turn original M14 attack on the V11 rigid-hardware/soft-tissue rig."""
from pathlib import Path
import bpy, json, math, re
from mathutils import Vector, Quaternion

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004'
OUT=ROOT/'ProductionV12'
for folder in ('Authoring','Exports','Records'):(OUT/folder).mkdir(parents=True,exist_ok=True)
header=(PROJECT/'Source/FPSGAME/Monsters/M14WhirlwindMotion.h').read_text(encoding='utf8')
C={name:float(value) for name,value in re.findall(r'constexpr float (\w+)\s*=\s*([-\d.]+)f;',header)}
ready,spin,recover=C['ReadySeconds'],C['SpinSeconds'],C['RecoverSeconds']
accel,brake=C['AccelSeconds'],C['BrakeSeconds']
duration=ready+spin+recover

def ease(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)

def phase(t):
    t=max(0.,min(spin,t-ready));area=spin-.5*(accel+brake)
    if t<accel:
        u=t/accel;return accel*(u**3-.5*u**4)/area
    if t<=spin-brake:return (t-.5*accel)/area
    u=(t-(spin-brake))/brake
    return (spin-brake-.5*accel+brake*(u-u**3+.5*u**4))/area

def speed(t):
    return ease((t-ready)/accel)*(1-ease((t-ready-spin+brake)/brake))

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ProductionV11/Authoring/M14_Hardware_TrunkSlam_v11.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['M14_Rig'];obj=bpy.data.objects['M14_SoftDeathMesh']
rig.animation_data.action=None
# Bone authoring/export needs no evaluation of the two-million-face skin.
modifiers=[(m,m.show_viewport) for m in obj.modifiers if m.type=='ARMATURE']
for modifier,_ in modifiers:modifier.show_viewport=False
for key in obj.data.shape_keys.key_blocks:key.value=0
inverse={bone.name:bone.matrix_local.to_3x3().inverted() for bone in rig.data.bones}
previous={}

def turn(name,axis,angle):
    q=Quaternion(inverse[name]@Vector(axis),angle)
    if name in previous and previous[name].dot(q)<0:q.negate()
    rig.pose.bones[name].rotation_quaternion=q;previous[name]=q.copy()

def shift(name,value):rig.pose.bones[name].location=inverse[name]@Vector(value)

name='A_M14_Whirlwind_v12'
action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
scene.render.fps=60;scene.frame_start=0;scene.frame_end=round(duration*60)
for frame in range(scene.frame_end+1):
    scene.frame_set(frame);t=frame/60
    for pb in rig.pose.bones:
        pb.location=(0,0,0);pb.rotation_quaternion=(1,0,0,0);pb.scale=(1,1,1)
    wind=ease(t/ready)*(1-ease((t-ready-spin)/recover))
    run=speed(t)
    delayed=speed(t-.075)
    settling=max(0.,t-ready-spin)
    rebound=math.sin(settling*math.pi*3/recover)*math.exp(-5*settling/recover) if settling>0 else 0.
    turn('root',(0,0,1),math.radians(C['WindDegrees']*wind+C['TurnDegrees']*phase(t)))
    crouch=.045*wind+.020*run
    shift('base',(0,0,-crouch))
    # The trunk shares one root rotation. Small compression and paired bends
    # retain mass without winding the spine sections against one another.
    for k in range(1,6):
        shift(f'spine_{k:02d}',(0,0,-.009*wind))
        turn(f'spine_{k:02d}',(1,0,0),(.009*wind+.008*rebound)*(1 if k<3 else -.5))
    lift=ease((t-ready+.10)/.20)*(1-ease((t-ready-spin)/.30))
    for k in range(8):
        angle=2*math.pi*k/8;radial=Vector((math.cos(angle),math.sin(angle),0))
        # Eight supports lift only modestly. No long unilateral skirt lashes.
        shift(f'rootfan_{k:02d}',radial*(.020*run-.012*wind)+Vector((0,0,crouch)))
        shift(f'roottoe_{k:02d}',radial*(.105*run-.018*wind)+Vector((0,0,.14*lift)))
    for side,sign in (('L',1),('R',-1)):
        load=-sign*(.038*delayed+.009*rebound)
        for k in range(3):
            angle=load*(1 if k==0 else .22)
            # Chains and their adjacent membrane share the same small motion.
            turn(f'mem_{side}_{k}',(0,1,0),angle)
            turn(f'chain_{side}_{k}',(0,1,0),angle)
        turn('sac_'+side,(0,1,0),-sign*(.055*delayed+.018*rebound))
    shift('maw',(0,.035*wind,.012*wind))
    for pb in rig.pose.bones:
        pb.keyframe_insert('location',frame=frame,group=pb.name)
        pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name)
        pb.keyframe_insert('scale',frame=frame,group=pb.name)
for slot in action.slots:
    for layer in action.layers:
        for strip in layer.strips:
            bag=strip.channelbag(slot)
            if bag:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'Exports'/f'{name}.fbx'),object_types={'ARMATURE'},use_selection=True,
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
    add_leaf_bones=False,use_armature_deform_only=True,armature_nodetype='NULL',path_mode='STRIP',
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
rig.animation_data.action=None;scene.frame_set(0)
for pb in rig.pose.bones:pb.location=(0,0,0);pb.rotation_quaternion=(1,0,0,0);pb.scale=(1,1,1)
for modifier,enabled in modifiers:modifier.show_viewport=enabled
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M14_Whirlwind_v12.blend'),compress=True)
report={'complete':True,'clip':name,'source':'ProductionV11/Authoring/M14_Hardware_TrunkSlam_v11.blend',
    'timing_source':'Source/FPSGAME/Monsters/M14WhirlwindMotion.h','timing':C,'duration':duration,'fps':60,
    'frames':scene.frame_end+1,'active_turns':6,'rigid_hardware_preserved':True,
    'geometry_edits':False,'skin_weight_edits':False,'unit_bone_scales':True,'tested':False,'rendered':False}
(OUT/'Records/authoring.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('M14_V12_WHirlwind_AUTHORED',flush=True)
