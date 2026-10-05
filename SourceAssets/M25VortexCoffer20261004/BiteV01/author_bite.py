"""Author one non-looping bite on the accepted M25 skeleton. No renders or tests."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'RigV01/M25_VortexCoffer_RigAndCrawl_V01.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
# An animation-only editing file; the full bound model stays in the accepted source.
for ob in list(bpy.data.objects):
    if ob!=rig: bpy.data.objects.remove(ob,do_unlink=True)
rig.animation_data_clear()
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)
spec=json.loads((ROOT.parent/'RigV01/skeleton_spec.json').read_text(encoding='utf-8'))
meta={s['name']:s for s in spec}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
inverse={n:m.inverted() for n,m in rest.items()}
scene=bpy.context.scene
scene.render.fps=30
scene.frame_start=1
scene.frame_end=43
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1.
rig.data.pose_position='POSE'
rig.animation_data_create()
action=bpy.data.actions.new('M25_Bite_V01')
rig.animation_data.action=action
action.use_fake_user=True
def curve(t,keys):
    for i in range(len(keys)-1):
        a,x=keys[i];b,y=keys[i+1]
        if t<=b:
            f=max(0.,min(1.,(t-a)/(b-a)));f=f*f*(3.-2.*f)
            return x+(y-x)*f
    return keys[-1][1]
def move(M,delta):
    M=M.copy();M.translation+=Vector(delta);return M
def twist(M,axis,angle):
    p=M.translation.copy()
    R=Quaternion(Vector(axis),angle).to_matrix().to_4x4()
    M=R@M;M.translation=p
    return M
previous={}
for f in range(1,44):
    t=(f-1)/30.
    retract=curve(t,[(0,0),(.18,.7),(.42,1),(.60,0),(1.4,0)])
    thrust=curve(t,[(0,0),(.44,0),(.633333,1),(.78,.88),(1.12,.25),(1.4,0)])
    opening=curve(t,[(0,0),(.16,.35),(.38,1),(.52,1),(.68,0),(1.4,0)])
    closing=curve(t,[(0,0),(.55,0),(.70,1),(.82,.9),(1.18,.2),(1.4,0)])
    settle=curve(t,[(0,0),(.80,0),(.96,1),(1.18,-.25),(1.4,0)])
    pose={}
    for pb in rig.pose.bones:
        n=pb.name;s=meta[n];parent=pb.parent
        M=pose[parent.name]@inverse[parent.name]@rest[n] if parent else rest[n].copy()
        region=s['region']
        if region=='body':
            w=(s['section']/6.)**1.6
            M=move(M,(0,-w*(.18*thrust-.09*retract-.016*settle),w*(.045*opening+.02*thrust)))
            M=twist(M,(1,0,0),math.radians(w*(2.5*closing-2.*opening)))
        elif region=='sac':
            w=(s['section']/6.)**1.4
            M=move(M,(s['side']*w*(.012*opening-.01*closing),0,0))
        elif region=='mouth':
            M=move(M,(0,-(.15*thrust-.035*retract),.045*opening+.012*thrust))
        elif region=='maw_rim':
            a=s['angle'];radial=.32*opening-.46*closing
            M=move(M,(.39*math.cos(a)*radial,0,.34*math.sin(a)*radial))
            M=twist(M,(-math.sin(a),0,math.cos(a)),math.radians(8.*opening-10.*closing))
        elif region=='tendril_base':
            front=max(0.,math.cos(s['angle']))
            M=move(M,(0,-front*(.045*thrust-.018*retract),front*.015*opening))
        elif region in ('tendril_mid','tendril_tip'):
            # Counter the base compression so the support feet stay on their original ground.
            M=rest[n].copy()
            if region=='tendril_mid':
                front=max(0.,math.cos(s['angle']))
                M=move(M,(0,-front*.012*thrust,0))
        pose[n]=M
        local_rest=inverse[parent.name]@rest[n] if parent else rest[n]
        local_pose=pose[parent.name].inverted()@M if parent else M
        basis=local_rest.inverted()@local_pose
        location,rotation,scale=basis.decompose()
        if n in previous and previous[n].dot(rotation)<0:rotation.negate()
        previous[n]=rotation.copy()
        pb.rotation_mode='QUATERNION'
        pb.location=location;pb.rotation_quaternion=rotation;pb.scale=scale
        pb.keyframe_insert('location',frame=f,group=n)
        pb.keyframe_insert('rotation_quaternion',frame=f,group=n)
        pb.keyframe_insert('scale',frame=f,group=n)
# Every frame is baked; linear keys avoid overshoot between the authored contact samples.
for layer in action.layers:
    for strip in layer.strips:
        for slot in action.slots:
            bag=strip.channelbag(slot)
            if bag:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='LINEAR'
rig['action_contract']='Bite: 1.4s, contact .60-.76s, planted root and toes, forward-only'
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True);bpy.context.view_layer.objects.active=rig
blend=ROOT/'M25_Bite_V01.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
fbx=ROOT/'A_M25_Bite_V01.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),object_types={'ARMATURE'},use_selection=True,
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,
    bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
    bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
    bake_anim_step=1.,bake_anim_simplify_factor=0.,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',use_custom_props=True,path_mode='AUTO',embed_textures=False)
record=dict(stage='animation_exported',source=str(SOURCE),blend=str(blend),fbx=str(fbx),
    skeleton=rig.data.name,bones=len(rig.data.bones),fps=30,frames=43,seconds=1.4,
    contact_start=.60,contact_end=.76,front_body_thrust_m=.18,maw_extra_thrust_m=.15,
    root_motion=False,loop=False,original_mesh_and_weights_unchanged=True,rendered=False,tested=False)
(ROOT/'animation_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('M25_BITE_EXPORTED',flush=True)
