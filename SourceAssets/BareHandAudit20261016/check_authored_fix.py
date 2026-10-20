"""Dry-run generic_fix on the master and all Authored profiles; write nothing but a report."""
import json, multiprocessing
from pathlib import Path
from audit_mesh import audit
from generic_fix import plan_mesh, apply_json, surface_change_mm

O = Path(__file__).parent
B = O.parent / 'ModularOutfit20260925/BarePalmV7'


def run(path):
    d = json.loads(path.read_text())
    ops = plan_mesh(d); fx = apply_json(d, ops); a = audit(fx)
    mm, dropped = surface_change_mm(d, fx)
    return path.stem, dict(notes=dict(ops['notes']), removed=len(ops['remove']), added=len(ops['add']),
                           degenerate=a['degenerate_faces'], winding=a['inconsistent_winding_edges'], nonmanifold=a['nonmanifold_edges'],
                           openings=[(l['region'], l['perimeter_cm']) for l in a['boundary_loops']], dropped=dropped, max_change_mm=mm)


if __name__ == '__main__':
    files = [B / 'M4_original.json'] + sorted((B / 'Authored').glob('*.json'))
    with multiprocessing.Pool(6) as pool:
        rows = dict(pool.map(run, files))
    (O / 'authored_fix_dryrun.json').write_text(json.dumps(rows, indent=1))
    for k, r in rows.items():
        print('%-12s rm %3d add %3d deg %d wind %d nonman %d openings %d dropped %2d change %.2f mm normals %d %s' % (
            k, r['removed'], r['added'], r['degenerate'], r['winding'], r['nonmanifold'], len(r['openings']), r['dropped'],
            r['max_change_mm'], r['notes'].get('normal_corners_replaced', 0),
            {x: y for x, y in r['notes'].items() if x.startswith('fold_') and x != 'fold_regions_fixed' or x == 'needle_face_skipped'}))
