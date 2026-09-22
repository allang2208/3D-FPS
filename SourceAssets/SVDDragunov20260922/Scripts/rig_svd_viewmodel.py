"""Build the SVD viewmodel: shared Manny arms + the eight SVD parts, rigid-bound to WPN_* bones.

Follows the project's weapon layout: the runtime viewmodel is ONE skeletal mesh containing
the arms and the weapon (M4: SK_M4_FoldingSights_HK416). The arms keep their own skinning;
each SVD part gets an Armature modifier and a single vertex group at weight 1.0, so it rides
its WPN bone rigidly. Placement comes from Scripts/align_to_arms.py (grip matched to the M4
grip, muzzle +Y, no rotation).

Bone map:
    SM_SVD_Body            -> WPN_root          (receiver, barrel, stock, grip)
    SM_SVD_Magazine        -> WPN_SOCKET_Magazine
    SM_SVD_Trigger         -> WPN_Trigger
    SM_SVD_ChargingHandle  -> WPN_ChargingHandle
    SM_SVD_SafetyLever     -> WPN_root          (the rig has no safety bone)
    scope body/mount/lens  -> WPN_root          (a dedicated optic bone can come with the ADS work)

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <case_root>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

PARTS = {
    'SM_SVD_Body': 'WPN_root',
    'SM_SVD_Magazine': 'WPN_SOCKET_Magazine',
    'SM_SVD_Trigger': 'WPN_Trigger',
    'SM_SVD_ChargingHandle': 'WPN_ChargingHandle',
    'SM_SVD_SafetyLever': 'WPN_root',
    'SM_SVD_ScopeBody': 'WPN_root',
    'SM_SVD_ScopeMount': 'WPN_root',
    'SM_SVD_ScopeLens': 'WPN_root',
}
M4_WEAPON_PREFIXES = ('M4_Handguard', 'M4_Flash Hider', 'M4_Magazine', 'M4_Trigger', 'M4_Grip',
                      'M4_M4 Body', 'M4_Stock')


def center(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return sum(pts, Vector((0, 0, 0))) / 8.0


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    m4_fbx = next(Path('D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910').rglob(
        'SK_M4_FoldingSights_HK416.fbx'))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(m4_fbx))
    bpy.context.view_layer.update()
    armature = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    arms = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and 'Arms' in o.name)

    # the SVD replaces the M4 weapon: drop the M4 parts, keep the arms and the skeleton
    removed = []
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o is not arms and any(o.name.startswith(p) for p in M4_WEAPON_PREFIXES):
            removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()

    # replicate the placement computed by align_to_arms.py
    m4_grip_mesh = None
    # (the M4 grip was deleted above; recompute the reference from the bone it was bound to)
    ref = json.loads((case / 'Receipts' / 'alignment.json').read_text(encoding='utf-8-sig'))
    translation = Vector(ref['translation'])
    rot = Matrix.Rotation(math.radians(ref['yaw_deg']), 4, 'Z')

    # Body roll correction (SKILL references/integration.md, ASH-12 case): the ADS calibration
    # aligns the sight axis only - FindBetweenNormals maps one axis and leaves roll free - so a
    # mesh that sits rolled relative to the rig shows up as a crooked gun in ADS. Both weapons
    # are rigid to WPN_root, so the difference against the M4's own body roll is fixed in every
    # pose. Measured in Scripts/measure_roll_vs_m4.py: M4 -3.688 deg, SVD -0.648 deg.
    roll_fix = json.loads((case / 'Receipts' / 'roll_vs_m4.json').read_text(encoding='utf-8-sig'))
    roll_deg = float(roll_fix.get('applied_angle_deg', 0.0))  # see the receipt's decision field
    grip = Vector(roll_fix['grip_contact_m'])
    roll_matrix = (Matrix.Translation(grip)
                   @ Matrix.Rotation(math.radians(roll_deg), 4, 'Y')
                   @ Matrix.Translation(-grip))
    matrix = roll_matrix @ Matrix.Translation(translation) @ rot

    report = {'armature': armature.name, 'arms_mesh': arms.name, 'removed_m4_parts': removed,
              'translation': ref['translation'], 'yaw_deg': ref['yaw_deg'],
              'roll_correction_deg': roll_deg, 'roll_axis': 'Y (barrel)', 'roll_about': list(grip),
              'roll_reference': roll_fix['roll_difference_deg'], 'parts': {}}

    for name, bone in PARTS.items():
        fbx = case / 'Authored' / (name + '.fbx')
        before = set(bpy.context.scene.objects)
        bpy.ops.import_scene.fbx(filepath=str(fbx))
        new = [o for o in bpy.context.scene.objects if o not in before and o.type == 'MESH']
        if not new:
            raise RuntimeError('import produced no mesh for %s' % name)
        obj = new[0]
        obj.name = name
        obj.data.name = name
        obj.matrix_world = matrix @ obj.matrix_world
        bpy.context.view_layer.update()

        # rigid bind: one vertex group at weight 1.0
        if bone not in armature.data.bones:
            raise RuntimeError('bone %r missing from %s' % (bone, armature.name))
        obj.parent = armature
        obj.matrix_parent_inverse = armature.matrix_world.inverted()
        mod = obj.modifiers.new('Armature', 'ARMATURE')
        mod.object = armature
        for vg in list(obj.vertex_groups):
            obj.vertex_groups.remove(vg)
        group = obj.vertex_groups.new(name=bone)
        group.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')

        mn, mx = [min((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box) for i in range(3)], \
                 [max((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box) for i in range(3)]
        report['parts'][name] = {
            'bone': bone, 'verts': len(obj.data.vertices),
            'bbox_min': [round(v, 5) for v in mn], 'bbox_max': [round(v, 5) for v in mx],
        }
        print('BOUND %-24s -> %-22s verts=%d' % (name, bone, len(obj.data.vertices)))

    # weapon-space checks in the rig frame
    body = bpy.context.scene.objects['SM_SVD_Body']
    report['assembled'] = {
        'body_center': [round(v, 5) for v in center(body)],
        'weapon_length_m': round(max((bpy.context.scene.objects[n].matrix_world @ Vector(c)).y
                                     for n in PARTS for c in bpy.context.scene.objects[n].bound_box)
                                 - min((bpy.context.scene.objects[n].matrix_world @ Vector(c)).y
                                       for n in PARTS for c in bpy.context.scene.objects[n].bound_box), 5),
    }

    out = case / 'Authored' / 'SK_SVD_Viewmodel.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    fbx_out = case / 'Authored' / 'SK_SVD_Manny.fbx'
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects:
        if o.type in {'MESH', 'ARMATURE'}:
            o.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.fbx(filepath=str(fbx_out), use_selection=True,
                             object_types={'MESH', 'ARMATURE'}, axis_forward='-Y', axis_up='Z',
                             bake_anim=False, add_leaf_bones=False, mesh_smooth_type='FACE',
                             use_tspace=False, path_mode='COPY')
    report['blend'] = str(out)
    report['fbx'] = str(fbx_out)
    (case / 'Receipts' / 'rig.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('RIG_SVD_DONE', json.dumps({'parts': len(report['parts']), 'fbx': str(fbx_out)}))


main()
