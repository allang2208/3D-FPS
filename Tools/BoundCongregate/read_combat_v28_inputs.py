"""Read the live authoring defaults needed to apply percentage changes once."""
from pathlib import Path
import json
import unreal as u
out=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/CombatV28')
out.mkdir(exist_ok=True)
bp=u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate')
cdo=u.get_default_object(bp.generated_class())
fields=('flurry_range','flurry_palm_radius','flurry_damage','flurry_finisher_damage','flurry_cooldown',
        'bite_trigger_range','bite_reach','bite_damage','bite_contact_seconds','bite_cooldown',
        'tentacle_range','tentacle_windup_seconds','tentacle_strike_seconds','tentacle_recover_seconds',
        'tentacle_cooldown','tentacle_impact_damage','tentacle_tick_damage')
report={key:cdo.get_editor_property(key) for key in fields}
report.update({key:cdo.get_editor_property(key).get_path_name() for key in ('visual_mesh','flurry_clip','bite_clip')})
path=out/'before_values.json'
if not path.exists():path.write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report),flush=True)
