"""Tight seal of A762 PSO_ScopeBody mount-cutout onto the tube cylinder.

Only the open saddle window into the tube — not upper left jaws, not gun adapters.
Project patch (cutout verts + one ring if still outside tube) onto R=0.0200.
Trial file first; editable overwritten only after visual OK (separate step).
"""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R_IN = 0.1024, 0.0200

bak = OUT / 'PSO1_A762_Editable.before-tuck.blend'
work = OUT / 'PSO1_A762_cutout_seal_work.blend'
shutil.copy2(bak, work)

bpy.ops.wm.open_mainfile(filepath=str(work))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world.copy(); inv = mw.inverted()
bm = bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

def rad(v):
    return math.hypot(v.co.x, v.co.z - AXIS_Z)

seed = [v for v in bm.verts
        if rad(v) > 0.0215
        and v.co.x > 0.008
        and -0.095 < v.co.y < 0.03
        and v.co.z < 0.095]
patch = set(seed)
for v in seed:
    for e in v.link_edges:
        ov = e.other_vert(v)
        if ov.co.z < 0.100 and -0.10 < ov.co.y < 0.04 and ov.co.x > 0.0:
            if rad(ov) > 0.0190:
                patch.add(ov)

before_r = sorted((round(rad(v), 4) for v in patch), reverse=True)[:8]
projected = 0
for v in patch:
    dx, dz = v.co.x, v.co.z - AXIS_Z
    r = math.hypot(dx, dz)
    if r > R_IN:
        k = R_IN / r
        v.co.x = dx * k
        v.co.z = AXIS_Z + dz * k
        projected += 1

boundary = sum(1 for e in bm.edges if e.is_boundary)
for v in bm.verts:
    v.co = inv @ (v.co + DELTA)
bm.to_mesh(body.data); bm.free(); body.data.update()
for p in body.data.polygons:
    p.use_smooth = True

report = {'seed': len(seed), 'patch': len(patch), 'projected': projected,
          'boundary': boundary, 'before_r_max_sample': before_r}

for ob in scene.objects:
    if ob.type == 'MESH':
        keep = ob.name in ('PSO_ScopeBody', 'PSO_ScopeMount', 'PSO_ScopeLens')
        ob.hide_render = not keep; ob.hide_set(not keep)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1700; scene.render.resolution_y = 1100
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
sh.show_backface_culling = True; sh.show_cavity = True; sh.cavity_type = 'BOTH'
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 70
target = DELTA + Vector((0.01, -0.04, 0.09))
views = [
    ('cutseal_tq', Vector((0.22, -0.22, 0.12)), False),
    ('cutseal_under', Vector((0.12, -0.05, -0.22)), False),
    ('cutseal_side', Vector((0.30, 0.0, 0.03)), False),
    ('cutseal_bodyonly_under', Vector((0.12, -0.05, -0.22)), True),
    ('cutseal_bodyonly_tq', Vector((0.22, -0.22, 0.12)), True),
]
for name, off, hide_m in views:
    bpy.data.objects['PSO_ScopeMount'].hide_render = hide_m
    bpy.data.objects['PSO_ScopeLens'].hide_render = hide_m
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'PSO1_A762_cutout_seal_trial.blend'))
(OUT / 'a762_cutout_seal_trial.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('A762_CUTOUT_SEAL_TRIAL', json.dumps(report), flush=True)
