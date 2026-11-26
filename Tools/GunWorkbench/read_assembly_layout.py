"""Read current saved mesh bounds for the requested all-firearm placement diagnosis.

Run through Unreal's PythonScript commandlet. Does not spawn gameplay, render,
modify assets, or save packages.
"""
import datetime
import hashlib
import json
from pathlib import Path
import unreal as u

project = Path(u.Paths.project_dir()).resolve()
root = project/'SourceAssets/GunAssemblyReachability20261025'
root.mkdir(parents=True, exist_ok=True)
catalog = project/'Content/ColdSteelData/gun-assembly.json'
recipes = json.loads(catalog.read_text(encoding='utf-8-sig'))['recipes']
rows = []
issues = []
for recipe in recipes:
    row = {'recipe': recipe['id'], 'output': recipe['output'], 'meshes': []}
    entries = [('body', recipe['body_mesh'], None)] + [(part['id'], part['mesh'], part) for part in recipe['parts']]
    for part_id, path, part in entries:
        mesh = u.load_asset(path)
        if not isinstance(mesh, u.StaticMesh):
            issues.append({'recipe': recipe['id'], 'part': part_id, 'issue': 'mesh did not load'})
            continue
        bounds = mesh.get_bounds()
        extent = [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z]
        origin = [bounds.origin.x, bounds.origin.y, bounds.origin.z]
        row['meshes'].append({'part': part_id, 'path': path, 'origin_cm': origin, 'extent_cm': extent})
        if part:
            if max(abs(a-b) for a, b in zip(extent, part['extent'])) > .15:
                issues.append({'recipe': recipe['id'], 'part': part_id, 'issue': 'saved mesh and pick extent differ', 'saved_extent': extent, 'pick_extent': part['extent']})
            if max(abs(v) for v in origin) > .1:
                issues.append({'recipe': recipe['id'], 'part': part_id, 'issue': 'mesh pivot is offset from guide centre', 'origin': origin})
    rows.append(row)

result = {'captured_at': datetime.datetime.now().astimezone().isoformat(),
          'catalog_sha256': hashlib.sha256(catalog.read_bytes()).hexdigest(),
          'recipe_count': len(rows), 'mesh_count': sum(len(row['meshes']) for row in rows),
          'rows': rows, 'issues': issues, 'assets_modified': False,
          'scope': 'Fresh saved asset bounds read via Unreal Python commandlet; no gameplay or visual acceptance'}
(root/'saved-layout.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('ASSEMBLY_LAYOUT_READ '+json.dumps({'recipes': len(rows), 'meshes': result['mesh_count'], 'issues': issues}, ensure_ascii=False))
