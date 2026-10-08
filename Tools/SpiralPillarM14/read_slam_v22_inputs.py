"""Read the currently bound slam as authoring input; no gameplay is run."""
from pathlib import Path
import json
import unreal as u

out = Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004/ProductionV22/Records')
out.mkdir(parents=True, exist_ok=True)
bp = u.load_asset('/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14')
cdo = u.get_default_object(bp.generated_class())
result = {}
for key in ('trunk_slam_clip', 'trunk_slam_sound', 'visual_mesh', 'bite_clip', 'bite_sound'):
    asset = cdo.get_editor_property(key)
    result[key] = asset.get_path_name() if asset else None
for key in ('slam_contact_seconds', 'slam_cooldown', 'slam_min_range', 'slam_trigger_range',
            'slam_damage_multiplier', 'slam_body_radius', 'bite_contact_seconds'):
    result[key] = float(cdo.get_editor_property(key))
result['duration_seconds'] = cdo.get_editor_property('trunk_slam_clip').get_play_length()
result['skeleton'] = cdo.get_editor_property('visual_mesh').skeleton.get_path_name()
result['pie_active'] = bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world())
(out / 'active_inputs.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
print('M14_V22_INPUTS ' + json.dumps(result))
