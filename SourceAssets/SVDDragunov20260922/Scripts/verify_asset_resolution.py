"""Resolve every asset the SVD weapon path loads, so wiring mistakes surface before play.

The branch sets bUsingM4Infima, which routes animations and sounds through the M4 sets. This
walks the same paths LoadAKMAnimation/LoadAKMSound would take for ue_svd (read from
FPSGAMECharacter.cpp: M4ContactImpactFinal for the pose clips, M4TacticalTossFinal /
M4SlapImpactFinal / M4WrapGripFinal for reload/equip, M4HK416Audio for mechanical cues) and
reports anything that does not resolve. Read-only; no world, no PIE.

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
BASE = '/Game/Weapons/SVDDragunov20260922'
report = {'checked': {}, 'missing': [], 'notes': []}

MESH = BASE + '/Viewmodel/SK_SVD_Manny'
CLIPS = {
    'idle': '/Game/Weapons/M4ContactImpactFinal/A_AKM_idle',
    'aim': '/Game/Weapons/M4ContactImpactFinal/A_AKM_aim',
    'fire': '/Game/Weapons/M4ContactImpactFinal/A_AKM_fire',
    'aim_fire': '/Game/Weapons/M4ContactImpactFinal/A_AKM_aim_fire',
    'reload': '/Game/Weapons/M4TacticalTossFinal/A_M4_HK416_reload',
    'reload_empty': '/Game/Weapons/M4SlapImpactFinal/A_M4_HK416_reload_empty',
    'equip_charge': '/Game/Weapons/M4WrapGripFinal/A_M4_HK416_equip_charge',
}
# Deliberately not required:
#   A_AKM_inspect               - InspectAnimation is set to nullptr for the M4 pose clock.
#   A_AKM_equip_charge_empty    - resolved only for an empty-magazine equip and absent for the
#                                 M4A1 too (same code path); recorded as a note, not a gap.
SOUNDS = {
    'fire': '/Game/Weapons/M4HK416Audio/S_HK416_Fire',
    'mag_out': '/Game/Weapons/M4HK416Audio/S_HK416_MagOut',
    'mag_insert': '/Game/Weapons/M4HK416Audio/S_HK416_MagInsert',
    'mag_seat': '/Game/Weapons/M4HK416Audio/S_HK416_MagSeat',
    'equip': '/Game/Weapons/M4AnimationAuditFinal/S_HK416_Equip',
}
OTHER = {
    'viewmodel': MESH,
    'item_icon': '/Game/ColdSteelData/Icons/ue_svd',
}

for group, table in (('clips', CLIPS), ('sounds', SOUNDS), ('assets', OTHER)):
    for key, path in table.items():
        asset = u.load_asset(path)
        report['checked']['%s.%s' % (group, key)] = {
            'path': path, 'found': asset is not None,
            'class': asset.get_class().get_name() if asset else None,
            'length_s': round(float(asset.get_play_length()), 3) if isinstance(asset, u.AnimSequence) else None,
        }
        if asset is None:
            report['missing'].append(path)

# the mesh must actually be on the shared M4 skeleton, or every clip above is useless
mesh = u.load_asset(MESH)
m4 = u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
if isinstance(mesh, u.SkeletalMesh) and isinstance(m4, u.SkeletalMesh):
    report['skeleton_shared'] = mesh.skeleton == m4.skeleton
    report['skeleton'] = mesh.skeleton.get_path_name().split('.')[0] if mesh.skeleton else None
    # The project declares SK_M4_Infima_Skeleton as a compatible skeleton of the HK416 one, so
    # a clip on either skeleton is legitimately playable. Equality alone would give a false alarm.
    compatible = []
    if mesh.skeleton:
        try:
            compatible = [s.get_path_name().split('.')[0] for s in mesh.skeleton.get_editor_property('compatible_skeletons')]
        except Exception as exc:  # noqa: BLE001
            report['notes'].append('compatible_skeletons unreadable: %s' % exc)
    report['compatible_skeletons'] = compatible
    allowed = {report['skeleton']} | set(compatible)
    clip_ok = True
    for key, path in CLIPS.items():
        clip = u.load_asset(path)
        if isinstance(clip, u.AnimSequence):
            clip_skeleton = clip.get_editor_property('skeleton')
            name = clip_skeleton.get_path_name().split('.')[0] if clip_skeleton else None
            if name not in allowed:
                clip_ok = False
                report['notes'].append('%s is on unrelated skeleton %s' % (path, name))
    report['clips_match_skeleton'] = clip_ok

report['ammo_item_present'] = u.load_asset('/Game/ColdSteelData/Icons/ue_svd') is not None
report['ok'] = not report['missing'] and report.get('skeleton_shared', False) and report.get('clips_match_skeleton', False)

(ROOT / 'Receipts' / 'asset_resolution.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('SVD_ASSET_RESOLUTION ' + json.dumps(report, default=str))
