import bpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');O=P/'HeadQualityR2/Authored'
bpy.ops.wm.open_mainfile(filepath=str(P/'ProductionR1/Authored/ChapelNun_Complete_Source.blend'))
for obj in list(bpy.data.objects):
    if obj.name=='SK_NunHead' or obj.name.startswith('Nun_LowBun_'):
        bpy.data.objects.remove(obj,do_unlink=True)
with bpy.data.libraries.load(str(O/'Nun_Head_Hair_R2.blend'),link=False) as (src,dst):
    dst.objects=[name for name in src.objects if name=='SK_NunHead' or name.startswith('Nun_LowBun_')]
rig=bpy.data.objects['Kaitlin_Nun_Rig']
for obj in dst.objects:
    bpy.context.scene.collection.objects.link(obj)
    if obj.name=='SK_NunHead':
        mod=obj.modifiers.new('NativeBinding','ARMATURE');mod.object=rig;obj.parent=rig
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ChapelNun_Complete_R2.blend'))
print('COMPLETE_NUN_R2_SOURCE_SAVED',flush=True)
