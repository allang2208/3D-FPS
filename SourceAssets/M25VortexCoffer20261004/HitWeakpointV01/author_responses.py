"""Author short recoil and soft collapse on the accepted M25 skeleton; no renders/tests."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Quaternion
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'BiteV01/M25_Bite_V01.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
rig.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
spec=json.loads((ROOT.parent/'RigV01/skeleton_spec.json').read_text(encoding='utf-8'))
meta={s['name']:s for s in spec}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
inverse={n:m.inverted() for n,m in rest.items()}
scene=bpy.context.scene
scene.render.fps=30
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
rig.data.pose_position='POSE';rig.animation_data_create()
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def move(M,d):M=M.copy();M.translation+=Vector(d);return M
def twist(M,axis,degrees):
    p=M.translation.copy()
    M=Quaternion(Vector(axis),math.radians(degrees)).to_matrix().to_4x4()@M
    M.translation=p;return M
records=[]
for role,seconds in [('Hit',.6),('Death',1.6)]:
    end=round(seconds*30)+1
    scene.frame_start=1;scene.frame_end=end
    action=bpy.data.actions.new('M25_'+role+'_V01')
    rig.animation_data.action=action;action.use_fake_user=True
    previous={}
    for frame in range(1,end+1):
        t=(frame-1)/30.
        hit=smooth(t/.12) if t<=.12 else (1-smooth((t-.12)/.48))
        collapse=smooth((t-.08)/1.25)
        pose={}
        for pb in rig.pose.bones:
            n=pb.name;s=meta[n];parent=pb.parent;region=s['region']
            M=pose[parent.name]@inverse[parent.name]@rest[n] if parent else rest[n].copy()
            if role=='Hit':
                if region=='body':
                    w=.25+.75*(s['section']/6.)**1.5
                    M=move(M,(0,.032*w*hit,-.008*w*hit))
                    M=twist(M,(1,0,0),-1.6*w*hit)
                elif region=='mouth':
                    M=move(M,(0,.045*hit,.012*hit))
                elif region=='maw_rim':
                    a=s['angle']
                    M=move(M,(-.39*math.cos(a)*.10*hit,0,-.34*math.sin(a)*.10*hit))
                elif region in ('tendril_mid','tendril_tip'):
                    M=rest[n].copy()
            else:
                if region=='body':
                    # Flatten the mound without cumulative hierarchical scale.
                    M=rest[n].copy()
                    h=M.translation.z
                    M=move(M,(0,0,-max(0,h-.08)*.45*collapse))
                    M=twist(M,(0,1,0),3.0*collapse)
                elif region=='sac':
                    M=move(M,(s['side']*.032*collapse,0,-.025*collapse))
                elif region=='mouth':
                    M=move(M,(0,-.035*collapse,-.035*collapse))
                    M=twist(M,(1,0,0),6*collapse)
                elif region=='maw_rim':
                    a=s['angle']
                    M=move(M,(.39*math.cos(a)*.10*collapse,0,-.34*math.sin(a)*.30*collapse))
                elif region=='electrode':
                    M=twist(M,(0,1,0),4.*math.sin(s.get('section',0)+.5)*collapse)
                elif region in ('tendril_base','tendril_mid','tendril_tip'):
                    M=rest[n].copy()
                    if region!='tendril_tip':
                        M=move(M,(0,0,-max(0,M.translation.z-.04)*.35*collapse))
            pose[n]=M
            local_rest=inverse[parent.name]@rest[n] if parent else rest[n]
            local_pose=pose[parent.name].inverted()@M if parent else M
            location,rotation,scale=(local_rest.inverted()@local_pose).decompose()
            if n in previous and previous[n].dot(rotation)<0:rotation.negate()
            previous[n]=rotation.copy()
            pb.rotation_mode='QUATERNION'
            pb.location=location;pb.rotation_quaternion=rotation;pb.scale=scale
            for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame,group=n)
    for layer in action.layers:
        for strip in layer.strips:
            for slot in action.slots:
                bag=strip.channelbag(slot)
                if bag:
                    for fc in bag.fcurves:
                        for key in fc.keyframe_points:key.interpolation='LINEAR'
    scene.frame_set(1)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True);bpy.context.view_layer.objects.active=rig
    fbx=ROOT/('A_M25_'+role+'_V01.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),object_types={'ARMATURE'},use_selection=True,
        add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
        bake_anim_step=1.,bake_anim_simplify_factor=0.,axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',use_custom_props=True,
        path_mode='AUTO',embed_textures=False)
    records.append(dict(role=role,seconds=seconds,frames=end,fbx=str(fbx)))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'M25_HitDeath_V01.blend'),compress=True)
(ROOT/'animation_receipt.json').write_text(json.dumps(dict(stage='animations_exported',
    animations=records,source=str(SOURCE),root_motion=False,full_mesh_modified=False,
    rendered=False,tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('M25_HIT_DEATH_EXPORTED',flush=True)
