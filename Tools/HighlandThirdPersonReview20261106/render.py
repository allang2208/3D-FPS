"""Render current UE render-buffer skin driven by the final native poses."""
from pathlib import Path
import json, sys
import bpy
import numpy as np
from mathutils import Vector, Quaternion

ROOT = Path('D:/FPS3D/FPSGAME/Saved/HighlandThirdPersonReview20261106/native-v3')
arg = sys.argv[sys.argv.index('--') + 1:]
if len(arg)>3:ROOT=Path(arg[3])
kind, case = arg[:2]
mode = arg[2] if len(arg) > 2 else 'keys'
folder = ROOT / kind / case
meta = json.loads((ROOT / kind / 'mesh.json').read_text(encoding='utf-8-sig'))
motion = json.loads((folder / 'motion.json').read_text(encoding='utf-8-sig'))
names = meta['names']
poses = np.fromfile(folder / 'poses.bin', np.float32).reshape(-1, len(names), 10)
convert = np.array([-.01, .01, .01])

def mats(v):
    result = np.tile(np.eye(4), (len(v), 1, 1))
    for i, p in enumerate(v):
        result[i, :3, :3] = np.array(Quaternion((p[6], *p[3:6])).to_matrix()) * p[7:10]
        result[i, :3, 3] = p[:3]
    return result

rest_inv = np.linalg.inv(mats(np.array(meta['rest'])))
bind = np.fromfile(ROOT / kind / 'skin.bind', np.float32).reshape(-1, 3)
bones = np.fromfile(ROOT / kind / 'skin.bones', np.uint16).reshape(len(bind), -1)
weights = np.fromfile(ROOT / kind / 'skin.weights', np.float32).reshape(bones.shape)
weights /= weights.sum(axis=1, keepdims=True).clip(1e-9)
faces = np.fromfile(ROOT / kind / 'skin.indices', np.uint32).reshape(-1, 3)[:, ::-1]
groups = []
for b in np.unique(bones):
    vi, wi = np.where((bones == b) & (weights > 0))
    groups.append((b, vi, weights[vi, wi, None]))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def mesh(name, vertices, triangles, color):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices.tolist(), [], triangles.tolist())
    data.update()
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.color = color
    for p in data.polygons:
        p.use_smooth = True
    return obj

body = mesh('Actual UE body skin', bind * convert, faces, (.46, .52, .61, 1))
blade = 'highland_broadblade' if case.endswith('sweep') else 'highland_ridge_piercer'
grip = 'long_twohand' if case.startswith('LongGrip') else 'factory'
part_specs = json.loads((ROOT / 'parts.json').read_text())[blade + '/' + grip]
parts = []
for spec in part_specs:
    before = set(scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(ROOT / 'parts' / spec['file']), use_anim=False)
    imported = set(scene.objects) - before
    for obj in imported:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        verts = np.array([list(obj.matrix_world @ v.co) for v in obj.data.vertices]) * 100
        verts = verts * spec['scale'] + spec['location']
        triangles = np.array([list(t.vertices) for t in obj.data.loop_triangles], dtype=int)[:, ::-1]
        color = (.20, .55, .72, 1) if spec['slot'] == 'blade_1' else (.32, .23, .12, 1)
        proxy = mesh(spec['slot'], verts * convert, triangles, color)
        parts.append((proxy, verts))
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)

for x in range(-4, 5):
    for y in range(-3, 6):
        v = np.array([[x, y, 0], [x+1, y, 0], [x+1, y+1, 0], [x, y+1, 0]]) * .4
        mesh('floor', v, np.array([[0, 1, 2], [0, 2, 3]]), (.16, .18, .21, 1) if (x+y)%2 else (.22, .25, .28, 1))
scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading
sh.light = 'STUDIO'
sh.color_type = 'OBJECT'
sh.show_cavity = True
sh.show_shadows = True
sh.background_type = 'WORLD'
scene.world = bpy.data.worlds.new('Review')
scene.world.color = (.055, .065, .08)
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
cam_data = bpy.data.cameras.new('Review camera')
cam = bpy.data.objects.new('Review camera', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 2.35
cam_data.lens = 45
mount = mats(np.array([motion['mount']]))[0]
render = folder / ('render-' + mode)
render.mkdir(exist_ok=True)
if mode == 'all':
    indices = list(range(len(poses)))
else:
    pre = motion['lead_seconds']
    attack = motion['attack_seconds']
    times = [0, pre*.4, pre*.85, pre, pre+.033, pre+.067, pre+.2, pre+.367,
             pre+attack*.65, pre+attack*.9, pre+attack, pre+attack+.15, pre+attack+.35]
    if motion['role']=='RidgeThrust':times += [1/3,.4,.6,.7]
    indices = sorted(set(min(len(poses)-1, max(0, round(t*30))) for t in times))
for fi in indices:
    p = mats(poses[fi])
    skin = p @ rest_inv
    vertices = np.zeros_like(bind)
    for bi, vi, w in groups:
        m = skin[bi]
        # Render-buffer influences can contain duplicate bones; accumulate them.
        np.add.at(vertices, vi, (bind[vi] @ m[:3, :3].T + m[:3, 3]) * w)
    body.data.vertices.foreach_set('co', (vertices * convert).ravel())
    body.data.update()
    frame = motion['frames'][fi]
    correction = np.eye(4)
    correction[:3, :3] = np.array(Quaternion((0, 0, 1), -np.deg2rad(frame['roll'])).to_matrix())
    correction[2, 3] = -frame['slide']
    weapon = p[names.index('hand_r')] @ mount @ correction
    for obj, v in parts:
        obj.data.vertices.foreach_set('co', ((v @ weapon[:3, :3].T + weapon[:3, 3]) * convert).ravel())
        obj.data.update()
    targets = [('front', (2.4, 4.0, 1.8), (0, .12, .95), 2.35),
               ('back', (-2.8, -3.6, 2.1), (0, .12, 1.1), 2.2)]
    if mode == 'wrists':
        center = (p[names.index('hand_r'), :3, 3] + p[names.index('hand_l'), :3, 3])*.5*convert
        targets = [(n, center + np.array(offset), center, .78) for n, offset in
                   [('front', (1.4, 2.4, 1.0)), ('back', (-1.6, -2, 1))]]
    for label, location, target, scale in targets:
        cam.location = location
        cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam_data.ortho_scale = scale
        scene.render.filepath = str(render / f'{fi:04d}-{label}.png')
        bpy.ops.render.render(write_still=True)
(render / 'frames.json').write_text(json.dumps(indices))
print('NATIVE_SKIN_RENDERED', kind, case, mode, len(indices))
