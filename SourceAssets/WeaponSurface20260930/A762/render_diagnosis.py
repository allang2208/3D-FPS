"""Blender (background): diagnostic close-ups of the A762 defects (not a look render).

blender -b A762_SurfaceBake.blend -P render_diagnosis.py -- <out_dir>
Workbench, orthographic, backface culling on (as the single-sided UE materials):
grey = normal, blue = rebuilt parts, red = spike-tip faces, yellow = see-through faces.
"""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).parent
args = sys.argv[sys.argv.index('--') + 1:]
out_dir = Path(args[0])
by_slot = '--by-slot' in args
out_dir.mkdir(parents=True, exist_ok=True)
diag = json.loads((HERE / 'Bake' / 'surface_diagnosis.json').read_text(encoding='utf-8'))
header_mats = None
ob = bpy.data.objects['A762_BAKE']
me = ob.data
F = len(me.polygons)
mats = np.empty(F, np.int32)
me.polygons.foreach_get('material_index', mats)
names = [m.name.replace('BAKE_', '') for m in me.materials]

# Runtime triangle index -> bake face index.
with open(HERE.parent / 'inspect' / 'geometry' / 'A762.bin', 'rb') as f:
    header = json.loads(f.readline().decode('utf-8'))
    raw = f.read()
T, Vd = header['triangles'], header['vertices']
dump_mat = np.frombuffer(raw[Vd * 12 + T * 12: Vd * 12 + T * 16], np.int32)
arm = np.array([any(k in (m or '') for k in ('Manny', 'BarePalm', 'BareNative', 'BareFamily')) for m in header['materials']])
face_map = np.nonzero(~arm[dump_mat])[0]
to_face = {int(t): i for i, t in enumerate(face_map)}

color = np.tile(np.array([0.55, 0.55, 0.55, 1.0]), (F, 1))
rebuilt = [i for i, n in enumerate(names) if any(k in n for k in ('Rebuilt', '03', '04', 'Rail', 'Flash', 'Handguard'))]
color[np.isin(mats, rebuilt)] = [0.35, 0.45, 0.7, 1.0]
for name, e in diag['slots'].items():
    for t in e.get('see_through_runtime_triangles', []):
        color[to_face[t]] = [1.0, 0.85, 0.0, 1.0]
# Red: the planned deletion set (spike_selection.json), matched by centroid (UE -> Blender flips Y).
sel_file = HERE / 'Bake' / ('teeth_selection.json' if (HERE / 'Bake' / 'teeth_selection.json').exists() else 'spike_selection.json')
sel = json.loads(sel_file.read_text(encoding='utf-8'))
co = np.empty(len(me.vertices) * 3, np.float32)
me.vertices.foreach_get('co', co)
co = co.reshape(-1, 3).astype(np.float64)
corner = np.empty(F * 3, np.int32)
me.loops.foreach_get('vertex_index', corner)
cent = co[corner.reshape(F, 3)].mean(1)
from mathutils.kdtree import KDTree
kd = KDTree(F)
for i, c in enumerate(cent):
    kd.insert(c, i)
kd.balance()
matched = 0
for c in sel['centroids']:
    _, i, dist = kd.find((c[0], -c[1], c[2]))
    if dist < 1e-3:
        color[i] = [1.0, 0.1, 0.1, 1.0]
        matched += 1
print('DELETE_SET_MATCHED', matched, len(sel['centroids']), flush=True)
if by_slot:
    # Distinct colour per Meshy slot; rebuilt parts stay blue-grey.
    palette = {'M_A762_Receiver': (0.6, 0.6, 0.6), 'M_A762_Bolt': (0.9, 0.2, 0.9), 'M_A762_Trigger': (0.1, 0.8, 0.2),
               'M_A762_FactoryRearGrip': (0.9, 0.5, 0.1), 'M_A762_Inside': (0.0, 0.9, 0.9),
               'M_A762_FrontAssembly_Rebuilt': (0.2, 0.3, 0.9), 'M_A762_UpperReceiver03': (0.45, 0.35, 0.8),
               'M_A762_SightInner': (0.9, 0.9, 0.2)}
    color[:] = [0.35, 0.45, 0.7, 1.0]
    for name, rgb in palette.items():
        if name in names:
            color[mats == names.index(name)] = [*rgb, 1.0]
attr = me.color_attributes.get('DIAG') or me.color_attributes.new('DIAG', 'FLOAT_COLOR', 'CORNER')
attr.data.foreach_set('color', np.repeat(color, 3, axis=0).astype(np.float32).ravel())
me.color_attributes.active_color = attr

scene = bpy.context.scene
for o in scene.objects:
    o.hide_render = o is not ob
scene.render.engine = 'BLENDER_WORKBENCH'
shading = scene.display.shading
shading.light = 'STUDIO'
shading.color_type = 'VERTEX'
shading.show_backface_culling = True
shading.show_cavity = False
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
cam_data = bpy.data.cameras.new('DiagCam')
cam_data.type = 'ORTHO'
cam = bpy.data.objects.new('DiagCam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
# Blender coordinates: x across the gun, y along it (UE y mirrored), z up.
views = {
    'magwell_left': ((5.2, 22.0, -7.5), (-1, 0, 0), 16.0),
    'magwell_right': ((5.2, 22.0, -7.5), (1, 0, 0), 16.0),
    'receiver_left': ((5.2, 20.0, -5.0), (-1, 0, 0), 34.0),
    'receiver_right': ((5.2, 20.0, -5.0), (1, 0, 0), 34.0),
    'underside': ((5.2, 20.0, -5.0), (0, 0, -1), 34.0),
}
for name, (target, side, width) in views.items():
    t = Vector(target)
    d = Vector(side)
    cam.location = t + d * 60
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Z' if abs(d.z) < 0.9 else 'Y').to_euler()
    cam_data.ortho_scale = width
    scene.render.filepath = str(out_dir / ('a762_' + name + '.png'))
    bpy.ops.render.render(write_still=True)
    print('RENDERED', scene.render.filepath, flush=True)
