"""Compare this sight import with its source and the preserved R1 body."""
import gzip
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

O = Path(__file__).parent

def read(name):
    with gzip.open(O / ('saved_' + name + '.json.gz'), 'rt') as f:
        d = json.load(f)
    d['v'] = np.asarray(d['vertices'])
    d['t'] = np.asarray(d['triangles'])
    d['m'] = np.asarray(d['material_ids'])
    return d

def distance(a, b):
    return float(max(cKDTree(a).query(b)[0].max(), cKDTree(b).query(a)[0].max()))

before, after = read('before'), read('after')
report = {'body_materials': {}, 'after_triangles': len(after['t'])}
for name in before['materials']:
    if name == 'SVCH_New_FactorySights':
        continue
    a = before['t'][before['m'] == before['materials'].index(name)]
    b = after['t'][after['m'] == after['materials'].index(name)]
    error = distance(before['v'][np.unique(a)], after['v'][np.unique(b)]) * 10
    report['body_materials'][name] = {'before_triangles': len(a), 'after_triangles': len(b), 'max_position_error_mm': error}
expected = np.load(O / 'export_expected_vertices.npy') * [100, -100, 100]
report['source_to_saved_max_position_error_mm'] = distance(expected, after['v']) * 10
report['body_preserved'] = all(x['before_triangles'] == x['after_triangles'] and x['max_position_error_mm'] < .01 for x in report['body_materials'].values())
report['source_matches_saved'] = report['source_to_saved_max_position_error_mm'] < .01
(O / 'saved_geometry_check.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
if not report['body_preserved'] or not report['source_matches_saved']:
    raise SystemExit(1)
