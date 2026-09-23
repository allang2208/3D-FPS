"""Advance Khaimera's coherent native downstroke, preserving every joint pose."""
import bpy,json,math
from pathlib import Path
ROOT=Path(__file__).parent
SOURCE=ROOT.parent/'claw_reference_20260923'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'Mutant3_OpenClaw_Animated.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
scene=bpy.context.scene;scene.render.fps=60;scene.render.fps_base=1
roles=['PounceWindup','PounceFlight','PounceLand']
# Retain the complete native shoulder/elbow/wrist relationship, including the
# original hand-end bones still influencing the palm. New fingers stay in claw.
arm_bones=[side+n for side in ['Left','Right'] for n in ['Shoulder','Arm','ForeArm','Hand','Hand_End','Hand_End_end']]
pose_bones=[b.name for b in rig.pose.bones]
contract=json.loads((SOURCE/'animation_contract.json').read_text())
contract['clips']={r:contract['clips'][r] for r in roles}
source_actions={r:bpy.data.actions['A_Mutant3_'+r] for r in roles}

def activate(action):
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    for track in rig.animation_data.nla_tracks:track.mute=True

def sample_native_pose(source_seconds):
    # Keep torso lean, clavicles, arms and pelvis at the SAME source time.
    # The baseline already contains the accepted claw and grounded feet.
    if source_seconds<=.60:
        action=source_actions['PounceFlight'];time=(source_seconds-.08)/.52*.65
    else:
        action=source_actions['PounceLand'];time=(source_seconds-.60)/1.65*.80
    activate(action)
    f=time*60;scene.frame_set(math.floor(f),subframe=f%1)
    return {n:(rig.pose.bones[n].location.copy(),rig.pose.bones[n].rotation_quaternion.copy(),
               rig.pose.bones[n].scale.copy()) for n in pose_bones}

samples={};mapped_times={}
for role in ['PounceFlight','PounceLand']:
    count=contract['clips'][role]['frames'][1]
    times=[.08+(.92-.08)*f/count if role=='PounceFlight' else .92+(2.25-.92)*f/count for f in range(count+1)]
    mapped_times[role]=times
    samples[role]=[sample_native_pose(t) for t in times]

out=ROOT/'animations';out.mkdir(exist_ok=True)
for role in roles:
    original=source_actions[role]
    original.name='NativeBeforeRake_'+original.name
    action=original.copy();action.name='A_Mutant3_'+role;action.use_fake_user=True
    activate(action)
    scene.frame_start,scene.frame_end=contract['clips'][role]['frames']
    previous={}
    if role!='PounceWindup':
        for f,pose in enumerate(samples[role]):
            scene.frame_set(f)
            for n in pose_bones:
                p,q,s=pose[n];q=q.copy()
                if n in previous and q.dot(previous[n])<0:q.negate()
                pb=rig.pose.bones[n];pb.rotation_mode='QUATERNION'
                pb.location=p;pb.rotation_quaternion=q;pb.scale=s
                for channel in ['location','rotation_quaternion','scale']:
                    pb.keyframe_insert(channel,frame=f,group=n)
                previous[n]=q.copy()
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if curve.data_path.startswith('pose.bones['):
                        for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for obj in bpy.data.objects:
        if obj.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in obj.modifiers):obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(out/(action.name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
        mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
    print('REFERENCE_RAKE_EXPORTED '+role,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Mutant3_Pounce_ReferenceRake.blend'))
contract['revision']='Coherent native Khaimera poses including torso lean and arm chain; original downstroke advanced into late flight; no IK or joint-facing overrides'
contract['state']='Three animation FBX files authored; import pending'
contract['arm_bones']=arm_bones
contract['source_arm_times_seconds']=mapped_times
contract['source_native_downstroke_seconds']=[.60,.88]
contract['flight_downstroke_seconds']=[(.60-.08)/(.92-.08)*.65,(.88-.08)/(.92-.08)*.65]
(ROOT/'animation_contract.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
print('REFERENCE_RAKE_AUTHORING_COMPLETE',flush=True)
