"""Physical wrap UVs and the shared brown linen PBR set for this grip."""
import math
from pathlib import Path

def author_linen(obj):
    import bpy
    me=obj.data
    uv=me.uv_layers.active or me.uv_layers.new(name='UVMap')
    bounds=[(min(v.co[k] for v in me.vertices),max(v.co[k] for v in me.vertices)) for k in range(3)]
    cx,cy=[sum(bounds[k])*.5 for k in (0,1)]
    zmin,zmax=bounds[2]
    for face in me.polygons:
        coords=[]
        for i in face.loop_indices:
            v=me.vertices[me.loops[i].vertex_index].co
            coords.append([(math.atan2(v.y-cy,v.x-cx)/math.tau+.5)%1,(v.z-zmin)/(zmax-zmin)])
        if max(v[0] for v in coords)-min(v[0] for v in coords)>.5:
            for v in coords:
                if v[0]<.5:v[0]+=1
        for i,co in zip(face.loop_indices,coords):uv.data[i].uv=co
    # Texture UV0 now defines the cloth tangent basis, instead of the old
    # wood/leather atlas. Reuse the approved material's physical weave.
    mat=me.materials[0];mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
    bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial')
    links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    texroot=Path(__file__).parent.parent/'BowGripSeries20260927/Textures'
    for kind in ('BaseColor','ORM','Normal'):
        n=nodes.new('ShaderNodeTexImage')
        n.image=bpy.data.images.load(str(texroot/('T_Bow_Grip_WovenLinen_'+kind+'.png')),check_existing=True)
        if kind=='BaseColor':links.new(n.outputs['Color'],bs.inputs['Base Color'])
        else:
            n.image.colorspace_settings.name='Non-Color'
            if kind=='ORM':
                split=nodes.new('ShaderNodeSeparateColor');links.new(n.outputs['Color'],split.inputs['Color'])
                links.new(split.outputs['Green'],bs.inputs['Roughness'])
            else:
                normal=nodes.new('ShaderNodeNormalMap');normal.uv_map=uv.name;normal.inputs['Strength'].default_value=.7
                links.new(n.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
    mat.diffuse_color=(.155,.078,.030,1)
