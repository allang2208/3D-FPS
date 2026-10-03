import json
from pathlib import Path

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ASH12Fix20260925')
for clip in ('reload_empty', 'quick_melee'):
    rows = json.loads((HERE / f'probe_{clip}.json').read_text())
    print('====', clip, 'camera-space [right, forward, up] cm')
    print('%5s %5s %9s %26s %26s %26s %26s %26s' % ('f', '<20', 'closestF', 'shoulder_r',
                                                    'elbow_r', 'hand_r', 'elbow_l', 'hand_l'))
    for r in rows:
        c = r.get('closest') or {}
        print('%5d %5s %9s %26s %26s %26s %26s %26s' % (
            r['frame'], r.get('onscreen_under_20cm'), c.get('forward_cm'),
            r.get('upperarm_r'), r.get('lowerarm_r'), r.get('hand_r'),
            r.get('lowerarm_l'), r.get('hand_l')))
