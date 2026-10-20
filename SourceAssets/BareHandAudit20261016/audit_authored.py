"""Audit the master and every Authored V7 profile (offline JSON), skin sections only."""
import json, multiprocessing
from pathlib import Path
from audit_mesh import audit

O = Path(__file__).parent
B = O.parent / 'ModularOutfit20260925/BarePalmV7'


def run(path):
    d = json.loads(path.read_text())
    mats = d['triangle_materials']
    r = audit(d)
    shoulder = [l for l in r['boundary_loops'] if l['region'] in ('upperarm', 'shoulder') and l['perimeter_cm'] > 20]
    other = [l for l in r['boundary_loops'] if l not in shoulder]
    return path.stem, dict(triangles=r['triangles'], materials=sorted(set(mats)), degenerate=r['degenerate_faces'],
        inconsistent_winding_edges=r['inconsistent_winding_edges'], nonmanifold=r['nonmanifold_edges'],
        shoulder_openings=len(shoulder), other_openings=other, cracks=len(r['boundary_cracks']),
        normal_against_majority=min(r['faces_normal_against_winding'], r['triangles'] - r['faces_normal_against_winding']),
        texel=r['texel_scale_cm_per_uv'])


if __name__ == '__main__':
    files = [B / 'M4_original.json'] + sorted((B / 'Authored').glob('*.json'))
    with multiprocessing.Pool(6) as pool:
        rows = dict(pool.map(run, files))
    (O / 'authored_audit.json').write_text(json.dumps(rows, indent=1))
    for k, r in rows.items():
        print('%-12s tris %6d deg %d wind %2d nonman %d shoulder %d other %d cracks %d normals %d' % (
            k, r['triangles'], r['degenerate'], r['inconsistent_winding_edges'], r['nonmanifold'], r['shoulder_openings'],
            len(r['other_openings']), r['cracks'], r['normal_against_majority']))
        for l in r['other_openings'][:6]:
            print('      opening', l['side'], l['region'], 'perimeter %.2f cm' % l['perimeter_cm'], 'span', l['span_cm'])
