"""Rebake support translation on six existing actions without changing choreography."""
from pathlib import Path
import json
import shutil
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'GroundingRepair'
OUT.mkdir(exist_ok=True)
SOURCE=ROOT/'Animations'
REV='RootLocalSupport20260927V1'
ROLES=('Idle','Slam','GrandSlam','Hit','Dizzy','Death')
def backup(file):
    target=(ROOT.parents[1]/'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/GroundingRepair/BeforeSource')/file.relative_to(ROOT)
    if file.exists() and not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(file,target)

blend=SOURCE/'FleshHand_Animated.blend'
receipt_path=SOURCE/'authoring.json'
backup(blend);backup(receipt_path)
receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(blend))
scene=bpy.context.scene
rig=next(o for o in scene.objects if o.type=='ARMATURE')
mesh=max((o for o in scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
rig.animation_data_create()
inverse_root=rig.data.bones['root'].matrix_local.to_3x3().inverted()
inverse_object=rig.matrix_world.inverted().to_3x3()
report={'revision':REV,'state':'baking','clips':{},'changed_channels':'root.location only',
        'fps':scene.render.fps,'rendered':False,'runtime_tested':False}
def record():
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
record()
for role in ROLES:
    action=bpy.data.actions.get('A_FleshHand_'+role)
    if not action:raise RuntimeError('Missing source action: '+role)
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    row=receipt['clips'][role]
    scene.frame_start=0;scene.frame_end=int(row['frames'])
    corrections=[]
    for frame in range(scene.frame_end+1):
        scene.frame_set(frame)
        # Discard the old erroneous horizontal grounding key, retaining every
        # authored joint rotation, scale and local translation below the root.
        root=rig.pose.bones['root']
        root.location=(0,0,0)
        bpy.context.view_layer.update()
        evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        low=min((evaluated.matrix_world@v.co).z for v in evaluated.data.vertices)
        root.location=inverse_root@(inverse_object@Vector((0,0,-low)))
        root.keyframe_insert('location',frame=frame,group='root')
        corrections.append(-low)
    for layer in action.layers:
        for strip in layer.strips:
            for slot in action.slots:
                bag=strip.channelbag(slot)
                if bag:
                    for channel in bag.fcurves:
                        if channel.data_path=='pose.bones["root"].location':
                            for key in channel.keyframe_points:key.interpolation='LINEAR'
    file=SOURCE/('A_FleshHand_'+role+'.fbx')
    backup(file)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
        add_leaf_bones=False,use_armature_deform_only=False,use_mesh_modifiers=False,
        bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,bake_anim_step=1,bake_anim_simplify_factor=0,
        mesh_smooth_type='OFF',path_mode='AUTO')
    row['grounding_revision']=REV
    report['clips'][role]={'file':str(file),'duration_seconds':row['duration_seconds'],
        'frames':row['frames'],'loop':row['loop'],
        'vertical_correction_range_m':[min(corrections),max(corrections)]}
    record();print('HAND_GROUNDING_REBAKED '+role,flush=True)
rig.animation_data.action=None
for bone in rig.pose.bones:
    bone.location=(0,0,0);bone.rotation_mode='QUATERNION'
    bone.rotation_quaternion=(1,0,0,0);bone.scale=(1,1,1)
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
receipt['grounding_revision']=REV
receipt['grounding_repaired_roles']=list(ROLES)
receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
report['state']='six_actions_baked_and_exported';report['blend']=str(blend)
record();print('HAND_BASIC_GROUNDING_AUTHORED '+str(OUT/'authoring.json'),flush=True)
