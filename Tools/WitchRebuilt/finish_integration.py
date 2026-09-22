"""Persist the completed import/build boundary, without running the candidate."""
import unreal as u,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
report=json.loads((root/'ue_delivery.json').read_text())
required={'mesh','cloth','bottle',*('animation_'+n for n in ('Idle','Walk','CastPoison','ThrowPoisonBottle','Hit','DeathBackward','TurnLeft','TurnRight'))}
if not required.issubset(report['completed']):raise RuntimeError('Import stages remain: '+str(sorted(required-set(report['completed']))))
cls=u.load_class(None,'/Script/FPSGAME.WitchRebuiltMonster')
if not cls:raise RuntimeError('Native candidate class has not been loaded')
report.update({'status':'Native class and isolated assets integrated; runtime/visual test pending user',
               'f6':{'id':'WitchRebuilt','label':'巫婆·重建候选','class':'/Script/FPSGAME.WitchRebuiltMonster'},
               'runtime_tested':False,'visual_tested':False})
(root/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Saved candidate integration record; no PIE or rendering performed')
