import json
from pathlib import Path

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ASH12Fix20260925')
for clip, frames in (('reload_empty', None), ('quick_melee', None)):
    path = HERE / f'probe_{clip}.json'
    if not path.exists():
        continue
    rows = json.loads(path.read_text())
    print('====', clip, len(rows), 'frames')
    print('%5s %9s %9s %28s %28s %28s' % ('f', 'under20', 'closest_fwd', 'upperarm_r[R,F,U]',
                                          'lowerarm_r(elbow)[R,F,U]', 'hand_r[R,F,U]'))
    for r in rows:
        c = r.get('closest') or {}
        print('%5d %9s %9s %28s %28s %28s' % (
            r['frame'], r.get('onscreen_under_20cm'), c.get('forward_cm'),
            r.get('upperarm_r'), r.get('lowerarm_r'), r.get('hand_r')))
