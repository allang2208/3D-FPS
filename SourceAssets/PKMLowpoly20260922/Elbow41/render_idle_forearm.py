"""Close-up of the shipped PKM idle arms, left against right.

The right arm is the control: same mesh, same clip, same lighting.  Anything
that shows on the left and not on the right is a left-arm (weights / bone /
pose) problem rather than a modelling one.
"""
import json
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Elbow41'
OUT = HERE / 'Review' / 'idle_forearm'

BLEND = E39 / 'Edit' / 'PKM_idle_Elbow39.blend'
ACTION = 'PKM_idle_Elbow39'
WHICH = (('shipped', BLEND, ACTION, 60, [0, 30, 60]),
         ('prefix', ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
          'PKM_Game_idle_Wrist12', 60, [0, 30, 60]))

mesh_data = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
author = np.load(E39 / 'author_rig.npz', allow_pickle=True)
V7_VERTS = mesh_data['verts'].astype(np.float64)
V7_TRIS = mesh_data['tris'].astype(np.int64)
V7_WIDX = mesh_data['w_idx']
V7_WVAL = mesh_data['w_val'].astype(np.float64)
V7_BONES = list(mesh_data['bones'])
AU_BONES = list(author['bones'])
AU_REST = author['rest'].astype(np.float64)
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
N_V7, N_AU = len(V7_BONES), len(AU_BONES)
MAP = np.array([AU_INDEX.get(n, -1) for n in V7_BONES])
HOMO = np.concatenate([V7_VERTS, np.ones((len(V7_VERTS), 1))], axis=1)


def deform(rig):
    pose = np.zeros((N_AU, 4, 4))
    for i, name in enumerate(AU_BONES):
        pose[i] = np.array(rig.pose.bones[name].matrix)
    delta = pose @ np.linalg.inv(AU_REST)
    skin = np.tile(np.eye(4), (N_V7, 1, 1))
    m = MAP >= 0
    skin[m] = delta[MAP[m]]
    out = np.zeros_like(V7_VERTS)
    for k in range(V7_WIDX.shape[1]):
        idx, w = V7_WIDX[:, k], V7_WVAL[:, k]
        act = (idx >= 0) & (w > 0.0)
        out[act] += w[act, None] * np.einsum('nij,nj->ni', skin[idx[act]],
                                             HOMO[act])[:, :3]
    return out


def camera_at(scene, name, loc, target, lens):
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    data.lens = lens
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return cam


summary = {}
for tag, blend, action_name, fps, frames in WHICH:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.render.fps = fps
    for ob in bpy.data.objects:
        ob.hide_render = not (ob.type == 'MESH' and 'PKM' in ob.name
                              and 'Belt' not in ob.name and 'Round' not in ob.name)

    me = bpy.data.meshes.new('Arm')
    me.from_pydata([tuple(v) for v in V7_VERTS], [], [tuple(t) for t in V7_TRIS])
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(bpy.data.materials.new('ArmMat'))
    arm = bpy.data.objects.new('Arm', me)
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
    scene.render.resolution_x, scene.render.resolution_y = 820, 820

    folder = OUT / tag
    folder.mkdir(parents=True, exist_ok=True)

    scene.frame_set(frames[0])
    bpy.context.view_layer.update()
    world = rig.matrix_world

    for side in ('l', 'r'):
        elbow = world @ rig.pose.bones['lowerarm_%s' % side].matrix.translation
        shoulder = world @ rig.pose.bones['upperarm_%s' % side].matrix.translation
        wrist = world @ rig.pose.bones['hand_%s' % side].matrix.translation
        fore = (wrist - elbow).normalized()
        upper = (elbow - shoulder).normalized()
        bend_axis = fore.cross(upper).normalized()
        out_dir = -(fore + upper).normalized()
        mid = (elbow + wrist) * 0.5
        cams = {
            'outer': camera_at(scene, 'O' + side, mid + out_dir * 0.30 + bend_axis * 0.06,
                               mid, 50),
            'inner': camera_at(scene, 'I' + side, mid - out_dir * 0.30 - bend_axis * 0.06,
                               mid, 50),
            'profile': camera_at(scene, 'P' + side, mid + bend_axis * 0.30, mid, 50),
            'along': camera_at(scene, 'A' + side, wrist + fore * 0.22 + out_dir * 0.10,
                               mid, 50),
        }
        for cam_key, cam in cams.items():
            scene.camera = cam
            for f in frames:
                scene.frame_set(f)
                bpy.context.view_layer.update()
                posed = deform(rig)
                arm.data.vertices.foreach_set('co', posed.ravel())
                arm.data.update()
                bpy.context.view_layer.update()
                scene.render.filepath = str(folder / ('%s_%s_%04d.png' % (side, cam_key, f)))
                bpy.ops.render.render(write_still=True)
        summary['%s/%s' % (tag, side)] = {
            'elbow': [round(float(v), 4) for v in elbow],
            'wrist': [round(float(v), 4) for v in wrist],
        }
    print('FOREARM_DONE', tag, flush=True)

(OUT / 'forearm_report.json').write_text(
    json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
print('FOREARM_ALL_DONE')