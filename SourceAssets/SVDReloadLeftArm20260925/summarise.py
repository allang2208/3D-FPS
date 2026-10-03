import json
from pathlib import Path

JOB = Path(r'D:\FPS3D\FPSGAME\SourceAssets\SVDReloadLeftArm20260925')
print('%-22s %-34s %8s %8s %8s %8s %9s %8s' % ('clip', 'anchor/pole', 'before', 'after',
                                              'worst_b', 'worst_a', 'hand_mm', 'len_mm'))
for family in ['base', 'vertical', 'canted', 'prism', 'angled']:
    for clip in ['reload', 'reload_empty']:
        path = JOB / f'authoring_{family}_{clip}.json'
        if not path.exists():
            continue
        d = json.loads(path.read_text())[f'{family}/{clip}']
        before = [v for v in d['before_min_depth_mm'].values()]
        after = [v for v in d['after_min_depth_mm'].values()]
        key = list(d['before_min_depth_mm'].keys())
        peak_b = max((v, k) for k, v in d['before_min_depth_mm'].items() if v is not None)
        print('%-22s %-34s %8s %8s %8s %8s %9s %8s' % (
            f'{family}/{clip}',
            str(d['params']['anchor']) + ' ' + str(d['params']['elbow_pole']),
            ' '.join(str(d['before_min_depth_mm'][k]) for k in key[:3]),
            ' '.join(str(d['after_min_depth_mm'][k]) for k in key[:3]),
            min(v for v in before if v is not None),
            min(v for v in after if v is not None),
            d['hand_world_delta_mm'], d['bone_length_delta_mm']))
