"""Derive the recipe folio from the actual equipped spellbook. No renders."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
SOURCE = PROJECT / 'SourceAssets/SpellbookEvildeer20261009/PagesV1/Spellbook_16Pages.blend'
OUT = ROOT / 'Export'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01
rig = bpy.data.objects['SpellbookRig']
skin = bpy.data.objects['SK_Spellbook_Alchemy_16Pages']
rig.animation_data_clear()
rig.matrix_world = Matrix.Identity(4)
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
    bone.rotation_mode = 'XYZ'
rig.pose.bones['Cover_Front'].rotation_euler.y = math.pi
for p in range(7):
    leaf = rig.pose.bones[f'Page_{p+1}_00']
    leaf.rotation_euler.y = math.pi if p < 3 else 0
    leaf.location.z = .10 + .02 * (p if p < 3 else 6-p)
bpy.context.view_layer.update()

evaluated = skin.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=bpy.context.evaluated_depsgraph_get())
width = max(v.co.x for v in skin.data.vertices)
height = max(v.co.y for v in skin.data.vertices) - min(v.co.y for v in skin.data.vertices)
lift = -min(v.co.z for v in mesh.vertices)
left_groups = {g.index for g in skin.vertex_groups if g.name.startswith('Page_3_')}
right_groups = {g.index for g in skin.vertex_groups if g.name.startswith('Page_4_')}
left_verts = {v.index for v in skin.data.vertices if any(g.group in left_groups for g in v.groups)}
right_verts = {v.index for v in skin.data.vertices if any(g.group in right_groups for g in v.groups)}
left_mat = bpy.data.materials.new('RecipeLeft')
right_mat = bpy.data.materials.new('RecipeRight')
old_slots = len(mesh.materials)
mesh.materials.append(left_mat)
mesh.materials.append(right_mat)
uv = mesh.uv_layers.active.data
for face in mesh.polygons:
    if face.normal.z < .9 or face.material_index < 2:
        continue
    side = -1 if all(v in left_verts for v in face.vertices) else 1 if all(v in right_verts for v in face.vertices) else 0
    if not side:
        continue
    face.material_index = old_slots + (side > 0)
    for li in face.loop_indices:
        co = mesh.vertices[mesh.loops[li].vertex_index].co
        # Whole-page UVs: leave the original cover/edge UVs completely intact.
        uv[li].uv = ((co.x+width)/width if side < 0 else co.x/width, co.y/height+.5)
for vertex in mesh.vertices:
    vertex.co.z += lift
body = bpy.data.objects.new('SM_AlchemyManualOpen', mesh)
scene.collection.objects.link(body)

# The page is the existing thin double-sided, subdivided leaf, not a box.
turn_mesh = mesh.copy()
bm = bmesh.new(); bm.from_mesh(turn_mesh)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in right_verts], context='VERTS')
bm.to_mesh(turn_mesh); bm.free()
turn_uv = turn_mesh.uv_layers.active.data
for face in turn_mesh.polygons:
    if abs(face.normal.z) < .9:
        continue
    front = face.normal.z > 0
    face.material_index = old_slots + (1 if front else 0)
    for li in face.loop_indices:
        co = turn_mesh.vertices[turn_mesh.loops[li].vertex_index].co
        turn_uv[li].uv = (co.x/width if front else 1-co.x/width, co.y/height+.5)
for v in turn_mesh.vertices:
    v.co.z -= lift + .16
    v.co.z += .12 * math.sin(math.pi * v.co.x / width)
turn = bpy.data.objects.new('SM_AlchemyManualLeaf', turn_mesh)
scene.collection.objects.link(turn)

closed_source = bpy.data.objects['SM_Spellbook_Alchemy_Closed']
closed = bpy.data.objects.new('SM_AlchemyManualClosed', closed_source.data.copy())
scene.collection.objects.link(closed)
bottom = min(v.co.z for v in closed.data.vertices)
for v in closed.data.vertices:
    v.co.x -= width/2
    v.co.z -= bottom

records=[]
for obj in (body, turn, closed):
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False); obj.select_set(True); bpy.context.view_layer.objects.active=obj
    # Compact unused slots but preserve their existing material identities.
    used=sorted({p.material_index for p in obj.data.polygons})
    mats=[obj.data.materials[i] for i in used]
    indices=[used.index(p.material_index) for p in obj.data.polygons]
    obj.data.materials.clear()
    for m in mats:obj.data.materials.append(m)
    for face,index in zip(obj.data.polygons,indices):face.material_index=index
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')), use_selection=True, object_types={'MESH'},
        axis_forward='-Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
        mesh_smooth_type='FACE', use_tspace=False, bake_anim=False, path_mode='STRIP')
    obj.data.calc_loop_triangles()
    records.append(dict(name=obj.name,materials=[m.name for m in mats],triangles=len(obj.data.loop_triangles)))
for obj in list(scene.objects):
    if obj not in (body,turn,closed):bpy.data.objects.remove(obj,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'AlchemyManual.blend'))
spec=dict(source=str(SOURCE),parts=records,width_cm=width,height_cm=height,leaf_height_cm=lift+.20,
    author='evildeer',license='CC BY 4.0',rendered=False)
(ROOT/'manifest.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
header=PROJECT/'Source/FPSGAME/Building/AlchemyManualGeometry.h'
header.write_text('#pragma once\n// Authored from the existing spellbook; centimetres, spine origin.\n'
    +f'namespace AlchemyManualGeometry {{ constexpr float LeafHeight={lift+.20:.8f}f; constexpr float Width={width:.8f}f; constexpr float Height={height:.8f}f; }}\n',encoding='utf-8')
print('ALCHEMY_MANUAL_EXPORTED '+json.dumps(spec),flush=True)
