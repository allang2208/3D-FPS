"""Full editable R9 source, retaining the restored original Meshy face and gown."""
import bpy
from pathlib import Path
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115')
R=N/'HairNativeCombR9'
bpy.ops.wm.open_mainfile(filepath=str(N/'FaceOriginalRestoreR6/Authored/ChapelNun_OriginalFace_ReferenceHair_R6.blend'))
for ob in list(bpy.data.objects):
 if ob.name.startswith('Nun_LowBun_') or ob.name=='Editable_SweepGuides':
  bpy.data.objects.remove(ob,do_unlink=True)
with bpy.data.libraries.load(str(R/'Authored/Nun_NativeComb_R9.blend'),link=False) as (src,dst):
 dst.objects=[name for name in src.objects if name.startswith('Nun_LowBun_')]
mat=bpy.data.materials.new('NativeBlackHair_R9_Preview');mat.use_nodes=True
nt=mat.node_tree;nt.nodes.clear();shader=nt.nodes.new('ShaderNodeBsdfHairPrincipled');shader.parametrization='MELANIN'
shader.inputs['Melanin'].default_value=.94;shader.inputs['Melanin Redness'].default_value=0
shader.inputs['Roughness'].default_value=.42
out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(shader.outputs[0],out.inputs['Surface'])
for ob in dst.objects:
 bpy.context.scene.collection.objects.link(ob)
 ob['ue_material']='/Game/Characters/ChapelNun20261115/HairReferenceR5/Materials/MI_Nun_Hair'
 if ob.type=='CURVES':ob.data.materials.append(mat)
for im in bpy.data.images:
 if im.source=='FILE':im.pack()
bpy.context.scene['hair_reference']=str(N/'Design/NunHead_R2.png')
bpy.context.scene['hair_revision']='NativeCombR9; native strand shapes, asymmetric sweep and close interwoven low chignon'
bpy.context.scene['surface_revision']='FaceOriginalRestoreR6; original Meshy face and clothing unchanged'
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Authored/ChapelNun_OriginalFace_NativeComb_R9.blend'))
print('FULL_REFERENCE_HAIR_PACKAGED',flush=True)
