"""Independent, offline audit of -DungeonLayoutProbe output. No UE or assets changed."""
import argparse
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def match(a, b):
    return (max(abs(x - y) for x, y in zip(a['position'], b['position'])) <= 1
            and dot(a['normal'], b['normal']) < -.999
            and abs(a['width'] - b['width']) < 1
            and abs(a['height'] - b['height']) < 1)


def resolved_modules(catalog):
    result = {}
    for module in catalog['modules']:
        if 'shell_id' in module:
            library = catalog['room_recipe_library']
            module = {**library['shells'][module['shell_id']],
                      **library['interiors'][module['interior_recipe_id']], **module}
        result[module['id']] = module
    return result


def audit(report, catalog):
    errors = []
    if not report['success']:
        return {'seed': report['seed'], 'errors': [report['failure']], 'success': False}
    pieces = report['pieces']
    modules = resolved_modules(catalog)
    for name, module in modules.items():
        for cell in module['cells']:
            if any(cell['min'][a] < module['min'][a] - .01 or cell['max'][a] > module['max'][a] + .01 for a in range(3)):
                errors.append(f'occupancy outside broad-phase bounds: {name}')
        for side in module.get('side_sockets', []):
            source = side.get('port_index', -1)
            if source >= 0 and (source >= len(module['ports']) or not match(side, {**module['ports'][source], 'normal': [-n for n in module['ports'][source]['normal']]})):
                errors.append(f'side socket differs from reused primary port: {name}/{source}')
    graph = {i: set() for i in range(-1, len(pieces))}
    ports = [(-1, report['start'])] + [(i, p) for i, piece in enumerate(pieces) for p in piece['ports']]
    for owner, port in ports:
        mates = [(j, other) for j, other in ports if j != owner and match(port, other)]
        if len(mates) != 1:
            errors.append(f'port degree {owner}/{port.get("index")}: {len(mates)}')
        for j, _ in mates:
            graph[owner].add(j)
    seen = {-1}
    queue = deque([-1])
    while queue:
        for next_node in graph[queue.popleft()] - seen:
            seen.add(next_node)
            queue.append(next_node)
    if len(seen) != len(graph):
        errors.append('disconnected geometry')
    counts = Counter(p['route'] for p in pieces if p['combat'])
    expected = dict(zip(['Approach', 'Route1', 'Route2', 'Route3'], report['counts']))
    if counts != expected:
        errors.append(f'room counts {counts} != {expected}')
    kinds = Counter(p['module'] for p in pieces)
    for kind, count in [('StairDrop1080', 3), ('BossPumpHall', 1), ('BossConfluence', 1)]:
        if kinds[kind] != count:
            errors.append(f'{kind}: {kinds[kind]} != {count}')
    overlaps = 0
    for i, piece in enumerate(pieces):
        if not any(match(p, report['start']) for p in piece['ports']):
            for cell in piece['cells']:
                if all(min(cell['max'][a], catalog['reserved_max'][a]) - max(cell['min'][a], catalog['reserved_min'][a]) > 8 for a in range(3)):
                    errors.append(f'piece {i} overlaps reserved start area')
        if not all(math.isfinite(n) for key in ('origin', 'scale') for n in piece[key]):
            errors.append(f'nonfinite transform {i}')
        scale = piece['scale']
        if min(scale) <= 0 or abs(scale[0] - 1) > .0001 or abs(scale[2] - 1) > .0001 or (piece['module'] != 'Transit' and abs(scale[1] - 1) > .0001):
            errors.append(f'nonrigid room {i}')
        if piece['link_cm'] > 1200.1 or piece['link_turns'] > 2:
            errors.append(f'link metadata over budget {i}')
        for j, other in enumerate(pieces[:i]):
            seams = [p for p in piece['ports'] for q in other['ports'] if match(p, q)]
            for a in piece['cells']:
                for b in other['cells']:
                    low = [max(x, y) for x, y in zip(a['min'], b['min'])]
                    high = [min(x, y) for x, y in zip(a['max'], b['max'])]
                    if not all(h - l > 8 for l, h in zip(low, high)):
                        continue
                    legal = False
                    for port in seams:
                        axis = 0 if abs(port['normal'][0]) > .5 else 1
                        side = 1 - axis
                        depth = 45 if 'Treasure' in (piece['module'], other['module']) else 25
                        at = port['position']
                        half = port['width'] / 2 + 30
                        legal |= (low[axis] >= at[axis] - depth - .001 and high[axis] <= at[axis] + depth + .001
                                  and low[side] >= at[side] - half - .001 and high[side] <= at[side] + half + .001)
                    if not legal:
                        errors.append(f'illegal cells overlap {i}/{j}')
                    overlaps += 1
    identities = [p['mission_id'] for p in pieces if p['mission_id']]
    if len(identities) != len(set(identities)):
        errors.append('duplicate mission identities')
    ids = {p['mission_id']: i for i, p in enumerate(pieces) if p['mission_id']}
    ids['entry'] = -1
    if report['mission_edges']:
        for edge in report['mission_edges']:
            if edge['optional'] or edge['to'] == 'reward.final':
                continue
            start, end = ids.get(edge['from']), ids.get(edge['to'])
            if start is None or end is None:
                errors.append(f'missing mission {edge}')
                continue
            visited = {start}
            queue = deque([start])
            while queue:
                for n in graph[queue.popleft()] - visited:
                    if n == -1 or pieces[n]['route'].startswith('Loop.'):
                        continue
                    if n != end and pieces[n]['mission_id']:
                        continue
                    visited.add(n)
                    queue.append(n)
            if end not in visited or not edge['realized']:
                errors.append(f'broken mission edge {edge}')
            if start >= 0 and pieces[start]['mission_depth'] >= pieces[end]['mission_depth']:
                errors.append(f'non-increasing mission stage {edge["from"]} -> {edge["to"]}')
    # Recover maximal physical connector chains, independently of LinkLength labels
    # (branches can be assembled backwards, so labels alone are insufficient).
    flat = {'Transit', 'Threshold', 'RouteElbow'}
    connectors = {i for i, p in enumerate(pieces) if p['module'] in flat}
    max_room_link, max_junction_link = 0, 0
    while connectors:
        first = min(connectors)
        chain, ends = {first}, set()
        queue = deque([first])
        while queue:
            for n in graph[queue.popleft()]:
                if n in connectors:
                    if n not in chain:
                        chain.add(n)
                        queue.append(n)
                else:
                    ends.add(n)
        connectors -= chain
        length = sum(400 if pieces[i]['module'] == 'RouteElbow' else math.dist(pieces[i]['ports'][0]['position'], pieces[i]['ports'][1]['position']) for i in chain)
        turns = sum(pieces[i]['module'] == 'RouteElbow' for i in chain)
        if len(ends) != 2:
            errors.append(f'connector chain ends {sorted(chain)}: {sorted(ends)}')
            continue
        if all(i >= 0 and pieces[i]['combat'] for i in ends):
            max_room_link = max(max_room_link, length)
            if length > 1200.1 or turns > 2:
                errors.append(f'physical room link exceeds budget {sorted(ends)}: {length:.1f} cm/{turns} bends')
        else:
            max_junction_link = max(max_junction_link, length)
            if length > 1200.1 or turns > 2:
                errors.append(f'physical junction/terminal link exceeds budget {sorted(ends)}: {length:.1f} cm/{turns} bends')
    for loop in report['loops']:
        if not all(0 <= loop[k] < len(pieces) and pieces[loop[k]]['combat'] for k in ('from', 'to')):
            errors.append(f'stale loop endpoints {loop}')
    if report['corridor_cm'] > report['corridor_budget_cm'] + .1 or report['route_estimate_cm'] > report['route_budget_cm'] + .1:
        errors.append('global budget exceeded')
    boss = next(p for p in pieces if p['module'] == 'BossPumpHall')
    if abs(boss['ports'][0]['position'][2] - report['start']['position'][2] + 1080) > 1:
        errors.append('boss floor depth')
    signature = hashlib.sha256(json.dumps(pieces, sort_keys=True).encode()).hexdigest()
    return {'seed': report['seed'], 'success': not errors, 'errors': errors, 'signature': signature,
            'pieces': len(pieces), 'rooms': dict(counts), 'grammar': report['grammar'],
            'plan_ms': report['plan_ms'], 'max_room_link_cm': max_room_link,
            'max_junction_link_cm': max_junction_link, 'legal_cell_seams': overlaps}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    parser.add_argument('catalog', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding='utf-8'))
    results = [audit(r, catalog) for r in json.loads(args.report.read_text(encoding='utf-8'))]
    signatures = {}
    for r in results:
        if 'signature' in r:
            prior = signatures.setdefault(r['seed'], r['signature'])
            if prior != r['signature']:
                r['errors'].append('same seed produced different layout')
                r['success'] = False
    args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'passed': sum(r['success'] for r in results), 'total': len(results),
                      'failures': [r for r in results if not r['success']]}, ensure_ascii=False))
    raise SystemExit(0 if all(r['success'] for r in results) else 1)


if __name__ == '__main__':
    main()
