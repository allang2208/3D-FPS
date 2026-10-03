"""Look at the hand through the PKM sprint entry: original authoring vs Sprint44."""
import importlib.util
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
OUT = ROOT / 'Sprint44' / 'Review' / 'hand'
OUT.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location('elbow39_author', E39 / 'author_elbow39.py')
E = importlib.util.module_from_spec(spec)
sys.modules['elbow39_author'] = E
spec.loader.exec_module(E)

md = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
V, T = md['verts'].astype(np.float64), md['tris'].astype(np.int64)
WIDX, WVAL = md['w_idx'], md['w_val'].astype(np.float64)
V7_BONES = list(md['bones'])
AU_BONES = list(E.AU_BONES)
AU_REST_M = E.AU_REST_M
AU_INDEX = E.AU_INDEX
HOMO = np.concatenate([V, np.ones((len(V), 1))], axis=1)
HAND_BONES = {n for n in V7_BONES if n == 'hand_l' or (
    n.endswith('_l') and n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')))}
hidx = [V7_BONES.index(n) for n in HAND_BONES]
W = np.zeros((len(V), len(V7_BONES)))
for k in range(WIDX.shape[1]):
    i2, w = WIDX[:, k], WVAL[:, k]
    a = (i2 >= 0) & (w > 0)
    np.add.at(W, (np.where(a)[0], i2[a]), w[a])
HANDV = np.where(W[:, hidx].sum(axis=1) > 0.5)[0]

CASES = (('original', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
          'PKM17_base_sprint_enter'),
         ('sprint44', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_enter_Sprint44.blend',
          'PKM_sprint_enter_Sprint44'))
FRAMES = [0, 4, 8, 12, 16, 20, 26, 34, 42]


def deform(rig):
    pose = {b.name: np.array(rig.pose.bones[b.name].matrix) for b in rig.pose.bones}
    skin = np.tile(np.eye(4), (len(V7_BONES), 1, 1))
    for i, n in enumerate(V7_BONES):
        if n in pose:
            skin[i] = pose[n] @ np.linalg.inv(np.array(AU_REST_M[AU_INDEX[n]]))
    out = np.zeros_like(V)
    for k in range(WIDX.shape[1]):
        idx, w = WIDX[:, k], WVAL[:, k]
        a = (idx >= 0) & (w > 0)
        out[a] += w[a, None] * np.einsum('nij,nj->ni', skin[idx[a]], HOMO[a])[:, :3]
    return out, pose


for tag, blend, action in CASES:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    act = bpy.data.actions[action]
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.render.fps = 120
    for ob in list(bpy.data.objects):
        if ob.type == 'MESH':
            ob.hide_render = True
    me = bpy.data.meshes.new('M')
    me.from_pydata([tuple(v) for v in V], [], [tuple(t) for t in T])
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(bpy.data.materials.new('m'))
    arm = bpy.data.objects.new('M', me)
    scene.collection.objects.link(arm)
    arm.matrix_world = rig.matrix_world.copy()
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'SINGLE'
    scene.display.shading.single_color = (0.55, 0.55, 0.55)
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x, scene.render.resolution_y = 640, 640

    for f in FRAMES:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        posed, pose = deform(rig)
        arm.data.vertices.foreach_set('co', posed.ravel())
        arm.data.update()
        bpy.context.view_layer.update()
        w = rig.matrix_world @ rig.pose.bones['hand_l'].matrix.translation
        hx = np.array(rig.pose.bones['hand_l'].matrix.col[0][:3])
        hy = np.array(rig.pose.bones['hand_l'].matrix.col[1][:3])
        hz = np.array(rig.pose.bones['hand_l'].matrix.col[2][:3])
        for nm, d, up in (('a', hz, hy), ('b', -hz, hx), ('c', hx, hz)):
            cd = bpy.data.cameras.new('c%s%d' % (nm, f))
            cam = bpy.data.objects.new('c%s%d' % (nm, f), cd)
            scene.collection.objects.link(cam)
            cd.lens = 55
            loc = w + Vector(d.tolist()) * 0.22
            cam.location = loc
            cam.rotation_euler = (w + Vector(up.tolist()) * 0.01
                                  - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
            scene.camera = cam
            scene.render.filepath = str(OUT / ('%s_%s_%04d.png' % (tag, nm, f)))
            bpy.ops.render.render(write_still=True)
    print('RENDERED', tag, flush=True)
print('HAND_RENDER_DONE')