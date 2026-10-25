"""Bake the supplied bed takes at their native 30 Hz seconds for UE import."""
import bpy,json
from pathlib import Path
from mathutils import Matrix

OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/MeshySitLieBed37120261024')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Imported/source_unmodified.blend'))
rig=bpy.data.objects['target_character']
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.find_armature()==rig]
for obj in bpy.context.scene.objects:
    if obj.animation_data:obj.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
source=json.loads((OUT/'source_world.json').read_text())
scene=bpy.context.scene;scene.render.fps=30;scene.render.fps_base=1.
reference={n:rig.data.bones[n].matrix_local.copy() for n in source['names']}
for name,take in source['clips'].items():
    action=bpy.data.actions.new(name);action.use_fake_user=True
    rig.animation_data_create();rig.animation_data.action=action
    for i,frame in enumerate(take['frames']):
        world={n:Matrix(m) for n,m in zip(source['names'],frame)}
        for n in source['names']:
            bone=rig.data.bones[n];parent=bone.parent.name if bone.parent else None
            local_rest=reference[parent].inverted()@reference[n] if parent else reference[n]
            local_pose=world[parent].inverted()@world[n] if parent else world[n]
            location,rotation,scale=(local_rest.inverted()@local_pose).decompose()
            p=rig.pose.bones[n];p.rotation_mode='QUATERNION';p.location=location;p.rotation_quaternion=rotation;p.scale=scale
            for prop in ('location','rotation_quaternion','scale'):p.keyframe_insert(prop,frame=i,group=n)
    print('MESHY_BED_BAKED',name,len(take['frames']),take['duration'],flush=True)
rig.animation_data.action=bpy.data.actions['sleep']
scene.frame_start=0;scene.frame_end=len(source['clips']['sleep']['frames'])-1;scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
for obj in [rig,*meshes]:obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'Meshy_Bed_Source.fbx'),use_selection=True,
    object_types={'ARMATURE','MESH'},add_leaf_bones=False,axis_forward='-Y',axis_up='Z',
    bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,
    bake_anim_step=1.,bake_anim_simplify_factor=0.,path_mode='AUTO')
print('MESHY_BED_FBX_EXPORTED',flush=True)
