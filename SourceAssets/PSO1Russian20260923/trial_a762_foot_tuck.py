"""Mark non-bore body loops and render. Then trial foot-only cylinder tuck on a copy."""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Vector, Matrix

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R_IN, FOOT_MAX_Z = 0.1024, 0.0200, 0.072

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
mount = bpy.data.objects['PSO_ScopeMount']
lens = bpy.data.objects['PSO_ScopeLens']

# Backup before any edit
bak = OUT / 'PSO1_A762_Editable.before-bodyfix.blend'
if not bak.exists():
    shutil.copy2(O / 'PSO1_A762_Editable.blend', bak)

# Work in source space baked into body
mw = body.matrix_world.copy()
inv = mw.inverted()
bm = bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

# Foot-only patch: same window as PKM foot, plus one ring. Do NOT include upper left jaws.
foot = [v for v in bm.verts if v.co.z < FOOT_MAX_Z and -0.095 < v.co.y < 0.05]
patch = set(foot)
for v in foot:
    for e in v.link_edges:
        patch.add(e.other_vert(v))
# Also include verts that are clearly the open saddle wall: x>0.01, r>0.022, z<0.095, y in foot band
extra = [v for v in bm.verts
         if v.co.x > 0.010 and -0.095 < v.co.y < 0.05 and v.co.z < 0.095
         and math.hypot(v.co.x, v.co.z - AXIS_Z) > 0.022]
for v in extra:
    patch.add(v)
    for e in v.link_edges:
        # only add neighbour if still in the lower saddle band
        ov = e.other_vert(v)
        if ov.co.z < 0.100 and -0.10 < ov.co.y < 0.06:
            patch.add(ov)

projected = 0
for v in patch:
    dx, dz = v.co.x, v.co.z - AXIS_Z
    r = math.hypot(dx, dz)
    if r > R_IN:
        k = R_IN / r
        v.co.x = dx * k
        v.co.z = AXIS_Z + dz * k
        projected += 1

# Write back to world
for v in bm.verts:
    v.co = inv @ (v.co + DELTA)
boundary_after = sum(1 for e in bm.edges if e.is_boundary)
bm.to_mesh(body.data); bm.free(); body.data.update()

# Soften only the patched area normals
for p in body.data.polygons:
    p.use_smooth = True

report = {'foot_seed': len(foot), 'extra_seed': len(extra), 'patch': len(patch),
          'projected': projected, 'boundary_edges': boundary_after}

# Render body+mount+lens
for ob in scene.objects:
    if ob.type == 'MESH':
        keep = ob.name in ('PSO_ScopeBody', 'PSO_ScopeMount', 'PSO_ScopeLens')
        ob.hide_render = not keep
        ob.hide_set(not keep)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
sh.show_backface_culling = True
sh.show_cavity = True; sh.cavity_type = 'BOTH'
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 70
target = DELTA + Vector((0.01, -0.04, 0.09))
for name, off in {
    'foottuck_tq': Vector((0.22, -0.22, 0.12)),
    'foottuck_under': Vector((0.12, -0.05, -0.22)),
    'foottuck_side': Vector((0.30, 0.0, 0.03)),
    'foottuck_bodyonly_under': Vector((0.12, -0.05, -0.22)),
}.items():
    if 'bodyonly' in name:
        mount.hide_render = True; lens.hide_render = True
    else:
        mount.hide_render = False; lens.hide_render = False
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

# Save trial blend separately first; only overwrite editable if visuals look good (done after review)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'PSO1_A762_foottuck_trial.blend'))
(OUT / 'a762_foottuck_trial.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('A762_FOOTTUCK_TRIAL', json.dumps(report), flush=True)
