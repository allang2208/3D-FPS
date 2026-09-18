"""Render the factory QBZ magazine and the extended version side by side.

Both are aligned to the shared authoring convention first (length axis down -Z,
origin on the throat top-face centre) so the only difference the camera sees is
the added length. Same camera for both shots, so the extension is measurable by
eye.
"""
import bpy, json, math
import numpy as np

SRC = r"D:\FPS3D\FPSGAME\SourceAssets\QBZ191MagazineSeat20260913\QBZ191_MagazineSeat_Editable.blend"
OUT = r"D:\FPS3D\FPSGAME\SourceAssets\ExtMagUniversal20260917"
KEEP_TOP, EXTEND = 0.080, 0.060


def rot_between(a, b):
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if c < -1.0 + 1e-9:
        perp = np.array([1.0, 0.0, 0.0]) if abs(a[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        ax = np.cross(a, perp); ax = ax / np.linalg.norm(ax)
        return 2.0 * np.outer(ax, ax) - np.eye(3)
    K = np.array([[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]])
    return np.eye(3) + K + K @ K * (1.0 / (1.0 + c))


bpy.ops.wm.open_mainfile(filepath=SRC)
mag = bpy.data.objects['QBZ191_Magazine_Export']
me = mag.data
mwm = np.array(mag.matrix_world)
R3, T3 = mwm[:3, :3], mwm[:3, 3]
co0 = np.array([R3 @ np.array(v.co[:]) + T3 for v in me.vertices])

mean = co0.mean(axis=0)
_, sv, vt = np.linalg.svd(co0 - mean, full_matrices=False)
axis = vt[0]
if axis[2] > 0:
    axis = -axis
Rm = rot_between(axis, np.array([0.0, 0.0, -1.0]))
co = co0 @ Rm.T
ztop = float(co[:, 2].max())
top = co[co[:, 2] > ztop - 0.004]
cx, cy = float(top[:, 0].mean()), float(top[:, 1].mean())
co = co - np.array([cx, cy, ztop])

factory = co.copy()
z = co[:, 2].copy()
extended = co.copy()
extended[:, 2] = np.where(z < -KEEP_TOP, z - EXTEND, z)

info = {'len_factory': round(float(np.ptp(factory[:, 2])), 4),
        'len_extended': round(float(np.ptp(extended[:, 2])), 4),
        'extended_min': [round(float(v), 4) for v in extended.min(axis=0)],
        'extended_max': [round(float(v), 4) for v in extended.max(axis=0)]}

for o in bpy.data.objects:
    if o is not mag:
        o.hide_render = True

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.color_type = 'SINGLE'
scene.display.shading.single_color = (0.32, 0.33, 0.35)
scene.display.shading.show_object_outline = True
scene.render.resolution_x, scene.render.resolution_y = 1000, 760

cam_data = bpy.data.cameras.new('PreviewCam')
cam_data.type = 'ORTHO'
cam = bpy.data.objects.new('PreviewCam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

# frame both pieces identically: union bounds of the extended one plus margin
lo, hi = extended.min(axis=0), extended.max(axis=0)
mid = (lo + hi) / 2
dim = float(max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))
cam_data.ortho_scale = dim * 1.35
cam.location = (float(mid[0]) + 1.5, float(mid[1]), float(mid[2]))
cam.rotation_mode = 'XYZ'

views = {
    'side': (math.radians(90), 0.0, math.radians(90)),
    'front': (math.radians(90), 0.0, 0.0),
}


def write(verts):
    loc = (verts - T3) @ R3
    for v, p in zip(me.vertices, loc):
        v.co = (float(p[0]), float(p[1]), float(p[2]))
    me.update()


for tag, verts in (('factory', factory), ('ext40', extended)):
    write(verts)
    for name, eul in views.items():
        cam.rotation_euler = eul
        scene.render.filepath = OUT + r"\Reference\cmp_" + tag + "_" + name + ".png"
        bpy.ops.render.render(write_still=True)

write(extended)
bpy.ops.wm.save_as_mainfile(filepath=OUT + r"\ExtMag40_Editable.blend")
bpy.ops.object.select_all(action='DESELECT')
mag.select_set(True)
bpy.context.view_layer.objects.active = mag
bpy.ops.export_scene.fbx(filepath=OUT + r"\FBX\SM_ExtMag_QBZ40.fbx",
                         use_selection=True, apply_unit_scale=True, object_types={'MESH'},
                         mesh_smooth_type='FACE', add_leaf_bones=False, path_mode='COPY')
print("CMP40 " + json.dumps(info))
