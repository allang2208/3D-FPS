"""Author the four elemental heads in Blender and bake their production textures.

Run with Blender --background --factory-startup --python this_file.
No preview rendering, gameplay, or tests. Coordinates and FBX convention inherit V21.
"""
import bpy
import bmesh
import json
import math
import random
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'Export'
TEX = OUT / 'Textures'
TEX.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT.parent / 'BarkRebuildV21/Staff_NaturalBark_V21.blend'
VARIANTS = [('frozen_crystal', 'Ice'), ('magma_core', 'Magma'),
            ('jade_spirit_crystal', 'Jade'), ('storm_core', 'Storm')]
PREFIX = 'SM_Staff_head_crystal_'
SIZE = 1024
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
with bpy.data.libraries.load(str(SOURCE), link=False) as (src, dst):
    dst.objects = [PREFIX + key for key, _ in VARIANTS]
sources = {obj.name: obj for obj in dst.objects}
reference = bpy.data.collections.new('V21_Original_Interfaces')
bpy.context.scene.collection.children.link(reference)
for obj in sources.values():
    reference.objects.link(obj)
    obj.hide_set(True)
    obj.hide_render = True
reference.hide_render = True

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 1
scene.render.bake.margin = 12
scene.render.bake.use_clear = True
scene.render.bake.use_selected_to_active = False
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene['author_units'] = 'mesh coordinates are UE centimetres, matching V21 FBX'


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def extract(source, metal, name):
    obj = bpy.data.objects.new(name, source.data.copy())
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    remove = [f for f in bm.faces if
              ('metal' in source.data.materials[f.material_index].name.lower()) != metal]
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    for f in bm.faces:
        f.material_index = 0
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.materials.clear()
    return obj


def unwrap(obj):
    activate(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=.025)
    bpy.ops.object.mode_set(mode='OBJECT')
    while len(obj.data.uv_layers) > 1:
        obj.data.uv_layers.remove(obj.data.uv_layers[-1])
    obj.data.uv_layers[0].name = 'UVMap'
    obj.data.uv_layers.active_index = 0


def craft_facets(obj, kind):
    # Shrink inward from the old surface: existing crown clearances stay available.
    for v in obj.data.vertices:
        a = math.atan2(v.co.y, v.co.x)
        z = v.co.z
        inward = .975 - .020 * (.5 + .5 * math.sin(a * 3.0 + z * .47))
        if z > 65.3:
            v.co.x *= inward
            v.co.y *= inward
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=.10 if kind == 'Jade' else .045,
                   segments=2 if kind == 'Jade' else 1, affect='EDGES', clamp_overlap=True)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    for p in obj.data.polygons:
        p.use_smooth = False
    unwrap(obj)


class Graph:
    def __init__(self, name):
        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nodes = self.mat.node_tree.nodes
        self.nodes.clear()
        self.links = self.mat.node_tree.links
        self.output = self.node('ShaderNodeOutputMaterial')
        self.bs = self.node('ShaderNodeBsdfPrincipled')
        self.links.new(self.bs.outputs['BSDF'], self.output.inputs['Surface'])
        self.coord = self.node('ShaderNodeTexCoord').outputs['Generated']

    def node(self, kind):
        return self.nodes.new(kind)

    def input(self, n, pin, value):
        if isinstance(value, (int, float, tuple, list)):
            n.inputs[pin].default_value = value
        else:
            self.links.new(value, n.inputs[pin])

    def math(self, op, a, b=0):
        n = self.node('ShaderNodeMath')
        n.operation = op
        self.input(n, 0, a)
        self.input(n, 1, b)
        return n.outputs[0]

    def noise(self, scale, detail=2., rough=.65):
        n = self.node('ShaderNodeTexNoise')
        self.input(n, 'Vector', self.coord)
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        return n.outputs['Fac']

    def ramp(self, value, stops):
        n = self.node('ShaderNodeValToRGB')
        cr = n.color_ramp
        cr.interpolation = 'EASE'
        for elem in list(cr.elements)[2:]:
            cr.elements.remove(elem)
        for idx, (position, color) in enumerate(stops):
            elem = cr.elements[idx] if idx < 2 else cr.elements.new(position)
            elem.position = position
            elem.color = (*color, 1) if len(color) == 3 else color
        self.input(n, 'Fac', value)
        return n.outputs['Color']

    def mix(self, factor, a, b):
        n = self.node('ShaderNodeMixRGB')
        self.input(n, 0, factor)
        self.input(n, 1, a)
        self.input(n, 2, b)
        return n.outputs[0]

    def range(self, value, low, high):
        return self.math('ADD', low, self.math('MULTIPLY', value, high-low))


def recipe(kind):
    g = Graph('M_StaffCraft_' + kind + '_V33')
    cloud = g.noise(3.4 if kind != 'Mount' else 6, 3)
    grain = g.noise(130, 2)
    vor = g.node('ShaderNodeTexVoronoi')
    vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs['Scale'].default_value = {'Ice': 7, 'Magma': 6, 'Jade': 4, 'Storm': 5, 'Mount': 28}[kind]
    # Warped mineral borders avoid a uniform painted polygon grid.
    warp = g.node('ShaderNodeTexNoise')
    g.input(warp, 'Vector', g.coord)
    warp.inputs['Scale'].default_value = 3.3
    scale = g.node('ShaderNodeVectorMath'); scale.operation = 'SCALE'
    g.input(scale, 0, warp.outputs['Color']); scale.inputs['Scale'].default_value = .12
    add = g.node('ShaderNodeVectorMath'); add.operation = 'ADD'
    g.input(add, 0, g.coord); g.input(add, 1, scale.outputs[0])
    g.input(vor, 'Vector', add.outputs[0])
    edge = vor.outputs['Distance']
    crack = g.ramp(edge, [(0., (1, 1, 1)), (.025 if kind == 'Magma' else .013, (0, 0, 0))])
    broken = g.math('MULTIPLY', crack, g.range(cloud, .15, 1.0))
    if kind == 'Ice':
        color = g.ramp(cloud, [(.22, (.035,.12,.18)), (.54, (.17,.40,.49)), (.78, (.56,.73,.75))])
        color = g.mix(g.math('MULTIPLY', broken,.62), color, (.57,.79,.83,1))
        rough = g.range(cloud, .08, .26)
        opacity = g.range(cloud, .22, .50)
        glow = g.math('MULTIPLY', broken,.60)
        bump_height = g.math('ADD', g.math('MULTIPLY', grain,.035), g.math('MULTIPLY',broken,.07))
        transmission = .68
    elif kind == 'Magma':
        color = g.ramp(cloud, [(.2, (.009,.006,.005)), (.56, (.033,.020,.016)), (.8, (.10,.055,.032))])
        color = g.mix(broken,color,(.62,.065,.004,1))
        rough = g.mix(broken,g.range(grain,.34,.60),(.14,.14,.14,1))
        opacity = 1.0
        glow = broken
        bump_height = g.math('SUBTRACT',g.math('MULTIPLY',grain,.22),g.math('MULTIPLY',broken,.7))
        transmission = 0.
    elif kind == 'Jade':
        color = g.ramp(cloud, [(.2, (.008,.042,.019)), (.43, (.018,.16,.062)), (.62, (.10,.34,.16)), (.82, (.39,.57,.31))])
        color = g.mix(g.math('MULTIPLY',broken,.35),color,(.26,.40,.13,1))
        rough = g.range(cloud,.18,.32)
        opacity = 1.
        glow = g.math('MULTIPLY',g.math('POWER',cloud,4.),.7)
        bump_height = g.math('MULTIPLY',grain,.05)
        transmission = .12
        g.bs.inputs['Subsurface Weight'].default_value=.35
        g.bs.inputs['Subsurface Radius'].default_value=(.35,.8,.25)
    elif kind == 'Storm':
        color = g.ramp(cloud, [(.2, (.025,.014,.068)), (.53, (.115,.068,.22)), (.82, (.35,.27,.49))])
        rough = g.range(cloud,.10,.24)
        opacity = g.range(cloud,.20,.39)
        glow = g.math('MULTIPLY',broken,.14)
        bump_height = g.math('MULTIPLY',grain,.025)
        transmission = .78
    else:
        color = g.ramp(cloud, [(.24, (.027,.024,.019)), (.51, (.12,.095,.059)), (.78, (.25,.20,.12))])
        rough = g.range(grain,.29,.53)
        opacity = 1.
        glow = 0.
        bump_height = g.math('MULTIPLY',grain,.10)
        transmission = 0.
        g.bs.inputs['Metallic'].default_value=.8
    g.input(g.bs,'Base Color',color)
    g.input(g.bs,'Roughness',rough)
    g.bs.inputs['IOR'].default_value=1.46 if kind=='Ice' else 1.54
    g.bs.inputs['Transmission Weight'].default_value=transmission
    bump=g.node('ShaderNodeBump')
    g.input(bump,'Height',bump_height)
    bump.inputs['Strength'].default_value=.3
    bump.inputs['Distance'].default_value=.055
    g.input(g.bs,'Normal',bump.outputs['Normal'])
    palette={'Ice':(.10,.55,.80,1),'Magma':(1.,.10,.002,1),'Jade':(.08,.52,.19,1),
             'Storm':(.24,.10,.75,1),'Mount':(0,0,0,1)}
    g.bs.inputs['Emission Color'].default_value=palette[kind]
    g.input(g.bs,'Emission Strength',g.math('MULTIPLY',glow,2.5 if kind=='Magma' else .3))
    combine=g.node('ShaderNodeCombineColor');combine.mode='RGB'
    for pin, value in [('Red',rough),('Green',opacity),('Blue',glow)]:g.input(combine,pin,value)
    g.mat['packed_channels']='R roughness; G opacity; B localized emission/illumination mask'
    return g, color, combine.outputs['Color']


def bake(obj, kind):
    g,color,packed = recipe(kind)
    obj.data.materials.append(g.mat)
    activate(obj)
    images={}
    emit=g.node('ShaderNodeEmission')
    target=g.node('ShaderNodeTexImage')
    for channel, socket in [('BaseColor',color),('RGE',packed),('Normal',None)]:
        image=bpy.data.images.new('T_StaffCraft_'+kind+'_'+channel+'_V33',width=SIZE,height=SIZE,alpha=False)
        image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
        target.image=image
        for node in g.nodes:node.select=False
        target.select=True;g.nodes.active=target
        if socket is not None:
            g.links.new(socket,emit.inputs['Color'])
            g.links.new(emit.outputs[0],g.output.inputs['Surface'])
            bpy.ops.object.bake(type='EMIT')
        else:
            g.links.new(g.bs.outputs['BSDF'],g.output.inputs['Surface'])
            bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT')
        image.filepath_raw=str(TEX/(image.name+'.png'));image.file_format='PNG';image.save();image.pack()
        images[channel]=image.name
        print('BAKED '+kind+' '+channel,flush=True)
    g.links.new(g.bs.outputs['BSDF'],g.output.inputs['Surface'])
    return g.mat, images


def vertex_signal(obj,value):
    attr=obj.data.color_attributes.get('CoreSignal') or obj.data.color_attributes.new(name='CoreSignal',type='BYTE_COLOR',domain='CORNER')
    for c in attr.data:c.color=(value,0,0,1)


def core_material(kind):
    g=Graph('M_StaffCraft_'+kind+'Inner_V33')
    signal=g.node('ShaderNodeVertexColor');signal.layer_name='CoreSignal'
    sep=g.node('ShaderNodeSeparateColor');g.input(sep,'Color',signal.outputs['Color'])
    if kind=='Ice':
        g.bs.inputs['Base Color'].default_value=(.12,.31,.36,1)
        g.bs.inputs['Roughness'].default_value=.38
        tint=(.12,.60,.72,1)
        strength=.15
    else:
        g.input(g.bs,'Base Color',g.mix(sep.outputs['Red'],(.013,.007,.03,1),(.18,.09,.42,1)))
        g.bs.inputs['Roughness'].default_value=.30
        tint=(.30,.15,1.,1)
        strength=4.
    g.bs.inputs['Emission Color'].default_value=tint
    g.input(g.bs,'Emission Strength',g.math('MULTIPLY',sep.outputs['Red'],strength))
    return g.mat


def inner_geometry(kind):
    mat=core_material(kind);objects=[]
    if kind=='Ice':
        for i,(pos,scale) in enumerate([((.1,.15,70.5),(.65,.48,2.9)),((-.75,.25,69),(.32,.22,1.65)),((.45,-.5,72),(.30,.2,1.35))]):
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=pos)
            obj=bpy.context.object;obj.name='Ice_Inclusion_'+str(i);obj.scale=scale
            obj.rotation_euler=(.13*i,.16*(i-1),.4*i)
            bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
            obj.data.materials.append(mat);vertex_signal(obj,.6);objects.append(obj)
    else:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=(0,0,71))
        obj=bpy.context.object;obj.name='Storm_Suspended_Dark_Core';obj.scale=(1.15,.95,1.5)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        obj.data.materials.append(mat);vertex_signal(obj,0);objects.append(obj)
        rng=random.Random(3304)
        for branch in range(7):
            a=branch*math.tau/7
            pts=[]
            for step in range(9):
                t=step/8;radius=.65+1.5*math.sin(math.pi*t)
                pts.append(Vector((math.cos(a+t)*radius+rng.uniform(-.18,.18),
                                   math.sin(a+t)*radius+rng.uniform(-.18,.18),67.4+t*7.3)))
            verts=[]
            for i,p in enumerate(pts):
                tangent=(pts[min(i+1,8)]-pts[max(i-1,0)]).normalized()
                n=tangent.cross(Vector((0,1,0))).normalized();other=tangent.cross(n)
                radius=.018+.018*math.sin(math.pi*i/8)
                verts.extend([p+radius*(math.cos(k*math.tau/5)*n+math.sin(k*math.tau/5)*other) for k in range(5)])
            faces=[(j*5+k,j*5+(k+1)%5,(j+1)*5+(k+1)%5,(j+1)*5+k) for j in range(8) for k in range(5)]
            faces += [tuple(reversed(range(5))),tuple(40+k for k in range(5))]
            data=bpy.data.meshes.new('Bound_Lightning');data.from_pydata(verts,[],faces);data.update()
            arc=bpy.data.objects.new('Internal_Arc_'+str(branch),data);bpy.context.collection.objects.link(arc)
            arc.data.materials.append(mat);vertex_signal(arc,1);objects.append(arc)
    return objects


manifest=[]
material_manifest={}
mount_material=None
for key,kind in VARIANTS:
    old=sources[PREFIX+key]
    metal=extract(old,True,kind+'_Original_Mount')
    gem=extract(old,False,kind+'_Faceted_Shell')
    craft_facets(gem,kind)
    if mount_material is None:
        unwrap(metal)
        mount_material,maps=bake(metal,'Mount')
        material_manifest['Mount']={'material':mount_material.name,'textures':maps}
        mount_uv=[tuple(loop.uv) for loop in metal.data.uv_layers[0].data]
    else:
        # All four mounts come from the identical V21 lower neck and seat.
        while metal.data.uv_layers:metal.data.uv_layers.remove(metal.data.uv_layers[-1])
        uv=metal.data.uv_layers.new(name='UVMap')
        for loop,co in zip(uv.data,mount_uv):loop.uv=co
        metal.data.materials.append(mount_material)
    mat,maps=bake(gem,kind)
    material_manifest[kind]={'material':mat.name,'textures':maps}
    objects=[metal,gem]+(inner_geometry(kind) if kind in ('Ice','Storm') else [])
    for obj in objects:
        if not obj.data.uv_layers:unwrap(obj)
        if not obj.data.color_attributes:vertex_signal(obj,0)
    # Keep an editable collection, and export a joined copy at the original pivot.
    collection=bpy.data.collections.new(key+'_Editable')
    scene.collection.children.link(collection)
    for obj in objects:
        for c in list(obj.users_collection):c.objects.unlink(obj)
        collection.objects.link(obj)
    copies=[]
    for obj in objects:
        copy=obj.copy();copy.data=obj.data.copy();scene.collection.objects.link(copy);copies.append(copy)
    activate(copies[0])
    for obj in copies:obj.select_set(True)
    bpy.ops.object.join()
    joined=bpy.context.object;joined.name=PREFIX+key+'_V33'
    scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    filename=OUT/(PREFIX+key+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(filename),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,
        apply_scale_options='FBX_SCALE_ALL',path_mode='AUTO',embed_textures=False)
    manifest.append({'id':key,'kind':kind,'name':PREFIX+key,'fbx':str(filename),
        'materials':[m.name for m in joined.data.materials],
        'triangles':sum(len(p.vertices)-2 for p in joined.data.polygons)})
    joined.hide_render=True;joined.hide_set(True)
    collection.hide_render=True
    for obj in objects:obj.hide_set(True)
    print('EXPORTED '+key,flush=True)

# Artist file opens with the ice variant available; no render is performed.
for obj in bpy.data.collections['frozen_crystal_Editable'].objects:obj.hide_set(False)
bpy.data.collections['frozen_crystal_Editable'].hide_render=False
scene['revision']=33
scene['design']='ice fractures; obsidian magma fissures; cloudy jade; smoke-purple shell with contained lightning'
scene['interface']='V21 original neck and seat retained; crown envelope retained; pivot and dimensions unchanged'
for area in (bpy.context.screen.areas if bpy.context.screen else []):
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_location=Vector((0,0,71))
        area.spaces.active.region_3d.view_distance=30
(OUT/'meshes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(OUT/'materials.json').write_text(json.dumps(material_manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Staff_ElementalCrystals_V33.blend'))
(ROOT/'author-receipt.json').write_text(json.dumps({'complete':True,'revision':33,
    'source':str(SOURCE),'blend':str(ROOT/'Staff_ElementalCrystals_V33.blend'),
    'texture_size':SIZE,'texture_maps':15,'meshes':manifest,'runtime_tested':False,
    'preview_rendered':False,'texture_baked':True},indent=2),encoding='utf-8')
print('STAFF_CRYSTAL_CRAFT_V33_AUTHORED',flush=True)
