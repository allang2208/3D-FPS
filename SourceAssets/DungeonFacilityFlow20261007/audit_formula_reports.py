"""Independent checks of native layout output; no Unreal startup or asset writes."""
import argparse
from collections import Counter, deque
import hashlib
import itertools
import json
from pathlib import Path
import statistics


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def near(a, b):
    return all(abs(x-y) <= 1.001 for x, y in zip(a, b))


def mates(a, b):
    return (near(a['position'], b['position'])
            and sum(x*y for x, y in zip(a['normal'], b['normal'])) < -.999
            and abs(a['width']-b['width']) < 1
            and abs(a['height']-b['height']) < 1)


def reachable(graph, start, allowed):
    seen = {start}
    queue = deque([start])
    while queue:
        for other in graph[queue.popleft()]:
            if other not in seen and allowed(other):
                seen.add(other)
                queue.append(other)
    return seen


def audit(report, catalog):
    errors = []
    if not report['success']:
        return {'seed': report['seed'], 'passed': False, 'errors': [report['failure']]}
    pieces = report['pieces']
    modules = {m['id']: m for m in catalog['modules']}
    themes = {t['id']: t['sequence'] for t in catalog['themed_routes']['routes']}
    sequences = {tuple(v): k for k, v in themes.items()}
    missions = {p['mission_id']: i for i, p in enumerate(pieces) if p['mission_id']}
    if len(missions) != sum(bool(p['mission_id']) for p in pieces):
        errors.append('Duplicate mission identities')
    if report['counts'] != [0, 6, 6, 6]:
        errors.append('Wrong room counts')
    pairs = []
    levels = []
    for route in range(1, 4):
        room_ids = [missions.get(f'Route{route}.{slot}') for slot in range(6)]
        if any(i is None for i in room_ids):
            errors.append(f'Route{route}: missing mandatory room')
            continue
        rooms = [pieces[i] for i in room_ids]
        pair = [sequences.get(tuple(p['module'] for p in rooms[s:s+3])) for s in (0, 3)]
        if None in pair:
            errors.append(f'Route{route}: reversed/broken themed sequence')
        else:
            pairs.append(pair)
        levels.append(round(rooms[0]['ports'][0]['position'][2]-report['start']['position'][2], 3))
        for p in rooms:
            if any(abs(s-1) > .0001 for s in p['scale']):
                errors.append(f"Scaled authored room: {p['module']}")
        if any(p['mission_depth'] >= q['mission_depth'] for p, q in zip(rooms, rooms[1:])):
            errors.append(f'Route{route}: non-increasing progression')
    if Counter(t for pair in pairs for t in pair) != Counter(themes.keys()):
        errors.append('Themes omitted or duplicated')
    if 'drawn_theme_pairs' in report and Counter(map(tuple,pairs)) != Counter(map(tuple,report['drawn_theme_pairs'].values())):
        errors.append('Spatial search changed a drawn pair or its order')
    for key in ('entry', 'reception', 'fork.late', 'confluence', 'archive', 'boss'):
        if key not in missions:
            errors.append(f'Missing mission: {key}')
    ports = [(-1, report['start'])] + [(i, port) for i, p in enumerate(pieces) for port in p['ports']]
    graph = {i: set() for i in range(-1, len(pieces))}
    shared = {}
    for idx, (owner, port) in enumerate(ports):
        matches = [(other, remote) for j, (other, remote) in enumerate(ports)
                   if j != idx and other != owner and mates(port, remote)]
        if len(matches) != 1:
            errors.append(f'Port {owner}/{port.get("index", "start")} has {len(matches)} mates')
        for other, remote in matches:
            graph[owner].add(other)
            if owner >= 0 and other >= 0:
                shared.setdefault(tuple(sorted((owner, other))), []).append(port)
    if len(reachable(graph, -1, lambda _: True)) != len(pieces)+1:
        errors.append('Disconnected piece graph')
    for edge in report['mission_edges']:
        if edge['optional'] or edge['to'] == 'reward.final':
            continue
        a, b = missions.get(edge['from']), missions.get(edge['to'])
        if a is None or b is None or b not in reachable(
                graph, a, lambda i: i == b or (i >= 0 and not pieces[i]['mission_id'])):
            errors.append(f"Mission edge missing in physical graph: {edge['from']} -> {edge['to']}")
    # Check every occupied box independently. Matched doorway collars are the
    # only accepted intersections; these are planner cells, not physics bodies.
    for i, a in enumerate(pieces):
        for j in range(i):
            b = pieces[j]
            overlap_error = False
            for ca, cb in itertools.product(a['cells'], b['cells']):
                low = [max(x,y) for x,y in zip(ca['min'],cb['min'])]
                high = [min(x,y) for x,y in zip(ca['max'],cb['max'])]
                if any(hi-lo <= 8.001 for lo,hi in zip(low, high)):
                    continue
                legal = False
                depth = max(45 if 'Treasure' in (a['module'], b['module']) else 30,
                            modules[a['module']].get('port_seam_depth_cm',30),
                            modules[b['module']].get('port_seam_depth_cm',30)) + .101
                for port in shared.get((j,i), []):
                    axis = 0 if abs(port['normal'][0]) > .5 else 1
                    side = 1-axis
                    at = port['position']
                    width = port['width']/2+30.001
                    if (low[axis] >= at[axis]-depth and high[axis] <= at[axis]+depth
                            and low[side] >= at[side]-width and high[side] <= at[side]+width):
                        legal = True
                        break
                if not legal:
                    errors.append(f"Illegal occupancy overlap: {i}/{a['module']} and {j}/{b['module']}")
                    overlap_error = True
                    break
            if overlap_error:
                continue
    if report['corridor_cm'] > report['corridor_budget_cm']+.1:
        errors.append('Global corridor budget exceeded')
    for route, detail in enumerate(report['route_length_details'], 1):
        # Six rooms, four inside-theme joins, and three theme boundaries.
        bridge_enabled = report.get('theme_bridges_enabled', report['attempt'] >= 3)
        height = levels[route-1] if len(levels) == 3 else 0
        expected = 7*1200 if not bridge_enabled else 4*1200+4800+2*(4600 if abs(height)>.1 else 4800)
        if abs(detail['link_budget_cm']-expected) > .1:
            errors.append(f'Route{route}: incorrect boundary allowance')
        if detail['link_walk_cm'] > detail['link_budget_cm']+.1:
            errors.append(f'Route{route}: corridor budget exceeded')
    canonical = [{k:p[k] for k in ('module','route','mission_id','origin','yaw','scale','side')} for p in pieces]
    fingerprint = hashlib.sha256(json.dumps(canonical,sort_keys=True).encode()).hexdigest()
    return {'seed':report['seed'],'passed':not errors,'errors':errors,'pairs':pairs,
            'levels_cm':levels,'piece_count':len(pieces),'layout_sha256':fingerprint,
            'plan_ms':report['plan_ms'],'attempt':report['attempt']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report')
    parser.add_argument('catalog')
    parser.add_argument('output')
    args = parser.parse_args()
    reports, catalog = read(args.report), read(args.catalog)
    results = [audit(r,catalog) for r in reports]
    seen = {}
    repeats = []
    for r in results:
        if r['seed'] in seen:
            repeats.append({'seed':r['seed'],'same':r.get('layout_sha256') == seen[r['seed']].get('layout_sha256') and r['passed']})
        seen[r['seed']] = r
    unique = list(seen.values())
    pairs = sorted(set(tuple(p) for r in results for p in r.get('pairs',[])))
    partitions = {tuple(sorted(tuple(sorted(p)) for p in r['pairs'])) for r in results if len(r.get('pairs',[])) == 3}
    times = sorted(r['plan_ms'] for r in reports)
    summary = {'runs':len(results),'unique_seeds':len(unique),
               'passed_runs':sum(r['passed'] for r in results),
               'failed_unique':[r['seed'] for r in unique if not r['passed']],
               'ordered_pair_coverage':len(pairs),'ordered_pairs':pairs,
               'pair_partition_coverage':len(partitions),
               'ordered_pairing_coverage':len({tuple(sorted(map(tuple,r['pairs']))) for r in results if len(r.get('pairs',[]))==3}),
               'floor_offsets_cm':sorted(set(v for r in results for v in r.get('levels_cm',[]))),
               'median_ms':statistics.median(times),'max_ms':max(times),
               'p95_ms':times[min(len(times)-1, int(len(times)*.95))],
               'repeat_checks':repeats,'results':results}
    Path(args.output).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('results','ordered_pairs')},ensure_ascii=False))
    for r in results:
        if not r['passed']:
            print(r['seed'],r['errors'][:4])
    raise SystemExit(0 if all(r['passed'] for r in results) and all(r['same'] for r in repeats) else 1)


if __name__ == '__main__':
    main()
