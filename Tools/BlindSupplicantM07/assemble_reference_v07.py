"""Assemble original-source hand/hindleg authoring into one true rest rig."""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'RecoveryOriginalV07/rig_motion'


def make_reference():
    hand_path = ROOT/'RecoveryOriginalV07/hands/hand_anatomy_v07.json'
    leg_path = ROOT/'RecoveryOriginalV07/legs/hindleg_anatomy_v07.json'
    hands = json.loads(hand_path.read_text(encoding='utf-8'))
    legs = json.loads(leg_path.read_text(encoding='utf-8'))
    record = json.loads((ROOT/'RecoveryOriginalV06/rig_motion/original_rig_guides.json').read_text(encoding='utf-8'))
    old = record['joint_guides_source']
    scale = 2.06087560339
    ground = -.7519199848

    def convert(point):
        return Vector((point[0]*scale, -point[2]*scale, (point[1]-ground)*scale))

    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'RecoveryOriginalV06/rig_motion/M07_OriginalReference_Meter_V06.blend'))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    rig.name = 'Armature'
    rig.data.name = 'M07_OriginalReferenceV07'
    rig.animation_data_clear()
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    edit = rig.data.edit_bones

    def set_bone(name, a, b, parent, roll_axis=None):
        bone = edit.get(name) or edit.new(name)
        bone.head, bone.tail = convert(a), convert(b)
        bone.use_connect = False
        bone.parent = edit[parent] if parent else None
        if roll_axis is not None:
            bone.align_roll(Vector((roll_axis[0], -roll_axis[2], roll_axis[1])))
        return bone

    for side in ('l', 'r'):
        hand = hands['sides'][side]
        wrist = hand['wrist_source']
        chains = hand['finger_chains_source']
        palm = hand['hand_normal_source']
        set_bone('hand_'+side, wrist, chains['middle'][0], 'lowerarm_'+side, palm)
        old['hand_'+side] = wrist
        # Keep the arm shaft centered on its original shoulder and elbow.
        edit['lowerarm_'+side].tail = convert(wrist)
        for name, spec in hand['bones_source'].items():
            bone = set_bone(name, spec['head_source'], spec['tail_source'], hand['bone_parent'][name], palm)
            if 'frame_axes_source_columns' in spec:
                columns = [Vector((v[0], -v[2], v[1])) for v in spec['frame_axes_source_columns']]
                frame = Matrix(columns).transposed().to_4x4()
                frame.translation = convert(spec['head_source'])
                bone.matrix = frame
                bone.length = (convert(spec['tail_source'])-bone.head).length
    for name, point in legs['joints_source'].items():
        old[name] = point
    bpy.ops.object.mode_set(mode='OBJECT')
    sys.path.insert(0, str(Path(__file__).parent))
    import author_hindlegs_v07
    author_hindlegs_v07.apply_reference(rig, unit_scale=1)
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.matrix_basis = Matrix.Identity(4)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    scene.render.fps = 30
    scene.frame_set(0)
    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT/'M07_OriginalReference_Meter_V07.blend'
    rig['reference_revision'] = 'OriginalV07'
    rig['visible_geometry_source'] = 'Original Meshy GLB only'
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    record.update({'revision': 'OriginalV07', 'joint_guides_source': old,
        'joint_guides_m': {n: list(convert(p)) for n, p in old.items()},
        'finger_fit_method': 'Original surface finger branches and MCP/PIP/DIP chains; weighted metacarpals and separate thumb CMC',
        'finger_guides_m': {finger+'_'+side: [list(convert(p)) for p in chain[:3]]
            for side, hand in hands['sides'].items() for finger, chain in hand['finger_chains_source'].items()},
        'finger_tip_guides_m': {finger+'_'+side: list(convert(chain[3]))
            for side, hand in hands['sides'].items() for finger, chain in hand['finger_chains_source'].items()},
        'hand_anatomy_source': str(hand_path), 'hindleg_anatomy_source': str(leg_path),
        'bone_count': len(rig.data.bones), 'bone_names': list(rig.data.bones.keys()),
        'parents': {b.name: b.parent.name if b.parent else None for b in rig.data.bones},
        'meter_reference_source': str(destination),
        'tested': False, 'rendered': False, 'user_accepted': False})
    (OUT/'original_rig_guides.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print('M07_ORIGINAL_V07_ANATOMICAL_REFERENCE_SAVED '+str(destination), flush=True)
    return destination
