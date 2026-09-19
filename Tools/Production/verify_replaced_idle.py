"""Fresh-process check of the replaced axe idle. Read-only.

Confirms the equipped-axe idle now carries the two-hand clip and that the other four clips of the
set plus the pickaxe clips are untouched.
"""
import json
import math
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
GRIP = '/Game/Items/ProductionTools/GripMotion20260913'
report = {'clips': {}}


def sample_travel(animation, bone):
    """Rotation sweep of one bone across the clip: proves the track carries animation."""
    library = u.AnimationLibrary
    first = None
    worst = 0.0
    length = animation.get_play_length()
    for step in range(9):
        time = length * step / 8.0
        quat = library.get_bone_pose_for_time(animation, bone, time, False).rotation
        q = (quat.w, quat.x, quat.y, quat.z)
        if first is None:
            first = q
            continue
        dot = abs(sum(a * b for a, b in zip(first, q)))
        worst = max(worst, 2.0 * math.degrees(math.acos(max(-1.0, min(1.0, dot)))))
    return round(worst, 4)


for clip in ['Idle', 'Walk', 'Equip', 'Swing', 'HitRecover']:
    animation = u.load_asset(f'{GRIP}/A_Harvest_Axe_{clip}')
    entry = {'loaded': bool(animation)}
    if animation:
        skeleton = animation.get_editor_property('skeleton')
        entry.update({'play_length_s': round(animation.get_play_length(), 4),
                      'skeleton': skeleton.get_path_name() if skeleton else None})
        if clip == 'Idle':
            entry['lowerarm_r_rotation_travel_deg'] = sample_travel(animation, 'lowerarm_r')
            entry['hand_l_rotation_travel_deg'] = sample_travel(animation, 'hand_l')
    report['clips'][clip] = entry

for clip in ['Idle', 'Walk', 'Equip', 'Swing', 'HitRecover']:
    animation = u.load_asset(f'{GRIP}/A_Harvest_Pickaxe_{clip}')
    report['clips']['Pickaxe_' + clip] = {'loaded': bool(animation),
                                          'play_length_s': round(animation.get_play_length(), 4) if animation else None}

(ROOT / 'SourceAssets/KimodoAxeIdle20260919/idle-readback.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
u.log('AXE_IDLE_READBACK_DONE')