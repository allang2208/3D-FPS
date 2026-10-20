"""Write the V8 surface repair into the master and every Authored profile JSON (backups in Before/)."""
import json, shutil, multiprocessing
from pathlib import Path
from audit_mesh import audit
from generic_fix import plan_mesh, apply_json

O = Path(__file__).parent; P = O.parents[1]
B = O.parent / 'ModularOutfit20260925/BarePalmV7'
CONTRACT = 'V8 20261016: fold-free palm/thumb patches, micro-edge collapse, native rest-pose normals; positions/weights/UV retained'


def run(path):
    backup = O / 'Before' / path.relative_to(P)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists(): shutil.copy2(path, backup)
    d = json.loads(backup.read_text())
    if d.get('contract', '').startswith('V8 20261016'): return path.stem, 'already V8'
    ops = plan_mesh(d); fx = apply_json(d, ops); a = audit(fx)
    if a['degenerate_faces'] or a['inconsistent_winding_edges'] or a['nonmanifold_edges']:
        return path.stem, 'REJECTED %s' % {k: a[k] for k in ('degenerate_faces', 'inconsistent_winding_edges', 'nonmanifold_edges')}
    fx['contract'] = CONTRACT
    path.write_text(json.dumps(fx, separators=(',', ':')), encoding='utf-8')
    return path.stem, 'written: -%d +%d faces, %d normal corners' % (len(ops['remove']), len(ops['add']), len(ops['normals']))


if __name__ == '__main__':
    files = [B / 'M4_original.json'] + sorted((B / 'Authored').glob('*.json'))
    with multiprocessing.Pool(6) as pool:
        rows = dict(pool.map(run, files))
    manifest = json.loads((B / 'manifest.json').read_text(encoding='utf-8-sig'))
    for entry in manifest:
        d = json.loads(Path(entry['authored']).read_text())
        entry['vertices'] = len(d['positions']); entry['triangles'] = len(d['triangles'])
    backup = O / 'Before' / (B / 'manifest.json').relative_to(P)
    if not backup.exists(): shutil.copy2(B / 'manifest.json', backup)
    (B / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (O / 'offline_receipt.json').write_text(json.dumps(rows, indent=1))
    for k, v in rows.items(): print(k, v)
