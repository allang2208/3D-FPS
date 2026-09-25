"""Save editable V6 geometry on the accepted armature, without rendering.

The Blender skin is an authoring preview. The shipped material is the UE V5
reference-pose skin field with V6 full-arm coverage.
"""
import json
from pathlib import Path
import bpy

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4'
ROOT=BASE/'BareUpperArmsV6'
source=json.loads((ROOT/'M4_original.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(BASE/'WristContourV4/M4_OriginalShape_BareHands_Editable.blend'))
obj=bpy.data.objects['M4_OriginalShape_BareHands']
hand_skin=obj.data.materials[-1]

skin=bpy.data.materials.new('M4_V6_BareArms_Preview');skin.use_nodes=True
nodes=skin.node_tree.nodes;links=skin.node_tree.links
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
bsdf.inputs['Base Color'].default_value=(.372,.232,.182,1)
bsdf.inputs['Roughness'].default_value=.49
bsdf.inputs['Subsurface Weight'].default_value=.10
bsdf.inputs['Specular IOR Level'].default_value=.35
texture=nodes.new('ShaderNodeTexImage')
texture.image=bpy.data.images.load(str(BASE/'WristContourV4/T_M4OriginalShape_SkinMicro.png'),check_existing=True)
texture.image.colorspace_settings.name='Non-Color';texture.image.pack()
texture.projection='BOX';texture.projection_blend=.35
coords=nodes.new('ShaderNodeTexCoord')
scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs['Scale'].default_value=12.5
links.new(coords.outputs['Object'],scale.inputs[0]);links.new(scale.outputs['Vector'],texture.inputs['Vector'])
channels=nodes.new('ShaderNodeSeparateColor');links.new(texture.outputs['Color'],channels.inputs['Color'])
bump=nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.000091
links.new(channels.outputs['Blue'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
skin['AuthoringPreview']='8 cm skin detail; UE material is authoritative for animated normal projection and scattering'

mesh=bpy.data.meshes.new('M4_BareUpperArmsV6_NativeBinding')
# One handedness reflection, keeping corrected native UE face order.
mesh.from_pydata([(p[0]*.01,-p[1]*.01,p[2]*.01) for p in source['positions']],[],source['triangles'])
mesh.update()
for material in (skin,skin,hand_skin):mesh.materials.append(material)
obj.data=mesh
obj.vertex_groups.clear()
for name in sorted({n for w in source['weights'] for n in w}):obj.vertex_groups.new(name=name)
for i,weights in enumerate(source['weights']):
    for name,value in weights.items():obj.vertex_groups[name].add([i],value,'REPLACE')
uv=mesh.uv_layers.new(name='NativeGrip_SkinUV');normals=[]
for polygon,coords,mat,ns in zip(mesh.polygons,source['uv'],source['triangle_materials'],source['normals']):
    polygon.material_index=mat;polygon.use_smooth=True
    for loop,(u,v),n in zip(polygon.loop_indices,coords,ns):
        uv.data[loop].uv=(u,1-v);normals.append((n[0],-n[1],n[2]))
mesh.normals_split_custom_set(normals)
obj['AuthoringContract']='V6 bare upperarms and elbow fairing; native rig and weights; accepted V4 distal forearm, wrists and hand grip'
obj['SurfaceAuthoring']='V6 full arm skin coverage; shipped UE uses V5 unified skin, Blender material is an authoring preview'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'M4_OriginalShape_BareHands_Editable.blend'))
print('M4_BARE_UPPERARMS_EDITABLE_SAVED')
