"""Compare the requested left-arm source diagnosis against UE sequence samples."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
OUT = Path(__file__).resolve().parent
result = dict(runtime_tested=False, bodies={})
for label in ('jason', 'kaitlin'):
    result['bodies'][label] = {}
    for stage, sample_file, source_dir in [
        ('before', 'installed-before.json', OUT.with_name('KukriDashHands20261028')),
        ('after', 'saved-samples.json', OUT)]:
        captured = json.loads((OUT / sample_file).read_text())['bodies'][label]
        source = json.loads((source_dir / (label + '-actions.json')).read_text())
        names = {n: i for i, n in enumerate(source['names'])}
        frames = np.asarray(source['clips']['Dash']['frames'])
        errors = []
        for t, row in captured['frames'].items():
            k = round(float(t) * source['clips']['Dash']['rate_num'])
            for name, q in row.items():
                errors.append(float(np.degrees((R.from_quat(frames[k, names[name], 3:7]).inv() * R.from_quat(q)).magnitude())))
        result['bodies'][label][stage] = dict(asset=captured['asset'], max_source_sample_error_degrees=max(errors))
        if max(errors) > .01:
            raise RuntimeError('Saved pose differs from author source: ' + label + ' ' + stage + ' ' + str(max(errors)))
(OUT / 'saved-comparison.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
