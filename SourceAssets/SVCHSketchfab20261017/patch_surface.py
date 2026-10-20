import io
import re
from pathlib import Path

p = Path(r'D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\author_svch.py')
src = p.read_text(encoding='utf-8')

if 'import bmesh' not in src:
    src = src.replace('import bpy\n', 'import bmesh\nimport bpy\nimport math\n', 1)

helper = '''# --------------------------------------------------------------------------
# Surface finishing (skills/ue5-weapon-workflow: geometry before material)
#
# The source is a flat-shaded low-poly mesh with no UVs: every facet reads as a
# separate plate and the WS1 grain has nothing to tile on. Each part gets
#   * smooth shading with sharp edges above SHARP_ANGLE, so barrels shade as
#     cylinders while rails, ports and machined steps stay crisp;
#   * a small chamfer on those hard edges, which gives a low-poly model a
#     highlight to catch instead of a razor-thin silhouette;
#   * a real UV layout so the shared surface master's grain and scratches work.
# --------------------------------------------------------------------------
SHARP_ANGLE = math.radians(35.0)
BEVEL_ANGLE = math.radians(40.0)
BEVEL_WIDTH_M = 0.0006      # 0.6 mm chamfer


def finish_surface(ob, bevel=0.0, uv_angle=66.0):
    """Smooth-by-angle, optional chamfer, and a UV layout."""
    me = ob.data
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))

    bm = bmesh.new()
    bm.from_mesh(me)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            e.smooth = e.calc_face_angle(math.pi) < SHARP_ANGLE
        else:
            e.smooth = False
    bm.to_mesh(me)
    bm.free()
    me.update()

    bpy.context.view_layer.objects.active = ob
    for other in list(bpy.context.selected_objects):
        other.select_set(False)
    ob.select_set(True)

    if bevel > 0.0:
        mod = ob.modifiers.new('SVCH_Bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 1
        mod.limit_method = 'ANGLE'
        mod.angle_limit = BEVEL_ANGLE
        bpy.ops.object.modifier_apply(modifier=mod.name)

    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(uv_angle), island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')


ARTICULATED = {'''

if 'def finish_surface' not in src:
    assert 'ARTICULATED = {' in src
    src = src.replace('ARTICULATED = {', helper, 1)

src = src.replace("mesh_smooth_type='FACE'", "mesh_smooth_type='OFF'")


# call it: weapon parts get the chamfer, arms only smoothing + UVs
old_part = """        ob.modifiers.new('SVCh rigid', 'ARMATURE').object = rig
        objs.append(ob)"""
new_part = """        finish_surface(ob, bevel=BEVEL_WIDTH_M)
        ob.modifiers.new('SVCh rigid', 'ARMATURE').object = rig
        objs.append(ob)"""
if old_part in src and 'finish_surface(ob, bevel' not in src:
    src = src.replace(old_part, new_part, 1)

old_arms = """    arms.parent = rig
    arms.modifiers.new('Armature', 'ARMATURE').object = rig"""
new_arms = """    finish_surface(arms, bevel=0.0, uv_angle=75.0)
    arms.parent = rig
    arms.modifiers.new('Armature', 'ARMATURE').object = rig"""
if old_arms in src and 'finish_surface(arms' not in src:
    src = src.replace(old_arms, new_arms, 1)

p.write_text(src, encoding='utf-8')
print('bmesh import:', 'import bmesh' in src)
print('math import:', '\nimport math\n' in src)
print('helper:', 'def finish_surface' in src)
print('part call:', 'finish_surface(ob, bevel' in src)
print('arms call:', 'finish_surface(arms' in src)
print('smooth type OFF:', "mesh_smooth_type='OFF'" in src)
