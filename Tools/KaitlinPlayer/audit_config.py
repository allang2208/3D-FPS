"""Read-only audit of the published female selection routes; no UE launch."""
import hashlib
import itertools
import json
from pathlib import Path

P = Path('D:/FPS3D/FPSGAME')
W = P / 'SourceAssets/KaitlinPlayer20261023'
A = W / 'Audit'
A.mkdir(exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
b, m = (read(P / 'Content/ColdSteelData' / name) for name in ('player_body.json', 'modular_outfits.json'))
f, n = b['body_variants']['kaitlin'], m['body_variants']['kaitlin']
issues, notes = [], []
refs = {}


def walk(value, route):
    if isinstance(value, str) and value.startswith('/Game/'):
        refs.setdefault(value, []).append(route)
    elif isinstance(value, dict):
        for key, child in value.items():
            walk(key, route + '/<key>')
            walk(child, route + '/' + key)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            walk(child, route + '/' + str(i))


walk(f, 'body'); walk(n, 'modular')
for path, routes in refs.items():
    file = P / 'Content' / (path[6:].split('.')[0] + '.uasset')
    if not file.exists():
        issues.append({'kind': 'missing_package', 'path': path, 'routes': routes})
for name, male, female in [('clips', b['clips'], f['clips']), ('items', m['items'], n['items']),
                           ('backpacks', b['outfits'], f['outfits']), ('headwear', b['head_equipment'], f['head_equipment'])]:
    if set(male) != set(female):
        issues.append({'kind': 'catalog_mismatch', 'catalog': name, 'missing': sorted(set(male)-set(female)), 'extra': sorted(set(female)-set(male))})
retarget = read(W / 'retargeted_assets.json')
for key, path in b['clips'].items():
    # Other feature authors may publish their own body-specific sequence. Check
    # those independently in UE, rather than replacing them with our retarget.
    if retarget.get(path) != f['clips'].get(key) and '/KaitlinPlayer20261023/Motion/' in f['clips'].get(key, ''):
        issues.append({'kind': 'stale_animation', 'role': key})

# Mirror UpdatePresentation's actual world/owner path ordering, including empty
# robe underlayers and actual boot-selected trousers. Profile fallback strings
# are intentionally not treated as selected when a rig_meshes map exists.
items = n['items']
by_slot = {s: [''] + [k for k, v in items.items() if v['slot'] == s] for s in (3, 7, 13, 15)}
profile = n['profiles'][f['body_mesh']]
selected = set()
routes = []
preload_missing = []
for owner, shirt_id, pants_id, shoes_id, gloves_id in itertools.product(
        (False, True), by_slot[7], by_slot[15], by_slot[13], by_slot[3]):
    shirt, pants, shoes, gloves = [items.get(k, {}) for k in (shirt_id, pants_id, shoes_id, gloves_id)]
    if owner: gloves = {}
    rig = 'Kaitlin'
    part = lambda recipe, key: recipe.get('rig_meshes', {}).get(rig, '') if 'rig_meshes' in recipe else profile.get(key, '')
    owner_shirt = shirt.get('owner_body_meshes', {}).get(rig, '')
    if owner and not owner_shirt and not shirt.get('base_material_overrides', {}).get(rig): shirt = {}
    under = shirt.get('underlayer_meshes', {})
    base = gloves.get('skin_meshes', {}).get(rig) or profile['native_bare_skin']
    paths = [under.get(base, base)]
    trousers = pants.get('shoe_fit_meshes', {}).get(shoes_id, {}).get(rig) or (part(pants, 'pants') if pants else '')
    if shirt and (not owner or owner_shirt):
        fitted = ''
        if pants and trousers:
            fit_maps = [shirt.get('pants_mesh_fit_meshes', {}).get(trousers, {}),
                        shirt.get('pants_fit_meshes', {}).get(pants_id, {}), shirt.get('pants_fit_default', {})]
            fitted = next((x.get('owner_body_meshes' if owner else 'rig_meshes', {}).get(rig)
                           for x in fit_maps if x.get('owner_body_meshes' if owner else 'rig_meshes', {}).get(rig)), '')
        paths.append(fitted or (owner_shirt if owner else part(shirt, 'shirt')))
    if gloves: paths.append(part(gloves, 'gloves'))
    if pants:
        inner = shirt.get('pants_underlayer_default', {})
        fallback = inner.get('shoe_fit_meshes', {}).get(shoes_id, {}).get(rig) or inner.get('rig_meshes', {}).get(rig)
        p = under.get(trousers, fallback or trousers)
        if p: paths.append(p)
        elif trousers not in under: paths.append('')
    if shoes:
        p = part(shoes, 'shoes')
        if under.get(p, p): paths.append(under.get(p, p))
        elif p not in under: paths.append('')
    context = [owner, shirt_id, pants_id, shoes_id, gloves_id]
    if any(not p or '/KaitlinPlayer20261023/' not in p for p in paths):
        issues.append({'kind': 'world_route_invalid', 'context': context, 'paths': paths})
    selected.update(paths)
    routes.append({'selection': context, 'paths': paths})

    # Mirror CollectBodyAssets for the body rig, checking every rendered path
    # is resident before the asynchronous appearance transaction commits.
    load_paths = {profile['native_bare_skin']}
    selected_pants = {trousers} if trousers else set()
    inner_sources = {profile['native_bare_skin']} | selected_pants
    for recipe, field in ((shoes, 'rig_meshes'), (items.get(gloves_id, {}), 'skin_meshes')):
        if recipe.get(field, {}).get(rig): inner_sources.add(recipe[field][rig])
    exact = bool(items.get(shirt_id, {}).get('pants_mesh_fit_meshes', {}).get(trousers))

    def collect(value):
        if isinstance(value, str):
            if value.startswith('/Game/'): load_paths.add(value)
        elif isinstance(value, list):
            for child in value: collect(child)
        elif isinstance(value, dict):
            for key, child in value.items():
                if key in ('rig_meshes','owner_body_meshes','skin_meshes','base_material_overrides'):
                    collect(child.get(rig))
                elif key == 'shoe_fit_meshes': collect(child.get(shoes_id, {}).get(rig))
                elif key == 'pants_mesh_fit_meshes':
                    for p in selected_pants: collect(child.get(p))
                elif key == 'pants_fit_meshes':
                    if not exact and selected_pants: collect(child.get(pants_id))
                elif key == 'pants_fit_default':
                    if not exact and selected_pants: collect(child)
                elif key == 'underlayer_meshes':
                    for p in inner_sources: collect(child.get(p))
                else: collect(child)

    for item in (shirt_id,pants_id,shoes_id,gloves_id): collect(items.get(item))
    if set(paths)-load_paths:
        preload_missing.append({'selection':context,'missing':sorted(set(paths)-load_paths)})

for path, pr in n['profiles'].items():
    if pr['rig_profile'] == 'Kaitlin': continue
    if path not in m['profiles']: issues.append({'kind': 'unknown_view_profile', 'path': path})
    if '/KaitlinPlayer20261023/ViewSkin/' not in pr.get('native_bare_skin', ''):
        issues.append({'kind': 'male_view_skin', 'path': path})
    if pr.get('native_bare_arms'): issues.append({'kind': 'baked_male_arms', 'path': path})

view_routes = 0
for path, pr in n['profiles'].items():
    if pr['rig_profile'] == 'Kaitlin': continue
    rig = pr['rig_profile']
    for shirt_id,gloves_id in itertools.product(by_slot[7],by_slot[3]):
        shirt,gloves = items.get(shirt_id,{}),items.get(gloves_id,{})
        paths = [gloves.get('skin_meshes',{}).get(rig) or pr['native_bare_skin']]
        if shirt: paths.append(shirt.get('rig_meshes',{}).get(rig,''))
        if gloves and (not gloves.get('glove_in_base') or pr.get('separate_gloves')):
            paths.append(gloves.get('rig_meshes',{}).get(rig,''))
        if any(not p for p in paths): issues.append({'kind':'view_route_missing','profile':path,'shirt':shirt_id,'gloves':gloves_id})
        if '/KaitlinPlayer20261023/ViewSkin/' not in paths[0]: issues.append({'kind':'view_route_male_skin','profile':path,'shirt':shirt_id,'gloves':gloves_id,'base':paths[0]})
        view_routes += 1
for pack_id, recipe in f['outfits'].items():
    for shirt_id in by_slot[7]:
        path = recipe.get('world_mesh_by_shirt', {}).get(shirt_id) or recipe.get('world_mesh')
        if not path or '/KaitlinPlayer20261023/Backpacks/' not in path:
            issues.append({'kind': 'pack_route_invalid', 'pack': pack_id, 'shirt': shirt_id})

# The task's immutable fit inputs allow a direct check for source edits since
# fitting. A changed upstream source is evidence, not permission to overwrite it.
drift = []
for folder in ('WorldGarments', 'Backpacks'):
    for source, row in read(W / folder / 'manifest.json').items():
        file = P / 'Content' / (source[6:].split('.')[0] + '.uasset')
        if row.get('source_sha256') and hashlib.sha256(file.read_bytes()).hexdigest() != row['source_sha256']:
            drift.append(source)
issues.extend({'kind':'preload_missing',**row} for row in preload_missing)
report = {'scope': 'saved configuration and deterministic runtime path selection', 'issues': issues,
          'counts': {'references': len(refs), 'world_owner_combinations': len(routes), 'selected_world_meshes': len(selected),
                     'view_profiles': len(n['profiles'])-1, 'view_combinations':view_routes, 'items': len(items), 'animation_roles': len(f['clips']),
                     'unique_animations': len(set(f['clips'].values())), 'backpack_combinations': len(f['outfits'])*len(by_slot[7])},
          'changed_upstream_meshes': drift, 'notes': notes}
(A / 'config.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
(A / 'routes.json').write_text(json.dumps(routes, separators=(',', ':')), encoding='utf-8')
(A / 'references.json').write_text(json.dumps(refs, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'notes'}, ensure_ascii=False))
