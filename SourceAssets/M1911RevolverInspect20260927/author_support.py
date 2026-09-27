"""Shared native bare-arm binding and animation export helpers; no spin motion."""
import bpy
import bmesh
from pathlib import Path
from mathutils import Matrix, Vector
SOURCES = Path(__file__).resolve().parent.parent
DURATION = 0.0

def install_bare_arms(rig, profile):
    """Transport accepted native V7 skin into the original author rig's bind space."""
    source = SOURCES / f'ModularOutfit20260925/BarePalmV7/Editable/{profile}_BareArmsV7.blend'
    originals = list(bpy.data.objects)
    with bpy.data.libraries.load(str(source), link=False) as (available, selected):
        selected.objects = list(available.objects)
    bare_rig = next(o for o in selected.objects if o and o.type == 'ARMATURE')
    for obj in selected.objects:
        if not obj or obj.type != 'MESH':
            continue
        bpy.context.collection.objects.link(obj)
        transforms = {g.index: rig.data.bones[g.name].matrix_local @ bare_rig.data.bones[g.name].matrix_local.inverted()
            for g in obj.vertex_groups if g.name in rig.data.bones and g.name in bare_rig.data.bones}
        for v in obj.data.vertices:
            influences = [(g.weight, transforms[g.group]) for g in v.groups if g.group in transforms]
            total = sum(w for w, _ in influences)
            if total:
                v.co = sum((m @ v.co * w for w, m in influences), Vector()) / total
        obj.parent = rig
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = Matrix.Identity(4)
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE':
                mod.object = rig
        obj['inspect_skin_source'] = str(source)
    bpy.data.objects.remove(bare_rig, do_unlink=True)
    # Source scenes may combine gun and historical glove geometry. Keep only
    # their weapon-weighted faces; the accepted bare surface supplies the arms.
    for obj in originals:
        if obj.type != 'MESH' or not any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers):
            continue
        weapon_groups = {g.index for g in obj.vertex_groups if g.name.startswith('WPN_')}
        keep = {v.index for v in obj.data.vertices if sum(g.weight for g in v.groups if g.group in weapon_groups) > .5}
        if not keep:
            obj.hide_render = True
            obj.hide_set(True)
            continue
        bm = bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context='VERTS')
        bm.to_mesh(obj.data); bm.free(); obj.data.update()
    return str(source)

def bake_action(rig, scene, name, rows, frames):
    action = bpy.data.actions.new(name); action.use_fake_user = True
    rig.animation_data.action = action
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
        for prop in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(prop, frame=0)
    curves = {(c.data_path, c.array_index): c for c in action.layers[0].strips[0].channelbag(action.slots[0]).fcurves}
    for n in rows[0]:
        for prop, field, size in [('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)]:
            for axis in range(size):
                c = curves[(f'pose.bones["{n}"].{prop}', axis)]
                c.keyframe_points.clear(); c.keyframe_points.add(len(frames))
                c.keyframe_points.foreach_set('co', [v for frame, row in zip(frames, rows) for v in (frame, row[n][field][axis])])
                for k in c.keyframe_points:
                    k.interpolation = 'LINEAR'
                c.update()
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_start = 0; scene.frame_end = round(DURATION * 60); scene.frame_set(0)
    return action
