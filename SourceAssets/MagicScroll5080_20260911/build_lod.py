import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent;asset=sys.argv[sys.argv.index('--')+1]
def setup():
    s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.margin=12;s.render.bake.use_selected_to_active=True;s.render.bake.cage_extrusion=.0002;s.render.bake.max_ray_distance=.0005
def reduce(source,target,name):
    o=source.copy();o.data=source.data.copy();bpy.context.collection.objects.link(o);o.name=name
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    o.data.calc_loop_triangles();mod=o.modifiers.new('Candidate reduction','DECIMATE');mod.ratio=min(1,target/len(o.data.loop_triangles));mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    for i,m in enumerate(o.data.materials):o.data.materials[i]=m.copy()
    return o
def bake(target,sources,tag,color=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in [target]+sources:o.select_set(True);o.hide_render=False
    bpy.context.view_layer.objects.active=target
    m=target.data.materials[0];nt=m.node_tree;p=nt.nodes.get('Principled BSDF')
    image=bpy.data.images.new(tag+'_normal',width=2048,height=2048);image.colorspace_settings.name='Non-Color';image.generated_color=(.5,.5,1.,1.);bpy.context.scene.render.bake.use_clear=False
    tex=nt.nodes.new('ShaderNodeTexImage');tex.image=image;nt.nodes.active=tex
    bpy.ops.object.bake(type='NORMAL')
    # Unhit rays and backward thin-wall hits cannot encode the outward tangent normal.
    # Keep the geometric normal for those texels instead of introducing black shading.
    import numpy as np
    pixels=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(pixels)
    rgba=pixels.reshape((-1,4));invalid=rgba[:,2]<.5
    print('Discarding invalid thin-wall bake texels',int(invalid.sum()),flush=True)
    rgba[invalid,:3]=(.5,.5,1.)
    image.pixels.foreach_set(pixels);image.update()

    image.filepath_raw=str(P/(image.name+'.png'));image.file_format='PNG';image.save();image.pack()
    normal=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex.outputs['Color'],normal.inputs['Color']);nt.links.new(normal.outputs['Normal'],p.inputs['Normal'])
    if color:
        image=bpy.data.images.new(tag+'_basecolor',width=2048,height=2048)
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=image;nt.nodes.active=tex
        bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})
        image.filepath_raw=str(P/(image.name+'.png'));image.file_format='PNG';image.save();image.pack();nt.links.new(tex.outputs['Color'],p.inputs['Base Color'])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(next(P.glob('magic_scroll_baseline_textured_master*.glb'))))
src=next(o for o in bpy.context.scene.objects if o.type=='MESH')
matrix=Matrix.Diagonal((.6,.6,1.,1.))@src.matrix_world
points=[matrix@v.co for v in src.data.vertices];lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
origin=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));scale=.24/(hi.z-lo.z)
for v in src.data.vertices:v.co=(matrix@v.co-origin)*scale
src.matrix_world=Matrix.Identity(4)
src.data.calc_loop_triangles();original=len(src.data.loop_triangles)
target=reduce(src,20000,'Magic scroll LOD0')
target.data.validate(verbose=True);target.data.update()
setup();bake(target,[src],'magic_scroll_lod0')
bpy.data.objects.remove(src,do_unlink=True)
bpy.ops.object.select_all(action='DESELECT');target.select_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'magic_scroll_lod0_editable.blend'))
(P/'Delivery').mkdir(exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(P/'Delivery/magic_scroll.glb'),export_format='GLB',use_selection=True)
target.data.calc_loop_triangles()
(P/'lod_report.json').write_text(json.dumps({'source_triangles':original,'game_triangles':len(target.data.loop_triangles),'height_m':.24,'normal_bake':'2K selected-to-active from textured master','source':'RTX5080 TRELLIS2 three independent views'} ,indent=2))
