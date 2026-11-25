"""Pack the authored temple surface on the head copy of the native GLB material."""
from pathlib import Path
import bpy

root=Path(__file__).resolve().parents[5]
folder=root/'SourceAssets/HillsVillageStable/StablemasterHeadR5'
blend=folder/'StablemasterNative.blend'
bpy.ops.wm.open_mainfile(filepath=str(blend))
material=bpy.data.objects['SK_Stablemaster_Head_R5'].data.materials[0]
bsdf=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
pending=[link.from_node for link in bsdf.inputs['Base Color'].links]
seen=set()
while pending:
    node=pending.pop()
    if node in seen:continue
    seen.add(node)
    if node.type=='TEX_IMAGE':
        color=bpy.data.images.load(str(folder/'T_Stablemaster_Head_R5_Color.png'),check_existing=True)
        color.colorspace_settings.name='sRGB';color.pack()
        node.image=color
        break
    pending.extend(link.from_node for socket in node.inputs for link in socket.links)
else:
    raise RuntimeError('The native material has no base color texture')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
