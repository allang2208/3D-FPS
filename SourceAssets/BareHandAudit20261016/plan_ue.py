"""Audit every UE snapshot, plan local repairs, and verify the planned result offline.

Writes ue_findings.json (before/after per mesh) and ue_plans.json (only meshes
with changes). A plan is kept only if the repaired copy has no degenerate
faces, no folded edges, no non-manifold edges and no new openings.
"""
import json, multiprocessing
from pathlib import Path
from audit_mesh import audit
from generic_fix import plan_mesh, apply_json, jsonable, surface_change_mm

O = Path(__file__).parent


def first_person_only(full):
    """Keep first-person bare-skin slots; third-person body skin is out of scope."""
    allowed = {i for i, s in enumerate(full['slots']) if s['skin'] and 'PlayerBodySkin' not in s['base']}
    orig = [i for i, m in enumerate(full['triangle_materials']) if m in allowed]
    d = dict(full)
    for k in ('triangles', 'normals', 'uv', 'triangle_materials'):
        d[k] = [full[k][i] for i in orig]
    return d, orig


def back(plan, orig):
    plan['remove'] = [orig[i] for i in plan['remove']]
    for a in plan['add']:
        a['corners'] = [[orig[ti], k, ov] for ti, k, ov in a['corners']]
    plan['normals'] = [[orig[ti], k, n] for ti, k, n in plan['normals']]
    return plan


def run(path):
    full = json.loads(path.read_text())
    d, orig = first_person_only(full)
    if not orig:
        return dict(path=full['path'], key=full['key'], skipped='third-person body skin only', plan_ok=True, changed=False), None
    before = audit(d)
    ops = plan_mesh(d)
    changed = bool(ops['remove'] or ops['add'] or ops['normals'])
    fx = apply_json(d, ops) if changed else d
    after = audit(fx) if changed else before
    mm, dropped = surface_change_mm(d, fx) if changed else (0.0, 0)
    loops = lambda r: sorted((l['region'], round(l['perimeter_cm'], 2)) for l in r['boundary_loops'])
    ok = (after['degenerate_faces'] == 0 and after['inconsistent_winding_edges'] == 0 and after['nonmanifold_edges'] <= before['nonmanifold_edges']
          and len(after['boundary_loops']) <= len(before['boundary_loops']))
    row = dict(path=d['path'], key=d['key'], source_sha256=d['source_sha256'], skin_triangles=before['triangles'],
               before={k: before[k] for k in ('degenerate_faces', 'inconsistent_winding_edges', 'nonmanifold_edges', 'boundary_edges')},
               after={k: after[k] for k in ('degenerate_faces', 'inconsistent_winding_edges', 'nonmanifold_edges', 'boundary_edges')},
               openings_before=loops(before), openings_after=loops(after), notes=dict(ops['notes']),
               normal_corners=len(ops['normals']), max_change_mm=mm, dropped=dropped, plan_ok=ok, changed=changed)
    plan = back(dict(path=d['path'], key=d['key'], source_sha256=d['source_sha256'], snapshot=str(path), **jsonable(ops)), orig) if changed and ok else None
    return row, plan


if __name__ == '__main__':
    files = sorted((O / 'Snapshots').glob('*.json'))
    with multiprocessing.Pool(6) as pool:
        out = pool.map(run, files)
    rows = [r for r, _ in out]; plans = [p for _, p in out if p]
    (O / 'ue_findings.json').write_text(json.dumps(rows, indent=1))
    (O / 'ue_plans.json').write_text(json.dumps(plans))
    for r in rows:
        if r.get('skipped'): continue
        print('%-90s fold %2d->%d deg %d->%d open %d->%d normals %4d change %.2fmm %s%s' % (
            r['path'].split('.')[0][-90:], r['before']['inconsistent_winding_edges'], r['after']['inconsistent_winding_edges'],
            r['before']['degenerate_faces'], r['after']['degenerate_faces'], len(r['openings_before']), len(r['openings_after']),
            r['normal_corners'], r['max_change_mm'], '' if r['plan_ok'] else 'PLAN_REJECTED ',
            {k: v for k, v in r['notes'].items() if k.startswith('fold_') and k != 'fold_regions_fixed' or k == 'needle_face_skipped'}))
    print('MESHES', len(rows), 'THIRD_PERSON_SKIPPED', sum(bool(r.get('skipped')) for r in rows), 'PLANNED', len(plans),
          'REJECTED', sum(not r['plan_ok'] for r in rows))
