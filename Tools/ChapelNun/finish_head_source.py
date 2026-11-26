import bpy,runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/ChapelNun20261115/HeadQualityR2/Authored'
bpy.ops.wm.open_mainfile(filepath=str(O/'Nun_Head_Hair_R2.blend'))
head=bpy.data.objects['SK_NunHead']
for i,rough in [(2,.22),(3,.44)]:
    mat=head.data.materials[i];bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Roughness'].default_value=rough
    if i==2:
        for link in list(bs.inputs['Normal'].links):mat.node_tree.links.remove(link)
        bs.inputs['Subsurface Weight'].default_value=.1
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Nun_Head_Hair_R2.blend'))
runpy.run_path(str(P/'Tools/ChapelNun/package_head_quality.py'),run_name='__main__')
print('FINAL_HEAD_SOURCE_SAVED',flush=True)
