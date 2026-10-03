"""Render SVD and A762 ScopeBody-only from the same relative camera for comparison."""
import bpy
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets')
OUT = O / 'PSO1Russian20260923/inspect_akm_a762'

def render_body(blend, body_name, delta, tag):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    for ob in scene.objects:
        if ob.type == 'MESH':
            keep = ob.name == body_name
            ob.hide_render = not keep; ob.hide_set(not keep)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 1600; scene.render.resolution_y = 1000
    sh = scene.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (0.65, 0.65, 0.67)
    sh.show_backface_culling = True; sh.show_cavity = True; sh.cavity_type = 'BOTH'
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 70
    target = Vector(delta) + Vector((0.0, -0.04, 0.10))
    for name, off in {
        'under': Vector((0.12, -0.05, -0.22)),
        'tq': Vector((0.22, -0.22, 0.12)),
    }.items():
        cam.location = target + off
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(OUT / ('%s_bodyonly_%s.png' % (tag, name)))
        bpy.ops.render.render(write_still=True)
    print('RENDERED', tag, flush=True)

render_body(O/'PSO1Russian20260923/PSO1_A762_Editable.blend', 'PSO_ScopeBody', (0.010, -0.015, 0.035), 'A762')
render_body(O/'SVDMatteDetail20260923/SVD_MatteDetail_Editable.blend', 'SM_SVD_ScopeBody', (0.0, 0.0, 0.0), 'SVD')
print('COMPARE_RENDER_DONE', flush=True)
