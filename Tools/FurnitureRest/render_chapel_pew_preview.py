"""Render saved UE skin poses at the actual chapel slot; never alter motion."""
import json
import math
import os
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector

ROOT = Path(os.environ.get('CHAPEL_PREVIEW_ROOT', 'D:/FPS3D/FPSGAME/SourceAssets/ChapelFurniture20261116/PreviewR1'))
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
manifest = read(ROOT / 'manifest.json')
profile = manifest['profile']
slot = profile['slots'][1]
scale = np.asarray(profile['scale'])
anchor = np.asarray(slot['seat']) * scale
anchor[2] -= manifest['type']['surface_height']
angle = math.radians(slot['yaw'] - 90)
turn = np.array([[math.cos(angle), -math.sin(angle), 0], [math.sin(angle), math.cos(angle), 0], [0, 0, 1]])
reflect = np.array([1, -1, 1]) / 100
pew = read(ROOT / 'pew.json')
still = '--stills' in sys.argv


def matrices(values):
    values = np.asarray(values)
    x, y, z, w = values[:, 3:7].T
    result = np.tile(np.eye(4), (len(values), 1, 1))
    result[:, :3, :3] = np.stack([
        1 - 2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w),
        2*(x*y+z*w), 1 - 2*(x*x+z*z), 2*(y*z-x*w),
        2*(x*z-y*w), 2*(y*z+x*w), 1 - 2*(x*x+y*y)], axis=1).reshape(-1, 3, 3) * values[:, None, 7:]
    result[:, :3, 3] = values[:, :3]
    return result


def prepare_skin(geo, names):
    indices = {n: i for i, n in enumerate(names)}
    points = np.asarray(geo['positions'])
    binds = matrices([b['bind'] for b in geo['bones']])
    mapped = []
    for i, bone in enumerate(geo['bones']):
        while geo['bones'][i]['name'] not in indices:
            i = geo['bones'][i]['parent']
            if i < 0:
                raise RuntimeError('Head/body ancestor missing: ' + bone['name'])
        mapped.append(i)
    rows = {}
    for v, weights in enumerate(geo['weights']):
        combined = {}
        for bone, weight in weights:
            index = mapped[bone]
            combined[index] = combined.get(index, 0.) + weight
        for bone, weight in combined.items():
            rows.setdefault(bone, []).append((v, weight))
    groups = [(indices[geo['bones'][b]['name']], np.linalg.inv(binds[b]),
               np.asarray(v)[:, 0].astype(int), np.asarray(v)[:, 1, None]) for b, v in rows.items()]

    def skin(world):
        result = np.zeros_like(points)
        for index, inverse, ids, weights in groups:
            m = world[index] @ inverse
            result[ids] += (points[ids] @ m[:3, :3].T + m[:3, 3]) * weights
        return (result @ turn.T + anchor) * reflect
    return skin


def make_mesh(name, points, triangles, color, smooth=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(np.asarray(points).tolist(), [], np.asarray(triangles, dtype=int)[:, ::-1].tolist())
    data.update()
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    ob.color = (*color, 1)
    for face in data.polygons:
        face.use_smooth = smooth
    return ob


def update(ob, values):
    ob.data.vertices.foreach_set('co', np.ascontiguousarray(values).ravel())
    ob.data.update()


def point_at(camera, target, delta, ortho):
    target = Vector(target)
    camera.location = target + Vector(delta)
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = ortho


for variant, color in (('default', (.19, .49, .72)), ('kaitlin', (.74, .38, .22))):
    folder = ROOT / variant
    rig = read(folder / 'saved_poses.json')
    body = read(folder / 'body.json')
    head = read(folder / 'head.json')
    skin_body, skin_head = prepare_skin(body, rig['names']), prepare_skin(head, rig['names'])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 640
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 15
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'OBJECT'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.display.shading.curvature_ridge_factor = 1.15
    scene.display.shading.curvature_valley_factor = 1.1
    scene.display.shading.background_type = 'WORLD'
    scene.world = bpy.data.worlds.new('Neutral contact studio')
    scene.world.color = (.045, .055, .07)
    scene.display.render_aa = '8'
    scene.view_settings.view_transform = 'Standard'
    init = matrices(rig['clips']['Idle']['world'][18])
    body_ob = make_mesh('Native saved body', skin_body(init), body['triangles'], color)
    head_ob = make_mesh('Native neutral head', skin_head(init), head['triangles'], color)
    p = np.asarray(pew['positions']) * scale * reflect
    bench = make_mesh('Actual full pew', p, pew['triangles'], (.48, .33, .18))
    cutaway = make_mesh('Near-side cutaway of the same pew', p, pew['triangles'], (.48, .33, .18))
    bm = bmesh.new()
    bm.from_mesh(cutaway.data)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                          plane_co=(0, -.36, 0), plane_no=(0, 1, 0),
                          clear_inner=True, clear_outer=False)
    bm.to_mesh(cutaway.data)
    bm.free()
    cutaway.hide_render = True
    bpy.ops.mesh.primitive_plane_add(size=20)
    floor = bpy.context.object
    floor.name = 'Floor Z=0'
    floor.color = (.21, .23, .26, 1)
    for axis in (0, 1):
        for v in np.arange(-2, 2.01, .25):
            corners = np.array([[-2, v-.0006, .0003], [2, v-.0006, .0003], [2, v+.0006, .0003], [-2, v+.0006, .0003]])
            if axis:
                corners = corners[:, [1, 0, 2]]
            make_mesh('25 cm floor guide', corners, [[0, 2, 1], [0, 3, 2]], (.29, .31, .34), False)
    camera_data = bpy.data.cameras.new('Contact view')
    camera = bpy.data.objects.new('Contact view', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    camera_data.lens = 50
    views = {
        'overview': ((-.20, 0, .91), (-3.8, -3.7, 1.8), 2.8, False),
        'side': ((-.35, 0, .95), (0, -4, .20), 2.08, True),
        'seat': ((-.10, 0, .62), (0, -3, .08), .66, True),
        'feet': ((-.48, 0, .13), (-3, -2, .50), .68, True),
        'palms': ((-.20, 0, .76), (-2.8, -1.4, 3), .72, True),
    }
    if os.environ.get('CHAPEL_PREVIEW_HANDS') == '1':
        views['side'] = ((-.45, 0, .98), (-3.2, -2.4, 2.1), 1.55, True)

    def draw(view, path):
        target, delta, ortho, cut = views[view]
        bench.hide_render = cut
        cutaway.hide_render = not cut
        point_at(camera, target, delta, ortho)
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    if still:
        for view in views:
            draw(view, folder / (view + '.png'))
        print('CHAPEL_CONTACT_STILLS', variant, flush=True)
        if '--motion' not in sys.argv:
            continue
    timeline = []
    for phase in ('Enter', 'Idle', 'Exit'):
        duration = rig['clips'][phase]['duration'] if phase != 'Idle' else 1.6
        timeline.extend((phase, float(t)) for t in np.arange(0, duration, 1/15))
    timeline += [('Exit', rig['clips']['Exit']['duration'])] * 7
    if '--keyframes' in sys.argv:
        timeline = [('Enter', 0.), ('Enter', .6), ('Enter', 1.13), ('Enter', 1.7), ('Enter', 2.33),
                    ('Idle', .6), ('Exit', .4), ('Exit', 1.), ('Exit', 1.7), ('Exit', 2.43), ('Exit', 3.1)]
    for view in ('overview', 'side'):
        (folder / view).mkdir(exist_ok=True)
    for i, (phase, t) in enumerate(timeline):
        take = rig['clips'][phase]
        pose = matrices(take['world'][min(round(t * take['rate']), len(take['world']) - 1)])
        update(body_ob, skin_body(pose))
        update(head_ob, skin_head(pose))
        for view in ('overview', 'side'):
            draw(view, folder / view / f'{i:04d}.png')
        if i % 15 == 0:
            print('CHAPEL_PREVIEW_FRAME', variant, i, len(timeline), flush=True)
    (folder / 'timeline.json').write_text(json.dumps(timeline), encoding='utf-8')
    print('CHAPEL_PREVIEW_RENDERED', variant, len(timeline), flush=True)
