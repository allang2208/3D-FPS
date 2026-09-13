"""Attach the UE-baked tool clips to the accepted editable miner mesh.

Only animation data is replaced. Bone rest frames, mesh, weights and materials
come from the accepted snapshot. No rendering or acceptance checks are run.
"""
import bpy,json,sys
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets')
O=R/('InfectedMiner20260913/PickaxeSingleHand/Delivery' if '--pickaxe' in sys.argv else 'InfectedMiner20260913/Delivery')
contract=json.loads((O/'rebuild.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(R/'InfectedMiner20260912/Review/Hand_UserAccepted_20260912/InfectedMiner_Editable.blend'))
rig=bpy.data.objects['MinerRig'];scene=bpy.context.scene;scene.render.fps=30
target_rest={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
ordered=sorted(rig.pose.bones,key=lambda b:len(b.parent_recursive))
for state in ['Idle','Walk','Attack']:
    existing=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(O/f'A_Miner_{state}.fbx'),anim_offset=0)
    imported=set(bpy.data.objects)-existing
    donor=next(o for o in imported if o.type=='ARMATURE')
    donor_rest={b.name:donor.matrix_world@b.matrix_local for b in donor.data.bones}
    source_action=donor.animation_data.action
    old=bpy.data.actions.get('A_Miner_'+state)
    if old:old.name='Previous_'+old.name;old.use_fake_user=False
    action=bpy.data.actions.new('A_Miner_'+state);action.use_fake_user=True
    rig.animation_data.action=action
    count=round(contract['clips'][state]['seconds']*30)
    action.use_frame_range=True;action.frame_start=1;action.frame_end=count+1
    for frame in range(count+1):
        scene.frame_set(frame);bpy.context.view_layer.update()
        poses={n:donor.matrix_world@donor.pose.bones[n].matrix@donor_rest[n].inverted()@rest
               for n,rest in target_rest.items() if n in donor_rest}
        for bone in ordered:
            if bone.name in poses:
                bone.matrix=rig.matrix_world.inverted()@poses[bone.name]
                bpy.context.view_layer.update()
        for bone in rig.pose.bones:
            bone.rotation_mode='QUATERNION'
            for channel in ['location','rotation_quaternion','scale']:
                bone.keyframe_insert(channel,frame=frame+1)
        if action.slots:rig.animation_data.action_slot=action.slots[0]
    for obj in imported:bpy.data.objects.remove(obj,do_unlink=True)
    if source_action.users==0:bpy.data.actions.remove(source_action)
    if old and old.users==0:bpy.data.actions.remove(old)
rig.animation_data.action=bpy.data.actions['A_Miner_Attack']
rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_start=1;scene.frame_end=round(contract['clips']['Attack']['seconds']*30)+1
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'InfectedMiner_Editable.blend'))
print('MINER_DEFAULT_EDITABLE_SAVED',flush=True)
