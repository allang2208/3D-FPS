"""Tight left-elbow shots of the real V7 PKM arm, from the bend-axis profile
and the outer side, for idle and reload."""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow39'
OUT = HERE / 'Review'

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
TAG = ARGS[0] if ARGS else 'current'

CLIPS = {
    'idle': (ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
             'PKM_Game_idle_Wrist12', 60, [0, 30, 60]),
    'reload': (ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
               'PKM16_base_reload', 120, [0, 130, 260, 390, 520, 650, 780]),
    'reload_empty': (ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend',
                     'PKM34_base_reload_empty', 120, [0, 200, 400, 600, 790]),
}

mesh_data = np.load(HERE / 'v7_mesh.npz', allow_pickle=True)
author = np.load(HERE / 'author_rig.npz', allow_pickle=True)
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


def skin_matrices(rig):
    pose = np.zeros((N_AU, 4, 4))
    for i, name in enumerate(AU_BONES):
        pose[i] = np.array(rig.pose.bones[name].matrix)
    delta = pose @ np.linalg.inv(AU_REST)
    out = np.tile(np.eye(4), (N_V7, 1, 1))
    mapped = MAP >= 0
    out[mapped] = delta[MAP[mapped]]
    return out


def deform(skin):
    out = np.zeros_like(V7_VERTS)
    homo = np.concatenate([V7_VERTS, np.ones((len(V7_VERTS), 1))], axis=1)
    for k in range(V7_WIDX.shape[1]):
        idx = V7_WIDX[:, k]
        w = V7_WVAL[:, k]
        active = (idx >= 0) & (w > 0.0)
        if not active.any():
            continue
        out[active] += w[active, None] * np.einsum(
            'nij,nj->ni', skin[idx[active]], homo[active])[:, :3]
    return out


def camera_at(scene, name, loc, target, lens):
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    data.lens = lens
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return cam


report = {}
for key, (blend, action_name, fps, frames) in CLIPS.items():
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
    scene.render.resolution_x, scene.render.resolution_y = 760, 760

    folder = OUT / TAG / (key + '_tight')
    folder.mkdir(parents=True, exist_ok=True)

    scene.frame_set(frames[0])
    bpy.context.view_layer.update()
    world = rig.matrix_world
    elbow = world @ rig.pose.bones['lowerarm_l'].matrix.translation
    shoulder = world @ rig.pose.bones['upperarm_l'].matrix.translation
    wrist = world @ rig.pose.bones['hand_l'].matrix.translation
    fore = (wrist - elbow).normalized()
    upper = (elbow - shoulder).normalized()
    bend_axis = fore.cross(upper).normalized()
    out_dir = -(fore + upper).normalized()

    cams = {
        'profile': camera_at(scene, 'P', elbow + bend_axis * 0.42, elbow, 55),
        'outer': camera_at(scene, 'O', elbow + out_dir * 0.42 + bend_axis * 0.10,
                           elbow, 55),
        'inner': camera_at(scene, 'I', elbow - out_dir * 0.42 - bend_axis * 0.10,
                           elbow, 55),
    }
    for cam_key, cam in cams.items():
        scene.camera = cam
        for f in frames:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            posed = deform(skin_matrices(rig))
            arm.data.vertices.foreach_set('co', posed.ravel())
            arm.data.update()
            bpy.context.view_layer.update()
            scene.render.filepath = str(folder / ('%s_%04d.png' % (cam_key, f)))
            bpy.ops.render.render(write_still=True)
    report[key] = {'elbow_world': [round(v, 4) for v in elbow], 'frames': frames}
    print('TIGHT_DONE', key, flush=True)

(OUT / TAG / 'tight_report.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('TIGHT_ALL_DONE', TAG, flush=True)