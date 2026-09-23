"""Continue prepared assets when the explicitly bounded statue is unambiguous."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
source=json.loads((ROOT/'Sources/scene.json').read_text())
if not source.get('native_hazard_ready'):
    print('DUNGEON_AWAITING_NATIVE_BUILD')
else:
    config=ROOT/'Config/scene-actions.json'
    if not config.exists():
        candidates=[a for a in source['actors'] if 4480<a['location'][0]<4950 and -4520<a['location'][1]<-3900 and not a['label'].startswith('DGN_RS_')]
        if len(candidates)!=1:
            print('DUNGEON_STATUE_SELECTION_REQUIRED',[(a['label'],a['location']) for a in candidates])
        else:
            statue=candidates[0];rotation=dict(statue['rotation']);rotation['yaw']-=90
            config.parent.mkdir(exist_ok=True)
            config.write_text(json.dumps({'statue':{'actor_path':statue['path'],'label':statue['label'],'rotation':rotation,'reason':'Turn the profile shown facing image-left towards the opening, outward along world -X; preserve the world bounds center.'}},indent=2),encoding='utf-8')
    if config.exists():
        p=ROOT/'Scripts/finalize_assets.py'
        exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
