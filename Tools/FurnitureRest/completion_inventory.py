"""Read-only inventory of the furniture roles the current game configuration uses."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/FurnitureRest20261022/CompletionAudit20261025'
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

body = read(ROOT / 'Content/ColdSteelData/player_body.json')
libraries = [read(ROOT / 'Content/ColdSteelData' / name) for name in
             ('furniture_rest.json', 'apartment_furniture_rest.json')]
types = {key: value for lib in libraries for key, value in lib['types'].items()}
timing = {key: value for lib in libraries for key, value in lib['clips'].items()}
cook_dirs = re.findall(r'^\+DirectoriesToAlwaysCook=\(Path="([^"]+)"\)',
                      (ROOT / 'Config/DefaultGame.ini').read_text(encoding='utf-8-sig'), re.M)
roles = []
for name, config in [('jason', body), ('kaitlin', body['body_variants']['kaitlin'])]:
    for role, asset in config['clips'].items():
        if not role.startswith('Rest.'):
            continue
        package = asset.split('.')[0]
        native = ROOT / 'Content' / (package.removeprefix('/Game/') + '.uasset')
        roles.append(dict(body=name, role=role, asset=asset, exists=native.is_file(),
                          always_cook=any(package.startswith(d.rstrip('/') + '/') for d in cook_dirs),
                          seconds=timing[role]['duration']))
profiles = [dict(profile, lying=all(types[s['kind']]['lying'] for s in profile['slots']))
            for lib in libraries for profile in lib['furniture']]
result = dict(models=len(profiles), slots=sum(len(p['slots']) for p in profiles),
              bed_models=sum(p['lying'] for p in profiles), kinds=len(types),
              roles=roles, profiles=profiles,
              missing_assets=[r for r in roles if not r['exists']],
              missing_cook_coverage=[r for r in roles if not r['always_cook']],
              bed_entry_including_align={k: .6 + timing['Rest.' + k + '.Enter']['duration']
                                         for k, v in types.items() if v['lying']},
              scope='Configured model paths and slots; not a census of every placed world instance.',
              upper_bunk_supported=False, packaged_build_run=False)
(OUT / 'inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k not in ('roles', 'profiles')}, ensure_ascii=False))
