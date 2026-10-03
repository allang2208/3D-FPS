"""Verify and render Elbow39: measures the exported actions against the
originals over every frame and writes before/after elbow close-ups."""
import json
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow39'
OUT = HERE / 'Review' / 'elbow39'

CLIPS = {
    'idle': (ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
             'PKM_Game_idle_Wrist12', 'PKM_idle_Elbow39', 60, [0, 20, 40, 60]),
    'reload': (ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
               'PKM16_base_reload', 'PKM_reload_Elbow39', 120,
               [0, 130, 260, 390, 520, 650, 780]),
    'reload_empty': (ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend',
                     'PKM34_base_reload_empty', 'PKM_reload_empty_Elbow39', 120,
                     [0, 160, 320, 480, 640, 790]),
}

mesh_data = np.load(HERE / 'v7_mesh.npz', allow_pickle=True)
author = np.load(HERE / 'author_rig.npz', allow_pickle=True)
V7_VERTS = mesh_data['verts'].astype(np.float64)
V7_TRIS = mesh_data['tris'].astype(np.int64)
V7_WIDX = mesh_data['w_idx']
V7_WVAL = mesh_data['w_val'].astype(np.float64)
V7_BONES = list(mesh_data['bones'])
V7_REST = mesh_data['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST = author['rest'].astype(np.float64)
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
N_V7 = len(V7_BONES)

IDX = {n: V7_BONES.index(n) for n in ('upperarm_l', 'lowerarm_l', 'hand_l')}
e_rest = V7_REST[IDX['lowerarm_l']][:3, 3].copy()
s_rest = V7_REST[IDX['upperarm_l']][:3, 3].copy()
w_rest = V7_REST[IDX['hand_l']][:3, 3].copy()
u0 = (e_rest - s_rest) / np.linalg.norm(e_rest - s_rest)
f0 = (w_rest - e_rest) / np.linalg.norm(w_rest - e_rest)
FLEN = float(np.linalg.norm(w_rest - e_rest))
REL = V7_VERTS - e_rest
T_ALL = REL @ f0 / FLEN
RADIUS = np.linalg.norm(REL - np.outer(T_ALL * FLEN, f0), axis=1)
ARM = (RADIUS < 0.070) & (T_ALL > -0.30) & (T_ALL < 0.92)
AIDX = np.where(ARM)[0]
P1_0 = u0 - (u0 @ f0) * f0
P1_0 /= np.linalg.norm(P1_0)
P2_0 = np.cross(f0, P1_0)
PERP0 = (V7_VERTS[AIDX] - e_rest) - np.outer((V7_VERTS[AIDX] - e_rest) @ f0, f0)
PHI0 = np.arctan2(PERP0 @ P2_0, PERP0 @ P1_0)
EDGES = np.arange(-0.30, 0.92, 0.05)
BIN = np.digitize(T_ALL[AIDX], EDGES) - 1
NB = len(EDGES) - 1
BIN_T = EDGES[:-1] + 0.025
BIN_OK = np.array([(BIN == b).sum() >= 8 for b in range(NB)])
FIT = BIN_OK & (BIN_T >= -0.10) & (BIN_T <= 0.90)
HOMO = np.concatenate([V7_VERTS, np.ones((len(V7_VERTS), 1))], axis=1)


def skin_matrices(rig):
    pose = np.zeros((len(AU_BONES), 4, 4))
    for i, name in enumerate(AU_BONES):
        pose[i] = np.array(rig.pose.bones[name].matrix)
    delta = pose @ np.linalg.inv(AU_REST)
    out = np.tile(np.eye(4), (N_V7, 1, 1))
    for i, n in enumerate(V7_BONES):
        if n in AU_INDEX:
            out[i] = delta[AU_INDEX[n]]
    return out


def deform(skin):
    out = np.zeros_like(V7_VERTS)
    for k in range(V7_WIDX.shape[1]):
        idx, w = V7_WIDX[:, k], V7_WVAL[:, k]
        act = (idx >= 0) & (w > 0.0)
        out[act] += w[act, None] * np.einsum('nij,nj->ni', skin[idx[act]],
                                             HOMO[act])[:, :3]
    return out


def profile(posed, e, u, f):
    p1 = u - (u @ f) * f
    p1 /= np.linalg.norm(p1)
    p2 = np.cross(f, p1)
    sub = posed[AIDX]
    rp = sub - e
    pp = rp - np.outer(rp @ f, f)
    phip = np.arctan2(pp @ p2, pp @ p1)
    dphi = np.degrees((phip - PHI0 + np.pi) % (2 * np.pi) - np.pi)
    vals = np.full(NB, np.nan)
    for b in range(NB):
        sel = BIN == b
        if sel.sum() >= 8:
            vals[b] = dphi[sel].mean()
    return vals


def camera_at(scene, name, loc, target, lens):
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    data.lens = lens
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return cam


def run(key, blend, action_name, fps, frames, render_dir, want_render):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    try:
        action = bpy.data.actions[action_name]
    except KeyError:
        return None
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.render.fps = int(fps)
    scene.render.fps_base = 1.0
    start, end = map(int, action.frame_range)
    stride = max(1, int(round(fps / 30.0)))

    rows = []
    for frame in range(start, end + 1, stride):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        e = np.array(rig.pose.bones['lowerarm_l'].matrix.translation)
        s = np.array(rig.pose.bones['upperarm_l'].matrix.translation)
        w = np.array(rig.pose.bones['hand_l'].matrix.translation)
        u = (e - s) / np.linalg.norm(e - s)
        f = (w - e) / np.linalg.norm(w - e)
        vals = profile(deform(skin_matrices(rig)), e, u, f)
        d = np.diff(vals[FIT])
        rng = abs(vals[FIT][-1] - vals[FIT][0])
        rows.append({'frame': frame, 'sec': round(frame / fps, 3),
                     'back': round(float(np.clip(d, 0, None).max()), 2),
                     'rms': round(float(np.sqrt(((vals[FIT] - np.interp(
                         BIN_T[FIT], [BIN_T[FIT][0], BIN_T[FIT][-1]],
                         [vals[FIT][0], vals[FIT][-1]])) ** 2).mean())), 2),
                     'tv': round(float(np.abs(d).sum()), 1),
                     'range': round(rng, 1)})

    if not want_render:
        return rows

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
    scene.render.resolution_x, scene.render.resolution_y = 720, 720

    scene.frame_set(frames[0])
    bpy.context.view_layer.update()
    cams = {}
    for cname in ('profile', 'outer', 'inner'):
        cams[cname] = camera_at(scene, cname, (0, 0, 0), (0, 0, 0), 55)
    render_dir.mkdir(parents=True, exist_ok=True)
    for fr in frames:
        scene.frame_set(fr)
        bpy.context.view_layer.update()
        world = rig.matrix_world
        elbow = world @ rig.pose.bones['lowerarm_l'].matrix.translation
        shoulder = world @ rig.pose.bones['upperarm_l'].matrix.translation
        wrist = world @ rig.pose.bones['hand_l'].matrix.translation
        fore = (wrist - elbow).normalized()
        upper = (elbow - shoulder).normalized()
        bend_axis = fore.cross(upper).normalized()
        out_dir = -(fore + upper).normalized()
        places = {
            'profile': elbow + bend_axis * 0.40,
            'outer': elbow + out_dir * 0.40 + bend_axis * 0.09,
            'inner': elbow - out_dir * 0.40 - bend_axis * 0.09,
        }
        arm.data.vertices.foreach_set('co', deform(skin_matrices(rig)).ravel())
        arm.data.update()
        bpy.context.view_layer.update()
        for cam_key, loc in places.items():
            cam = cams[cam_key]
            cam.location = loc
            cam.rotation_euler = (elbow - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
            scene.camera = cam
            scene.render.filepath = str(render_dir / ('%s_%04d.png' % (cam_key, fr)))
            bpy.ops.render.render(write_still=True)
    return rows


summary = {}
for key, (blend, action_name, new_name, fps, frames) in CLIPS.items():
    before = run(key, blend, action_name, fps, frames,
                 OUT / key / 'before', True)
    after = run(key, HERE / 'Edit' / (new_name + '.blend'), new_name, fps,
                frames, OUT / key / 'after', True)
    summary[key] = {
        'sampled': len(before),
        'worst_back_before': round(max(r['back'] for r in before), 2),
        'worst_back_after': round(max(r['back'] for r in after), 2),
        'mean_rms_before': round(float(np.mean([r['rms'] for r in before])), 2),
        'mean_rms_after': round(float(np.mean([r['rms'] for r in after])), 2),
        'mean_tv_before': round(float(np.mean([r['tv'] for r in before])), 1),
        'mean_tv_after': round(float(np.mean([r['tv'] for r in after])), 1),
        'rows_before': before, 'rows_after': after,
    }
    print('\n=== %s ===' % key)
    print('  worst backward step %.1f -> %.1f deg' % (
        summary[key]['worst_back_before'], summary[key]['worst_back_after']))
    print('  mean RMS to ramp    %.1f -> %.1f deg' % (
        summary[key]['mean_rms_before'], summary[key]['mean_rms_after']))
    print('  mean total variation %.1f -> %.1f deg' % (
        summary[key]['mean_tv_before'], summary[key]['mean_tv_after']))

(HERE / 'verify_elbow39.json').write_text(json.dumps(summary, indent=2),
                                          encoding='utf-8')
print('\nREVIEW39_DONE')