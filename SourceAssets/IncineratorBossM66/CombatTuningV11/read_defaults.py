"""Read configured lord combat baselines and M66's current attack defaults."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/CombatTuningV11')
(ROOT/'Records').mkdir(parents=True,exist_ok=True)
sources={
    'M88':('/Game/Monsters/BoundCongregate/BP_BoundCongregate',['rank','level','bite_damage','bite_trigger_range','bite_reach','bite_cooldown','flurry_damage','flurry_finisher_damage','flurry_range','flurry_cooldown']),
    'M20':('/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler',['rank','level','physical_attack','bite_trigger_range','bite_cooldown']),
    'FleshHand':('/Game/Monsters/FleshHand/BP_FleshHand',['rank','level','physical_attack','hammer_range','slam_radius']),
    'HandBrain':('/Game/Monsters/HandBrain/BP_HandBrain',['rank','level','physical_attack','slam_trigger_range','slam_radius','slam_cooldown']),
    'M66':('/Game/Monsters/IncineratorBossM66/BP_M66RigPreview',['rank','level','sweep_damage','sweep_trigger_range','sweep_hit_radius','sweep_cooldown','stopping_distance','visual_mesh','sweep_clip'])}
report={}
for name,(path,keys) in sources.items():
    bp=u.load_asset(path)
    if not bp:raise RuntimeError('Missing combat reference: '+path)
    cdo=u.get_default_object(bp.generated_class());row={'asset':path}
    for key in keys:
        value=cdo.get_editor_property(key)
        row[key]=value if isinstance(value,(int,float,bool,str)) else value.get_path_name() if isinstance(value,u.Object) else str(value)
    report[name]=row
(ROOT/'Records/combat_references.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M66_COMBAT_REFERENCE '+json.dumps(report,ensure_ascii=False))
