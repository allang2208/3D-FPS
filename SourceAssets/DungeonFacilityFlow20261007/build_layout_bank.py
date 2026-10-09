"""Collect audited native placements for all ordered pairings; never invent poses."""
import argparse
import copy
import json
from pathlib import Path
from audit_formula_reports import audit


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def contract(catalog):
    result = copy.deepcopy(catalog)
    for key in ('layout_bank', 'probe_pair_order', 'joint_layout_version'):
        result['facility_flow'].pop(key, None)
    return result


parser = argparse.ArgumentParser()
parser.add_argument('--catalog', required=True, type=Path)
parser.add_argument('--contract-report', type=Path)
parser.add_argument('--reports', nargs='+', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
catalog = read(args.catalog)
signature = read(args.contract_report)[0]['catalog_contract_sha1'] if args.contract_report else ''
if args.contract_report and len(signature) != 40:
    raise ValueError('Missing native catalog contract')
entries = {}
for path in args.reports:
    source_catalog = read(path.with_name(path.stem+'-catalog.json'))
    if contract(source_catalog) != contract(catalog):
        raise ValueError(f'Catalog changed since {path}')
    for report in read(path):
        if not report['success']:
            continue
        result = audit(report, catalog)
        if not result['passed']:
            raise ValueError(f'Native layout failed independent audit: {path} seed={report["seed"]}: {result["errors"][:3]}')
        key = '|'.join(sorted('>'.join(pair) for pair in result['pairs']))
        fields = ('module', 'route', 'origin', 'yaw', 'scale', 'active_ports', 'link_cm', 'link_turns', 'theme_bridge')
        # Optional side treasure rooms are drawn again from the actual run seed.
        pieces = [{k:p[k] for k in fields} for p in report['pieces'] if '_Treasure' not in p['route']]
        entry = {'route_pairs': {f'Route{i+1}':pair for i,pair in enumerate(result['pairs'])},
                 'levels_cm': result['levels_cm'],
                 'theme_bridges_enabled': report.get('theme_bridges_enabled', report['attempt']>=3),
                 'pieces': pieces, 'source_seed': report['seed'], 'source_report': path.name,
                 'source_layout_sha256': result['layout_sha256']}
        if key not in entries or len(pieces) < len(entries[key]['pieces']):
            entries[key] = entry
bank = {'version': 1, 'contract_sha1': signature, 'native_replay_pending': True, 'entries': dict(sorted(entries.items()))}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(json.dumps({'pairings':len(entries),'expected':120,'complete':len(entries)==120,'output':str(args.output)}))
