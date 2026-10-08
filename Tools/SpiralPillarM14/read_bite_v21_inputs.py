"""Read the active M14 bite settings as inputs to the V21 asset revision."""
import json
from pathlib import Path
import unreal as u

out = Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004/ProductionV21/Records')
out.mkdir(parents=True, exist_ok=True)
bp = u.load_asset('/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14')
cdo = u.get_default_object(bp.generated_class())
result = {}
for key in ('bite_clip', 'bite_sound', 'visual_mesh', 'idle_clip'):
    asset = cdo.get_editor_property(key)
    result[key] = asset.get_path_name() if asset else None
for key in ('bite_contact_seconds', 'bite_trigger_range', 'mouth_reach', 'bite_cooldown'):
    result[key] = float(cdo.get_editor_property(key))
result['duration_seconds'] = cdo.get_editor_property('bite_clip').get_play_length()
result['skeleton'] = cdo.get_editor_property('visual_mesh').skeleton.get_path_name()
(out / 'active_inputs.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
print('M14_V21_INPUTS ' + json.dumps(result))
