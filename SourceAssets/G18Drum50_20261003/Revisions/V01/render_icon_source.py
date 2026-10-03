"""Resume production icon creation from the completed editable model."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'G18_Drum50_Editable.blend'))
root=Matrix(json.loads((O/'authoring.json').read_text())['root'])
body=bpy.data.objects['Drum50_AuthoredBody'];neck=bpy.data.objects['Retained_G18_Feed_Neck'];scene=bpy.context.scene
mat=neck.data.materials[0];n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear();bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs[0],out.inputs['Surface'])
for ch,input_name in [('Base_color','Base Color'),('Roughness','Roughness'),('Metallic','Metallic')]:
    t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(O.parent/'G18Integration20260929/Textures'/('T_G18_'+ch+'.png')),check_existing=True)
    t.image.colorspace_settings.name='sRGB' if ch=='Base_color' else 'Non-Color';l.new(t.outputs['Color'],bs.inputs[input_name])
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'G18_Drum50_Editable.blend'))
source=(O/'author_drum.py').read_text();exec(compile(source[source.index('# Production source image'):],str(O/'author_drum.py'),'exec'))
