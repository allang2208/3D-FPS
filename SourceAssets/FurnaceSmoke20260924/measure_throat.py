# Read-only pass 3 (world-space): profile the charging throat, ignoring the outer skirt.
# For each radius from the mouth centre, report the median downward-ray hit depth so we can
# read where the collar inner wall ends and the open throat (line-of-sight down into the bowl)
# begins. Emitter disk radius = throat opening; emitter height = a touch below the rim so the
# plume rises OUT OF the mouth instead of popping above the collar.
import bpy, json, math, sys
from mathutils import Vector

FBX = r'D:\FPS3D\FPSGAME\SourceAssets\BlastFurnace20260923\Authored\SM_BlastFurnace.fbx'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
deps = bpy.context.evaluated_depsgraph_get()
mesh_obj = next((o for o in bpy.context.scene.objects if o.type == 'MESH'), None)
mw = mesh_obj.matrix_world
top_w = max((mw @ v.co).z for v in mesh_obj.data.vertices)
centre_w = mw @ Vector((-0.18, 0.0, 0.0))
centre_w = Vector((centre_w.x, centre_w.y, 0.0))

# sample concentric rings, 0.8cm apart, to 42cm; 24 spokes each
prof = {}
RING_STEP = 0.008
for ri in range(1, 54):
    r = ri * RING_STEP
    zs = []
    for s in range(24):
        th = s / 24 * 2 * math.pi
        x = centre_w.x + r * math.cos(th)
        y = centre_w.y + r * math.sin(th)
        hit, loc, *_ = bpy.context.scene.ray_cast(deps, Vector((x, y, top_w + 0.5)), Vector((0, 0, -1)))
        zs.append(loc.z if hit else top_w + 0.5)
    zs.sort()
    prof[round(r * 100, 2)] = round(zs[len(zs) // 2] * 100, 1)     # median hit depth per ring

# Throat = the largest radius band (from centre outward) whose median hit is well below the rim.
# Rim collar reads ~top; once past the inner wall the median drops (open bowl). The FIRST radius
# whose median is within 1cm of the rim after a run of open samples marks the outer collar edge.
open_r = [rr for rr, zz in prof.items() if zz < top_w * 100 - 3.0]      # clearly inside the throat
throat_max_cm = max(open_r) if open_r else None
# But ignore the far skirt: throat must be a CONTIGUOUS open run from the centre.
keys = sorted(prof)
contig = 0.0
for rr in keys:
    if prof[rr] < top_w * 100 - 3.0:
        contig = rr
    else:
        break

out = {
    'rim_top_cm': round(top_w * 100, 2),
    'centre_cm': [round(centre_w.x * 100, 2), round(centre_w.y * 100, 2)],
    'contiguous_open_throat_radius_cm': round(contig, 2),
    'any_open_max_radius_cm': throat_max_cm,
    'profile_cm_radius_to_medianhitZ': prof,
}
print(json.dumps({k: out[k] for k in out if k != 'profile_cm_radius_to_medianhitZ'}, indent=1))
print('PROFILE', json.dumps(prof))
with open(r'D:\FPS3D\FPSGAME\Saved\furnace_throat.json', 'w', encoding='utf8') as fh:
    json.dump(out, fh, indent=1)
