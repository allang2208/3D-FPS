import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
groups = json.loads((ROOT / 'Docs/Gameplay/search-container-groups-20261012.json').read_text(encoding='utf-8-sig'))

def pool(id, group, counts, pairs):
    return dict(id=id, group=group, count_weights=counts,
                entries=[dict(id=item, weight=weight) for item, weight in pairs])

daily = [('mineral_water', 35), ('soda_can', 30), ('bread', 15), ('baguette_bread', 20)]
data = dict(version=1, selection='weighted_without_replacement', units_per_entry=1,
    scope_map='L_Dungeon_Randomized', pools=[
    pool('visitor_daily', 'daily_supplies', [0, 70, 25, 5], daily),
    pool('ppe_daily', 'daily_supplies', [0, 70, 25, 5], daily),
    pool('office_documents', 'documents', [0, 70, 25, 5], [
        ('search_usb_drive',70), ('search_archive_tape',18),
        ('search_certified_admin_archive',11), ('search_encrypted_archive_case',1)]),
    pool('maintenance_parts', 'maintenance', [0, 70, 25, 5], [
        ('search_forging_alloy_blank',30), ('search_assembly_component_box',30),
        ('search_precision_mechanism',25), ('search_resin_adhesive',10), ('search_laminated_strip',5)]),
    pool('server_hardware', 'server_equipment', [0, 70, 25, 5], [
        ('search_ram_module',2800), ('search_network_card',2200), ('search_hard_disk',2000),
        ('search_ssd',1300), ('search_processor',800), ('search_graphics_card',600),
        ('search_raid_controller',250), ('search_compute_accelerator',50)])], bindings=[])

for entry in groups['container_bindings']:
    kind = entry['group']
    which = dict(documents='office_documents', maintenance='maintenance_parts', server_equipment='server_hardware').get(kind)
    if kind == 'daily_supplies':
        which = 'visitor_daily' if entry['module'] == 'FacilityReceptionHall' else 'ppe_daily'
    data['bindings'].append(dict(container_id=entry['container_id'], pool=which, module=entry['module'], caption=entry['caption']))

(ROOT / 'Content/ColdSteelData/scene_search_loot.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Authored 31 container bindings / 5 profiles / 4 groups.')
