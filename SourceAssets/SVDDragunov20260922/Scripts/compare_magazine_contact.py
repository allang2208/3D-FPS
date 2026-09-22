"""Compare the M4's magazine/socket relationship with the SVD's, for the reused reload clips.

The SVD is wired to ride the M4's animation set, so the reload clip drives
WPN_SOCKET_Magazine along a path authored for the M4's magazine. This measures where each
weapon's magazine actually sits relative to that shared bone; a large difference means the
hand meets the magazine at a different point than the clip was authored for.

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


def centre(obj):
    return sum((obj.matrix_world @ Vector(c) for c in obj.bound_box), Vector()) / 8.0


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    m4_fbx = next(Path('D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910').rglob(
        'SK_M4_FoldingSights_HK416.fbx'))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(m4_fbx))
    bpy.context.view_layer.update()
    armature = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    m4_mag = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and 'Magazine' in o.name)
    m4_bolt = next((o for o in bpy.context.scene.objects if o.type == 'MESH' and 'Body' in o.name), None)

    def bone_bind(name):
        bone = armature.data.bones.get(name)
        return armature.matrix_world @ bone.head_local if bone else None

    socket = bone_bind('WPN_SOCKET_Magazine')
    trigger_bone = bone_bind('WPN_Trigger')
    report = {
        'm4': {
            'magazine_center': [round(v, 5) for v in centre(m4_mag)],
            'magazine_size': [round(v, 5) for v in (m4_mag.dimensions)],
            'WPN_SOCKET_Magazine': [round(v, 5) for v in socket] if socket else None,
            'magazine_relative_to_socket': [round(v, 5) for v in (centre(m4_mag) - socket)] if socket else None,
        },
    }

    # SVD: rebuild the aligned assembly in the same rig frame
    ref = json.loads((case / 'Receipts' / 'alignment.json').read_text(encoding='utf-8-sig'))
    placement = Matrix.Translation(Vector(ref['translation'])) @ Matrix.Rotation(math.radians(ref['yaw_deg']), 4, 'Z')
    inv = placement.inverted()
    svd = {}
    for name in ('SM_SVD_Magazine', 'SM_SVD_ChargingHandle', 'SM_SVD_Body'):
        bpy.ops.import_scene.fbx(filepath=str(case / 'Authored' / (name + '.fbx')))
        obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith(name))
        obj.name = name
        obj.matrix_world = placement @ obj.matrix_world
        svd[name] = obj
    bpy.context.view_layer.update()

    mag_centre_model = inv @ centre(svd['SM_SVD_Magazine'])
    socket_model = inv @ socket
    report['svd'] = {
        'magazine_center': [round(v * 100, 2) for v in mag_centre_model],
        'magazine_size_cm': [round(v * 100, 2) for v in svd['SM_SVD_Magazine'].dimensions],
        'WPN_SOCKET_Magazine': [round(v * 100, 2) for v in socket_model],
        'magazine_relative_to_socket_cm': [round(v * 100, 2) for v in (mag_centre_model - socket_model)],
        'charger_handle_relative_to_trigger_bone_cm': [
            round(v * 100, 2) for v in ((inv @ centre(svd['SM_SVD_ChargingHandle'])) - (inv @ trigger_bone))],
    }
    m4_rel = report['m4']['magazine_relative_to_socket']
    report['delta_magazine_vs_m4_cm'] = [round((report['svd']['magazine_relative_to_socket_cm'][i] / 100 - m4_rel[i]) * 100, 2)
                                         for i in range(3)]
    (case / 'Receipts' / 'magazine_contact.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('MAGAZINE_CONTACT', json.dumps(report, default=str))


main()
