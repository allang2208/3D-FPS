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
from mathutils import Vector, noise

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'Export'
TEX = OUT / 'Textures'
TEX.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT.parent / 'BarkRebuildV21/Staff_NaturalBark_V21.blend'
VARIANTS = [('frozen_crystal', 'Ice'), ('magma_core', 'Magma'),
            ('storm_core', 'Storm')]
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


def weighted_finish(obj):
    # Keep broad optical faces and round only the small edge bevels.
    activate(obj)
    mod=obj.modifiers.new('Area weighted polish normals','WEIGHTED_NORMAL')
    mod.keep_sharp=True
    mod.weight=40
    bpy.ops.object.modifier_apply(modifier=mod.name)


def craft_mount(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    edges=[e for e in bm.edges if e.is_manifold and
           min(v.co.z for v in e.verts)>62.25 and e.calc_face_angle()>.40]
    result=bmesh.ops.bevel(bm,geom=edges,offset=.028,segments=2,
                           affect='EDGES',clamp_overlap=True)
    for f in result['faces']:f.smooth=True
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free()
    weighted_finish(obj)


def craft_facets(obj, kind):
    # Inherit V33's inward envelope, without repeatedly beveling the V33 mesh.
    for v in obj.data.vertices:
        a=math.atan2(v.co.y,v.co.x);z=v.co.z
        if z>65.3:
            inward=.975-.020*(.5+.5*math.sin(a*3.+z*.47))
            v.co.x*=inward;v.co.y*=inward
    bm=bmesh.new();bm.from_mesh(obj.data)
    seam=bm.faces.layers.int.new('MoltenSeam')
    if kind=='Magma':
        bm.normal_update()
        # Sink the shared edges first, then raise inset faces to the old shell.
        # The fissures therefore have depth and remain inside the old envelope.
        for v in bm.verts:v.co-=v.normal*.105
        result=bmesh.ops.inset_individual(bm,faces=list(bm.faces),
            thickness=.075,depth=.10,use_even_offset=True,use_relative_offset=False)
        for f in result['faces']:f[seam]=1
        edges=[e for e in bm.edges if e.is_manifold and e.calc_face_angle()>.34]
        bevel=bmesh.ops.bevel(bm,geom=edges,offset=.013,segments=1,
                             affect='EDGES',clamp_overlap=True)
    else:
        edges=[e for e in bm.edges if e.is_manifold and e.calc_face_angle()>.15]
        bevel=bmesh.ops.bevel(bm,geom=edges,
            offset={'Ice':.060,'Jade':.125,'Storm':.065}[kind],
            segments=3 if kind=='Jade' else 2,affect='EDGES',clamp_overlap=True)
    for f in bm.faces:f.smooth=False
    for f in bevel['faces']:f.smooth=True
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    color=bm.loops.layers.color.new('MineralData')
    for f in bm.faces:
        for loop in f.loops:loop[color]=(float(f[seam]),0,0,1)
    bm.to_mesh(obj.data);bm.free()
    weighted_finish(obj)
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
    g=Graph('M_StaffCraft_'+kind+'_V38')
    coord=g.coord
    stretch=g.node('ShaderNodeVectorMath');stretch.operation='MULTIPLY'
    g.input(stretch,0,coord)
    g.input(stretch,1,{'Ice':(12.,12.,.8),'Jade':(2.8,2.8,.55),
                      'Storm':(1.4,1.4,2.0),'Mount':(3.,3.,42.)}.get(kind,(1.,1.,1.)))
    g.coord=stretch.outputs[0]
    strand=g.noise(5.2,3)
    g.coord=coord
    cloud=g.noise(3.8,4,.60);grain=g.noise(155,2,.60)
    z=g.node('ShaderNodeSeparateXYZ');g.input(z,'Vector',coord)
    root=g.ramp(z.outputs['Z'],[(0,(1,1,1)),(.22,(0,0,0))])
    if kind=='Ice':
        # Explicitly opaque white ice, per the latest user direction.
        color=g.ramp(cloud,[(.18,(.53,.57,.59)),(.52,(.76,.79,.80)),(.82,(.92,.94,.95))])
        lines=g.ramp(strand,[(.55,(0,0,0)),(.69,(.20,.20,.20)),(.85,(.44,.44,.44))])
        color=g.mix(lines,color,(.90,.93,.95,1))
        rough=g.math('ADD',g.range(cloud,.18,.31),g.math('MULTIPLY',lines,.14))
        opacity=1.;glow=g.math('MULTIPLY',lines,.025)
        bump_height=g.math('ADD',g.math('MULTIPLY',grain,.025),g.math('MULTIPLY',strand,.035))
        transmission=0.
    elif kind=='Magma':
        # Warped, nonuniform molten channels, independent of the sphere topology.
        warp=g.node('ShaderNodeTexNoise');g.input(warp,'Vector',coord)
        warp.inputs['Scale'].default_value=3.1
        scale=g.node('ShaderNodeVectorMath');scale.operation='SCALE'
        g.input(scale,0,warp.outputs['Color']);scale.inputs['Scale'].default_value=.24
        add=g.node('ShaderNodeVectorMath');add.operation='ADD'
        g.input(add,0,coord);g.input(add,1,scale.outputs[0])
        vor=g.node('ShaderNodeTexVoronoi');vor.feature='DISTANCE_TO_EDGE'
        g.input(vor,'Vector',add.outputs[0]);vor.inputs['Scale'].default_value=5.2
        molten=g.ramp(vor.outputs['Distance'],[(0,(1,1,1)),(.035,(.80,.80,.80)),(.085,(0,0,0))])
        heat=g.math('MULTIPLY',molten,g.range(cloud,.55,1.))
        crust=g.ramp(cloud,[(.20,(.008,.005,.004)),(.52,(.04,.017,.009)),(.82,(.14,.049,.013))])
        hot=g.ramp(heat,[(0,(.24,.010,.002)),(.5,(.85,.075,.004)),(1,(1.,.33,.025))])
        color=g.mix(molten,crust,hot)
        rough=g.mix(molten,g.range(grain,.40,.64),(.20,.20,.20,1))
        opacity=1.;glow=heat;transmission=0.
        bump_height=g.math('SUBTRACT',g.math('MULTIPLY',grain,.22),g.math('MULTIPLY',molten,.35))
    elif kind=='Jade':
        mineral=g.math('ADD',g.math('MULTIPLY',cloud,.62),g.math('MULTIPLY',strand,.38))
        color=g.ramp(mineral,[(.20,(.007,.034,.018)),(.43,(.015,.10,.050)),
            (.60,(.072,.25,.128)),(.80,(.26,.45,.25))])
        vein=g.ramp(strand,[(.53,(0,0,0)),(.66,(.12,.12,.12)),(.80,(.30,.30,.30))])
        color=g.mix(vein,color,(.32,.44,.24,1))
        rough=g.range(mineral,.125,.245);opacity=1.
        glow=g.math('MULTIPLY',vein,.18)
        bump_height=g.math('MULTIPLY',grain,.012)
        transmission=.08
        g.bs.inputs['Subsurface Weight'].default_value=.24
        g.bs.inputs['Subsurface Radius'].default_value=(.18,.45,.22)
    elif kind=='Storm':
        color=g.ramp(cloud,[(.20,(.018,.012,.048)),(.54,(.060,.037,.16)),(.82,(.20,.13,.32))])
        rough=g.range(cloud,.075,.17)
        opacity=g.math('ADD',g.range(cloud,.21,.32),g.math('MULTIPLY',root,.065))
        glow=g.math('MULTIPLY',g.math('POWER',strand,6.),.08)
        bump_height=g.math('MULTIPLY',grain,.009)
        transmission=.78
    else:
        color=g.ramp(cloud,[(.20,(.042,.031,.018)),(.53,(.19,.135,.062)),(.82,(.34,.255,.135))])
        rough=g.math('ADD',g.range(cloud,.26,.38),g.math('MULTIPLY',strand,.085))
        opacity=1.;glow=0.;transmission=0.
        bump_height=g.math('ADD',g.math('MULTIPLY',strand,.025),g.math('MULTIPLY',grain,.010))
        g.bs.inputs['Metallic'].default_value=.82
    g.input(g.bs,'Base Color',color);g.input(g.bs,'Roughness',rough)
    g.bs.inputs['IOR'].default_value=1.31 if kind=='Ice' else 1.54
    g.bs.inputs['Transmission Weight'].default_value=transmission
    bump=g.node('ShaderNodeBump');g.input(bump,'Height',bump_height)
    bump.inputs['Strength'].default_value=.28;bump.inputs['Distance'].default_value=.045
    g.input(g.bs,'Normal',bump.outputs['Normal'])
    palette={'Ice':(.78,.88,1.,1),'Magma':(1.,.105,.004,1),'Jade':(.08,.52,.19,1),
             'Storm':(.28,.12,.85,1),'Mount':(0,0,0,1)}
    g.bs.inputs['Emission Color'].default_value=palette[kind]
    g.input(g.bs,'Emission Strength',g.math('MULTIPLY',glow,3.2 if kind=='Magma' else .25))
    combine=g.node('ShaderNodeCombineColor');combine.mode='RGB'
    for pin,value in [('Red',rough),('Green',opacity),('Blue',glow)]:g.input(combine,pin,value)
    g.mat['packed_channels']='R roughness; G opacity; B localized emission/illumination mask'
    return g,color,combine.outputs['Color']


def bake(obj, kind):
    g,color,packed = recipe(kind)
    obj.data.materials.append(g.mat)
    activate(obj)
    images={}
    emit=g.node('ShaderNodeEmission')
    target=g.node('ShaderNodeTexImage')
    for channel, socket in [('BaseColor',color),('RGE',packed),('Normal',None)]:
        image=bpy.data.images.new('T_StaffCraft_'+kind+'_'+channel+'_V38',width=SIZE,height=SIZE,alpha=False)
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


def vertex_signal(obj,value,phase=0.):
    attr=obj.data.color_attributes.get('CoreSignal') or obj.data.color_attributes.new(name='CoreSignal',type='BYTE_COLOR',domain='CORNER')
    for c in attr.data:c.color=(value,phase,0,1)
    obj.data.color_attributes.active_color=attr
    obj.data.color_attributes.render_color_index=list(obj.data.color_attributes).index(attr)


def core_material(kind):
    g=Graph('M_StaffCraft_'+kind+'Inner_V38')
    signal=g.node('ShaderNodeVertexColor');signal.layer_name='CoreSignal'
    sep=g.node('ShaderNodeSeparateColor');g.input(sep,'Color',signal.outputs['Color'])
    if kind=='Ice':
        g.bs.inputs['Base Color'].default_value=(.075,.20,.26,1)
        g.bs.inputs['Roughness'].default_value=.25
        tint=(.12,.60,.72,1);strength=.10
    else:
        g.input(g.bs,'Base Color',g.mix(sep.outputs['Red'],(.010,.006,.024,1),(.23,.15,.46,1)))
        g.bs.inputs['Roughness'].default_value=.20
        tint=(.38,.22,1.,1);strength=4.2
    g.bs.inputs['Emission Color'].default_value=tint
    g.input(g.bs,'Emission Strength',g.math('MULTIPLY',sep.outputs['Red'],strength))
    return g.mat


def arc_tube(points,name,mat,phase,width=.032):
    pts=[Vector(p) for p in points];sides=6;verts=[]
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        n=tangent.cross(Vector((0,1,0))).normalized();other=tangent.cross(n)
        radius=width*(.34+.66*math.sin(math.pi*i/(len(pts)-1)))
        verts.extend([p+radius*(math.cos(k*math.tau/sides)*n+math.sin(k*math.tau/sides)*other) for k in range(sides)])
    faces=[(j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k)
           for j in range(len(pts)-1) for k in range(sides)]
    faces += [tuple(reversed(range(sides))),tuple((len(pts)-1)*sides+k for k in range(sides))]
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat);vertex_signal(obj,1.,phase)
    for p in obj.data.polygons:p.use_smooth=True
    return obj


def magma_sphere():
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5,radius=1.)
    obj=bpy.context.object;obj.name='Magma_Irregular_Round_Sphere'
    for v in obj.data.vertices:
        d=v.co.normalized()
        broad=noise.noise_vector(d*2.2+Vector((8.2,3.7,9.1)))[0]
        middle=noise.noise_vector(d*7.3+Vector((4.6,1.8,7.4)))[1]
        fine=noise.noise_vector(d*21.0+Vector((2.1,5.2,3.7)))[2]
        r=4.88*(.98+.080*broad+.026*middle+.006*fine)
        p=d*r;p.y*=.98;p.z*=1.02
        # Melt the lowest cap into the existing seat without a floating ball.
        p.z-=.66*max(0.,(-d.z-.66)/.34)**2
        v.co=p+Vector((0,0,70.85))
    for p in obj.data.polygons:p.use_smooth=True
    unwrap(obj)
    obj['design']='irregular round molten sphere, no polygonal plate grid'
    return obj


def electric_tube(points,branch,mat,layer,parameters=None):
    pts=[Vector(p) for p in points];sides=6;verts=[]
    ts=parameters or [i/(len(pts)-1) for i in range(len(pts))]
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        n=tangent.cross(Vector((0,1,0))).normalized();other=tangent.cross(n)
        width=(.014 if layer else .046)*(0.78+.22*math.sin(i*2.7+branch))
        verts.extend([p+width*(math.cos(k*math.tau/sides)*n+math.sin(k*math.tau/sides)*other) for k in range(sides)])
    faces=[(j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k)
           for j in range(len(pts)-1) for k in range(sides)]
    faces += [tuple(reversed(range(sides))),tuple((len(pts)-1)*sides+k for k in range(sides))]
    data=bpy.data.meshes.new('Core_Bolt');data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new('Core_Bolt_'+str(branch)+'_'+str(layer),data)
    bpy.context.collection.objects.link(obj);data.materials.append(mat)
    uv=data.uv_layers.new(name='UVMap')
    for loop in data.loops:
        # UE FBX import flips V. The shader uses (1 - V) to recover branch ID.
        uv.data[loop.index].uv=(ts[loop.vertex_index//sides],branch/16.)
    vertex_signal(obj,float(layer),branch/8.)
    for p in data.polygons:p.use_smooth=True
    return obj


def inner_geometry(kind):
    # The solid seed is gone: every visible central piece belongs to the VFX.
    mat=core_material('Storm');objects=[]
    rng=random.Random(3809)
    for branch in range(8):
        a=branch*math.tau/8;z=-.70+1.4*((branch*3)%8)/7
        direction=Vector((math.cos(a)*math.sqrt(1-z*z),math.sin(a)*math.sqrt(1-z*z),z))
        side=direction.cross(Vector((0,0,1))).normalized()
        pts=[]
        for i in range(11):
            t=i/10.;r=2.25*(t*2-1)
            jitter=side*rng.uniform(-.15,.15)*math.sin(math.pi*t)
            pts.append(Vector((0,0,71))+direction*r+jitter)
        for layer in (0,1):objects.append(electric_tube(pts,branch,mat,layer))
        if branch%2==0:
            start=pts[5]
            fork=[start+side*(j*.30)+direction*(j*.20)+Vector((0,0,.09*j)) for j in range(5)]
            for layer in (0,1):objects.append(electric_tube(fork,branch,mat,layer,[.5+.1*j for j in range(5)]))
    return objects


manifest=[]
material_manifest={}
mount_material=None
for key,kind in VARIANTS:
    old=sources[PREFIX+key]
    metal=extract(old,True,kind+'_Original_Mount')
    gem=magma_sphere() if kind=='Magma' else extract(old,False,kind+'_Faceted_Shell')
    craft_mount(metal)
    if kind!='Magma':craft_facets(gem,kind)
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
    objects=[metal,gem]+(inner_geometry(kind) if kind=='Storm' else [])
    for obj in objects:
        if not obj.data.uv_layers:unwrap(obj)
        if not obj.data.color_attributes.get('CoreSignal'):vertex_signal(obj,0)
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
    joined=bpy.context.object;joined.name=PREFIX+key+'_V38'
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
scene['revision']=38
scene['design']='opaque white ice; irregular round molten sphere; continuously reshaped lightning core inside retained storm shell'
scene['interface']='V21 original neck and seat retained; crown envelope retained; pivot and lower mating surface retained; changes stay inside the previous silhouette'
for area in (bpy.context.screen.areas if bpy.context.screen else []):
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_location=Vector((0,0,71))
        area.spaces.active.region_3d.view_distance=30
(OUT/'meshes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(OUT/'materials.json').write_text(json.dumps(material_manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Staff_ElementalCrystals_V38.blend'))
(ROOT/'author-receipt.json').write_text(json.dumps({'complete':True,'revision':38,
    'source':str(SOURCE),'blend':str(ROOT/'Staff_ElementalCrystals_V38.blend'),
    'texture_size':SIZE,'texture_maps':12,'meshes':manifest,'runtime_tested':False,
    'preview_rendered':False,'texture_baked':True},indent=2),encoding='utf-8')
print('STAFF_CRYSTAL_CRAFT_V38_AUTHORED',flush=True)
