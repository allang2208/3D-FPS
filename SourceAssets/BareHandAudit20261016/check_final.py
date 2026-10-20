"""Compare read-back snapshots (Final/) with their pre-repair snapshots (Snapshots/)."""
import json, sys
from pathlib import Path
import numpy as np
from audit_mesh import audit
from plan_ue import first_person_only

O = Path(__file__).parent


def keyed(d):
    v = np.asarray(d['positions']); k = [tuple(x) for x in np.round(v / 1e-4).astype(np.int64)]
    return k


def check(key):
    before, _ = first_person_only(json.loads((O / 'Snapshots' / (key + '.json')).read_text()))
    after, _ = first_person_only(json.loads((O / 'Final' / (key + '.json')).read_text()))
    a = audit(after); b = audit(before)
    kb, ka = keyed(before), keyed(after)
    wb = {k: before['weights'][i] for i, k in enumerate(kb)}
    used = {ka[x] for f in after['triangles'] for x in f}
    new_positions = [k for k in used if k not in wb]
    wdiff = 0.0
    for i, k in enumerate(ka):
        if k in wb:
            w1, w2 = wb[k], after['weights'][i]
            wdiff = max(wdiff, sum(abs(w1.get(n, 0) - w2.get(n, 0)) for n in set(w1) | set(w2)))
    loops = lambda r: sorted((l['region'], round(l['perimeter_cm'], 2)) for l in r['boundary_loops'])
    return dict(path=after['path'], triangles=(b['triangles'], a['triangles']), degenerate=a['degenerate_faces'],
                folds=a['inconsistent_winding_edges'], nonmanifold=a['nonmanifold_edges'], openings_same=loops(a) == loops(b),
                new_positions=len(new_positions), max_weight_difference=round(wdiff, 6))


if __name__ == '__main__':
    keys = [f.stem for f in (O / 'Final').glob('*.json') if f.stem != 'index']
    rows = [check(k) for k in keys]
    (O / 'final_checks.json').write_text(json.dumps(rows, indent=1))
    bad = [r for r in rows if r['degenerate'] or r['folds'] or not r['openings_same'] or r['new_positions'] or r['max_weight_difference'] > 1e-4]
    for r in rows if len(rows) < 6 else bad: print(r)
    print('CHECKED', len(rows), 'PROBLEMS', len(bad))
