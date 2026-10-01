"""Keep the real retained idle; animate only subtle front-plate eye tremor."""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ArticulationV12/HundredEyedSlag_ArticulationV12.blend'))
scene=bpy.context.scene;scene.render.fps=60;scene.render.fps_base=1
rig=next(o for o in scene.objects if o.type=='ARMATURE');arm=rig.data
rest={b.name:b.matrix_local.copy() for b in arm.bones};inv={n:m.inverted() for n,m in rest.items()}
idle=next((bpy.data.actions.get(n) for n in ('A_HundredEyedSlag_Idle_V3','A_HundredEyedSlag_Idle_V2','A_HundredEyedSlag_Idle') if bpy.data.actions.get(n)),None)
if idle is None:idle=next(a for a in bpy.data.actions if a.name.startswith('A_HundredEyedSlag_Idle'))
idle_begin,idle_end=idle.frame_range;idle_duration=(idle_end-idle_begin)/60
contracts=[dict(name='EyeLaserWindup',seconds=1.5,offset=0.,loop=False),
    dict(name='EyeLaserFire',seconds=.65,offset=1.5,loop=False),
    dict(name='EyeLaserRecover',seconds=.5,offset=2.15,loop=False)]
def ease(u):
    u=max(0.,min(1.,u));return u*u*(3-2*u)
for c in contracts:
    c.update(action='A_HundredEyedSlag_'+c['name']+'_V13',file='Animations/A_HundredEyedSlag_'+c['name']+'_V13.fbx',
        fps=60,start_frame=1,end_frame_inclusive=round(c['seconds']*60)+1,root_motion=False)
    poses=[]
    rig.animation_data.action=idle;rig.animation_data.action_slot=idle.slots[0]
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    for f in range(c['end_frame_inclusive']):
        seconds=f/60;total=c['offset']+seconds
        phase=total%max(1/60,idle_duration)
        scene.frame_set(int(idle_begin+phase*60),subframe=(idle_begin+phase*60)%1)
        bpy.context.view_layer.update()
        original={p.name:p.matrix.copy() for p in rig.pose.bones}
        target={n:m.copy() for n,m in original.items()}
        strength=ease(seconds/.18) if c['name']=='EyeLaserWindup' else (1-ease(seconds/c['seconds']) if c['name']=='EyeLaserRecover' else 1.)
        eye=target['front_plate']
        eye.translation+=Vector((.0015*math.sin(total*39),.0025*math.sin(total*51),.003*math.sin(total*43)))*strength
        eyeq=Quaternion((0,1,0),.006*math.sin(total*37)*strength)@eye.to_quaternion()
        target['front_plate']=Matrix.LocRotScale(eye.translation,eyeq,Vector((1,1,1)))
        changed={'front_plate'}
        for b in arm.bones:
            if b.parent and b.parent.name in changed:
                target[b.name]=target[b.parent.name]@original[b.parent.name].inverted()@original[b.name]
                changed.add(b.name)
        poses.append(target)
    a=bpy.data.actions.new(c['action']);a.use_fake_user=True;rig.animation_data.action=a
    previous={}
    for frame,target in enumerate(poses,1):
        for b in arm.bones:
            n=b.name;basis=inv[n]@rest[b.parent.name]@target[b.parent.name].inverted()@target[n] if b.parent else inv[n]@target[n]
            pb=rig.pose.bones[n];pb.rotation_mode='QUATERNION';pb.matrix_basis=basis
            if n in previous:pb.rotation_quaternion.make_compatible(previous[n])
            previous[n]=pb.rotation_quaternion.copy();pb.scale=(1,1,1)
            for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame)
        if not rig.animation_data.action_slot:rig.animation_data.action_slot=a.slots[0]
    for curve in a.layers[0].strips[0].channelbag(a.slots[0]).fcurves:
        for p in curve.keyframe_points:p.interpolation='LINEAR'
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_IdleLaserV13.blend'))
(OUT/'Delivery/Animations').mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
for c in contracts:
    a=bpy.data.actions[c['action']];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    scene.frame_start=1;scene.frame_end=c['end_frame_inclusive'];scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=str(OUT/'Delivery'/c['file']),object_types={'ARMATURE'},bake_anim=True,
        use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
        bake_anim_step=1.,bake_anim_simplify_factor=0.)
(OUT/'animation_contract.json').write_text(json.dumps(dict(revision='ThreeAttacksV13',actions=contracts,
    source_idle_action=idle.name,source_idle_seconds=idle_duration,casting_hand_raise=False,
    additional_animation_bones=['front_plate'],eye_tremor_max_cm=[.15,.25,.30],
    mesh_weights_changed=False,mesh_revision='ArticulationV12',accepted_melee_animations_changed=False,
    active_attacks=['Sweep','Slam','EyeLaser'],jump_attack_active=False,
    laser_charge_seconds=1.5,laser_prediction=False,preview_rendered=False,tested=False),indent=2),encoding='utf-8')
print('SLAG_V13_THREE_IDLE_LASER_CLIPS_EXPORTED '+idle.name,flush=True)
