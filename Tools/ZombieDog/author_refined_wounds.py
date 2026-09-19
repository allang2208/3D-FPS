"""Produce editable wound stamps and fur-root correspondence for the V5 material.

Native Blender material graphs bake production masks/relief, without a preview.
All dimensions of the new relief are applied in cm by the runtime material.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets')
OUT = ROOT/'ZombieDogRefinedWoundsV5'
(OUT/'Textures').mkdir(parents=True, exist_ok=True)
SOURCE = ROOT/'ZombieDogRandomWoundsV4/ZombieDog_RandomWounds_Authoring.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
rig.data.pose_position = 'REST'
mesh = obj.data; world = obj.matrix_world.copy()
mesh.calc_loop_triangles()
triangles = [tuple(t.vertices) for t in mesh.loop_triangles if t.material_index == 0]
tree = BVHTree.FromPolygons([world@v.co for v in mesh.vertices],triangles,all_triangles=True)
fur_vertices = {i for p in mesh.polygons if p.material_index == 1 for i in p.vertices}
body_vertices = {i for p in mesh.polygons if p.material_index != 1 for i in p.vertices}
# CORNER domain also handles any vertex shared by fur and skin sections.
attribute = mesh.attributes.get('WoundSurfacePosition') or mesh.attributes.new('WoundSurfacePosition','FLOAT_VECTOR','CORNER')
for polygon in mesh.polygons:
    for loop_index in polygon.loop_indices:
        p = world @ mesh.vertices[mesh.loops[loop_index].vertex_index].co
        if polygon.material_index == 1:
            nearest = tree.find_nearest(p)
            if nearest[0] is not None: p = nearest[0]
        attribute.data[loop_index].vector = p

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 8
scene.render.bake.margin = 16; scene.render.bake.use_clear = True
scene.render.bake.use_selected_to_active = False
activate(obj); mesh.uv_layers.active = mesh.uv_layers['ZombieUV']; mesh.uv_layers['ZombieUV'].active_render = True
rest_image = bpy.data.images.new('T_ZombieDog_RefinedRestPosition',2048,2048,alpha=False,float_buffer=True)
rest_image.colorspace_settings.name = 'Non-Color'
rest_materials = []
for material in mesh.materials:
    ns = material.node_tree.nodes; lk = material.node_tree.links
    out = next(n for n in ns if n.type == 'OUTPUT_MATERIAL')
    previous = out.inputs['Surface'].links[0].from_socket
    attr = ns.new('ShaderNodeAttribute'); attr.attribute_name = 'WoundSurfacePosition'
    value = attr.outputs['Vector']
    for operation, vector in [('MULTIPLY',(100,-100,100)),('SUBTRACT',(-25,-115,-5)),('DIVIDE',(50,210,115))]:
        n = ns.new('ShaderNodeVectorMath'); n.operation = operation
        lk.new(value,n.inputs[0]); n.inputs[1].default_value = vector; value=n.outputs[0]
    em = ns.new('ShaderNodeEmission'); lk.new(value,em.inputs['Color']); lk.new(em.outputs[0],out.inputs['Surface'])
    target = ns.new('ShaderNodeTexImage'); target.image=rest_image; ns.active=target
    rest_materials.append((material,out,previous,em))
bpy.ops.object.bake(type='EMIT')
scene.render.image_settings.file_format='OPEN_EXR'; scene.render.image_settings.color_depth='16'; scene.render.image_settings.color_mode='RGB'
rest_image.save_render(str(OUT/'Textures/T_ZombieDog_RefinedRestPosition.exr'),scene=scene)
for material,out,previous,em in rest_materials:
    material.node_tree.links.new(previous,out.inputs['Surface']); material.node_tree.nodes.remove(em)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ZombieDog_RefinedWounds_Authoring.blend'))
print('REFINED_FUR_ROOT_ATLAS_AUTHORED',flush=True)

# Author four distinct wound shapes in four independent material graphs.
# RGB masks: tissue core / exposed skin / dry scab lip.
# RGB detail: signed shallow relief encoded around .5 / blood stain / fine fibres.
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=8
scene.render.bake.margin=0; scene.render.bake.use_clear=True; scene.render.bake.use_selected_to_active=False
vertices=[]; faces=[]
for tile in range(4):
    x=tile%2; y=tile//2; base=len(vertices)
    vertices += [(x,y,0),(x+1,y,0),(x+1,y+1,0),(x,y+1,0)]
    faces.append((base,base+1,base+2,base+3))
data=bpy.data.meshes.new('WoundStampCanvas'); data.from_pydata(vertices,[],faces); data.update()
canvas=bpy.data.objects.new('WoundStampCanvas',data); scene.collection.objects.link(canvas)
uv=data.uv_layers.new(name='UVMap')
for polygon in data.polygons:
    for li in polygon.loop_indices:
        p=data.vertices[data.loops[li].vertex_index].co; uv.data[li].uv=(p.x*.5,p.y*.5)
definitions=[]
for tile, title in enumerate(['LongTear','Abrasion','HealedScar','IrregularPatch']):
    material=bpy.data.materials.new('Wound_'+title); material.use_nodes=True
    ns=material.node_tree.nodes; ns.clear(); lk=material.node_tree.links
    def put(value,socket):
        if isinstance(value,bpy.types.NodeSocket): lk.new(value,socket)
        else: socket.default_value=value
    def mathn(operation,a,b=None,c=None):
        n=ns.new('ShaderNodeMath'); n.operation=operation; put(a,n.inputs[0])
        if b is not None: put(b,n.inputs[1])
        if c is not None: put(c,n.inputs[2])
        return n.outputs[0]
    def smooth(value,lo,hi):
        n=ns.new('ShaderNodeMapRange'); n.interpolation_type='SMOOTHSTEP'; n.clamp=True
        put(value,n.inputs['Value']); n.inputs['From Min'].default_value=lo; n.inputs['From Max'].default_value=hi
        return n.outputs[0]
    def noise(scale,detail=2):
        n=ns.new('ShaderNodeTexNoise'); lk.new(local,n.inputs['Vector'])
        n.inputs['Scale'].default_value=scale; n.inputs['Detail'].default_value=detail
        n.inputs['Roughness'].default_value=.52; return n.outputs['Fac']
    coords=ns.new('ShaderNodeTexCoord')
    sub=ns.new('ShaderNodeVectorMath'); sub.operation='SUBTRACT'
    lk.new(coords.outputs['UV'],sub.inputs[0]); sub.inputs[1].default_value=((tile%2)*.5+.25,(tile//2)*.5+.25,0)
    mul=ns.new('ShaderNodeVectorMath'); mul.operation='MULTIPLY'; lk.new(sub.outputs[0],mul.inputs[0]); mul.inputs[1].default_value=(4,4,1)
    local=mul.outputs[0]
    xy=ns.new('ShaderNodeSeparateXYZ'); lk.new(local,xy.inputs[0]); x=xy.outputs['X']; y=xy.outputs['Y']
    broad=noise(3.8,2); medium=noise(16,2); pores=noise(135,1)
    wave=mathn('MULTIPLY',mathn('SINE',mathn('MULTIPLY',x,5.4)),.055 if tile!=2 else .024)
    curve=mathn('ADD',wave,mathn('MULTIPLY',mathn('SUBTRACT',broad,.5),.075))
    local_y=mathn('SUBTRACT',y,curve)
    width=[.26,.48,.055,.45][tile]
    length=[.64,.56,.68,.61][tile]
    xx=mathn('DIVIDE',x,length); yy=mathn('DIVIDE',local_y,width)
    radial=mathn('SQRT',mathn('ADD',mathn('MULTIPLY',xx,xx),mathn('MULTIPLY',yy,yy)))
    jagged=mathn('ADD',mathn('MULTIPLY',mathn('SUBTRACT',broad,.5),[.12,.26,.05,.32][tile]),
                      mathn('MULTIPLY',mathn('SUBTRACT',medium,.5),[.045,.065,.02,.08][tile]))
    distance=mathn('ADD',mathn('SUBTRACT',radial,1),jagged)
    core=mathn('SUBTRACT',1,smooth(distance,-.14,.025))
    exposed=mathn('SUBTRACT',1,smooth(distance,.07,.42))
    crust=mathn('MULTIPLY',smooth(distance,-.21,-.06),mathn('SUBTRACT',1,smooth(distance,.045,.16)))
    crust=mathn('MULTIPLY',crust,mathn('ADD',.55,mathn('MULTIPLY',medium,.45)))
    stain=mathn('MULTIPLY',mathn('SUBTRACT',1,smooth(distance,.15,.77)),
                mathn('ADD',.6,mathn('MULTIPLY',broad,.4)))
    # Directional fibres, with variable spacing and broken continuity.
    phase=mathn('ADD',mathn('MULTIPLY',local_y,110),mathn('MULTIPLY',medium,5))
    fibres=mathn('ADD',.5,mathn('MULTIPLY',mathn('SINE',phase),.5))
    fibres=mathn('MULTIPLY',fibres,mathn('ADD',.25,mathn('MULTIPLY',pores,.75)))
    if tile==1:
        core=mathn('MULTIPLY',core,mathn('ADD',.38,mathn('MULTIPLY',smooth(medium,.35,.68),.62)))
        crust=mathn('MULTIPLY',crust,.6)
    if tile==2:
        crust=mathn('MULTIPLY',crust,.18); stain=mathn('MULTIPLY',stain,.25)
    depression=mathn('MULTIPLY',core,.045 if tile==2 else -.18 if tile!=1 else -.07)
    height=mathn('ADD',.5,mathn('ADD',depression,mathn('MULTIPLY',crust,.08)))
    height=mathn('ADD',height,mathn('MULTIPLY',core,mathn('MULTIPLY',mathn('SUBTRACT',fibres,.5),.025)))
    # Keep all stamp channels inside their padded tile.
    edge=mathn('MULTIPLY',mathn('SUBTRACT',1,smooth(mathn('ABSOLUTE',x),.85,.98)),
                         mathn('SUBTRACT',1,smooth(mathn('ABSOLUTE',y),.85,.98)))
    outputs={}
    for semantic,channels in [('Masks',[core,exposed,crust]),('Detail',[height,stain,fibres])]:
        combine=ns.new('ShaderNodeCombineColor')
        for ch,s in enumerate(channels):
            if semantic=='Detail' and ch==0:
                s=mathn('ADD',.5,mathn('MULTIPLY',mathn('SUBTRACT',s,.5),edge))
            else: s=mathn('MULTIPLY',s,edge)
            put(s,combine.inputs[ch])
        outputs[semantic]=combine.outputs[0]
    out=ns.new('ShaderNodeOutputMaterial'); em=ns.new('ShaderNodeEmission'); lk.new(em.outputs[0],out.inputs['Surface'])
    lk.new(outputs['Masks'],em.inputs['Color'])
    data.materials.append(material); data.polygons[tile].material_index=tile
    definitions.append((material,em,outputs))
activate(canvas)
for semantic in ['Masks','Detail']:
    img=bpy.data.images.new('T_ZombieDog_Wound'+semantic,2048,2048,alpha=False,float_buffer=semantic=='Detail')
    img.colorspace_settings.name='Non-Color'
    for material,em,outputs in definitions:
        material.node_tree.links.new(outputs[semantic],em.inputs['Color'])
        target=material.node_tree.nodes.new('ShaderNodeTexImage'); target.image=img; material.node_tree.nodes.active=target
    bpy.ops.object.bake(type='EMIT')
    if semantic=='Detail':
        scene.render.image_settings.file_format='OPEN_EXR'; scene.render.image_settings.color_depth='16'; scene.render.image_settings.color_mode='RGB'
        img.save_render(str(OUT/'Textures'/(img.name+'.exr')),scene=scene)
    else:
        img.filepath_raw=str(OUT/'Textures'/(img.name+'.png')); img.file_format='PNG'; img.save()
    print('REFINED_WOUND_STAMP_BAKED',semantic,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'WoundStamp_Library.blend'))
(OUT/'authoring_manifest.json').write_text(json.dumps(dict(source=str(SOURCE),
    stamps=['LongTear','Abrasion','HealedScar','IrregularPatch'],
    masks_rgb=['core','exposed_skin','dry_crust'],detail_rgb=['relief_around_0.5','blood_stain','fine_fibres'],
    atlas_size=2048,fur_position='nearest underlying skin surface in rest pose',
    geometry_modified=False,runtime_tested=False,preview_rendered=False),indent=2),encoding='utf-8')
print('REFINED_WOUND_SOURCES_AUTHORED',flush=True)
