"""Build the bilateral Eagle Talon relief and export each fitted blade seat in sword space."""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler
from mathutils.kdtree import KDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import talon_profile as P

ART = HERE/'Art'
BASE = 'SM_ForgedSteelGreatsword_EagleTalonGuard'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene


def collection(name):
    result = bpy.data.collections.new(name)
    scene.collection.children.link(result)
    return result


parts = collection('01 | Eagle Talon - editable metalwork')
fittings = collection('02 | Blade seat alternatives')
exports = collection('03 | Assembled export meshes')


def create_steel():
    mat = bpy.data.materials.new('M_EagleTalon_ForgedSteel')
    mat.use_nodes = True
    nodes, link = mat.node_tree.nodes, mat.node_tree.links.new
    bs = nodes.get('Principled BSDF')
    def texture(name, raw, pos):
        tex = nodes.new('ShaderNodeTexImage')
        tex.label = name
        tex.image = bpy.data.images.load(str(ART/('T_EagleTalon_'+name+'.png')))
        if raw:
            tex.image.colorspace_settings.name = 'Non-Color'
        tex.image.pack()
        tex.location = pos
        return tex.outputs['Color']
    link(texture('BaseColor',False,(-720,560)),bs.inputs['Base Color'])
    mask = nodes.new('ShaderNodeSeparateColor')
    mask.location = (-350,280)
    link(texture('ORM',True,(-720,260)),mask.inputs['Color'])
    link(mask.outputs['Green'],bs.inputs['Roughness'])
    link(mask.outputs['Blue'],bs.inputs['Metallic'])
    normal = nodes.new('ShaderNodeNormalMap')
    normal.location = (-330,-50)
    link(texture('Normal',True,(-720,-10)),normal.inputs['Color'])
    link(normal.outputs['Normal'],bs.inputs['Normal'])
    bs.inputs['Emission Color'].default_value = (.36,.71,1.,1.)
    glow = nodes.new('ShaderNodeValue')
    glow.name = glow.label = 'IceStrength'
    glow.outputs[0].default_value = 0.
    glow.location = (-730,-560)
    times = nodes.new('ShaderNodeMath')
    times.operation = 'MULTIPLY'
    times.location = (-310,-370)
    link(texture('IceMask',True,(-720,-295)),times.inputs[0])
    link(glow.outputs[0],times.inputs[1])
    link(times.outputs[0],bs.inputs['Emission Strength'])
    mat.diffuse_color = (.26,.24,.22,1)
    return mat


steel = create_steel()


def solid(name, points, coordinates, faces, wall_uv=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points,[],faces)
    mesh.update()
    mesh.materials.append(steel)
    uv = mesh.uv_layers.new(name='UVMap')
    wall_uv = wall_uv or {}
    for poly in mesh.polygons:
        poly.use_smooth = True
        special = wall_uv.get(poly.index)
        for i,k in enumerate(poly.loop_indices):
            uv.data[k].uv = special[i] if special else coordinates[mesh.loops[k].vertex_index]
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    mesh.set_sharp_from_angle(angle=math.radians(43))
    obj = bpy.data.objects.new(name,mesh)
    parts.objects.link(obj)
    return obj


def sample_edge(points, amount):
    samples = P.bezier(points,64)
    arc = np.r_[0,np.cumsum(np.linalg.norm(np.diff(samples,axis=0),axis=1))]
    return np.stack([np.interp(amount,arc/arc[-1],samples[:,i]) for i in (0,1)],axis=1)


def close_rim(faces, border, block, wall_uv, coords):
    perim = 0.
    for a,b in zip(border,border[1:]+border[:1]):
        advance = math.dist(coords[a],coords[b])
        # Give thickness its own brushed strip. Keep this UV continuous across the wrap.
        wall_uv[len(faces)] = [(perim,.060),(perim+advance,.060),
                               (perim+advance,.175),(perim,.175)]
        faces.append((a,b,b+block,a+block))
        perim += advance


def strip(name, traces, hand, kind, course=0):
    # Profile the full cross-section, including the blunt root and a single closed tip.
    n = 130 if kind=='talon' else 78
    ts = np.linspace(0,1,n+1)
    edge_a,edge_b = [sample_edge(path,ts) for path in traces]
    sections = np.array([0,.023,.055,.105,.18,.28,.39,.47,.49,.51,.56,.66,.77,.87,.94,.975,1])
    stride = len(sections)
    points,uv,faces = [],[],[]
    for surface in (1,-1):
        for i,t in enumerate(ts[:-1]):
            for s in sections:
                x,y = edge_a[i]*(1-s)+edge_b[i]*s
                if hand=='R':
                    x = 2*P.CENTER-x
                # Ridges converge smoothly into the forged tip. Each feather seats
                # below its predecessor, leaving visible lips on the outer fan.
                if kind=='talon':
                    ridge = 1-abs(s-.47)/(.47 if s<.47 else .53)
                    depth = (.25+.94*ridge+.20*math.sin(math.pi*s))*(1-.30*t)
                    depth *= min(1,(1-t)*10)**.63
                elif kind=='barb':
                    depth = (.29+.92*math.sin(math.pi*s)**.69)*(1-.34*t)
                    depth *= min(1,(1-t)*8)**.54
                else:
                    field = 1.64-.095*course-.25*t
                    depth = field+.15*math.sin(math.pi*s)-.075*s
                    depth -= .085*max(0,1-s/.10)+.19*max(0,1-(1-s)/.14)
                    depth *= min(1,.12+(1-t)*13)**.66
                points.append(P.model_point(x,y,surface*depth))
                uv.append(P.front_uv(x,y))
        x,y = edge_a[-1]
        if hand=='R':
            x = 2*P.CENTER-x
        # A subpixel end face preserves a real polished edge at grazing angles.
        points.append(P.model_point(x,y,surface*.009))
        uv.append(P.front_uv(x,y))
    block = n*stride+1
    tip = block-1
    for base in (0,block):
        for i in range(n-1):
            for j in range(stride-1):
                a = base+i*stride+j
                faces.append((a,a+stride,a+stride+1,a+1))
        for j in range(stride-1):
            a = base+(n-1)*stride+j
            faces.append((a,base+tip,a+1))
    border = [i*stride for i in range(n)]+[tip]
    border += [i*stride+stride-1 for i in reversed(range(n))]
    border += list(range(stride-2,0,-1))
    side_uv = {}
    close_rim(faces,border,block,side_uv,uv)
    return solid(name,points,uv,faces,side_uv)


def groove_index():
    lines = [P.bezier(line,96) for line in P.ENGRAVINGS]
    tree = KDTree(sum(map(len,lines)))
    index = 0
    for line in lines:
        for x,y in line:
            tree.insert((x,y,0),index)
            index += 1
    tree.balance()
    return tree


channels = groove_index()


def crest_depth(dx,y,half):
    # The raised pentagonal rim is an actual lip around the engraved face.
    distance = (half-dx)*(.64 if y<97 else .95)
    dome = 2.06+.23*(1-dx/max(half,1))+.05*math.cos((y-80)/64)
    rim = .145*math.exp(-((distance-3.2)/2.05)**2)
    trench = -.080*math.exp(-((distance-7.2)/1.8)**2)
    d = channels.find((P.CENTER-dx,y,0))[2]
    engraving = -.093*math.exp(-(d/1.65)**2)-.055*math.exp(-(d/3.7)**2)
    land = .039*math.exp(-((d-3.6)/1.65)**2)
    center = .072*math.exp(-(dx/1.9)**2) if 28<y<153 else 0
    return dome+rim+trench+engraving+land+center-.10*math.exp(-(distance/.85)**2)


def beak_depth(dx,y,half):
    # The overhanging brow shades the eyes. Two planes meet on the long bill ridge.
    q = dx/max(half,.01)
    rise = math.sin(math.pi*min(1,max(0,(y-145)/172)))**.68
    depth = 2.22+.38*(1-q)+(.29+.20*(1-q))*rise-.17*q*q
    brow = abs(y-(169+.89*dx))*.75
    if dx<28 and y<201:
        depth -= .075*math.exp(-(brow/1.65)**2)
    return depth


def face_plate(name,widths,depth_fn,resolution):
    keys = np.array(widths)
    ys = np.unique(np.r_[keys[:,0],np.arange(keys[0,0],keys[-1,0],1.4)])
    xs = np.linspace(-1,1,resolution)
    points,uv,faces = [],[],[]
    for side in (1,-1):
        for y in ys:
            half = np.interp(y,keys[:,0],keys[:,1])
            for frac in xs:
                dx = frac*half
                d = depth_fn(abs(dx),y,half)
                points.append(P.model_point(P.CENTER+dx,y,side*d))
                uv.append(P.front_uv(P.CENTER+dx,y))
    cols = len(xs)
    block = len(ys)*cols
    for base in (0,block):
        for row in range(len(ys)-1):
            for col in range(cols-1):
                a = base+row*cols+col
                faces.append((a,a+cols,a+cols+1,a+1))
    border = list(range(cols))+[row*cols+cols-1 for row in range(1,len(ys))]
    border += list(range(block-2,block-cols-1,-1))+[row*cols for row in range(len(ys)-2,0,-1)]
    side_uv = {}
    close_rim(faces,border,block,side_uv,uv)
    return solid(name,points,uv,faces,side_uv)


def ferrule():
    # Two turned lips, with a deep relief groove and a slight rolled rim at the grip joint.
    rings = [(364,64,1.94),(363,69,1.99),(360,71,2.02),(355,72,2.03),
             (341,72,2.03),(338,70,1.99),(336,66,1.94),(333,66,1.94),
             (331,70,1.99),(328,73,2.04),(314,73,2.04),(310,71,2.01),(308,67,1.96)]
    count = 112
    points,coords,faces = [],[],[]
    for y,rx,ry in rings:
        for i in range(count):
            angle = math.tau*i/count
            x = P.CENTER+rx*math.cos(angle)
            points.append(P.model_point(x,y,ry*math.sin(angle)))
            coords.append(P.front_uv(x,y))
    for j in range(len(rings)-1):
        for i in range(count):
            a,b = j*count+i,j*count+(i+1)%count
            faces.append((a,b,b+count,a+count))
    faces.extend([tuple(reversed(range(count))),tuple(range(len(points)-count,len(points)))])
    special={}
    for index in (len(faces)-2,len(faces)-1):
        special[index]=[(.5+.13*math.cos(math.tau*i/count),.12+.055*math.sin(math.tau*i/count)) for i in faces[index]]
    return solid('Ferrule | double turned lips',points,coords,faces,special)


for hand in ('L','R'):
    strip(hand+' | swept talon',P.TALON,hand,'talon')
    strip(hand+' | inner secondary point',P.BARB,hand,'barb')
    for course,trace in enumerate(P.VANES):
        strip(f'{hand} | mantle feather {course+1:02d}',trace,hand,'feather',course)
face_plate('Eagle | engraved mask and eye fans',P.CREST_WIDTH,crest_depth,101)
face_plate('Eagle | brow and faceted beak',P.BEAK_WIDTH,beak_depth,55)
ferrule()

# These two trimmed blade sections already carry the blade finish UVs, split
# normals and the original factory/Executioner mating surfaces respectively.
donor = HERE.parent/'RavenQuillGuard/Art/NestedV4/RavenQuillGuard.blend'
with bpy.data.libraries.load(str(donor),link=False) as (_,loaded):
    loaded.objects = ['Original blade root','Wide blade root']
regular,wide = loaded.objects
for seat in (regular,wide):
    fittings.objects.link(seat)
    seat.hide_set(False)
    seat.hide_render = False


def export(name,seat):
    bpy.ops.object.select_all(action='DESELECT')
    copies = []
    for source in [seat,*parts.objects]:
        obj = source.copy()
        obj.data = source.data.copy()
        exports.objects.link(obj)
        obj.select_set(True)
        copies.append(obj)
    result = copies[0]
    bpy.context.view_layer.objects.active = result
    bpy.ops.object.join()
    result.name = result.data.name = name
    bpy.ops.export_scene.fbx(filepath=str(ART/(name+'.fbx')),use_selection=True,
        object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=False,use_tspace=True,use_triangles=True,mesh_smooth_type='FACE',path_mode='STRIP')
    result.data.calc_loop_triangles()
    return {'triangles':len(result.data.loop_triangles),
            'slots':[m.name for m in result.data.materials]}


products = {BASE:export(BASE,regular),BASE+'_ExecutionerSeat':export(BASE+'_ExecutionerSeat',wide)}
exports.hide_viewport = exports.hide_render = True
wide.hide_set(True)
wide.hide_render = True
bpy.ops.object.select_all(action='DESELECT')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            view = area.spaces.active
            view.region_3d.view_rotation = Euler((math.pi/2,0,0)).to_quaternion()
            view.region_3d.view_location = (0,0,-.028)
            view.region_3d.view_distance = .43
            view.region_3d.view_perspective = 'ORTHO'
            view.clip_start = .0005
            view.overlay.show_overlays = False
            view.shading.type = 'MATERIAL'
# Keep the original seat textures portable, along with the new packed metal maps.
for image in bpy.data.images:
    if image.source=='FILE' and image.filepath and not image.packed_file:
        if Path(bpy.path.abspath(image.filepath)).is_file():
            image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'EagleTalonGuard.blend'),compress=True)
(ART/'exports.json').write_text(json.dumps(products,indent=2)+'\n',encoding='utf8')
