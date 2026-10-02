"""Read retained finger tracks needed by the new mesh reference bind."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent
clips=json.loads((O.parent/'pose_sources.json').read_text(encoding='utf-8'))
left={n for n in clips[0]['poses'][0]['bones'] if n.endswith('_l') and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))}
rows=[]
for clip in clips:
    a=u.load_asset(clip['path'])
    names={str(n) for n in u.AnimationLibrary.get_animation_track_names(a)}
    rows.append(dict(path=clip['path'],missing_left_digit_tracks=sorted(left-names),track_count=len(names)))
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
(O/'animation_contract.json').write_text(json.dumps(dict(clips=rows,
    skeleton_modifier_available=hasattr(u,'SkeletonModifier'),game_world=world.get_name() if world else None),indent=2),encoding='utf-8')
u.log('CLOVEN_M16_NEUTRAL_ANIMATION_CONTRACT_READ '+str(len(rows)))
