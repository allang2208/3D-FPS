"""Run with Blender --background --python. Kenney CC0 source -> matching tools."""
import bpy, os, math, random
from mathutils import Vector
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
SOURCE = os.path.join(ROOT, 'tools/basic-tools/source/kenney/Models/GLB format')
OUT = os.path.join(ROOT, 'assets/models/basic_tools')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
def material(name, color, metal, rough):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = metal
    bs.inputs['Roughness'].default_value = rough
    return m
wood = material('Oiled ash wood', (.24,.105,.042), 0, .72)
steel = material('Forged cool steel', (.29,.34,.37), .78, .39)
edge = material('Honed steel edge', (.52,.58,.61), .85, .28)
# Small repeatable wood texture: long fibres, low contrast, no colorful atlas.
grain=bpy.data.images.new('Ash wood fibres',width=128,height=512)
rng=random.Random(731)
pixels=[]
for y in range(512):
    for x in range(128):
        phase=x+2.5*math.sin(y/73)+1.2*math.sin(y/29)
        fibre=math.sin(phase*1.8)*.05+math.sin(phase*.31)*.09+rng.uniform(-.018,.018)
        shade=.93+fibre
        pixels.extend((.51*shade,.34*shade,.215*shade,1))
grain.pixels=pixels
grain.pack()
texture=wood.node_tree.nodes.new('ShaderNodeTexImage')
texture.image=grain
wood.node_tree.links.new(texture.outputs['Color'],wood.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
models=[]
for kind, height in [('axe',.72), ('pickaxe',.86)]:
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.import_scene.gltf(filepath=os.path.join(SOURCE, 'tool-'+kind+'.glb'))
    meshes=[o for o in bpy.context.selected_objects if o.type=='MESH']
    # Atlas color at each polygon's UV differentiates wood from metal.
    for obj in meshes:
        original=list(obj.data.materials)
        assignments=[]
        for poly in obj.data.polygons:
            mat=original[poly.material_index]
            tex=next((n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE'),None)
            uv=obj.data.uv_layers.active.data[poly.loop_indices[0]].uv
            x=min(tex.size[0]-1,max(0,int(uv.x*tex.size[0])))
            y=min(tex.size[1]-1,max(0,int(uv.y*tex.size[1])))
            k=(y*tex.size[0]+x)*4
            r,g,b=tex.pixels[k:k+3]
            assignments.append(0 if r>b*1.2 else (2 if r>.65 else 1))
        obj.data.materials.clear()
        for m in [wood,steel,edge]: obj.data.materials.append(m)
        for p,i in zip(obj.data.polygons,assignments): p.material_index=i
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes: obj.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0]
    bpy.ops.object.join()
    obj=bpy.context.object
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    vertices=[v.co.copy() for v in obj.data.vertices]
    lo=Vector(tuple(min(v[i] for v in vertices) for i in range(3)))
    hi=Vector(tuple(max(v[i] for v in vertices) for i in range(3)))
    # Blender Z up; Godot export converts to Y up. Grip 22% from handle bottom.
    factor=height/(hi.z-lo.z)
    grip=Vector((0,0,lo.z+(hi.z-lo.z)*.22))
    for v in obj.data.vertices: v.co=(v.co-grip)*factor
    uv_layer=obj.data.uv_layers.active
    for poly in obj.data.polygons:
        if poly.material_index==0:
            for loop_index in poly.loop_indices:
                p=obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
                uv_layer.data[loop_index].uv=((p.x+p.y)*13+.5,p.z*1.5)
    obj.name='Basic_'+kind
    bevel=obj.modifiers.new('Fine forged edge bevel','BEVEL')
    bevel.width=.0015; bevel.segments=2
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,kind+'_v1.glb'),use_selection=True,export_format='GLB')
    obj.location.x = -.48 if kind=='axe' else .48
    models.append(obj)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'tools/basic-tools/basic_tools.blend'))
print('BASIC_TOOLS_EXPORTED', [(o.name,len(o.data.polygons)) for o in models])
