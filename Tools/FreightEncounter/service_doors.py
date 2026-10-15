"""Keep the station's service doors; retire its decorative vent and floor hatch."""
import copy
import json
import math
from pathlib import Path

STATION = 'AbandonedTransitStation'
REMOVED = {STATION+'.vent.02', STATION+'.hatch.03'}
SERVICE_WALK = dict(min=[-1582, 1080, -5], max=[-900, 1640, 280])
# Exact closed-fixture reservations authored alongside the two retired outlets.
REMOVED_RESERVATIONS = [([2285, 1275, -4.8], [2585, 1575, 320.2]),
                        ([665, 1325, -4.8], [1045, 1525, 320.2])]

def patch_module(module):
    if module.get('id') != STATION:
        return module
    out = copy.deepcopy(module)
    out['parts'] = [p for p in out.get('parts', []) if p.get('fixture_id') not in REMOVED]
    out['runtime_actors'] = [a for a in out.get('runtime_actors', []) if a.get('id') not in REMOVED]
    if 'scene_keep_clear' in out:
        def retired(box):
            return box.get('owner') == 'room_closed_fixtures_20261009' and any(
                all(abs(a-b)<.1 for k, expected in [('min', lo), ('max', hi)]
                    for a,b in zip(box.get(k, []), expected))
                for lo, hi in REMOVED_RESERVATIONS)
        out['scene_keep_clear'] = [b for b in out['scene_keep_clear'] if not retired(b)]
    walks = out.setdefault('walk_mask', [])
    if SERVICE_WALK not in walks:
        walks.append(copy.deepcopy(SERVICE_WALK))
    return out

def patch_document(data):
    if 'modules' in data:
        out = copy.deepcopy(data)
        out['modules'] = [patch_module(m) for m in out['modules']]
        return out
    return patch_module(data)

def update_sources(project, output):
    import runpy
    relatives = runpy.run_path(str(Path(__file__).with_name('catalog_patch.py')))['SOURCES']
    changed = []
    for relative in relatives:
        path = project/'SourceAssets'/relative
        if not path.exists():
            continue
        raw = path.read_text(encoding='utf-8-sig')
        old = json.loads(raw);new = patch_document(old)
        if old == new:
            continue
        backup = output/'Before/SourceAssets'/relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_text(raw, encoding='utf8')
        path.write_text(json.dumps(new, ensure_ascii=False, indent=2), encoding='utf8')
        changed.append(str(path.relative_to(project)))
    # The fixture authoring pass must not reintroduce the retired outlets.
    path = project/'SourceAssets/DungeonFacilityFlow20261007/SpawnEntries20261009/placements.json'
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    data[STATION] = [e for e in data[STATION] if e['id'] not in REMOVED]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
    changed.append(str(path.relative_to(project)))
    return changed

if __name__ == '__main__':
    project = Path(__file__).resolve().parents[2]
    output = project/'SourceAssets/FreightDoorReinforcements20261014'
    (output/'Receipts').mkdir(parents=True, exist_ok=True)
    changed = update_sources(project, output)
    (output/'Receipts/sources.json').write_text(json.dumps(changed, indent=2), encoding='utf8')
    print('FREIGHT_DOOR_SOURCES_SAVED', len(changed))
