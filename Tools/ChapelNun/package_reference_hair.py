"""Package the preserved R4 character surfaces with the R5 editable groom."""
import bpy
from pathlib import Path
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');R=N/'HairReferenceR5'
bpy.ops.wm.open_mainfile(filepath=str(N/'RefinementR4/Authored/ChapelNun_Final_R4.blend'))
for ob in list(bpy.data.objects):
 if ob.name.startswith('Nun_LowBun_') or ob.name=='Editable_SweepGuides':bpy.data.objects.remove(ob,do_unlink=True)
with bpy.data.libraries.load(str(R/'Authored/Nun_ReferenceHair_R5.blend'),link=False) as (src,dst):
 dst.objects=[n for n in src.objects if n.startswith('Nun_LowBun_') or n=='Editable_SweepGuides']
mat=bpy.data.materials.new('NativeBlackHair_R5_Preview');mat.use_nodes=True;nt=mat.node_tree;nt.nodes.clear()
shader=nt.nodes.new('ShaderNodeBsdfHairPrincipled');shader.parametrization='MELANIN';shader.inputs['Melanin'].default_value=.94;shader.inputs['Melanin Redness'].default_value=0;shader.inputs['Roughness'].default_value=.42
out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(shader.outputs[0],out.inputs['Surface'])
for ob in dst.objects:
 bpy.context.scene.collection.objects.link(ob)
 ob['ue_material']='/Game/Characters/ChapelNun20261115/HairReferenceR5/Materials/MI_Nun_Hair'
 if ob.type=='CURVES':ob.data.materials.append(mat)
for im in bpy.data.images:
 if im.source=='FILE':im.pack()
bpy.context.scene['hair_reference']=str(N/'Design/NunHead_R2.png')
bpy.context.scene['surface_revision']='RefinementR4; original Meshy face retained'
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Authored/ChapelNun_ReferenceHair_R5.blend'))
print('REFERENCE_HAIR_PACKAGED',flush=True)
