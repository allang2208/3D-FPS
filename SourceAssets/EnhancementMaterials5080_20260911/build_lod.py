import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent;asset=sys.argv[sys.argv.index('--')+1]
def setup():
    s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.margin=12;s.render.bake.use_selected_to_active=True;s.render.bake.cage_extrusion=.002;s.render.bake.max_ray_distance=.004
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
    image=bpy.data.images.new(tag+'_normal',width=2048,height=2048);image.colorspace_settings.name='Non-Color'
    tex=nt.nodes.new('ShaderNodeTexImage');tex.image=image;nt.nodes.active=tex
    bpy.ops.object.bake(type='NORMAL')
    image.filepath_raw=str(P/(image.name+'.png'));image.file_format='PNG';image.save();image.pack()
    normal=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex.outputs['Color'],normal.inputs['Color']);nt.links.new(normal.outputs['Normal'],p.inputs['Normal'])
    if color:
        image=bpy.data.images.new(tag+'_basecolor',width=2048,height=2048)
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=image;nt.nodes.active=tex
        bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})
        image.filepath_raw=str(P/(image.name+'.png'));image.file_format='PNG';image.save();image.pack();nt.links.new(tex.outputs['Color'],p.inputs['Base Color'])
if asset=='enhancement_stone':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(next(P.glob('enhancement_stone_high_textured_master*.glb'))))
    src=next(o for o in bpy.context.scene.objects if o.type=='MESH');matrix=Matrix.Rotation(math.pi/2,4,'Y')@src.matrix_world
    points=[matrix@v.co for v in src.data.vertices];lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)));origin=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));scale=.14/(hi.z-lo.z)
    for v in src.data.vertices:v.co=(matrix@v.co-origin)*scale
    src.matrix_world=Matrix.Identity(4)
    target=reduce(src,20000,'Enhancement stone LOD0')
    setup();bake(target,[src],'enhancement_stone_lod0')
    bpy.data.objects.remove(src,do_unlink=True);kept=[target]
    method='20k candidate; tangent normal baked from cleaned/remeshed 99,756-triangle textured high master. Direct bake from 9,075,790-triangle raw geometry was rejected: 48.4 percent negative tangent Z texels and visible dark patches. Raw geometry and rejected bake are preserved separately.'
else:
    bpy.ops.wm.open_mainfile(filepath=str(P/'magic_dust_physical_editable.blend'));setup()
    lid=bpy.data.objects['Closed steel lid with geometric knurling'];powder=bpy.data.objects['Contained powder volume']
    grains=[bpy.data.objects[n] for n in ['Individual powder grains','Packed powder side grains']]
    glass=bpy.data.objects['Glass vessel with interior wall'];crystals=bpy.data.objects['Embedded crystalline mineral fragments']
    glass.hide_render=True;crystals.hide_render=True
    lid_low=reduce(lid,3000,'Steel lid LOD0');bake(lid_low,[lid],'magic_dust_lid_lod0')
    lid.hide_render=True;lid_low.hide_render=True
    powder_low=reduce(powder,1800,'Powder LOD0');bake(powder_low,[powder]+grains,'magic_dust_powder_lod0',True)
    for o in [lid,powder]+grains:bpy.data.objects.remove(o,do_unlink=True)
    kept=[lid_low,powder_low,glass,crystals]
    method='Physical rebuild candidate; lid and powder reduced; 6800 separate powder grains baked into tangent normals and powder base color. Glass inner/outer wall and visible blue crystals retained.'
for o in kept:o.hide_render=False
bpy.ops.object.select_all(action='DESELECT')
for o in kept:o.select_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/(asset+'_lod0_editable.blend')))
bpy.ops.export_scene.gltf(filepath=str(P/(asset+'_lod0_candidate.glb')),export_format='GLB',use_selection=True)
(P/(asset+'_lod0_provenance.json')).write_text(json.dumps({'method':method,'engine_integration':False},indent=2))
