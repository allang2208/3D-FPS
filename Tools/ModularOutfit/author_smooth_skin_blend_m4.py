"""Write the smooth variant as a new editable shape and packed skin material."""
import json,runpy
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4';ROOT=BASE/'SmoothSkinV2'
data=json.loads((ROOT/'M4_original.json').read_text());shape=json.loads((ROOT/'M4_bare_shape.json').read_text())
def point(p):return Vector((p[0],-p[1],p[2]))*.01
def normal(n):return Vector((n[0],-n[1],n[2])).normalized()
bpy.ops.wm.open_mainfile(filepath=str(BASE/'M4_OriginalShape_BareHands_Editable.blend'))
obj=bpy.data.objects['M4_OriginalShape_BareHands']
keys=obj.data.shape_keys.key_blocks
for key in keys:key.value=0
basis=keys[0];key=obj.shape_key_add(name='Smooth_Skin_V2_Contact_Constrained')
tree=KDTree(len(data['positions']))
for i,p in enumerate(data['positions']):tree.insert(point(p),i)
tree.balance()
for i,v in enumerate(basis.data):
    _,j,distance=tree.find(v.co)
    if distance>.00003:raise RuntimeError('Original editable correspondence missing')
    key.data[i].co=v.co+point(shape['positions'][j])-point(data['positions'][j])
key.value=1
obj['AuthoringContract']='Original skeleton, weights, UV and grip contacts. Quadratic surface fairing and rebuilt smooth hand normals.'
obj['MaxDorsalDisplacementMM']=1.4
# Map the authored continuous normals back to the unchanged original topology.
sum_normals=[Vector() for _ in data['positions']];count=[0]*len(sum_normals)
for tri,ns,mat in zip(data['triangles'],shape['normals'],shape['triangle_materials']):
    if mat!=2:continue
    for vi,n in zip(tri,ns):sum_normals[vi]+=normal(n);count[vi]+=1
split=[]
for loop in obj.data.loops:
    _,vi,_=tree.find(basis.data[loop.vertex_index].co)
    split.append(sum_normals[vi].normalized() if count[vi] else obj.data.corner_normals[loop.index].vector.copy())
obj.data.normals_split_custom_set(split)
path=ROOT/'M4_OriginalShape_BareHands_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(path))
runpy.run_path(str(PROJECT/'Tools/ModularOutfit/finish_original_shape_blend.py'),init_globals={'AUTHOR_ROOT':str(ROOT)})
# Add the same physical pore height to the Blender authoring material.
obj=bpy.data.objects['M4_OriginalShape_BareHands']
skin=obj.data.materials[-1];nodes=skin.node_tree.nodes;links=skin.node_tree.links
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
normalmap=next(n for n in nodes if n.type=='NORMAL_MAP')
micro=nodes.new('ShaderNodeTexImage');micro.image=bpy.data.images.load(str(ROOT/'T_M4OriginalShape_SkinMicro.png'))
micro.image.colorspace_settings.name='Non-Color';micro.image.pack()
uv=nodes.new('ShaderNodeTexCoord');scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE'
parameters=json.loads((ROOT/'micro_surface.json').read_text())
scale.inputs['Scale'].default_value=parameters['tile_repeat'];links.new(uv.outputs['UV'],scale.inputs[0]);links.new(scale.outputs['Vector'],micro.inputs['Vector'])
channels=nodes.new('ShaderNodeSeparateColor');links.new(micro.outputs['Color'],channels.inputs['Color'])
bump=nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=parameters['height_range_cm']*.01
links.new(channels.outputs['Blue'],bump.inputs['Height']);links.new(normalmap.outputs['Normal'],bump.inputs['Normal'])
links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('M4_SMOOTH_SKIN_EDITABLE_SAVED')
