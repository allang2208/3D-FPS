"""Install the approved power collectibles, loot and durable authoring recipes."""
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
from power_containers import TOOLBOXES, patch_document

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
DATA = PROJECT / 'Content/ColdSteelData'


def read(path):
    return json.loads(path.read_text('utf-8-sig'))


def backup(path):
    target = ROOT / 'Before' / path.relative_to(PROJECT)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(path, target)


def write(path, value):
    backup(path)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


installed = read(ROOT / 'Receipts/installation.json')
if installed['stage'] != 'assets_installed':
    raise RuntimeError('Install saved model packages before registering items')
icons = read(ROOT / 'presentation.json')
meshes = read(ROOT / 'Receipts/ue-import.json')
specs = [
    ('search_industrial_fuse_set', '工业熔断器组', 'uncommon', 120,
     '供能站配电设备的备用熔断器，陶瓷管身、金属端帽与铜质触片成组收纳在绝缘托架中。完整的电气备件，可作为收集物带回出售。'),
    ('search_power_control_module', '功率控制模块', 'rare', 900,
     '从供能站设备中拆下的功率控制组件，铝制散热底座上保留着控制电路、接线端子和紧固件。可作为电气战利品带回出售。'),
    ('search_energy_storage_cell', '密封储能电芯', 'epic', 1600,
     '供能站备用储能单元中的密封电芯，金属壳体带有压封接缝、绝缘极柱和泄压结构。可作为收集物带回出售。'),
]
definitions = {}
for identity, name, rarity, value, description in specs:
    icon = next(i for i in icons['icons'] if i['id'] == identity)
    mesh = next(i for i in meshes['meshes'] if i['item_id'] == identity)
    definitions[identity] = dict(id=identity, name=name, category='material', type='电气收集物',
        loot_group='maintenance', rarity=rarity, price=value, sell_souls=value, desc=description,
        grid_w=icon['grid_w'], grid_h=icon['grid_h'], stack=1, stack_max=1, maxStack=1,
        inventory_unit='组' if identity.endswith('fuse_set') else '件',
        icon=icon['ue_icon'], ue_icon=icon['ue_icon'], icon_fallback=name, world_mesh=mesh['path'])
path = DATA / 'items.json'
raw = path.read_text('utf-8-sig')
current = json.loads(raw)
for identity in definitions.keys() & current.keys():
    if definitions[identity] != current[identity]:
        raise RuntimeError('Existing definition differs: ' + identity)
new = {k: v for k, v in definitions.items() if k not in current}
if new:
    backup(path)
    tail = json.dumps(new, ensure_ascii=False, indent=2)[1:-1].strip('\n')
    path.write_text(raw[:raw.rfind('}')].rstrip() + ',\n' + tail + '\n}\n', encoding='utf8')


def pool(identity, group, entries):
    return dict(id=identity, group=group, count_weights=[0, 100, 0, 0],
                entries=[dict(id=k, weight=v) for k, v in entries])


pools = [
    pool('power_staff_supplies', 'daily_supplies', [
        ('mineral_water', 34), ('soda_can', 28), ('bread', 16), ('baguette_bread', 16),
        ('search_industrial_multimeter', 5), ('search_precision_tool_kit', 1)]),
    pool('power_records', 'documents', [
        ('search_usb_drive', 80), ('search_archive_tape', 18), ('search_certified_admin_archive', 2)]),
    pool('power_maintenance', 'maintenance', [
        ('search_industrial_fuse_set', 28), ('search_assembly_component_box', 23),
        ('search_precision_mechanism', 18), ('search_industrial_multimeter', 12),
        ('search_precision_tool_kit', 6), ('search_cordless_impact_wrench', 3),
        ('search_power_control_module', 7), ('search_energy_storage_cell', 3)]),
]
inventory = read(PROJECT / 'Saved/PowerLootReview20261014/production-containers.json')
bindings = []
for room in inventory['modules']:
    for actor in room.get('runtime_actors', []):
        identity = actor.get('container_id', '')
        if actor.get('type') != 'scene_container' or '.Server.' in identity:
            continue
        if '.PPE_' in identity:
            profile = 'power_staff_supplies'
        elif '.Records_' in identity:
            profile = 'power_records'
        else:
            continue
        bindings.append(dict(container_id=identity, pool=profile,
                             module=room['id'], caption=actor['caption']))
for actor in TOOLBOXES:
    bindings.append(dict(container_id=actor['container_id'], pool='power_maintenance',
                         module='GeneratorHall', caption=actor['caption']))
path = DATA / 'scene_search_loot.json'
loot = read(path)
pool_ids = {p['id'] for p in pools}
binding_ids = {b['container_id'] for b in bindings}
loot['pools'] = [p for p in loot['pools'] if p['id'] not in pool_ids] + pools
loot['bindings'] = [b for b in loot['bindings'] if b['container_id'] not in binding_ids] + bindings
write(path, loot)

# Change current source documents rather than replacing them with audit snapshots.
sources = ['SourceAssets/DungeonPowerTheme20261004RefineV2/Config/module-drafts.json',
           'SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json']
for relative in sources:
    path = PROJECT / relative
    write(path, patch_document(read(path)))

path = PROJECT / 'Config/DefaultGame.ini'
raw = path.read_text('utf-8-sig')
entry = '+DirectoriesToAlwaysCook=(Path="/Game/Items/PowerCollectibles20261014/V1")'
if entry not in raw:
    backup(path)
    header = '[/Script/UnrealEd.ProjectPackagingSettings]'
    if header not in raw:
        raise RuntimeError('Packaging section missing')
    path.write_text(raw.replace(header, header + '\n' + entry, 1), encoding='utf8')
for icon in icons['icons']:
    icon['inventory_registered'] = True
write(ROOT / 'presentation.json', icons)
report = dict(stage='data_installed', timestamp_utc=datetime.now(timezone.utc).isoformat(),
              items=definitions, pools=pools, bindings=bindings, source_catalogs=sources,
              runtime_tested=False, multiplayer_tested=False, tests_run=False)
(ROOT / 'Receipts/data-installation.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print('POWER_DATA_INSTALLED items=%d bindings=%d pools=%d' % (len(definitions), len(bindings), len(pools)))
