"""Author two RSH-only compact game optics and direct saddles in Blender.

Geometry is designed in the measured rail frame (+X forward, metres). Export
bakes the inverse of the existing RSH body offset, keeping the deployed mount
contract, catalog IDs and all consumers of those assets intact.
"""
import json
import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector

O = Path(__file__).resolve().parent
S = O.parent
OUT = O / 'Exports'
OUT.mkdir(parents=True, exist_ok=True)
MOUNTS = json.loads((S / 'RSH12Optics20261004/mounts.json').read_text())
FINISH = json.loads((S / 'RSH12Optics20261004/finish_reference.json').read_text())
DEST = '/Game/Weapons/RSH12/Optics20261004/Meshes/'
bpy.context.preferences.filepaths.save_version = 0
report = dict(meshes={}, variants={}, source='Original compact game-optic geometry; RSH 2_l measured rail interface', runtime_tested=False)


def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:
        ob.hide_set(False)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]


def material(name, color, metal, rough):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1.)
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Roughness'].default_value = rough
    return mat


def finish(ob, mat='Metal', bevel=.00018):
    select([ob])
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    ob.data.materials.clear()
    ob.data.materials.append(mats[mat])
    if bevel:
        mod = ob.modifiers.new('Machined edge radius', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        bpy.ops.object.modifier_apply(modifier=mod.name)
    # A physical 4 cm projection, with no reuse of a rifle body UV atlas.
    uv = ob.data.uv_layers.get('UV0') or ob.data.uv_layers.new(name='UV0')
    for face in ob.data.polygons:
        axes = [i for i in range(3) if i != max(range(3), key=lambda j: abs(face.normal[j]))]
        for li in face.loop_indices:
            p = ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv = (p[axes[0]] / .04 + .5, p[axes[1]] / .04 + .5)
    return ob


def mesh(name, verts, faces, mat='Metal', bevel=.00018):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return finish(ob, mat, bevel)


def box(name, center, size, mat='Metal', bevel=.00025):
    bpy.ops.mesh.primitive_cube_add(size=1., location=center)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    return finish(ob, mat, bevel)


def extrude(name, x0, x1, section, mat='Metal', bevel=.00018):
    n = len(section)
    verts = [(x, y, z) for x in (x0, x1) for y, z in section]
    faces = [tuple(range(n-1, -1, -1)), tuple(range(n, 2*n))]
    faces += [(i, (i+1) % n, (i+1) % n+n, i+n) for i in range(n)]
    return mesh(name, verts, faces, mat, bevel)


def cylinder(name, center, radius, depth, axis='Y', mat='Metal', count=40):
    rotation = {'Y': (math.pi/2, 0., 0.), 'X': (0., math.pi/2, 0.), 'Z': (0., 0., 0.)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=count, radius=radius, depth=depth, location=center, rotation=rotation)
    ob = bpy.context.object
    ob.name = name
    return finish(ob, mat, min(.00012, depth*.20))


def rounded_window(width, bottom, top, radius, taper=0.):
    """Counterclockwise yz loop, optionally narrowing the upper shoulders."""
    points = []
    for cy, cz, start in ((width/2-radius, top-radius, 0), (-width/2+radius, top-radius, 90),
                          (-width/2+radius, bottom+radius, 180), (width/2-radius, bottom+radius, 270)):
        for step in range(7):
            angle = math.radians(start + step*15)
            y = cy + radius*math.cos(angle)
            z = cz + radius*math.sin(angle)
            y *= 1.-taper*(z-bottom)/(top-bottom)
            points.append((y, z))
    return points


def frame(name, x0, x1, outer, inner, bevel=.00016):
    n = len(outer)
    verts = [(x, y, z) for x, loop in ((x0, outer), (x1, outer), (x0, inner), (x1, inner)) for y, z in loop]
    faces = []
    for a, b in ((0, n), (2*n, 3*n), (0, 2*n), (n, 3*n)):
        faces += [(a+i, a+(i+1) % n, b+(i+1) % n, b+i) for i in range(n)]
    ob = mesh(name, verts, faces, bevel=0.)
    ob.data.materials.append(mats['Inner'])
    for p in ob.data.polygons[n:2*n]:
        p.material_index = 1
    select([ob])
    mod = ob.modifiers.new('Window edge breaks', 'BEVEL')
    mod.width = bevel
    mod.segments = 3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob


def glass(name, x, loop):
    # One optical pane avoids accumulating several transparency layers.
    return mesh(name, [(x, y, z) for y, z in loop], [tuple(range(len(loop)-1, -1, -1))], 'Glass', 0.)


def reticle(x, z, size):
    r = size/2
    ob = mesh('Optical circle dot plane', [(x, -r, z-r), (x, -r, z+r), (x, r, z+r), (x, r, z-r)], [(0, 1, 2, 3)], 'Reticle', 0.)
    uv = ob.data.uv_layers.active
    for p in ob.data.polygons:
        for li in p.loop_indices:
            co = ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv = (co.y/size+.5, (co.z-z)/size+.5)
    return ob


def screw(name, x, sign, y, z, radius=.0014):
    obs = [cylinder(name, (x, sign*y, z), radius, .0007)]
    # A recessed dark slot rather than a raised cross welded onto the housing.
    obs.append(box(name+' slot', (x, sign*(y+.00036), z), (radius*1.3, .000035, .00030), 'Inner', .00004))
    return obs


def saddle():
    obs = [extrude('Direct low receiver plate', -.023, .023,
        [(-.0062, .00005), (.0062, .00005), (.0097, .0015), (.0095, .0024), (-.0095, .0024), (-.0097, .0015)])]
    # The underside follows the measured 2_l shoulders and its two rail slots.
    jaw = [(.0056, .00005), (.0084, -.00195), (.00715, -.00425), (.0102, -.00425), (.0102, .00135), (.0080, .00175)]
    for x in (-.0184012, .0184012):
        for sign in (-1, 1):
            obs.append(extrude('Rail shoulder clamp', x-.0037, x+.0037, [(sign*y, z) for y, z in jaw]))
            obs += screw('Rail clamp bolt', x, sign, .01055, -.0008, .00165)
        obs.append(box('Rail slot key', (x, 0, -.00205), (.00415, .0135, .0042), bevel=.00012))
    return obs


def open_optic():
    obs = [extrude('Tapered compact emitter chassis', -.0225, .0225,
        [(-.0094, .0024), (.0094, .0024), (.0125, .0054), (.0117, .0078), (-.0117, .0078), (-.0125, .0054)], bevel=.0004)]
    outer = rounded_window(.0288, .0068, .0328, .0032, .08)
    inner = rounded_window(.0242, .0100, .0291, .0025, .07)
    obs.append(frame('Open compact window frame', .0088, .0138, outer, inner))
    obs.append(glass('Recessed clear front window', .0117, inner))
    obs.append(reticle(.01145, .01955, .0062))
    # Short triangular roots visually carry the frame into the chassis.
    for sign in (-1, 1):
        section = [(sign*.0087, .0042), (sign*.0135, .0061), (sign*.0130, .0133), (sign*.0105, .014)]
        obs.append(extrude('Window foot', .0065, .0160, section, bevel=.00025))
        obs += screw('Window foot fastener', .0110, sign, .0135, .0078, .0010)
    obs.append(box('Emitter recess', (-.0157, 0, .00783), (.007, .0052, .00012), 'Inner', .00055))
    obs.append(box('Emitter lens', (-.0154, 0, .00794), (.0021, .0028, .00008), 'Glass', .00030))
    # Low side-loaded battery drawer, no long rifle battery box.
    obs.append(box('Battery drawer seam', (-.005, -.01175, .0057), (.0126, .00020, .0037), 'Inner', .00025))
    obs.append(box('Flush battery drawer', (-.005, -.01192, .0057), (.0118, .00032, .0031), bevel=.0002))
    for x in (-.014, -.0085):
        obs.append(box('Brightness button', (x, .01212, .0062), (.0039, .0007, .0025), 'Inner', .0005))
    for x in (-.0165, .019):
        for sign in (-1, 1):
            obs.append(cylinder('Chassis fastening well', (x, sign*.007, .0079), .00135, .00022, 'Z', 'Inner', 24))
            obs.append(cylinder('Recessed chassis screw', (x, sign*.007, .00804), .00092, .00016, 'Z', count=12))
    return obs, (.01145, 0., .01955), dict(style='Open compact window with short integrated feet', window_m=[.0242, .0191], reticle_plane_m=.0062)


def closed_optic():
    obs = [extrude('Compact sealed electronics deck', -.023, .023,
        [(-.0094, .0024), (.0094, .0024), (.0148, .0057), (.0141, .0080), (-.0141, .0080), (-.0148, .0057)], bevel=.00045)]
    outer = rounded_window(.0304, .0058, .0337, .0036, .025)
    inner = rounded_window(.0250, .0094, .0300, .0028, .018)
    obs.append(frame('Short protected optical housing', -.0185, .0195, outer, inner, .00023))
    # Separate thin protective eyebrows make a stepped silhouette, not a solid box.
    hood_outer = rounded_window(.0320, .0057, .0350, .0042, .025)
    hood_inner = rounded_window(.0306, .0062, .03385, .0037, .025)
    for a, b in ((-.0202, -.0169), (.0183, .0218)):
        obs.append(frame('Protective window rim', a, b, hood_outer, hood_inner, .00014))
    obs.append(glass('Protected clear window', -.0158, inner))
    obs.append(reticle(-.0160, .0197, .0064))
    # Side plate, low controls and a compact cap retain an enclosed-sight identity.
    obs.append(box('Side access gasket', (.001, -.0150, .017), (.021, .00035, .009), 'Inner', .0010))
    obs.append(box('Side access panel', (.001, -.01528, .017), (.0201, .00035, .0082), bevel=.0008))
    for x in (-.007, .0085):
        obs += screw('Side panel screw', x, -1, .0156, .017, .00105)
    obs.append(cylinder('Battery cap seal', (.0075, .015, .0174), .0048, .00055, mat='Inner'))
    obs.append(cylinder('Compact battery cap', (.0075, .0157, .0174), .00445, .0010))
    obs.append(box('Battery cap tool slot', (.0075, .01622, .0174), (.0049, .000025, .00055), 'Inner', .00010))
    for x in (-.012, -.0064):
        obs.append(box('Brightness button', (x, .0152, .0117), (.004, .00065, .0032), 'Inner', .00055))
    return obs, (-.016, 0., .0197), dict(style='Short enclosed window with thin protective rims', window_m=[.025, .0206], reticle_plane_m=.0064)


def export(key, obs, offset):
    for ob in obs:
        ob.data.transform(Matrix.Translation(-offset))
        select([ob])
        tri = ob.modifiers.new('Export tangent triangles', 'TRIANGULATE')
        bpy.ops.object.modifier_apply(modifier=tri.name)
        ob.data.update()
    name = 'SM_RSH12_' + key
    path = OUT / (name+'.fbx')
    select(obs)
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH'},
        axis_forward='-Y', axis_up='Z', bake_anim=False, mesh_smooth_type='FACE', use_tspace=True)
    verts = [v.co for ob in obs for v in ob.data.vertices]
    spec = dict(asset=DEST+name, fbx=str(path), triangles=sum(len(ob.data.polygons) for ob in obs),
        authored_bounds_m=[[min(v[i]+offset[i] for v in verts) for i in range(3)], [max(v[i]+offset[i] for v in verts) for i in range(3)]],
        baked_runtime_offset_m=list(offset), materials=sorted({m.name for ob in obs for m in ob.data.materials}))
    report['meshes'][key] = spec
    return spec


for key, author in (('holographic', open_optic), ('eoth_holographic', closed_optic)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = {
        'Metal': material('RSH_CompactMetal', FINISH['base_color'], FINISH['metallic'][0], FINISH['roughness'][0]),
        'Inner': material('RSH_CompactInner', (.005, .0055, .006), 0., .87),
        'Glass': material('RSH_CompactGlass', (.12, .17, .19), 0., .12),
        'Reticle': material('RSH_CompactReticle', (1., .015, .006), 0., .5),
    }
    body, center, design = author()
    rails = saddle()
    offset = Vector(MOUNTS['parts'][key]['body_offset_cm']) / 100
    spec = export(key, body, offset)
    aim = Vector(center)-offset
    def ue(p):
        return [p.x*100, -p.y*100, p.z*100]
    spec['sockets_cm'] = {'AimCenter': ue(aim), 'SightRear': ue(aim), 'SightFront': ue(aim+Vector((.10, 0, 0))), 'SightUp': ue(aim+Vector((0, 0, .01)))}
    export('Rail_'+key, rails, Vector((0, 0, 0)))
    report['variants'][key] = dict(**design, direct_seat_height_m=.0024, rail_width_m=MOUNTS['rail_shoulder_width_m'],
        aim_in_rail_frame_m=list(center), id_and_runtime_mount_unchanged=True)
    # Save an assembled, fully editable rail-frame source; FBXs retain their own pivots.
    for ob in body:
        ob.location = offset
    select(body+rails)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(key+'_Editable.blend')))
    print('RSH_COMPACT_OPTIC_AUTHORED', key, flush=True)

(O/'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf8')
