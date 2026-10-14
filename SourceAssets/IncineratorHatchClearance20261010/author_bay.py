"""Author one replacement wall bay using the existing room and opening envelopes."""
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
CONTAINERS = PROJECT / 'SourceAssets/IncineratorContainers20261003'
source = CONTAINERS / 'Scripts/prepare_layout.py'
ns = {'__file__': str(source), '__name__': 'treatment_bay_geometry'}
# Reuse the production authoring helpers without rebuilding any other bay.
exec(compile(source.read_text('utf8').split('# Totals are search entrances:')[0], str(source), 'exec'), ns)
np = ns['np']
identity = 'AbandonedIncineratorHall'
slot_id = 'Treatment.AbandonedIncineratorHall.HeatCabinet.1'
layout = json.loads((CONTAINERS / 'Config/layout.json').read_text('utf8'))
catalog = json.loads((PROJECT / 'SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json').read_text('utf8'))
room = next(m for m in catalog['modules'] if m['id'] == identity)
slots = [s for g in layout['groups'][identity] for s in g['slots']]
previous = next(s for s in slots if s['id'] == slot_id)
old_position = previous['variants'][0]['containers'][0]['position']
reserved = [s['clearance_cm'] for s in slots if s['id'] != slot_id]
reserved += room.get('scene_keep_clear', [])
module = ns['modules'][identity]
geometry = ns['room_surfaces'](module)
pool = ns['candidates'](module, 'HeatCabinet', geometry, [0])
pool = [p for p in pool if not any(ns['overlaps'](
    (np.array(p['box'][0]), np.array(p['box'][1])),
    (np.array(b['min']), np.array(b['max']))) for b in reserved)]
if not pool:
    raise RuntimeError('No available ground-floor wall bay; preserve current placement')
pool.sort(key=lambda p: math.dist(p['position'], old_position))
bay = pool[0]
result = dict(revision='incinerator_hatch_clearance_20261010', module=identity,
              slot=slot_id, previous_position=old_position,
              position=bay['position'], yaw=bay['yaw'],
              clearance_cm=dict(min=bay['box'][0], max=bay['box'][1]),
              floor_z=bay['floor_z'],
              authoring='Existing FBX surfaces, full cabinet opening envelope, 90cm access, all fixture and container reservations',
              game_run=False, rendered=False, tested=False)
(ROOT / 'bay.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
print('INCINERATOR_BAY_AUTHORED', json.dumps(result, ensure_ascii=False), flush=True)
