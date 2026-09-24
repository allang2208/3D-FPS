"""Bake the existing concrete's actual procedural height input, not its albedo."""
import ast,json,math
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'DungeonAtmosphereV2_20260921/Scripts/bake_structure_materials.py'
OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
# The old blend did not retain its orphan concrete material. Reconstruct exactly
# its deterministic height recipe from the original author helpers and constants.
tree=ast.parse(SOURCE.read_text())
helpers=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('n','mathnode','noise')]
exec(compile(ast.Module(body=helpers,type_ignores=[]),str(SOURCE),'exec'))
mat=bpy.data.materials.new('Concrete_OriginalHeight');mat.use_nodes=True
nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
uv=n(nodes,'ShaderNodeTexCoord');separate=n(nodes,'ShaderNodeSeparateXYZ');links.new(uv.outputs['UV'],separate.inputs[0])
au=mathnode(nodes,links,'MULTIPLY',separate.outputs['X'],math.tau)
av=mathnode(nodes,links,'MULTIPLY',separate.outputs['Y'],math.tau)
xyz=n(nodes,'ShaderNodeCombineXYZ')
links.new(mathnode(nodes,links,'COSINE',au),xyz.inputs['X']);links.new(mathnode(nodes,links,'SINE',au),xyz.inputs['Y'])
links.new(mathnode(nodes,links,'COSINE',av),xyz.inputs['Z']);w=mathnode(nodes,links,'SINE',av)
medium=noise(nodes,links,xyz.outputs[0],w,13)
grain=noise(nodes,links,xyz.outputs[0],w,112,2)
height=mathnode(nodes,links,'ADD',mathnode(nodes,links,'MULTIPLY',medium,.72),mathnode(nodes,links,'MULTIPLY',grain,.28))
depth_cm=.025*.55*100
output=nodes.new('ShaderNodeOutputMaterial')
emit=nodes.new('ShaderNodeEmission');links.new(height,emit.inputs['Color']);links.new(emit.outputs[0],output.inputs['Surface'])
bpy.ops.mesh.primitive_plane_add(size=2)
plane=bpy.context.object;plane.data.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=4
scene.render.bake.margin=0
image=bpy.data.images.new('Concrete_OriginalPhysicalHeight',2048,2048,alpha=False,float_buffer=True)
image.colorspace_settings.name='Non-Color'
tex=nodes.new('ShaderNodeTexImage');tex.image=image;nodes.active=tex;tex.select=True
bpy.ops.object.bake(type='EMIT')
image.filepath_raw=str(OUT/'Concrete_OriginalPhysicalHeight.exr');image.file_format='OPEN_EXR';image.save()
(OUT/'concrete-height.json').write_text(json.dumps({'source':str(SOURCE),'source_node':'V2_Concrete_Bake/Bump/Height',
    'texture':image.filepath_raw,'range_cm':depth_cm,'physical_tile_cm':200,'albedo_derived':False},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ConcreteHeight_Source.blend'))
print('CONCRETE_HEIGHT_AUTHORED',depth_cm,flush=True)
