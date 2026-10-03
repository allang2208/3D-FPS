"""Measure the left hand / magazine grip on the current M4 and M16 insertion sources.

Reports, per frame:
  * grip transform G = inverse(hand_l) @ magazine socket  (rig world space)
  * mesh contact: palm gap, per-digit gap, magazine penetration into the hand
  * a fixed palm/side source view for qualitative comparison
No file is written outside this directory.
"""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
DIGITS = ['thumb', 'index', 'middle', 'ring', 'pinky']
HANDGROUPS = [d + s for d in DIGITS for s in ('_01_l', '_02_l', '_03_l', '_metacarpal_l')] + ['hand_l']

def smooth(a, b, x):
    t = max(0., min(1., (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def world_bones(rig):
    W = rig.matrix_world
    return {b.name: W @ b.matrix for b in rig.pose.bones}

def eval_world(obj, dg):
    e = obj.evaluated_get(dg)
    me = e.to_mesh()
    M = e.matrix_world
    verts = [M @ v.co for v in me.vertices]
    polys = [list(p.vertices) for p in me.polygons]
    e.to_mesh_clear()
    return verts, polys

def dominant(groups, v):
    best, w = None, 0.0
    for g, x in v.groups.items():
        if x.weight > w:
            best, w = groups[g], x.weight
    return best

def nearest_report(points, tree):
    out = []
    for p in points:
        loc, nor, idx, dist = tree.find_nearest(p)
        if loc is None:
            out.append((dist, 0.0))
            continue
        inside = (p - loc).dot(nor) < 0
        out.append((dist, -dist if inside else dist))
    return out

def measure(label, path, action, frames, mag_source, mag_object, mag_groups, cam_frames):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    rig = bpy.data.objects['SK_M4_Infima']
    if action:
        a = bpy.data.actions[action]
        rig.animation_data.action = a; rig.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    groups = [g.name for g in arms.vertex_groups]
    rest_socket = rig.matrix_world @ rig.data.bones['WPN_SOCKET_Magazine'].matrix_local
    if mag_source is not None:
        with bpy.data.libraries.load(str(mag_source), link=False) as (src, dst):
            dst.objects = [mag_object]
        mag = dst.objects[0]
        bpy.context.scene.collection.objects.link(mag)
        mag_rest = mag.matrix_world.copy()
    else:
        mag = bpy.data.objects[mag_object]
        mag_rest = None
    result = {'file': str(path), 'action': rig.animation_data.action.name, 'frames': {}}
    dg = bpy.context.evaluated_depsgraph_get()
    for f in frames:
        bpy.context.scene.frame_set(int(f), subframe=f % 1)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        B = world_bones(rig)
        socket = B['WPN_SOCKET_Magazine']
        if mag_rest is not None:
            mag.matrix_world = socket @ rest_socket.inverted() @ mag_rest
        magverts, magpolys = eval_world(mag, dg)
        armverts, armpolys = eval_world(arms, dg)
        magtree = BVHTree.FromPolygons(magverts, magpolys, all_triangles=False)
        armtree = BVHTree.FromPolygons(armverts, armpolys, all_triangles=False)
        # palm / per-digit arm surface subsets
        e = arms.evaluated_get(dg); me = e.to_mesh()
        owner = [dominant(groups, v) for v in me.vertices]
        e.to_mesh_clear()
        subsets = {}
        for name in ['hand_l'] + [d + '_l' for d in DIGITS]:
            idx = [i for i, o in enumerate(owner) if o and (o == name or (name != 'hand_l' and o.startswith(name[:-2])))]
            if idx:
                subsets[name] = [armverts[i] for i in idx]
        contact = {}
        for name, pts in subsets.items():
            d = nearest_report(pts, magtree)
            signed = sorted(x[1] * 1000 for x in d)
            contact[name] = {'n': len(pts), 'min_mm': round(signed[0], 3),
                             'p05_mm': round(signed[len(signed) // 20], 3),
                             'median_mm': round(signed[len(signed) // 2], 3)}
        mag_to_arm = nearest_report(magverts[::3], armtree)
        pen = sorted(x[1] * 1000 for x in mag_to_arm)
        gm = socket.inverted() @ B['hand_l']
        result['frames'][str(f)] = {
            'grip_transform': [list(r) for r in gm],
            'grip_translation_mm': [round(x * 1000, 3) for x in gm.translation],
            'grip_rotation_deg': round(math.degrees(gm.to_quaternion().angle), 3),
            'hand_world': [round(x * 1000, 2) for x in B['hand_l'].translation],
            'mag_world': [round(x * 1000, 2) for x in socket.translation],
            'palm_gap_mm': contact.get('hand_l'),
            'digit_gap_mm': {k: v for k, v in contact.items() if k != 'hand_l'},
            'mag_into_hand_mm': {'min': round(pen[0], 3), 'max': round(pen[-1], 3),
                                 'penetrating_verts': sum(1 for x in pen if x < -0.001)},
            'arm_min_gap_mm': round(sum(x[0] * 1000 for x in mag_to_arm) / len(mag_to_arm), 3),
        }
        if f in cam_frames:
            render_view(label, arms, mag, B, f)
    return result

def render_view(label, arms, mag, B, f):
    s = bpy.context.scene
    c = bpy.data.objects.get('GripCamera')
    if c is None:
        c = bpy.data.objects.new('GripCamera', bpy.data.cameras.new('GripCamera'))
        s.collection.objects.link(c); s.camera = c; c.data.type = 'ORTHO'; c.data.ortho_scale = .26
    for o in s.objects:
        if o.type == 'MESH':
            vis = o.name in (arms.name, mag.name, 'M16A2_Magazine', 'M4_Magazine Light.003_Export')
            o.hide_render = not vis
            if o.name in bpy.context.view_layer.objects:
                o.hide_set(not vis)
    arms.color = (.22, .40, .57, 1); mag.color = (.73, .47, .13, 1)
    if not s.world:
        s.world = bpy.data.worlds.new('GripWorld')
    s.world.color = (.10, .10, .10)
    s.render.engine = 'BLENDER_WORKBENCH'; s.display.shading.light = 'STUDIO'
    s.display.shading.color_type = 'OBJECT'; s.display.shading.show_cavity = True
    s.display.shading.background_type = 'WORLD'
    s.render.resolution_x = 640; s.render.resolution_y = 640; s.render.resolution_percentage = 100
    s.render.use_compositing = False; s.render.use_sequencer = False
    p = {n: B[n].translation for n in ['hand_l', 'index_01_l', 'pinky_01_l', 'middle_02_l']}
    normal = (p['index_01_l'] - p['hand_l']).cross(p['pinky_01_l'] - p['hand_l']).normalized()
    center = (p['hand_l'] + p['middle_02_l']) / 2
    for sign, view in [(1, 'palm'), (-1, 'back'), (0, 'front')]:
        if view == 'front':
            c.location = center + Vector((0, 0, .30))
        else:
            c.location = center + normal * .30 * sign
        c.rotation_euler = (center - c.location).to_track_quat('-Z', 'Y').to_euler()
        s.render.filepath = str(O / f'{label}_{int(f)}_{view}.png')
        bpy.ops.render.render(write_still=True)

M4EXT = S / 'ExtMagPattern20260919/M4_ExtMag_Editable.blend'
report = {}
report['m4_reload'] = measure('m4_reload', S / 'ExtMagContact20260919/A_M4_ExtContact_reload.blend', None,
                              [43, 54, 61, 68, 76, 88, 95, 103, 108], M4EXT, 'SM_ExtMag_M440', True, [61, 76, 95])
report['m16_reload'] = measure('m16_reload', S / 'M16RemovalMelee20260920/Animations/base/A_M16_reload.blend', None,
                               [43, 54, 61, 68, 76, 88, 95, 103, 108], None, 'M16A2_Magazine', True, [61, 76, 95])
(O / 'measure_grip.json').write_text(json.dumps(report, indent=2))
print('MEASURE_OK', flush=True)