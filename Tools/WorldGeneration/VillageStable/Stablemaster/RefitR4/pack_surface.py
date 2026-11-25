"""Store the revised skin albedo in the editable assembly."""
from pathlib import Path
import bpy
p=Path(bpy.data.filepath).parent
head=bpy.data.objects['SK_Stablemaster_Head'];mat=head.data.materials[0]
bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
node=bs.inputs['Base Color'].links[0].from_node
if node.type!='TEX_IMAGE':raise ValueError('Expected Meshy base-color texture')
image=bpy.data.images.load(str(p/'T_Stablemaster_Head_R4_Color.png'));image.pack();node.image=image
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(p/'StablemasterR4.blend'),compress=True)
