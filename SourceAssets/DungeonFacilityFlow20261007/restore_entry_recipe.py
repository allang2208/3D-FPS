"""Restore the original fixed start and rigidly rebase the facility after its exit.

This is an asset recipe migration, not a layout generation or gameplay test.
"""
from pathlib import Path
import copy, hashlib, json

ROOT = Path(__file__).resolve().parent
REVISION = 'original_workshop_shrine_entry_20261008'
OPEN_PASSAGE = '/Game/Dungeons/FacilityFlow20261007/Meshes/SM_FacilityFlow_PassageOpenRear'

def contract_hash(catalog):
    # Match WriteContractJson / TPrettyJsonPrintPolicy on this Windows host.
    # Identifier-prefix writes deliberately put the value on its own line.
    data = copy.deepcopy(catalog)
    for key in ('layout_bank', 'probe_pair_order', 'joint_layout_version'):
        data['facility_flow'].pop(key, None)
    def quote(value):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    def emit(value, depth):
        tabs = '\t' * depth
        if isinstance(value, dict):
            return '{' + ''.join((',' if i else '') + '\r\n' + tabs + '\t' + quote(k) + ': ' +
                '\r\n' + tabs + '\t' + emit(value[k], depth+1) for i,k in enumerate(sorted(value))) + '\r\n' + tabs + '}'
        if isinstance(value, list):
            return '[' + (''.join((',' if i else '') + '\r\n' + tabs + '\t' + emit(v, depth+1)
                for i,v in enumerate(value)) + '\r\n' + tabs if value else '') + ']'
        if isinstance(value, bool): return 'true' if value else 'false'
        if value is None: return 'null'
        if isinstance(value, (float, int)): return format(float(value), '.17g')
        return quote(value)
    text = 'facility-layout-v1;rigid;12/48/46m;4turn;contact=8.001;' + emit(data, 0)
    return hashlib.sha1(text.encode('utf8')).hexdigest()

def extend(catalog, migrate_bank=True):
    result = copy.deepcopy(catalog)
    original = json.loads((ROOT/'Sources/production-catalog.json').read_text('utf8'))
    for key in ('start_position', 'start_normal', 'reserved_min', 'reserved_max', 'start_connection'):
        result[key] = copy.deepcopy(original[key])
    flow = result['facility_flow']
    flow['fixed_start_revision'] = REVISION
    flow['entry_style'] = 'original_corridor_workshop_shrine_then_side_breach'
    entry = next(m for m in result['modules'] if m['id'] == flow['entrance'])
    for p in entry['parts']:
        if p['mesh'].split('.')[-1].endswith('SM_FacilityFlow_Passage'):
            p['mesh'] = OPEN_PASSAGE
    entry['runtime_assets'] = [OPEN_PASSAGE if p.split('.')[-1].endswith('SM_FacilityFlow_Passage') else p
        for p in entry['runtime_assets']]
    # The preceding fixed scene remains at its approved original coordinates.
    # All generated pieces move together, preserving their mutual joins.
    bank = flow.get('layout_bank')
    if bank and migrate_bank:
        current_hash = contract_hash(catalog)
        if bank['contract_sha1'] != current_hash:
            raise RuntimeError('Layout bank does not belong to the current catalog; preserve it')
        delta = [result['start_position'][i] - catalog['start_position'][i] for i in range(3)]
        if any(delta):
            for item in bank['entries'].values():
                for piece in item['pieces']:
                    piece['origin'] = [piece['origin'][i] + delta[i] for i in range(3)]
            bank['entry_rebase'] = dict(revision=REVISION, translation_cm=delta,
                source_contract_sha1=bank['contract_sha1'], runtime_replay_required=True,
                regression_run=False)
        bank['contract_sha1'] = contract_hash(result)
    return result

if __name__ == '__main__':
    live = ROOT/'Sources/entry-restore-live-catalog.json'
    catalog = json.loads(live.read_text('utf8'))
    result = extend(catalog)
    (ROOT/'Config/catalog-original-entry-pending.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print('ORIGINAL_ENTRY_RECIPE_PREPARED', result['start_position'],len(result['facility_flow']['layout_bank']['entries']))
