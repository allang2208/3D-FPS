"""PKM sprint entry: left forearm/hand close-ups across the transition."""
import json
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Sprint43'
OUT = ROOT / 'Sprint44' / 'Review'

CASES = (('enter', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_enter_Sprint44.blend',
          'PKM_sprint_enter_Sprint44', [0, 6, 12, 18, 24, 30, 36, 42]),
         ('loop', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_loop_Sprint44.blend',
          'PKM_sprint_loop_Sprint44', [0, 12, 24, 36, 48, 60, 72]))

mesh_data = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
author = np.load(E39 / 'author_rig.npz', allow_pickle=True)
V = mesh_data['verts'].astype(np.float64)
T = mesh_data['tris'].astype(np.int64)
WIDX, WVAL = mesh_data['w_idx'], mesh_data['w_val'].astype(np.float64)
BONES = list(mesh_data['bones'])
AU_BONES = list(author['bones'])
AU_REST = author['rest'].astype(np.float64)
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
MAP = np.array([AU_INDEX.get(n, -1) for n in BONES])
HOMO = np.concatenate([V, np.ones((len(V), 1))], axis=1)


def deform(rig):
    pose = np.zeros((len(AU_BONES), 4, 4))
    for i, n in enumerate(AU_BONES):
        pose[i] = np.array(rig.pose.bones[n].matrix)
    delta = pose @ np.linalg.inv(AU_REST)
    skin = np.tile(np.eye(4), (len(BONES), 1, 1))
    m = MAP >= 0
    skin[m] = delta[MAP[m]]
    out = np.zeros_like(V)
    for k in range(WIDX.shape[1]):
        idx, w = WIDX[:, k], WVAL[:, k]
        a = (idx >= 0) & (w > 0.0)
        out[a] += w[a, None] * np.einsum('nij,nj->ni', skin[idx[a]], HOMO[a])[:, :3]
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
for tag, blend, action_name, frames in CASES:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    act = bpy.data.actions[action_name]
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.render.fps = 120
    for ob in bpy.data.objects:
        ob.hide_render = not (ob.type == 'MESH' and 'PKM' in ob.name
                              and 'Belt' not in ob.name and 'Round' not in ob.name)
    me = bpy.data.meshes.new('Arm')
    me.from_pydata([tuple(v) for v in V], [], [tuple(t) for t in T])
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
    scene.render.resolution_x, scene.render.resolution_y = 700, 700

    folder = OUT / tag
    folder.mkdir(parents=True, exist_ok=True)

    # cameras are rebuilt per frame: the arm swings 55 cm during the entry
    cam_names = ('outer', 'inner', 'profile')
    for f in frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        world = rig.matrix_world
        elbow = world @ rig.pose.bones['lowerarm_l'].matrix.translation
        shoulder = world @ rig.pose.bones['upperarm_l'].matrix.translation
        wrist = world @ rig.pose.bones['hand_l'].matrix.translation
        fore = (wrist - elbow).normalized()
        upper = (elbow - shoulder).normalized()
        bend_axis = fore.cross(upper).normalized()
        out_dir = -(fore + upper).normalized()
        mid = (elbow + wrist) * 0.5
        cams = {}
        for name in cam_names:
            if name == 'outer':
                cams[name] = camera_at(scene, 'C_outer_%d' % f,
                                       mid + out_dir * 0.30 + bend_axis * 0.06, mid, 50)
            elif name == 'inner':
                cams[name] = camera_at(scene, 'C_inner_%d' % f,
                                       mid - out_dir * 0.30 - bend_axis * 0.06, mid, 50)
            else:
                cams[name] = camera_at(scene, 'C_profile_%d' % f,
                                       mid + bend_axis * 0.30, mid, 50)
        posed = deform(rig)
        arm.data.vertices.foreach_set('co', posed.ravel())
        arm.data.update()
        bpy.context.view_layer.update()
        for name, cam in cams.items():
            scene.camera = cam
            scene.render.filepath = str(folder / ('%s_%04d.png' % (name, f)))
            bpy.ops.render.render(write_still=True)
        summary['%s_%d' % (tag, f)] = {
            'elbow': [round(float(v), 4) for v in elbow],
            'bend': round(float(np.degrees(np.arccos(np.clip(fore @ upper, -1, 1)))), 1),
        }
    print('RENDERED', tag, flush=True)

(OUT / 'sprint43_render.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print('SPRINT43_RENDER_DONE')