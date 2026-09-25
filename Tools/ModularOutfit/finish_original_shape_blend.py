"""Put authored skin materials on the editable derivative; no preview render."""
from pathlib import Path
import bpy

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=Path(globals().get('AUTHOR_ROOT',PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4'))
path=ROOT/'M4_OriginalShape_BareHands_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(path))
obj=bpy.data.objects['M4_OriginalShape_BareHands']
def material(name):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
    bsdf=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial')
    links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
    bsdf.inputs['Roughness'].default_value=.49
    bsdf.inputs['Subsurface Weight'].default_value=.12
    return mat,nodes,links,bsdf
def texture(nodes,path,noncolor=False):
    n=nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(path),check_existing=True)
    if noncolor:n.image.colorspace_settings.name='Non-Color'
    n.image.pack();return n
skin,nodes,links,bsdf=material('M4_OriginalShape_ProceduralSkin')
colour=texture(nodes,ROOT/'T_M4OriginalShape_SkinColour.png')
links.new(colour.outputs['Color'],bsdf.inputs['Base Color'])
surface=texture(nodes,ROOT/'T_M4OriginalShape_SkinSurface.png',True)
separate=nodes.new('ShaderNodeSeparateColor');links.new(surface.outputs['Color'],separate.inputs['Color'])
links.new(separate.outputs['Green'],bsdf.inputs['Roughness'])
normal=texture(nodes,ROOT/'T_M4OriginalShape_SkinNormal.png',True)
channels=nodes.new('ShaderNodeSeparateColor');links.new(normal.outputs['Color'],channels.inputs['Color'])
invert=nodes.new('ShaderNodeMath');invert.operation='SUBTRACT';invert.inputs[0].default_value=1
links.new(channels.outputs['Green'],invert.inputs[1])
combine=nodes.new('ShaderNodeCombineColor')
links.new(channels.outputs['Red'],combine.inputs['Red']);links.new(invert.outputs[0],combine.inputs['Green'])
links.new(channels.outputs['Blue'],combine.inputs['Blue'])
normalmap=nodes.new('ShaderNodeNormalMap');links.new(combine.outputs['Color'],normalmap.inputs['Color'])
links.new(normalmap.outputs['Normal'],bsdf.inputs['Normal'])
obj.data.materials.append(skin);skinindex=len(obj.data.materials)-1
names={g.index:g.name for g in obj.vertex_groups}
parent=list(range(len(obj.data.vertices)))
def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
for edge in obj.data.edges:
    a,b=edge.vertices;parent[find(b)]=find(a)
parts={}
for v in obj.data.vertices:parts.setdefault(find(v.index),[]).append(v)
prefix=('hand_','thumb_','index_','middle_','ring_','pinky_')
handparts={k for k,vs in parts.items() if sum(sum(g.weight for g in v.groups if names[g.group].startswith(prefix)) for v in vs)/len(vs)>.5}
for poly in obj.data.polygons:
    if (poly.material_index==2 if globals().get('KEEP_MATERIAL_PARTITION',False) else find(poly.vertices[0]) in handparts):poly.material_index=skinindex
forearm,nodes,links,bsdf=material('M4_OriginalShape_Forearm_NoLeatherCuff')
regions=texture(nodes,PROJECT/'SourceAssets/HandEquipmentAppearance/T_Manny_ForearmRegions.png',True)
separate=nodes.new('ShaderNodeSeparateColor');links.new(regions.outputs['Color'],separate.inputs['Color'])
mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX'
mix.inputs[1].default_value=(.02,.024,.027,1);mix.inputs[2].default_value=(.36,.235,.185,1)
links.new(separate.outputs['Red'],mix.inputs[0]);links.new(mix.outputs['Color'],bsdf.inputs['Base Color'])
obj.data.materials[1]=forearm
obj['SurfaceAuthoring']='OriginalShapeBareM4: locally authored anatomical skin; DirectX normal green inverted for Blender.'
bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('ORIGINAL_SHAPE_EDITABLE_MATERIALS_SAVED')
