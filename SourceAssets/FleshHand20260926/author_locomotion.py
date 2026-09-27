"""Upright palm-forward locomotion: alternating wrist support and delayed fingers.
Offline skeletal authoring only; no physics, preview, render or gameplay tests.
"""
from pathlib import Path
import json,math,shutil
import bpy
from mathutils import Vector,Quaternion
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Locomotion';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LocalRig/FleshHand_Green_WithLODs.blend'))
scene=bpy.context.scene;scene.render.fps=60
rig=next(o for o in scene.objects if o.type=='ARMATURE')
mesh=max((o for o in scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
for o in scene.objects:o.hide_set(False)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
axes={name:m.to_3x3().inverted() for name,m in rest.items()}
identity=Quaternion();palm=Vector((0,1,0));digits=('index','middle','ring','little')
def turn(name,world_axis,degrees):return Quaternion((axes[name]@Vector(world_axis)).normalized(),math.radians(degrees))
def curl(name,degrees):
    bone=rig.data.bones[name]
    axis=(bone.tail_local-bone.head_local).normalized().cross(palm).normalized()
    return turn(name,axis,degrees)
def reset():
    for p in rig.pose.bones:
        p.location=(0,0,0);p.scale=(1,1,1);p.rotation_mode='QUATERNION';p.rotation_quaternion=identity
def backup(path):
    target=(ROOT.parents[1]/'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/Locomotion/Before')/path.name
    if path.exists() and not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
def export(path):
    backup(path);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
        bake_anim_step=1,bake_anim_simplify_factor=0,path_mode='AUTO')
clips={}
for role,frames,weight in [('WalkWeighted',69,1.),('WalkScurry',42,.64)]:
    reset();action=bpy.data.actions.new('A_FleshHand_'+role);action.use_fake_user=True
    rig.animation_data_create();rig.animation_data.action=action;scene.frame_start=0;scene.frame_end=frames
    for frame in range(frames+1):
        scene.frame_set(frame);reset();phase=2*math.pi*frame/frames
        roll=math.sin(phase);drive=math.sin(2*phase);lift=math.sin(phase)**4
        # Wrist edges alternate their load. Keep the hand vertical and the palm +Y.
        rig.pose.bones['wrist'].rotation_quaternion=(turn('wrist',(0,1,0),6.8*weight*roll)
            @turn('wrist',(-1,0,0),4.5+4.8*weight*drive)
            @turn('wrist',(0,0,1),1.6*weight*math.sin(phase-.28)))
        # Palm and phalanges lag behind the weight shift instead of rocking as a block.
        rig.pose.bones['palm'].rotation_quaternion=(turn('palm',(0,1,0),-2.4*weight*math.sin(phase-.38))
            @turn('palm',(-1,0,0),-2.2*weight*math.sin(2*phase-.48)))
        for k,digit in enumerate(digits):
            delay=(.10,.26,.47,.68)[k]
            swing=math.sin(2*phase-delay)
            base=(8.,6.,9.,12.)[k]
            for n,factor in enumerate((.85,1.,.58),1):
                name=f'{digit}_{n:02d}'
                # Distal joints trail the proximal joint; no finger scaling/translation.
                bend=base+weight*(4.2*math.sin(2*phase-delay-(n-1)*.19)+1.2*math.sin(phase+k*.6))
                rig.pose.bones[name].rotation_quaternion=curl(name,bend*factor)
            meta=digit+'_metacarpal'
            rig.pose.bones[meta].rotation_quaternion=(curl(meta,(2 if k<2 else 4)+1.3*weight*swing)
                @turn(meta,(0,1,0),(k-1.5)*(.8+.35*weight*math.sin(phase-.2))))
        for n in range(1,4):
            name=f'thumb_{n:02d}'
            rig.pose.bones[name].rotation_quaternion=curl(name,(5+2.6*weight*math.sin(2*phase-.9-n*.16))*(1 if n==1 else .65))
        # Ground correction is solved on the source skin offline, in root-local axes.
        bpy.context.view_layer.update();evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        low=min((mesh.matrix_world@v.co).z for v in evaluated.data.vertices)
        offset=Vector((.018*weight*roll,.015*weight*math.sin(2*phase-.3),-low+.018*weight*lift))
        rig.pose.bones['root'].location=axes['root']@offset
        for p in rig.pose.bones:
            p.keyframe_insert('location',frame=frame,group=p.name)
            p.keyframe_insert('rotation_quaternion',frame=frame,group=p.name)
            p.keyframe_insert('scale',frame=frame,group=p.name)
    # Dense, linear samples preserve the cyclic trajectory without Bezier overshoot.
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='LINEAR'
    path=OUT/('A_FleshHand_'+role+'.fbx');export(path)
    clips[role]={'file':str(path),'frames':frames,'duration_seconds':frames/60,'loop':True,
                 'wrist_roll_degrees':6.8*weight,'root_sway_m':.018*weight,'additional_lift_m':.018*weight}
reset();rig.animation_data.action=None;blend=OUT/'FleshHand_Locomotion.blend';backup(blend)
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
report={'revision':'FleshHandLocomotion20260927V1','fps':60,'palm_axis':[0,1,0],'clips':clips,
    'method':'Alternating wrist-edge support, elastic palm lag, per-joint finger delay; no animated bone scale',
    'gameplay_displacement':'CharacterMovement; no root-motion extraction','runtime_tested':False,'rendered':False}
backup(OUT/'authoring.json');(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FLESHHAND_LOCOMOTION_AUTHORED '+str(OUT),flush=True)
