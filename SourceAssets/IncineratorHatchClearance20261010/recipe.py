"""Keep the incinerator heat cabinet assembly outside the floor-hatch bay."""
from pathlib import Path
import copy
import json
import math

ROOT = Path(__file__).resolve().parent
REVISION = 'incinerator_hatch_clearance_20261010'
MODULE = 'AbandonedIncineratorHall'
SLOT = 'Treatment.AbandonedIncineratorHall.HeatCabinet.1'


def bay():
    return json.loads((ROOT / 'bay.json').read_text('utf8'))


def apply_groups(groups):
    target = bay()
    for group in groups:
        for slot in group.get('slots', []):
            if slot['id'] != SLOT:
                continue
            for variant in slot['variants']:
                first = variant['containers'][0]
                origin = list(first['position'])
                angle = target['yaw'] - first['yaw']
                c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
                for item in variant['containers']:
                    x, y, z = [item['position'][i] - origin[i] for i in range(3)]
                    item['position'] = [target['position'][0] + c*x - s*y,
                                        target['position'][1] + s*x + c*y,
                                        target['position'][2] + z]
                    item['yaw'] = ((item['yaw'] + angle + 180) % 360) - 180
            slot['clearance_cm'] = copy.deepcopy(target['clearance_cm'])
            slot['floor_z'] = target['floor_z']
            slot['placement_revision'] = REVISION
            return True
    return False


def apply_layout(layout):
    return apply_groups(layout.get('groups', {}).get(MODULE, []))


def apply_module(module):
    return module['id'] == MODULE and apply_groups(module.get('warehouse_containers', {}).get('groups', []))


def reapply_catalog(catalog, contract_hash):
    if not any(apply_module(m) for m in catalog['modules'] if m['id'] == MODULE):
        return catalog
    bank = catalog.get('facility_flow', {}).get('layout_bank')
    if bank:
        bank['contract_sha1'] = contract_hash(catalog)
    return catalog
