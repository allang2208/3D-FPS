"""Preserve Infima deform hierarchy and motion; adapt the M4 trigger hinge.
Run with Blender 5.1 --background --factory-startup --python this_file.
The original M4Infima source and imported V3 assets are read-only inputs.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector

SOURCE = Path('D:/FPS3D/FPSGAME/SourceAssets/M4Infima')
OUT = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'M4_Infima_Candidate.blend'))
scene = bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
arm = bpy.data.objects['Armature']
gun = bpy.data.objects['SKEL_AssaultRifle']
CLIPS = {'idle': ('Idle_Loop',90), 'aim': ('Aim_Pose',1), 'fire': ('Fire',23),
         'aim_fire': ('Fire_Aimed',23), 'reload': ('Reload',94),
         'reload_empty': ('Reload',94), 'equip': ('Equip',31), 'inspect': ('Idle_Loop',90)}
GMAP = {'Grip':'WPN_root','Magazine':'WPN_SOCKET_Magazine','Trigger':'WPN_Trigger','Bolt':'WPN_bolt'}
FIT = Matrix(((100,0,0,-3.7),(0,100,0,-16),(0,0,100,4),(0,0,0,1)))
ANCHORS = {'WPN_RearSight':(.0369618,.1246755,.092796), 'WPN_FrontSight':(.0369144,-.1887776,.0925183),
           'WPN_SOCKET_Muzzle':(.037,-.29,.032), 'WPN_SOCKET_Eject':(.063,.08,.045)}

def set_action(obj, name):
    action = bpy.data.actions[name]
    obj.animation_data_create(); obj.animation_data.action = action; obj.animation_data.action_slot = action.slots[0]

def frame(value):
    scene.frame_set(int(value), subframe=value-int(value)); bpy.context.view_layer.update()

def rigid(matrix):
    return Matrix.LocRotScale(matrix.translation, matrix.to_quaternion(), Vector((1,1,1)))

set_action(arm,'A_FP_AssaultRifle_Idle_Pose'); set_action(gun,'A_WEP_Reference'); frame(0)
camera = scene.camera.matrix_world.normalized(); camera.translation = scene.camera.matrix_world.translation
T = Matrix(((.01,0,0,0),(0,0,-.01,0),(0,.01,0,0),(0,0,0,1))) @ camera.inverted()
arm_bind_world = arm.matrix_world.copy(); gun_bind_world = gun.matrix_world.copy()
source_basis = {obj.name:{b.name:b.matrix_basis.copy() for b in obj.pose.bones} for obj in (arm,gun)}
names = [b.name for b in arm.data.bones if b.use_deform and not b.name.startswith(('CB_','REF_'))]
trigger_vertices = [v.co.copy() for v in bpy.data.objects['M4_Trigger Straight Unreal'].data.vertices]
top_z = max(v.z for v in trigger_vertices)
hinge_vertices = [v for v in trigger_vertices if v.z >= top_z-.12]
hinge = sum(hinge_vertices,Vector())/len(hinge_vertices)
hinge.z = top_z
trigger_bind = gun.data.bones['Trigger'].matrix_local.copy(); trigger_bind.translation = hinge
grip_bind = gun.data.bones['Grip'].matrix_local.copy()
trigger_old_local = grip_bind.inverted() @ gun.data.bones['Trigger'].matrix_local
trigger_new_local = grip_bind.inverted() @ trigger_bind

def matrices():
    result = {n:rigid(T @ arm.matrix_world @ arm.pose.bones[n].matrix) for n in names}
    result.update({n:rigid(T @ gun.matrix_world @ gun.pose.bones[b].matrix) for b,n in GMAP.items()})
    grip_pose = gun.pose.bones['Grip'].matrix
    # Retain the source's local trigger rotation, but move its hinge to the M4's actual upper attachment.
    trigger_delta = trigger_old_local.inverted() @ grip_pose.inverted() @ gun.pose.bones['Trigger'].matrix
    result['WPN_Trigger'] = rigid(T @ gun.matrix_world @ grip_pose @ trigger_new_local @ trigger_delta)
    for n,p in ANCHORS.items():
        result[n] = rigid(T @ gun.matrix_world @ grip_pose @ grip_bind.inverted() @ Matrix.Translation(FIT @ Vector(p)))
    result['VM_Root'] = Matrix.Identity(4)
    return result

rest = {n:rigid(T @ arm_bind_world @ arm.data.bones[n].matrix_local) for n in names}
rest.update({n:rigid(T @ gun_bind_world @ gun.data.bones[b].matrix_local) for b,n in GMAP.items()})
rest['WPN_Trigger'] = rigid(T @ gun_bind_world @ trigger_bind)
rest.update({n:matrices()[n] for n in ANCHORS})
rest['VM_Root'] = Matrix.Identity(4)
parents = {'VM_Root':None}
for name in names:
    parent = arm.data.bones[name].parent
    while parent and parent.name not in names: parent = parent.parent
    parents[name] = parent.name if parent else 'VM_Root'
parents['WPN_root'] = 'ik_hand_gun'
assert parents['WPN_root'] in rest
for n in [*GMAP.values(),*ANCHORS]:
    if n != 'WPN_root': parents[n] = 'WPN_root'

# Create parents before children, so both export and local-pose evaluation are deterministic.
ordered = []
def append_bone(name):
    if name in ordered: return
    if parents[name]: append_bone(parents[name])
    ordered.append(name)
for name in rest: append_bone(name)
data = bpy.data.armatures.new('M4InfimaHierarchy')
rig = bpy.data.objects.new('SK_M4_Infima',data); scene.collection.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for name in ordered:
    b=data.edit_bones.new(name); b.length=.025; b.matrix=rest[name]
    if parents[name]: b.parent=data.edit_bones[parents[name]]
bpy.ops.object.mode_set(mode='OBJECT')

meshes=[]
for original in list(scene.objects):
    if original.type!='MESH' or (original.name!='SK_Manny_Arms' and not original.name.startswith('M4_')):continue
    mesh=bpy.data.objects.new(original.name+'_Export',original.data.copy());scene.collection.objects.link(mesh)
    # Blender 5.1 copies the mesh's deform-group definitions with Mesh.copy().
    # Rename those existing groups in place so the stored vertex indices still bind.
    if not mesh.vertex_groups:
        for group in original.vertex_groups:mesh.vertex_groups.new(name=group.name)
    for group in mesh.vertex_groups:group.name=GMAP.get(group.name,group.name)
    for vertex in mesh.data.vertices:
        for group in vertex.groups:
            assert group.weight<=1e-6 or mesh.vertex_groups[group.group].name in rest,(mesh.name,vertex.index,group.group)
    mesh.data.transform(T @ original.matrix_world)
    mesh.parent=rig;mesh.matrix_parent_inverse=Matrix.Identity(4);mesh.matrix_basis=Matrix.Identity(4)
    mod=mesh.modifiers.new('OriginalSkin','ARMATURE');mod.object=rig
    mesh.hide_render=False;mesh.hide_set(False);meshes.append(mesh)
    original.hide_render=True
for image in bpy.data.images:
    candidate=next(iter((SOURCE/'Original').rglob(Path(image.filepath.replace(chr(92),'/')).name)),None)
    if candidate:image.filepath=str(candidate)

reports=[]; cached={}
for key,(source,end) in CLIPS.items():
    # Restore the captured source setup before assigning each action; unkeyed channels cannot leak between clips.
    for obj in (arm,gun):
        obj.animation_data.action=None
        for name,basis in source_basis[obj.name].items():obj.pose.bones[name].matrix_basis=basis
    set_action(arm,'A_FP_AssaultRifle_'+source)
    set_action(gun,'A_FP_WEP_AssaultRifle_Reload' if source=='Reload' else 'A_FP_WEP_AssaultRifle_Fire' if source.startswith('Fire') else 'A_WEP_Reference')
    samples=[]
    for index in range(end*2+1):
        frame(index/2);samples.append(matrices())
    cached[key]=samples
    rig.animation_data_create();a=bpy.data.actions.new('M4_'+key);a.use_fake_user=True;rig.animation_data.action=a
    previous={}
    for index,poses in enumerate(samples):
        for name in ordered:
            parent=parents[name]
            local_rest=rest[parent].inverted() @ rest[name] if parent else rest[name]
            local_pose=poses[parent].inverted() @ poses[name] if parent else poses[name]
            basis=local_rest.inverted() @ local_pose
            loc,quat,scale=basis.decompose()
            if name in previous and previous[name].dot(quat)<0:quat.negate()
            previous[name]=quat.copy()
            b=rig.pose.bones[name];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=quat;b.scale=scale
            for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=index)
    for layer in a.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:point.interpolation='LINEAR'
    scene.render.fps=60;scene.frame_start=0;scene.frame_end=end*2
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/('A_AKM_'+key+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
    reports.append({'clip':key,'source':source,'duration':end/30,'sample_rate':60,'frames':end*2+1})

# Read back the completed local animation, not just the matrices used to write it.
validation={};max_error=0
for key,samples in cached.items():
    set_action(rig,'M4_'+key);error=0;sign_flips=0;previous={}
    for index,expected in enumerate(samples):
        frame(index)
        for name in ordered:
            b=rig.pose.bones[name]
            e=(b.matrix.translation-expected[name].translation).length*100
            error=max(error,e)
            q=b.rotation_quaternion
            if name in previous and previous[name].dot(q)<-.001:sign_flips+=1
            previous[name]=q.copy()
    validation[key]={'max_position_error_cm':error,'quaternion_sign_flips':sign_flips,'samples':len(samples)}
    max_error=max(max_error,error)
    assert error<.005,(key,error)
    assert sign_flips==0,(key,sign_flips)

rig.animation_data_clear()
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for mesh in meshes:mesh.select_set(True)
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_M4_Infima.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',
    add_leaf_bones=False,bake_anim=False,path_mode='COPY',embed_textures=True,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SK_M4_Infima_RigRepair.blend'))
(OUT/'export_report.json').write_text(json.dumps({'clips':reports,'parents':parents,'trigger_hinge_cm':list(hinge),
    'source':str(SOURCE/'M4_Infima_Candidate.blend'),'validation':validation,'max_position_error_cm':max_error,
    'empty_reload':'Preserved source Reload motion; no invented empty-only action.','source_landmarks_frames':[0,15,30,45,57,69,80,94]},indent=2))
print('M4_RIG_REPAIR_EXPORT_PASS',json.dumps(validation))
