"""Keep fitted attachment working materials consistent with the mirror gun."""
from pathlib import Path
import bpy
O=Path(__file__).parent;bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(O/'DanWesson715_Mirror_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
for ob in bpy.data.objects:
    if ob.type!='MESH' or not ob.name.startswith('DW715_Attachment_'):continue
    for mat in ob.data.materials:
        if not mat.use_nodes:continue
        for node in mat.node_tree.nodes:
            if node.type=='TEX_IMAGE' and node.image and node.image.name.startswith('T_DW715_Attachment_'):
                kind='ORM' if 'ORM' in node.image.name else 'BaseColor'
                node.image=bpy.data.images.load(str(O/'Textures'/('T_DW715_Mirror_Attachment_'+kind+'.png')),check_existing=True)
                node.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_Mirror_Editable.blend'))
print('DW715_MIRROR_EDITABLE_COMPLETE',flush=True)
