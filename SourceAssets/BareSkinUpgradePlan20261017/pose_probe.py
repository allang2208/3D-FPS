"""Read-only Blender probe: how does the accepted M4 V8 bare arm deform at the elbow and wrist?

Opens Editable/M4_BareArmsV7.blend without saving, applies synthetic left-arm poses about
anatomical axes derived from the bones, measures forearm cross-sections and renders
Workbench views. Run: blender -b -P pose_probe.py
"""
import bpy, json, math
from mathutils import Matrix, Vector
from pathlib import Path

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinUpgradePlan20261017/Probe'); OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/M4_BareArmsV7.blend')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
for o in bpy.data.objects:
    o.hide_render = o not in (arm, mesh)
pb = arm.pose.bones; M = arm.matrix_world


def head(n): return M @ pb[n].head


def rotate(name, axis, deg):
    p = pb[name]; Mi = M.inverted(); h = p.head.copy()
    a = (Mi.to_3x3() @ axis).normalized()
    p.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, a) @ Matrix.Translation(-h) @ p.matrix
    bpy.context.view_layer.update()


def reset():
    for p in pb: p.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def frame():
    S, E, W = head('upperarm_l'), head('lowerarm_l'), head('hand_l')
    up, fore = (E - S).normalized(), (W - E).normalized()
    hinge = up.cross(fore).normalized()
    radial = (head('index_metacarpal_l') - head('pinky_metacarpal_l')).normalized()
    palm = fore.cross(radial).normalized()
    return S, E, W, up, fore, hinge, radial, palm


def sections(tag):
    dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); me = ev.to_mesh()
    Mw = mesh.matrix_world; S, E, W, up, fore, *_ = frame(); L = (W - E).length
    verts = [Mw @ v.co for v in me.vertices]; rows = []
    for t in (.15, .35, .55, .75, .9, .97):
        c = E + fore * (L * t); seg = []
        for e in me.edges:
            a, b = verts[e.vertices[0]], verts[e.vertices[1]]; da, db = (a - c).dot(fore), (b - c).dot(fore)
            if (da < 0) != (db < 0):
                p = a + (b - a) * (da / (da - db))
                if (p - c).length < L * .3: seg.append(p)
        if len(seg) < 8: continue
        ctr = sum(seg, Vector()) / len(seg); seg.sort(key=lambda p: math.atan2((p - ctr).dot(fore.orthogonal()), (p - ctr).dot(fore.cross(fore.orthogonal()))))
        per = sum((seg[i] - seg[i - 1]).length for i in range(len(seg)))
        rows.append(dict(t=t, perimeter=round(per * (100 if L < 2 else 1), 2)))
    ev.to_mesh_clear(); return rows


scene = bpy.context.scene; scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading; sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (.78, .58, .48)
sh.show_cavity = True; sh.cavity_type = 'BOTH'; sh.cavity_ridge_factor = 1.0; sh.cavity_valley_factor = 1.0
sh.show_specular_highlight = True; scene.render.resolution_x, scene.render.resolution_y = 720, 540
scene.render.film_transparent = False; scene.world = scene.world or bpy.data.worlds.new('w')
cam_data = bpy.data.cameras.new('probe'); cam = bpy.data.objects.new('probe', cam_data); scene.collection.objects.link(cam); scene.camera = cam


def shoot(name, target, direction, dist):
    cam.location = target + direction.normalized() * dist
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam_data.lens = 50; cam_data.clip_start = dist * .01; cam_data.clip_end = dist * 20
    scene.render.filepath = str(OUT / (name + '.png')); bpy.ops.render.render(write_still=True)


S, E, W, up, fore, hinge, radial, palm = frame(); L = (W - E).length; unit = 100 if L < 2 else 1
poses = {
    'rest': [],
    'elbow_flex_plus50': [('lowerarm_l', hinge, 50)],
    'wrist_flex_50': [('hand_l', radial, 50)],
    'wrist_ext_50': [('hand_l', radial, -50)],
    'wrist_ulnar_25': [('hand_l', palm, 25)],
    'pronate_70_hand_only': [('hand_l', fore, 70)],
    'pronate_70_twist_split': [('lowerarm_twist_02_l', fore, 23), ('lowerarm_twist_01_l', fore, 46), ('hand_l', fore, 70)],
}
report = {}
for name, ops in poses.items():
    reset()
    for b, axis, deg in ops:
        if b in pb: rotate(b, axis, deg)
    S2, E2, W2, up2, fore2, hinge2, radial2, palm2 = frame()
    report[name] = dict(sections=sections(name))
    side = hinge2 if name.startswith('elbow') or name == 'rest' else radial2
    shoot(name + '_elbow', E2, -hinge2 * 1 + up2 * .2, L * 1.25)
    shoot(name + '_wrist_dorsal', W2 - fore2 * L * .12, -palm2, L * .75)
    shoot(name + '_wrist_side', W2 - fore2 * L * .12, radial2, L * .75)
reset()
report['scale_to_cm'] = unit; report['forearm_length'] = L * unit
(OUT / 'pose_probe.json').write_text(json.dumps(report, indent=1))
print('POSE_PROBE_DONE', json.dumps(report))
