"""Export an extended magazine in the rifle's own magazine-socket frame.

Standard: "the magazine's final pose is decided by the weapon interface"
(integration.md) and the aim direction may not be guessed from the longest
bounding-box axis (attachment-icons.md). So the part is NOT straightened: the
factory assembly vertices are lengthened along the magazine's own length axis,
then transformed into that rifle's WPN_SOCKET_Magazine frame and re-origined on
the throat top face. The runtime seat is then identity for that rifle.

Material slots are left untouched (weapon-finish.md keeps slot names and order
so the original-part hiding and reload splits keep working).

Run: blender -b -P export_insocket_pose.py -- <blend> <mag object> <label> <out fbx name>
"""
import bpy, json, sys
import numpy as np

argv = sys.argv[sys.argv.index('--') + 1:]
path, mag_name, label, out_name = argv[0], argv[1], argv[2], argv[3]
OUT = r"D:\FPS3D\FPSGAME\SourceAssets\ExtMagUniversal20260917"
KEEP_TOP, EXTEND = 0.100, 0.060

bpy.ops.wm.open_mainfile(filepath=path)
mag = bpy.data.objects[mag_name]
bpy.context.view_layer.update()

mwm = np.array(mag.matrix_world)
R3, T3 = mwm[:3, :3], mwm[:3, 3]
co = np.array([R3 @ np.array(v.co[:]) + T3 for v in mag.data.vertices])

# ---- lengthen along the magazine's own length axis --------------------------
mean = co.mean(axis=0)
_, sv, vt = np.linalg.svd(co - mean, full_matrices=False)
axis = vt[0]
if np.dot(axis, np.array([0.0, 0.0, -1.0])) < 0:
    axis = -axis
t = (co - mean) @ axis
t_top = t.min()                      # the throat end
co = co.copy()
co[t > t_top + KEEP_TOP] += axis * EXTEND
report = {'label': label, 'verts': int(len(co)),
          'len_before_m': round(float(np.ptp(t)), 4),
          'len_after_m': round(float(np.ptp((co - mean) @ axis)), 4),
          'axis': [round(float(x), 4) for x in axis]}

# ---- leave the factory orientation: express in the socket frame -------------
socket = None
for a in bpy.data.objects:
    if a.type == 'ARMATURE' and 'WPN_SOCKET_Magazine' in [b.name for b in a.pose.bones]:
        socket = (a, np.array(a.matrix_world) @ np.array(a.pose.bones['WPN_SOCKET_Magazine'].matrix))
if socket is None:
    raise RuntimeError('no WPN_SOCKET_Magazine bone found')
M_socket = socket[1]
co = (np.linalg.inv(M_socket) @ np.vstack([co.T, np.ones(len(co))]))[:3, :].T

# origin on the throat top face, still in the socket frame
ztop = float(co[:, 2].max())
top = co[co[:, 2] > ztop - 0.004]
centre = np.array([float(top[:, 0].mean()), float(top[:, 1].mean()), ztop])
co = co - centre
report['asset_min_m'] = [round(float(v), 4) for v in co.min(axis=0)]
report['asset_max_m'] = [round(float(v), 4) for v in co.max(axis=0)]
report['socket_world_m'] = [round(float(v), 4) for v in M_socket[:3, 3]]

# ---- bake the object transform, write the new vertices, export --------------
bpy.ops.object.select_all(action='DESELECT')
mag.select_set(True)
bpy.context.view_layer.objects.active = mag
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for v, p in zip(mag.data.vertices, co):
    v.co = (float(p[0]), float(p[1]), float(p[2]))
mag.data.update()
report['slots'] = [m.name if m else None for m in mag.data.materials]

bpy.ops.export_scene.fbx(filepath=OUT + "\FBX\\" + out_name,
                         use_selection=True, apply_unit_scale=True, object_types={'MESH'},
                         mesh_smooth_type='FACE', add_leaf_bones=False, path_mode='COPY')
report['fbx'] = out_name
print("INSOCKET " + json.dumps(report))
