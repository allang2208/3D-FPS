"""Repair the reported hand skin contamination and omitted forearm branch on V06."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'HandContinuityV08'
for folder in ('Authoring','Export','Records'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'ClawSweepV06/Authoring/M66_claw_sweep_v06.blend'))
rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body'];scene=bpy.context.scene
scene.frame_set(0);bpy.context.view_layer.update()
branch_names=('Bone_035','Bone_034')
branch_neutral={n:rig.pose.bones[n].matrix_basis.copy() for n in branch_names}
source_action=rig.animation_data.action
groups=[g.name for g in mesh.vertex_groups]
original=[{groups[g.group]:g.weight for g in v.groups if g.weight>1e-7} for v in mesh.data.vertices]
result=[dict(w) for w in original]
positions=np.array([v.co[:] for v in mesh.data.vertices])
def below(name,ancestor):
    bone=rig.data.bones[name]
    while bone.parent:
        bone=bone.parent
        if bone.name==ancestor:return True
    return False
arm={b.name for b in rig.data.bones if b.name=='Bone_027' or below(b.name,'Bone_027')}
changed=set();removed={}
for i,(x,y,z) in enumerate(positions):
    # This distal-arm region is outside the separate leg and oral-wall surface.
    # Preserve the shoulder attachment and the V05 mouth/eye edits.
    if not (x<-.46 and .45<z<2.28):continue
    retained={name:value for name,value in original[i].items() if name in arm}
    total=sum(retained.values());foreign={name:value for name,value in original[i].items() if name not in arm}
    if total<.04 or sum(foreign.values())<1e-6:continue
    result[i]={name:value/total for name,value in retained.items()};changed.add(i)
    for name,value in foreign.items():removed[name]=removed.get(name,0)+value
# Split UV vertices at an edited boundary must retain the same skin transform.
_,inverse=np.unique(np.rint(positions/1e-6).astype(np.int64),axis=0,return_inverse=True)
seams={}
for i,key in enumerate(inverse):seams.setdefault(int(key),[]).append(i)
for ids in seams.values():
    if len(ids)<2 or not any(i in changed for i in ids):continue
    mean={}
    for i in ids:
        for name,value in result[i].items():mean[name]=mean.get(name,0)+value/len(ids)
    for i in ids:result[i]=dict(mean);changed.add(i)
for i in changed:
    for group in list(mesh.data.vertices[i].groups):mesh.vertex_groups[group.group].remove([i])
    for name,value in result[i].items():mesh.vertex_groups[name].add([i],value,'REPLACE')

action=source_action.copy();action.name='A_M66_ClawSweep_V08';action.use_fake_user=True
rig.animation_data.action=action
if action.slots:rig.animation_data.action_slot=action.slots[0]
# The complete original shoulder/elbow/wrist action remains unchanged. The
# omitted branch must inherit its new parent, instead of compensating back to
# the old body-space position with metre-long local translation keys.
for frame in range(157):
    scene.frame_set(frame)
    for name in branch_names:
        pb=rig.pose.bones[name];pb.matrix_basis=branch_neutral[name]
        for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame,group=name)
for layer in action.layers:
    for strip in layer.strips:
        for curve in strip.channelbag(action.slots[0]).fcurves:
            if any('"'+n+'"' in curve.data_path for n in branch_names):
                for key in curve.keyframe_points:key.interpolation='LINEAR'
action['M66_source']='V06 full-arm sweep; only the omitted Bone_035/Bone_034 forearm branch is corrected'

# Save a true bind-pose mesh; animation is exported separately on the same rig.
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
options=dict(use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,
    use_mesh_modifiers=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
    mesh_smooth_type='OFF',path_mode='AUTO')
mesh_file=ROOT/'Export/SK_M66_HandContinuity_V08.fbx'
bpy.ops.export_scene.fbx(filepath=str(mesh_file),bake_anim=False,**options)
rig.animation_data.action=action
if action.slots:rig.animation_data.action_slot=action.slots[0]
scene.frame_start=0;scene.frame_end=156;scene.render.fps=60;scene.frame_set(0)
animation_file=ROOT/'Export/A_M66_ClawSweep_V08.fbx'
bpy.ops.export_scene.fbx(filepath=str(animation_file),bake_anim=True,bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
    bake_anim_step=1.,bake_anim_simplify_factor=0.,**options)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/M66_hand_continuity_v08.blend'))
manifest={'source':str(BASE/'ClawSweepV06/Authoring/M66_claw_sweep_v06.blend'),
    'fbx':str(mesh_file),'authoring':str(ROOT/'Authoring/M66_hand_continuity_v08.blend'),
    'edited_vertices':len(changed),'removed_foreign_influence_sums':removed,'corrected_branch':list(branch_names),
    'bones':len(rig.data.bones),'vertices':len(positions),'triangles':sum(len(p.vertices)-2 for p in mesh.data.polygons),
    'geometry_modified':False,'uv_modified':False,'main_sweep_trajectory_preserved':True,
    'clips':[{'role':'ClawSweep','action':action.name,'fbx':str(animation_file),'seconds':2.6,'fps':60,'frames':157,'loop':False}],
    'runtime_tested':False,'rendered':False}
(ROOT/'Records/animation_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('M66_HAND_CONTINUITY_AUTHORED '+json.dumps({'edited_vertices':len(changed),'removed':removed,'branch':list(branch_names)}),flush=True)
