import bpy, json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/FatZombieMeshy20260913')
for file in ('FatZombie_Meshy_Source.blend','FatZombie_Meshy_Animated.blend'):
    bpy.ops.wm.open_mainfile(filepath=str(root/file))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    bpy.context.scene.frame_set(0)
    b=rig.data.bones['Hips'];p=rig.pose.bones['Hips']
    print('FAT_SPACES '+json.dumps({'file':file,'object':rig.name,'object_matrix':[list(r) for r in rig.matrix_world],
        'rest':[list(r) for r in b.matrix_local], 'basis':[list(r) for r in p.matrix_basis],
        'pose':[list(r) for r in p.matrix], 'head_world':list((rig.matrix_world@p.matrix).translation),
        'meshes':[{'object':o.name,'matrix':[list(r) for r in o.matrix_world]} for o in bpy.data.objects if o.type=='MESH']}),flush=True)
for role in ('Idle','Walk','Attack','Death'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(root/'native_retarget'/f'A_FatZombie_Raw_{role}.fbx'))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    before=rig.matrix_world.copy()
    sample=[]
    for f in (rig.animation_data.action.frame_range[0], 81):
        bpy.context.scene.frame_set(int(f))
        sample.append({'frame':f,'rig_scale':list(rig.matrix_world.to_scale()),
            'hips_local':list(rig.pose.bones['Hips'].matrix.translation),
            'hips_world':list((rig.matrix_world@rig.pose.bones['Hips'].matrix).translation)})
    print('FAT_RAW_SPACES '+json.dumps({'role':role,'import_scale':list(before.to_scale()),
        'rest_local':list(rig.data.bones['Hips'].matrix_local.translation),'samples':sample}),flush=True)
