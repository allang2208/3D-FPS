"""Shared Blender authoring helpers for this production batch (not runtime code)."""
import bpy,math
from pathlib import Path
from mathutils import Vector,Matrix

def smooth(a,b,v):
    t=max(0.,min(1.,(v-a)/(b-a)));return t*t*(3-2*t)
def node(nt,typ,**kw):
    n=nt.nodes.new(typ)
    for k,v in kw.items():setattr(n,k,v)
    return n
def put(nt,socket,value):
    if hasattr(value,'node'):nt.links.new(value,socket)
    else:socket.default_value=value
def op(nt,operation,a,b=0):
    n=node(nt,'ShaderNodeMath',operation=operation);put(nt,n.inputs[0],a);put(nt,n.inputs[1],b);return n.outputs[0]
def mix(nt,t,a,b):
    n=node(nt,'ShaderNodeMixRGB',blend_type='MIX')
    for s,v in zip(n.inputs,(t,a,b)):put(nt,s,v)
    return n.outputs[0]
def tex(nt,path,color=False,uv=None):
    n=node(nt,'ShaderNodeTexImage');n.image=bpy.data.images.load(str(path),check_existing=True)
    n.image.colorspace_settings.name='sRGB' if color else 'Non-Color'
    if uv:
        coord=node(nt,'ShaderNodeUVMap',uv_map=uv);nt.links.new(coord.outputs[0],n.inputs['Vector'])
    return n
def make_mat(name):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.use_fake_user=True
    nt=m.node_tree;nt.nodes.clear();bs=node(nt,'ShaderNodeBsdfPrincipled');out=node(nt,'ShaderNodeOutputMaterial')
    nt.links.new(bs.outputs[0],out.inputs['Surface']);return m,nt,bs,out
def constant_material(name,color,metal,rough):
    m,nt,bs,out=make_mat(name)
    base=node(nt,'ShaderNodeRGB');base.outputs[0].default_value=(*color,1)
    orm=node(nt,'ShaderNodeCombineColor');orm.inputs[0].default_value=1
    orm.inputs[1].default_value=rough;orm.inputs[2].default_value=metal
    nt.links.new(base.outputs[0],bs.inputs['Base Color']);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    return m,{'BaseColor':base.outputs[0],'ORM':orm.outputs[0]},bs,out
def activate(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.hide_render=False
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
def midpoint(a,b):return (a[0].lerp(b[0],.5),a[1].lerp(b[1],.5),a[2].lerp(b[2],.5).normalized())
def derived_mesh(source,name,deform,levels=1,smooth_cord=False):
    source.calc_loop_triangles()
    data=[(source.vertices[l.vertex_index].co.copy(),source.uv_layers.active.data[i].uv.copy(),Vector(source.corner_normals[i].vector)) for i,l in enumerate(source.loops)]
    tris=[[data[i] for i in t.loops] for t in source.loop_triangles]
    for _ in range(levels):
        result=[]
        for a,b,c in tris:
            ab,bc,ca=midpoint(a,b),midpoint(b,c),midpoint(c,a)
            result.extend(((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)))
        tris=result
    vertices=[];lookup={};faces=[];uvs=[];normals=[];cache={}
    for tri in tris:
        face=[]
        for co,uv,n in tri:
            key=tuple(round(v,8) for v in co)
            if key not in lookup:lookup[key]=len(vertices);vertices.append(tuple(deform(co)))
            face.append(lookup[key]);uvs.append(uv)
            nk=key+tuple(round(v,6) for v in n)
            if nk not in cache:
                columns=[];h=.000002
                for axis in range(3):
                    delta=Vector();delta[axis]=h;columns.append((deform(co+delta)-deform(co-delta))/(2*h))
                jac=Matrix(columns).transposed();cache[nk]=tuple((jac.inverted_safe().transposed()@n).normalized())
            normals.append(cache[nk])
        faces.append(face)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    for label in ('UVMap','SourceUV'):
        layer=mesh.uv_layers.new(name=label)
        for i,v in enumerate(uvs):layer.data[i].uv=v
    mesh.uv_layers.active_index=0;mesh.uv_layers[0].active_render=True
    for p in mesh.polygons:p.use_smooth=True
    if not smooth_cord:mesh.normals_split_custom_set(normals)
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);return obj
def unwrap(obj):
    activate(obj);obj.data.uv_layers.active_index=0;obj.data.uv_layers[0].active_render=True
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.015)
    bpy.ops.object.mode_set(mode='OBJECT')
def bake(obj,materials,prefix,outdir,size=2048):
    activate(obj);scene=bpy.context.scene;scene.render.bake.margin=12
    scene.render.bake.use_clear=True;scene.render.bake.use_selected_to_active=False
    targets={};emitters={}
    for m,channels,bs,out in materials:
        nt=m.node_tree;targets[m]=node(nt,'ShaderNodeTexImage');emitters[m]=node(nt,'ShaderNodeEmission')
    maps={}
    for suffix in ('BaseColor','ORM','Normal'):
        image=bpy.data.images.new(prefix+'_'+suffix,width=size,height=size,alpha=False)
        image.colorspace_settings.name='sRGB' if suffix=='BaseColor' else 'Non-Color'
        for m,channels,bs,out in materials:
            nt=m.node_tree;t=targets[m];t.image=image;nt.nodes.active=t
            for n in nt.nodes:n.select=n==t
            if suffix=='Normal':nt.links.new(bs.outputs[0],out.inputs['Surface'])
            else:
                nt.links.new(channels[suffix],emitters[m].inputs['Color']);nt.links.new(emitters[m].outputs[0],out.inputs['Surface'])
        bpy.ops.object.bake(type='NORMAL' if suffix=='Normal' else 'EMIT',normal_space='TANGENT')
        image.filepath_raw=str(outdir/(prefix+'_'+suffix+'.png'));image.file_format='PNG';image.save();maps[suffix]=image
    for m,channels,bs,out in materials:m.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
    m,nt,bs,out=make_mat(prefix.replace('T_','M_'))
    for suffix,image in maps.items():
        t=node(nt,'ShaderNodeTexImage');t.image=image
        if suffix=='BaseColor':nt.links.new(t.outputs[0],bs.inputs['Base Color'])
        elif suffix=='ORM':
            sep=node(nt,'ShaderNodeSeparateColor');nt.links.new(t.outputs[0],sep.inputs[0]);nt.links.new(sep.outputs[1],bs.inputs['Roughness']);nt.links.new(sep.outputs[2],bs.inputs['Metallic'])
        else:
            nm=node(nt,'ShaderNodeNormalMap');nt.links.new(t.outputs[0],nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
    obj.data.materials.clear();obj.data.materials.append(m)
    for poly in obj.data.polygons:poly.material_index=0
    return {suffix:str(outdir/(image.name+'.png')) for suffix,image in maps.items()}
def cube(name,loc,dimensions,mat,bevel=.0005):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dimensions
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if bevel:
        mod=o.modifiers.new('EdgeRounds','BEVEL');mod.width=bevel;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
    return o
def torus(name,loc,radius,tube,mat,rotation=(math.pi/2,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius,minor_radius=tube,major_segments=48,minor_segments=10,location=loc,rotation=rotation)
    o=bpy.context.object;o.name=name;o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    return o
def join(parts,root):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=root;bpy.ops.object.join();return root
def export(obj,path):
    activate(obj);bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
        mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP',apply_unit_scale=True,bake_space_transform=False,add_leaf_bones=False)
