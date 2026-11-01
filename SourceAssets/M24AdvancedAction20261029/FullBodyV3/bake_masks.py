"""Author a unique WS1 RGBA mask from the final static geometry, not a preview."""
import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_AdvancedAction_FullBodyV3.blend'),use_scripts=False)
body=bpy.data.objects['M24_AdvancedAction_DetailBody'];original=list(body.data.materials)
for ob in bpy.data.objects:ob.hide_render=ob!=body
body.hide_set(False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16
s.render.threads_mode='FIXED';s.render.threads=8
s.render.bake.margin=8;s.render.bake.use_selected_to_active=False
body.data.uv_layers.active_index=1;body.data.uv_layers[1].active_render=True
image=bpy.data.images.new('T_M24_AAS_V3_SurfaceMask',width=2048,height=2048,alpha=True,float_buffer=True)
image.colorspace_settings.name='Non-Color';image.generated_color=(0,0,1,1)
m=bpy.data.materials.new('Mask authoring');m.use_nodes=True;n=m.node_tree.nodes;n.clear();l=m.node_tree.links
def node(kind):return n.new(kind)
def mathnode(op,*args):
    q=node('ShaderNodeMath');q.operation=op
    for i,a in enumerate(args):
        if isinstance(a,(int,float)):q.inputs[i].default_value=a
        else:l.new(a,q.inputs[i])
    return q.outputs[0]
geo=node('ShaderNodeNewGeometry');bev=node('ShaderNodeBevel');bev.inputs['Radius'].default_value=.00022;bev.samples=4
diff=node('ShaderNodeVectorMath');diff.operation='DISTANCE';l.new(geo.outputs['Normal'],diff.inputs[0]);l.new(bev.outputs['Normal'],diff.inputs[1])
edge=mathnode('MINIMUM',mathnode('MULTIPLY',diff.outputs['Value'],2.5),1.)
convex=mathnode('MINIMUM',mathnode('MAXIMUM',mathnode('MULTIPLY',mathnode('SUBTRACT',geo.outputs['Pointiness'],.5),80.),0.),1.)
edge=mathnode('MULTIPLY',edge,convex)
short=node('ShaderNodeAmbientOcclusion');short.inputs['Distance'].default_value=.003;short.samples=16;short.only_local=True
long=node('ShaderNodeAmbientOcclusion');long.inputs['Distance'].default_value=.022;long.samples=16;long.only_local=True
rgb=node('ShaderNodeCombineColor');rgb.mode='RGB'
l.new(edge,rgb.inputs[0]);l.new(mathnode('SUBTRACT',1.,short.outputs['AO']),rgb.inputs[1]);l.new(long.outputs['AO'],rgb.inputs[2])
emit=node('ShaderNodeEmission');l.new(rgb.outputs[0],emit.inputs['Color'])
output=node('ShaderNodeOutputMaterial');l.new(emit.outputs[0],output.inputs['Surface'])
target=node('ShaderNodeTexImage');target.image=image;n.active=target
for i in range(len(body.data.materials)):body.data.materials[i]=m
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.object.bake(type='EMIT',use_clear=False)
pixels=np.empty(2048*2048*4,dtype=np.float32);image.pixels.foreach_get(pixels);pixels=pixels.reshape((-1,4))
pixels[:,3]=1-np.clip(pixels[:,1],0,1);image.pixels.foreach_set(pixels.ravel())
image.filepath_raw=str(O/'Textures/T_M24_AAS_V3_SurfaceMask.png');image.file_format='PNG';image.save()
for i,mat in enumerate(original):body.data.materials[i]=mat
body.data.uv_layers.active_index=0;body.data.uv_layers[0].active_render=True
# Restore viewable work materials with the same UV0 microfinish used in UE.
for mat,key in zip(original,('Metal','Steel','Interior')):
    key={'M24_AAS_CoatedMetal':'Metal','M24_AAS_SatinSteel':'Steel','M24_AAS_Interior':'Interior'}[mat.name]
    p=next(x for x in mat.node_tree.nodes if x.type=='BSDF_PRINCIPLED');nodes=mat.node_tree.nodes;links=mat.node_tree.links
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map='Surface4cm'
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O/f'Textures/T_M24_AAS_V3_{key}_N.png'));tex.image.colorspace_settings.name='Non-Color'
    links.new(uv.outputs[0],tex.inputs['Vector']);norm=nodes.new('ShaderNodeNormalMap');norm.uv_map='Surface4cm';links.new(tex.outputs['Color'],norm.inputs['Color']);links.new(norm.outputs['Normal'],p.inputs['Normal'])
    rough=nodes.new('ShaderNodeTexImage');rough.image=bpy.data.images.load(str(O/f'Textures/T_M24_AAS_V3_{key}_R.png'));rough.image.colorspace_settings.name='Non-Color';links.new(uv.outputs[0],rough.inputs['Vector'])
    add=nodes.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=p.inputs['Roughness'].default_value-.5
    links.new(rough.outputs['Color'],add.inputs[0]);links.new(add.outputs[0],p.inputs['Roughness'])
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_AdvancedAction_FullBodyV3.blend'))
(O/'bake_receipt.json').write_text(json.dumps(dict(complete=True,resolution=2048,uv=1,
    channels={'R':'convex bevel proximity','G':'local cavity 3mm','B':'local AO 22mm','A':'1-cavity'},
    bevel_radius_mm=.22,geometry='final authored static body; native host excluded',runtime_tested=False),indent=2))
print('M24_DETAIL_V2_MASK_BAKED',flush=True)
