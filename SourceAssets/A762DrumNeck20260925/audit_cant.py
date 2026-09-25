"""Is the AKM magazine (and so the donor drum's tower) straight or canted?
Slices the AKM factory magazine in its own magazine-bone frame and prints the
cross-section centre per height, next to the donor drum tower."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector

O = Path(__file__).parent; S = O.parent
DONOR = S / 'LargeDrumUpgrade20260920/Export/SM_AKM_LargeDrum_Upgrade.fbx'
AKM = S / 'AKMReloadPolish20260911/base/A_AKM_reload.blend'
ZS = [0.030, 0.040, 0.045, 0.050, 0.060, 0.070, 0.080]


def slab(points, z, tol=0.002):
    row = [p for p in points if abs(p.z - z) <= tol]
    if len(row) < 4:
        return None
    xs = [p.x for p in row]; ys = [p.y for p in row]
    return {'n': len(row),
            'cx': round((min(xs) + max(xs)) / 2 * 1000, 2), 'cy': round((min(ys) + max(ys)) / 2 * 1000, 2),
            'dx': round((max(xs) - min(xs)) * 1000, 2), 'dy': round((max(ys) - min(ys)) * 1000, 2)}


bpy.ops.wm.open_mainfile(filepath=str(AKM), use_scripts=False)
r = bpy.data.objects['SK_M4_Infima']
xf = r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted() @ r.matrix_world.inverted()
mag = bpy.data.objects['AKM_FactoryMagazine_Preview']
akm_pts = [xf @ (mag.matrix_world @ v.co) for v in mag.data.vertices]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(DONOR))
donor_pts = [o.matrix_world @ v.co for o in bpy.context.scene.objects if o.type == 'MESH'
             for v in o.data.vertices]

print('z(mm) | AKM factory magazine            | AKM drum tower')
rows = {}
for z in ZS:
    a = slab(akm_pts, z); d = slab(donor_pts, z)
    rows[z] = {'akm_mag': a, 'drum_tower': d}
    print('%5.0f | %s | %s' % (z * 1000, json.dumps(a), json.dumps(d)), flush=True)
(O / 'akm_cant.json').write_text(json.dumps(rows, indent=1))
print('CANT_OK', flush=True)
