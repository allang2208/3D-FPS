"""Continuous geometric seams, closed cuts, and one wood UV field."""
import bpy,bmesh,math
from mathutils import Vector

def close_mesh(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0002)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.0001)
    bm.verts.index_update()
    seen=set();duplicates=[]
    for face in bm.faces:
        key=tuple(sorted(v.index for v in face.verts))
        if key in seen:duplicates.append(face)
        else:seen.add(key)
    if duplicates:bmesh.ops.delete(bm,geom=duplicates,context='FACES_ONLY')
    loose=[e for e in bm.edges if not e.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='EDGES')
    boundary=[e for e in bm.edges if e.is_boundary]
    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    # Cut caps must not smooth into the cylindrical wall.
    for face in bm.faces:
        if abs(face.normal.z)>.999:face.smooth=False
    bm.to_mesh(obj.data);bm.free();obj.data.update()

def wood_uv(obj):
    uv=obj.data.uv_layers.active or obj.data.uv_layers.new(name='UVMap')
    for polygon in obj.data.polygons:
        material=obj.data.materials[polygon.material_index]
        if not material or not any(key in material.name for key in ('BranchWood','Pine','Sandal')):continue
        if abs(polygon.normal.z)>.95:
            for i in polygon.loop_indices:
                co=obj.data.vertices[obj.data.loops[i].vertex_index].co
                uv.data[i].uv=(co.x/35+.5,co.y/35+.5)
            continue
        angles=[(math.atan2(obj.data.vertices[obj.data.loops[i].vertex_index].co.y,
                            obj.data.vertices[obj.data.loops[i].vertex_index].co.x)+math.pi)/math.tau for i in polygon.loop_indices]
        wraps=max(angles)-min(angles)>.5
        for i,a in zip(polygon.loop_indices,angles):
            co=obj.data.vertices[obj.data.loops[i].vertex_index].co
            uv.data[i].uv=(a+1 if wraps and a<.5 else a,(co.z+80)/35)

def wood_material(root,name,tint=(.55,.36,.19)):
    m=bpy.data.materials.new(name);m.use_nodes=True
    n=m.node_tree.nodes;links=m.node_tree.links
    bs=next(node for node in n if node.type=='BSDF_PRINCIPLED')
    def texture(suffix):
        node=n.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(root/'Inputs'/('T_WoodSurface_00A_'+suffix+'.png')),check_existing=True)
        if suffix!='BaseColor':node.image.colorspace_settings.name='Non-Color'
        return node
    base=texture('BaseColor');mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
    mix.inputs[2].default_value=(*tint,1);links.new(base.outputs['Color'],mix.inputs[1]);links.new(mix.outputs[0],bs.inputs['Base Color'])
    packed=texture('RHAOM');separate=n.new('ShaderNodeSeparateColor');links.new(packed.outputs['Color'],separate.inputs[0])
    links.new(separate.outputs['Red'],bs.inputs['Roughness'])
    normal=texture('Normal');rgb=n.new('ShaderNodeSeparateColor');links.new(normal.outputs['Color'],rgb.inputs[0])
    invert=n.new('ShaderNodeMath');invert.operation='SUBTRACT';invert.inputs[0].default_value=1;links.new(rgb.outputs['Green'],invert.inputs[1])
    combine=n.new('ShaderNodeCombineColor');links.new(rgb.outputs['Red'],combine.inputs['Red']);links.new(invert.outputs[0],combine.inputs['Green']);links.new(rgb.outputs['Blue'],combine.inputs['Blue'])
    nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.6;links.new(combine.outputs[0],nm.inputs['Color']);links.new(nm.outputs[0],bs.inputs['Normal'])
    return m


def repair_degenerate_uvs(obj):
    """Give rope/crystal end caps a 2-D UV area so UE can build tangents."""
    mesh=obj.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active
    bad=set()
    for tri in mesh.loop_triangles:
        a,b,c=[uv.data[i].uv for i in tri.loops]
        ab=b-a;ac=c-a
        if abs(ab.x*ac.y-ab.y*ac.x)<1e-11:bad.add(tri.polygon_index)
    for index in bad:
        face=mesh.polygons[index]
        dominant=max(range(3),key=lambda i:abs(face.normal[i]))
        axes=[i for i in range(3) if i!=dominant]
        for loop in face.loop_indices:
            co=mesh.vertices[mesh.loops[loop].vertex_index].co
            uv.data[loop].uv=(co[axes[0]]/10,co[axes[1]]/10)
    return len(bad)
