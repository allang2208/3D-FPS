"""Apply the updated master garment topology to editable action scenes.
Animation data and exported clips are not re-authored.
"""
import bpy
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Authoring')
master=ROOT/'WitchRebuilt_Master.blend'
bpy.ops.wm.open_mainfile(filepath=str(master))
names=[o.name for o in bpy.context.scene.objects if o.type=='MESH']
for role in ('Idle','Walk','CastPoison','ThrowPoisonBottle','Hit','DeathBackward','TurnLeft','TurnRight'):
    path=ROOT/f'WitchRebuilt_{role}.blend';bpy.ops.wm.open_mainfile(filepath=str(path))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='POSE'
    for o in list(bpy.context.scene.objects):
        if o.type=='MESH':bpy.data.objects.remove(o,do_unlink=True)
    with bpy.data.libraries.load(str(master),link=False) as (source,target):target.objects=list(names)
    for o in target.objects:
        bpy.context.scene.collection.objects.link(o)
        mw=o.matrix_world.copy();o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted();o.matrix_world=mw
        for mod in o.modifiers:
            if mod.type=='ARMATURE':mod.object=rig
        o.hide_render='SimulationProxy' in o.name;o.hide_set(o.hide_render)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print('UPDATED editable geometry '+role,flush=True)
