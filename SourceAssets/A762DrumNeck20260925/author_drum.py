"""Rebuild the A762 drum's feed tower.

The shipped drum is the AKM large drum with its upper neck remapped by a
smoothstep-blended affine fit; that both creases the tower and squeezes it to
58 mm where the A762 magazine is 72 mm deep.  Here the donor below z0 is kept
untouched and the tower is rebuilt as a straight canted prism whose cross-section
follows the A762 factory magazine's own envelope - the shape the well already
accepts - with a LINEAR ramp in z so no S-curve or crease is introduced.

Output: Exports-style FBX/blend identical in frame and scale to the shipped part.
"""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector, Matrix

O = Path(__file__).parent; S = O.parent
ACC = S / 'A762Meshy20260920/Accessories05'
DONOR = S / 'LargeDrumUpgrade20260920/Export/SM_AKM_LargeDrum_Upgrade.fbx'
Z0, Z1 = 0.045, 0.080          # tower split and full-target height
GROW = 0.0015                  # tower envelope = magazine section + 1.5 mm
SMOOTH = 0.006                 # section smoothing window


def mag_section():
    """A762 factory magazine envelope per height, in the magazine-bone rest frame."""
    bpy.ops.wm.open_mainfile(filepath=str(ACC / 'A762_AccessoryReady_Editable.blend'), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    xf = r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted() @ r.matrix_world.inverted()
    pts = [xf @ (o.matrix_world @ v.co) for o in bpy.context.scene.objects
           if o.type == 'MESH' and o.name.startswith('A762_R02_Magazine_') for v in o.data.vertices]
    zs = [z / 1000.0 for z in range(20, 101)]
    raw = {}
    for z in zs:
        row = [p for p in pts if abs(p.z - z) <= 0.002]
        if len(row) < 8:
            continue
        raw[z] = ((min(p.x for p in row) + max(p.x for p in row)) / 2,
                  (min(p.y for p in row) + max(p.y for p in row)) / 2,
                  max(p.x for p in row) - min(p.x for p in row),
                  max(p.y for p in row) - min(p.y for p in row))
    # smooth, then keep the envelope slightly outside the magazine
    out = {}
    keys = sorted(raw)
    for z in keys:
        near = [raw[k] for k in keys if abs(k - z) <= SMOOTH]
        cx = sum(v[0] for v in near) / len(near)
        cy = sum(v[1] for v in near) / len(near)
        dx = sum(v[2] for v in near) / len(near) + GROW
        dy = sum(v[3] for v in near) / len(near) + GROW
        out[z] = (cx, cy, dx, dy)
    return out


SECT = mag_section()
KEYS = sorted(SECT)
print('magazine envelope:')
for z in (0.045, 0.050, 0.060, 0.070, 0.075, 0.080):
    v = SECT.get(z)
    if v:
        print('  z=%3.0f mm  centre=(%.2f, %.2f)  size=(%.2f, %.2f)' % (z * 1000, v[0] * 1000, v[1] * 1000,
                                                                        v[2] * 1000, v[3] * 1000), flush=True)


def section_at(z):
    z = max(KEYS[0], min(KEYS[-1], z))
    lo = max([k for k in KEYS if k <= z])
    hi = min([k for k in KEYS if k >= z])
    if hi == lo:
        return SECT[lo]
    w = (z - lo) / (hi - lo)
    return tuple(SECT[lo][i] * (1 - w) + SECT[hi][i] * w for i in range(4))


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(DONOR))
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in objs:
    o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)

# donor tower reference: constant cross-section (it is a straight prism)
ref = None
row = [v.co for o in objs for v in o.data.vertices if 0.048 <= v.co.z <= 0.062]
ref = ((min(p.x for p in row) + max(p.x for p in row)) / 2,
       (min(p.y for p in row) + max(p.y for p in row)) / 2,
       max(p.x for p in row) - min(p.x for p in row),
       max(p.y for p in row) - min(p.y for p in row))
print('donor tower section: centre=(%.2f, %.2f) size=(%.2f, %.2f) mm' %
      (ref[0] * 1000, ref[1] * 1000, ref[2] * 1000, ref[3] * 1000), flush=True)

report = {'donor': str(DONOR), 'z0_mm': Z0 * 1000, 'z1_mm': Z1 * 1000, 'grow_mm': GROW * 1000,
          'donor_section_mm': [round(v * 1000, 3) for v in ref], 'samples': {}}


def shipped_target(y):
    """The value the shipped smoothstep map would give this vertex."""
    return 0.0448 + (y - 0.0197) * 0.87


for o in objs:
    for v in o.data.vertices:
        z = v.co.z
        if z <= Z0:
            continue
        t = max(0.0, min(1.0, (z - Z0) / (Z1 - Z0)))
        cx, cy, dx, dy = section_at(z)
        tx = cx + (v.co.x - ref[0]) * (dx / ref[2])
        ty = cy + (v.co.y - ref[1]) * (dy / ref[3])
        x_new = v.co.x * (1 - t) + tx * t
        y_new = v.co.y * (1 - t) + ty * t
        # never further forward than the part that ships today (that one clears the
        # receiver); the rebuild only extends the tower rearward to fill the well
        ts = max(0.0, min(1.0, (z - 0.045) / 0.030))
        ts = ts * ts * (3 - 2 * ts)
        y_ship = v.co.y * (1 - ts) + shipped_target(v.co.y) * ts
        v.co.x = x_new
        v.co.y = max(y_new, y_ship)
    o.data.update()

for z in (0.045, 0.050, 0.060, 0.070, 0.080):
    row = [v.co for o in objs for v in o.data.vertices if abs(v.co.z - z) <= 0.002]
    if len(row) < 4:
        report['samples'][z] = None
        continue
    rep = {'center': [round((min(p.x for p in row) + max(p.x for p in row)) / 2 * 1000, 2),
                      round((min(p.y for p in row) + max(p.y for p in row)) / 2 * 1000, 2)],
           'size': [round((max(p.x for p in row) - min(p.x for p in row)) * 1000, 2),
                    round((max(p.y for p in row) - min(p.y for p in row)) * 1000, 2)]}
    report['samples'][z] = rep
    print('  rebuilt z=%3.0f mm  centre=%s size=%s' % (z * 1000, rep['center'], rep['size']), flush=True)

out = O / 'Exports'
out.mkdir(exist_ok=True)
# keep the shipped slot naming so the UE material binding stays resolvable
for o in objs:
    for i, mat in enumerate(o.data.materials):
        mat.name = 'A762_drum_' + str(i)
bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    o.hide_set(False); o.select_set(True)
bpy.context.view_layer.objects.active = objs[-1]
bpy.ops.export_scene.fbx(filepath=str(out / 'SM_A762_drum.fbx'), use_selection=True,
                         object_types={'MESH'}, axis_forward='-Y', axis_up='Z', bake_anim=False,
                         mesh_smooth_type='FACE', use_tspace=False)
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'SM_A762_drum.blend'))
(O / 'authoring.json').write_text(json.dumps(report, indent=1))
print('DRUM_REBUILT', flush=True)
