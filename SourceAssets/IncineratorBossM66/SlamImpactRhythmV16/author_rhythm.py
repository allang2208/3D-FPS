"""Retime the accepted closed-fist slam: fast acceleration, 0.5 s grounded hold."""
import bpy,json,math
from pathlib import Path

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'SlamImpactRhythmV16'
for folder in ('Authoring','Export','Records'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
SOURCE=BASE/'FistSlamV14/Authoring/M66_fist_slam_v14.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body']
FPS=120;STRIKE=1.35;IMPACT=1.50;HOLD=.50;RECOVER=IMPACT+HOLD
SOURCE_IMPACT=98/60.;END=RECOVER+(3.5-SOURCE_IMPACT);COUNT=round(END*FPS)+1
def source_time(t):
    if t<=STRIKE:return t
    if t<IMPACT:
        u=(t-STRIKE)/(IMPACT-STRIKE)
        # The whole pose accelerates into the contact, then brakes at the floor.
        return STRIKE+(SOURCE_IMPACT-STRIKE)*u**1.65
    if t<=RECOVER:return SOURCE_IMPACT
    u=max(0.,min(1.,(t-RECOVER)/(END-RECOVER)))
    # Slow initial release from the planted fist, then a continuous recovery.
    return SOURCE_IMPACT+(3.5-SOURCE_IMPACT)*(2*u*u-u*u*u)

names=[b.name for b in rig.pose.bones];samples=[];mapping=[]
for i in range(COUNT):
    seconds=i/FPS;source_seconds=source_time(seconds);source_frame=source_seconds*60.
    scene.frame_set(int(source_frame),subframe=source_frame-int(source_frame));bpy.context.view_layer.update()
    samples.append({n:rig.pose.bones[n].matrix_basis.decompose() for n in names})
    mapping.append({'time':seconds,'source_time':source_seconds})

action=bpy.data.actions.new('A_M66_FistSlam_V16');action.use_fake_user=True;rig.animation_data.action=action
scene.render.fps=FPS;scene.frame_start=0;scene.frame_end=COUNT-1;previous={}
for frame,pose in enumerate(samples):
    scene.frame_set(frame)
    for n,(position,rotation,scale) in pose.items():
        pb=rig.pose.bones[n];pb.rotation_mode='QUATERNION'
        q=rotation.copy()
        if n in previous and q.dot(previous[n])<0:q.negate()
        pb.location=position;pb.rotation_quaternion=q;pb.scale=scale;previous[n]=q.copy()
        for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame,group=n)
if action.slots:rig.animation_data.action_slot=action.slots[0]
for layer in action.layers:
    for strip in layer.strips:
        for curve in strip.channelbag(action.slots[0]).fcurves:
            # Dense samples encode nonlinear source time; Bezier overshoot would
            # change the preserved fist contact and full-body support poses.
            for key in curve.keyframe_points:key.interpolation='LINEAR'
timing={'strike_start_seconds':STRIKE,'impact_seconds':IMPACT,'ground_hold_seconds':HOLD,
    'ground_hold_end_seconds':RECOVER,'end_seconds':END,'source_impact_seconds':SOURCE_IMPACT,
    'source_downstroke_seconds':SOURCE_IMPACT-STRIKE,'new_downstroke_seconds':IMPACT-STRIKE,
    'downstroke_average_speed_multiplier':(SOURCE_IMPACT-STRIKE)/(IMPACT-STRIKE),
    'contact_start_seconds':1.42,'contact_end_seconds':IMPACT,'rest_after_end_seconds':1.,
    'fps':FPS,'frames':COUNT,'runtime_tested':False,'rendered':False}
for key,value in timing.items():action[key]=value
action['M66_source']='V14 closed fist and complete body preserved; nonlinear downstroke and 0.5 s grounded recovery hold'
scene.frame_set(0);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=ROOT/'Export/A_M66_FistSlam_V16.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
    bake_anim_step=1.,bake_anim_simplify_factor=0.,use_mesh_modifiers=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
authoring=ROOT/'Authoring/M66_fist_slam_rhythm_v16.blend';bpy.ops.wm.save_as_mainfile(filepath=str(authoring))
manifest={'source':str(SOURCE),'authoring':str(authoring),'timing':timing,
    'clips':[{'role':'FistSlam','action':action.name,'fbx':str(fbx),'seconds':END,'fps':FPS,'frames':COUNT,'loop':False}],
    'bones':len(names),'mesh_modified':False,'weights_modified':False,'runtime_tested':False,'rendered':False}
(ROOT/'Records/animation_manifest.json').write_text(json.dumps(manifest,indent=2))
(ROOT/'Records/timing_contract.json').write_text(json.dumps(timing,indent=2))
(ROOT/'Records/source_time_mapping.json').write_text(json.dumps(mapping,indent=2))
contact=json.loads((BASE/'FistSlamV14/Records/fist_contact_definition.json').read_text())
contact['contact_start']=timing['contact_start_seconds'];contact['contact_end']=IMPACT
contact['source_definition']='FistSlamV14/Records/fist_contact_definition.json'
contact['purpose']='Same closed fist surface; V16 samples locate the V15 ground AOE at the retimed impact'
(ROOT/'Records/fist_contact_definition.json').write_text(json.dumps(contact,indent=2))
print('M66_SLAM_RHYTHM_V16_AUTHORED '+json.dumps(timing),flush=True)
