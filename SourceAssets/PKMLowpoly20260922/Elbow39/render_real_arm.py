"""Render the real PKM left arm: the V7 bare-arms surface that the base
viewmodel carries, skinned with its own weights and the pose the animation
actually plays.  Also renders the authoring arm object for cross-checking.

Only weapon parts and one arm surface are drawn, so template meshes and rig
controllers cannot fake a silhouette.
"""
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
             'PKM_Game_idle_Wrist12', 60),
    'reload': (ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
               'PKM16_base_reload', 120),
}

mesh_data = np.load(HERE / 'v7_mesh.npz', allow_pickle=True)
author = np.load(HERE / 'author_rig.npz', allow_pickle=True)
V7_VERTS = mesh_data['verts'].astype(np.float64)
V7_TRIS = mesh_data['tris'].astype(np.int64)
V7_WIDX = mesh_data['w_idx']
V7_WVAL = mesh_data['w_val'].astype(np.float64)
V7_BONES = list(mesh_data['bones'])
V7_BONE_INDEX = {n: i for i, n in enumerate(V7_BONES)}
AU_BONES = list(author['bones'])
AU_REST = author['rest'].astype(np.float64)
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
V7_OBJ_WORLD = mesh_data['obj_world'].astype(np.float64)

N_V7 = len(V7_BONES)
N_AU = len(AU_BONES)
MAP = np.array([AU_INDEX.get(n, -1) for n in V7_BONES])
missing = {n for n, m in zip(V7_BONES, MAP) if m < 0}
weighted = {V7_BONES[i] for i in np.unique(V7_WIDX[V7_WIDX >= 0])}
print('V7 bones %d, unmapped weighted: %s'
      % (N_V7, sorted(weighted.intersection(missing))), flush=True)


def skin_matrices(rig):
    """Armature-space delta per V7 bone, taken from the authoring rig."""
    pose = np.zeros((N_AU, 4, 4))
    for i, name in enumerate(AU_BONES):
        pose[i] = np.array(rig.pose.bones[name].matrix)
    delta_au = pose @ np.linalg.inv(AU_REST)
    out = np.tile(np.eye(4), (N_V7, 1, 1))
    mapped = MAP >= 0
    out[mapped] = delta_au[MAP[mapped]]
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
        m = skin[idx[active]]
        v = homo[active]
        out[active] += w[active, None] * np.einsum('nij,nj->ni', m, v)[:, :3]
    return out


def make_object(name, verts, tris, colour):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(t) for t in tris])
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(bpy.data.materials.new(name + '_mat'))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def setup(blend, action_name, fps):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.render.fps = fps

    weapon = [ob for ob in bpy.data.objects
              if ob.type == 'MESH' and 'PKM' in ob.name
              and 'Belt' not in ob.name and 'Round' not in ob.name]
    for ob in bpy.data.objects:
        ob.hide_render = True
    for ob in weapon:
        ob.hide_render = False

    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.studio_light = 'Default'
    scene.display.shading.color_type = 'SINGLE'
    scene.display.shading.single_color = (0.55, 0.55, 0.55)
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.display.shading.curvature_ridge_factor = 1.4
    scene.display.shading.curvature_valley_factor = 1.2
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False

    arm = make_object('ReviewArm', V7_VERTS, V7_TRIS, (0.6, 0.55, 0.5))
    arm.matrix_world = bpy.data.objects['PKM_Manny_Rig'].matrix_world.copy()
    return scene, rig, arm


def camera_at(scene, name, location, target, lens):
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    data.lens = lens
    cam.location = location
    cam.rotation_euler = (Vector(target) - Vector(location)).to_track_quat('-Z', 'Y').to_euler()
    return cam


report = {}
for key, (blend, action_name, fps) in CLIPS.items():
    scene, rig, arm = setup(blend, action_name, fps)
    start, end = map(int, bpy.data.actions[action_name].frame_range)
    span = end - start
    frames = [start + round(span * i / 12.0) for i in range(13)]
    folder = OUT / TAG / key
    folder.mkdir(parents=True, exist_ok=True)

    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    fp_cam = camera_at(scene, 'FP', (0.0, -0.06, 0.03), (0.0, 1.0, -0.03), 24)
    scene.camera = fp_cam

    elbow_cam = None
    scene.frame_set(start)
    bpy.context.view_layer.update()
    skin = skin_matrices(rig)
    world = rig.matrix_world
    elbow = world @ rig.pose.bones['lowerarm_l'].matrix.translation
    shoulder = world @ rig.pose.bones['upperarm_l'].matrix.translation
    wrist = world @ rig.pose.bones['hand_l'].matrix.translation
    fore = (wrist - elbow).normalized()
    upper = (elbow - shoulder).normalized()
    out_dir = -(fore + upper).normalized()          # outside of the bent elbow
    side = out_dir.cross(Vector((0, 0, 1)))
    if side.length < 1e-4:
        side = Vector((0, 0, 1))
    side.normalize()
    bend_axis = fore.cross(upper).normalized()
    elbow_cam = camera_at(scene, 'Elbow', elbow + out_dir * 0.62 + side * 0.10,
                          elbow + fore * 0.02, 42)
    side_cam = camera_at(scene, 'Side', elbow + bend_axis * 0.85,
                         elbow + fore * 0.03, 45)
    back_cam = camera_at(scene, 'Back', elbow - out_dir * 0.62 + side * 0.05,
                         elbow + fore * 0.02, 42)

    report[key] = {
        'elbow_world': [round(v, 4) for v in elbow],
        'shoulder_world': [round(v, 4) for v in shoulder],
        'wrist_world': [round(v, 4) for v in wrist],
        'frames': frames,
    }

    for cam_key, cam in (('fp', fp_cam), ('elbow', elbow_cam),
                         ('side', side_cam), ('back', back_cam)):
        scene.camera = cam
        if cam_key == 'fp':
            scene.render.resolution_x, scene.render.resolution_y = 960, 540
        else:
            scene.render.resolution_x, scene.render.resolution_y = 800, 800
        keys = frames if cam_key in ('fp', 'elbow') else frames[::3]
        for f in keys:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            posed = deform(skin_matrices(rig))
            arm.data.vertices.foreach_set('co', posed.ravel())
            arm.data.update()
            bpy.context.view_layer.update()
            scene.render.filepath = str(folder / ('%s_%04d.png' % (cam_key, f)))
            bpy.ops.render.render(write_still=True)

(OUT / TAG / 'render_report.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('RENDER_DONE', TAG, flush=True)