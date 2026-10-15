"""Install the approved freight loot and maintenance recipes into live data."""
import copy
import datetime
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
DATA = PROJECT / 'Content/ColdSteelData'
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

icons = read(PROJECT/'SourceAssets/FreightTools20261014/inventory_icons.json')
meshes = read(PROJECT/'SourceAssets/FreightTools20261014/delivery.json')
tool_specs = [
    ('search_industrial_multimeter', '工业数字万用表', 'rare', 600,
     '装卸站检修电路使用的便携仪表，橡胶护套包住机身，旋钮与成对表笔保留完整。可作为检修工具战利品带回出售。'),
    ('search_precision_tool_kit', '精密检修工具组', 'epic', 1200,
     '装卸站技术员保管的成套检修工具，批头、套筒与小型手工具按槽收纳在缓冲内衬中。工具与盒体齐全，可作为战利品带回出售。'),
    ('search_cordless_impact_wrench', '充电式冲击扳手', 'epic', 1600,
     '用于货架和装卸设备维护的电动扳手，金属传动头、套筒与可拆电池保持完整。可作为检修工具战利品带回出售。'),
]
definitions = {}
for identity, name, rarity, price, desc in tool_specs:
    icon = next(i for i in icons['icons'] if i['id'] == identity)
    asset = next(i for i in meshes['assets'] if i['id'] == identity)
    definitions[identity] = dict(id=identity, name=name, category='material', type='检修工具',
        loot_group='maintenance', rarity=rarity, price=price, sell_souls=price, desc=desc,
        grid_w=icon['grid_w'], grid_h=icon['grid_h'], stack=1, stack_max=1, maxStack=1,
        inventory_unit='套' if identity.endswith('tool_kit') else '件',
        icon=icon['ue_icon'], ue_icon=icon['ue_icon'], icon_fallback=name, world_mesh=asset['ue_mesh'])
# Append only these new definitions, preserving all unrelated concurrent entries/formatting.
path = DATA/'items.json'
raw = path.read_text(encoding='utf-8-sig')
current = json.loads(raw)
new = {k: v for k, v in definitions.items() if k not in current}
for k in definitions.keys() & current.keys():
    if current[k] != definitions[k]:
        raise RuntimeError('Existing tool definition differs; preserve it: ' + k)
if new:
    tail = json.dumps(new, ensure_ascii=False, indent=2)[1:-1].strip('\n')
    path.write_text(raw[:raw.rfind('}')].rstrip() + ',\n' + tail + '\n}\n', encoding='utf8')

loot = read(DATA/'scene_search_loot.json')
base = {p['id']: p for p in loot['pools']}
materials = ['search_forging_alloy_blank', 'search_assembly_component_box',
             'search_precision_mechanism', 'search_resin_adhesive', 'search_laminated_strip']
def pool(identity, weights, tools=()):
    return dict(id=identity, group='maintenance', count_weights=[0, 100, 0, 0],
        entries=[dict(id=k, weight=w) for k, w in zip(materials, weights)] +
                [dict(id=k, weight=w) for k, w in tools])
pools = [pool('freight_maintenance', [30, 30, 25, 10, 5]),
         pool('freight_tool_cabinet', [27, 27, 22, 9, 5],
              [(tool_specs[0][0], 6), (tool_specs[1][0], 3), (tool_specs[2][0], 1)]),
         pool('freight_tool_drawer', [26, 28, 24, 8, 4],
              [(tool_specs[0][0], 7), (tool_specs[1][0], 3)])]
for identity, source in [('freight_daily', 'visitor_daily'),
                         ('freight_documents', 'office_documents'), ('freight_hardware', 'server_hardware')]:
    p = copy.deepcopy(base[source]); p.update(id=identity, count_weights=[0, 100, 0, 0]); pools.append(p)
pool_ids = {p['id'] for p in pools}
loot['pools'] = [p for p in loot['pools'] if p['id'] not in pool_ids] + pools

# This inventory was read from the saved production map in the preceding audit.
inventory = read(PROJECT/'Saved/FreightCompletionAudit20261014/inventory.json')
bindings = []
exceptions = {'StationWorkshop.Rack.ToteB': 'freight_daily',
              'StationWorkshop.DispatchFiles': 'freight_documents',
              'StationWorkshop.Exterior.EquipmentCase': 'freight_hardware'}
for room in inventory['rooms']:
    for identity, c in {c['id']: c for c in room['all_candidates']}.items():
        profile = exceptions.get(identity, 'freight_maintenance')
        if '.Tools' in identity:
            profile = 'freight_tool_drawer' if identity.endswith('.Drawer') else 'freight_tool_cabinet'
        bindings.append(dict(container_id=identity, pool=profile, module=room['id'], caption=c['caption']))
authored_ids = {b['container_id'] for b in bindings}
loot['bindings'] = [b for b in loot['bindings'] if b['container_id'] not in authored_ids] + bindings
save(DATA/'scene_search_loot.json', loot)

# Preserve current base costs/output/assembly assets and apply only approved extra inputs.
# The retired bow-limb entry now corresponds to the live complete-bow recipe.
plan = read(PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json')['recipe_plan']
applied = []
for filename in ['forging-recipes.json', 'gun-assembly.json', 'woodworking-recipes.json']:
    path = DATA/filename
    raw = path.read_text(encoding='utf-8-sig')
    config = json.loads(raw)
    for spec in (r for r in plan if r['source_file'].endswith('/' + filename)):
        identity = 'woodwork_bow' if spec['recipe_id'] == 'woodwork_bow_limb' else spec['recipe_id']
        row = next(r for r in config['recipes'] if r['id'] == identity)
        added = []
        for entry in spec['additional_inputs']:
            existing = next((i for i in row['inputs'] if i['item'] == entry['item']), None)
            if existing and existing != entry:
                raise RuntimeError('Conflicting material quantity: ' + identity)
            if not existing:
                row['inputs'].append(entry); added.append(entry)
        if added:
            start = raw.index('"id": "' + identity + '"')
            match = re.search(r'"inputs"\s*:\s*\[[\s\S]*?\]', raw[start:])
            if not match:
                raise RuntimeError('Missing input array: ' + identity)
            replacement = '"inputs": ' + json.dumps(row['inputs'], ensure_ascii=False)
            raw = raw[:start + match.start()] + replacement + raw[start + match.end():]
        applied.append(dict(file=filename, recipe=identity, additional_inputs=spec['additional_inputs']))
    if filename == 'woodworking-recipes.json':
        raw = raw.replace('每件投入 2 木材，合格后领取对应装备 1 件；未领取工件可废弃返还 1 木材。',
            '长弓投入 2 木材、1 树脂胶包、1 层压木条；长杖投入 2 木材。合格后领取对应装备 1 件；废弃按实际投入逐项返还一半并向下取整。')
    path.write_text(raw, encoding='utf8')

path = PROJECT/'Config/DefaultGame.ini'
raw = path.read_text(encoding='utf-8-sig')
entry = '+DirectoriesToAlwaysCook=(Path="/Game/Items/FreightTools20261014/VisualRefine")'
if entry not in raw:
    header = '[/Script/UnrealEd.ProjectPackagingSettings]'
    raw = raw.replace(header, header + '\n' + entry, 1)
    path.write_text(raw, encoding='utf8')

save(ROOT/'Receipts/data-installation.json', dict(
    timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    item_definitions=definitions, freight_bindings=bindings, pools=pools, recipes=applied,
    runtime_tested=False, note='Data installed; native integration/build recorded separately'))
print(f'FREIGHT_DATA_INSTALLED tools={len(definitions)} bindings={len(bindings)} pools={len(pools)} recipes={len(applied)}')
