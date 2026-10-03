"""Produce the Witch's connected, skeleton-driven death garment; no previews."""
import bpy
import bmesh
import json
from pathlib import Path
from mathutils import Vector

root = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchCorpseFollow20261002')
source = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Authoring')
bpy.ops.wm.open_mainfile(filepath=str(source/'WitchRebuilt_Master.blend'))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
rig.animation_data_clear()
rig.data.pose_position = 'REST'
bpy.context.view_layer.update()
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and 'SimulationProxy' not in o.name]
lower = next(o for o in meshes if 'OriginalRobe_Render' in o.name or 'LowerRobe' in o.name)
rest = {b.name: b.matrix_local.translation.copy() for b in rig.data.bones}
pelvis = rest['pelvis']
calf_mid = (rest['calf_l'] + rest['calf_r'])*.5
foot_mid = (rest['foot_l'] + rest['foot_r'])*.5
left = rest['thigh_l'] - rest['thigh_r']
left.z = 0
left.normalize()
width = max(1., (rest['thigh_l']-rest['thigh_r']).length)

def smooth(t):
    t = max(0., min(1., t))
    return t*t*(3.-2.*t)

for vertex in lower.data.vertices:
    p = rig.matrix_world.inverted() @ (lower.matrix_world @ vertex.co)
    down = pelvis.z-p.z
    leg = smooth(down/max(1., pelvis.z-calf_mid.z))
    shin = smooth((calf_mid.z-p.z)/max(1., calf_mid.z-foot_mid.z))
    left_weight = .5 + .35*max(-1., min(1., (p-pelvis).dot(left)/width))
    weights = {'pelvis': 1.-leg}
    for side, side_weight in (('l', left_weight), ('r', 1.-left_weight)):
        weights['thigh_'+side] = leg*side_weight*(1.-.65*shin)
        weights['calf_'+side] = leg*side_weight*.55*shin
        weights['foot_'+side] = leg*side_weight*.10*shin
    for group in lower.vertex_groups:
        group.remove([vertex.index])
    for name, weight in weights.items():
        if weight > 1e-6:
            group = lower.vertex_groups.get(name) or lower.vertex_groups.new(name=name)
            group.add([vertex.index], weight, 'REPLACE')

# Restore only the covered leg faces omitted from the live runtime skin. The
# visible, refined hands/feet stay in the Master; no replacement body is generated.
with bpy.data.libraries.load(str(source/'WitchRebuilt_AnatomySource.blend'), link=False) as (available, loaded):
    loaded.objects = [n for n in available.objects if n == 'WitchRebuilt_CompleteBody']
leg_skin = loaded.objects[0]
if leg_skin is None:
    raise RuntimeError('Retained complete anatomical skin is missing')
bpy.context.collection.objects.link(leg_skin)
leg_skin.name = 'WitchCorpse_ContinuousLegSkin'

def omitted_leg(vertex):
    weights = {leg_skin.vertex_groups[g.group].name: g.weight for g in vertex.groups}
    visible_end = sum(w for n, w in weights.items() if n.startswith(
        ('hand_', 'foot_', 'ball_', 'index', 'middle', 'ring', 'pinky', 'thumb', 'neck_', 'head')))
    leg_weight = sum(w for n, w in weights.items() if n.startswith(('thigh_', 'calf_')))
    return visible_end < .5 and vertex.co.z > .15 and leg_weight > .2

keep = [omitted_leg(v) for v in leg_skin.data.vertices]
bm = bmesh.new()
bm.from_mesh(leg_skin.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if not all(keep[v.index] for v in f.verts)], context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.to_mesh(leg_skin.data)
bm.free()
leg_world = leg_skin.matrix_world.copy()
leg_skin.parent = rig
leg_skin.matrix_world = leg_world
for modifier in leg_skin.modifiers:
    if modifier.type == 'ARMATURE':
        modifier.object = rig
meshes.append(leg_skin)

bpy.ops.object.select_all(action='DESELECT')
for obj in [rig, *meshes]:
    obj.hide_set(False)
    obj.hide_render = False
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
root.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(root/'SK_WitchRebuilt_CorpseFollow.fbx'),
    use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
    use_armature_deform_only=False, armature_nodetype='NULL', bake_anim=False,
    axis_forward='-Y', axis_up='Z', apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_UNITS', use_mesh_modifiers=True)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'WitchRebuilt_CorpseFollow.blend'))
result = dict(source_master=str(source/'WitchRebuilt_Master.blend'),
              source_anatomy=str(source/'WitchRebuilt_AnatomySource.blend'),
              corpse_mesh=str(root/'SK_WitchRebuilt_CorpseFollow.fbx'),
              lower_robe=lower.name, restored_leg_skin_vertices=len(leg_skin.data.vertices),
              render_parts=[m.name for m in meshes], no_simulation_proxy_exported=True,
              geometry_uv_materials_preserved=True, runtime_tested=False)
(root/'authoring.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
