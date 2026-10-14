import unreal as u, json
from pathlib import Path
rows=[]
for path in ['/Game/Monsters/'+n+'/BP_'+n for n in ('M10Mawcrawler','SpiralPillarM14','VortexCofferM25')]:
    asset=u.load_asset(path)
    if not isinstance(asset,u.Blueprint): continue
    cdo=u.get_default_object(asset.generated_class());row={'asset':path}
    for prop in ('walk_speed','moving_turn_speed','pivot_turn_speed'):
        try: row[prop]=cdo.get_editor_property(prop)
        except Exception: pass
    try:
        move=cdo.get_editor_property('character_movement')
        row.update(max_walk_speed=move.max_walk_speed,rotation_yaw=move.rotation_rate.yaw)
    except Exception: pass
    rows.append(row)
Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014/Reports/movement_reference.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps(rows))
