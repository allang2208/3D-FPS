"""Scoped data audit and exact container-level probabilities (no game/save access)."""
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / 'SourceAssets/FacilitySearchLootGuaranteed20261013'
read = lambda path: json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
data = read('Content/ColdSteelData/scene_search_loot.json')
items = read('Content/ColdSteelData/items.json')
groups = read('Docs/Gameplay/search-container-groups-20261012.json')
catalog = read('SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json')
pools = {p['id']: p for p in data['pools']}
bindings = data['bindings']
assert len(pools) == 5 and len(bindings) == 31
assert len({b['container_id'] for b in bindings}) == 31
assert {b['container_id'] for b in bindings} == {b['container_id'] for b in groups['container_bindings']}
assert Counter(b['module'] for b in bindings) == {'FacilityReceptionHall': 15, 'FacilityTransit': 14, 'AccumulatorControl': 2}
for binding in bindings:
    module = next(m for m in catalog['modules'] if m['id'] == binding['module'])
    matches = [a for a in module['runtime_actors'] if a.get('container_id') == binding['container_id']]
    assert len(matches) == 1 and matches[0]['type'] == 'scene_container', binding
    assert 1 <= matches[0]['storage_pages'] <= 8
    assert binding['pool'] in pools

rarities = dict(common='普通', uncommon='优质', rare='稀有', epic='史诗', mythic='神话', legendary='传说')
names = dict(visitor_daily='访客寄存柜（6个）', ppe_daily='防护用品柜（6个）', office_documents='文件抽屉（15个）',
             maintenance_parts='检修工具箱（2个）', server_hardware='服务器柜（2个）')
lines = ['# 两厅与服务器柜搜索池 · 2026-10-13', '',
    '范围：正式随机设施地牢的接待大厅15个、分流大厅14个、已列出的服务器柜2个，共31个入口。按稳定容器ID绑定，不受六个分区排序影响。', '',
    '配置源：`Content/ColdSteelData/scene_search_loot.json`。投放21件已有物品；纪念腕表尚未制作，不投放。', '',
    '首次搜索必出1～3件：1件70%、2件25%、3件5%。先抽件数，再按权重不放回抽取具体物品；每件数量为1。同一箱不重复品类；不同箱允许相同物品。下表物品概率是“首次打开一个该类容器至少获得一次”的概率，不能直接相加当成100%。', '',
    '| 容器 | 1件 | 2件 | 3件 | 平均件数 |', '| --- | ---: | ---: | ---: | ---: |']
report = dict(scope_count=31, definitions_count=21, checks=[], pools={})
all_ids = set()
total_items = Fraction(0)
for pool in data['pools']:
    c = pool['count_weights']
    assert len(c) == 4 and c[0] == 0 and sum(c) == 100 and all(isinstance(n,int) and n>=0 for n in c)
    assert c[1] > c[2] > c[3] > 0
    assert len({e['id'] for e in pool['entries']}) == len(pool['entries'])
    assert all(isinstance(e['weight'],int) and e['weight']>0 for e in pool['entries'])
    count = sum(b['pool'] == pool['id'] for b in bindings)
    expected = Fraction(c[1]+2*c[2]+3*c[3],100)
    total_items += expected * count
    lines.append(f"| {names[pool['id']]} | {c[1]}% | {c[2]}% | {c[3]}% | {float(expected):.2f} |")
    total = sum(e['weight'] for e in pool['entries'])
    marginal = {}
    for entry in pool['entries']:
        id, weight = entry['id'], entry['weight']
        assert id in items, id
        item = items[id]
        assert item['rarity'] in rarities and item['grid_w']>0 and item['grid_h']>0
        assert item.get('maxStack',item.get('stack_max',1))>=1
        icon = item.get('ue_icon') or item.get('icon')
        assert icon and (ROOT/'Content/ColdSteelData'/icon).is_file(), (id, icon)
        if 'world_mesh' in item:
            mesh = item['world_mesh'].split('.')[0].removeprefix('/Game/')
            assert (ROOT/'Content'/f'{mesh}.uasset').is_file(), id
        else:
            assert id == 'mineral_water'  # Existing multipart bottle uses PotionVisuals instead.
            visual = next(v for v in read('Content/ColdSteelData/potion_visuals.json')['tiers'] if id in v['definitions'])
            for key in ('closed','half_closed','shell','liquid','stopper','liquid_material'):
                asset = visual[key].split('.')[0].removeprefix('/Game/')
                assert (ROOT/'Content'/f'{asset}.uasset').is_file(), (id,key)
        if id.startswith('search_'): assert item['loot_group'] == pool['group'], id
        all_ids.add(id)
        probability_two = Fraction(weight,total) + sum(
            Fraction(o['weight'],total)*Fraction(weight,total-o['weight'])
            for o in pool['entries'] if o['id'] != id)
        probability_three = probability_two + sum(
            Fraction(a['weight'],total)*Fraction(b['weight'],total-a['weight'])*Fraction(weight,total-a['weight']-b['weight'])
            for a in pool['entries'] for b in pool['entries']
            if a['id'] != id and b['id'] != id and a['id'] != b['id'])
        marginal[id] = Fraction(c[1],100)*Fraction(weight,total) + Fraction(c[2],100)*probability_two + Fraction(c[3],100)*probability_three
    assert sum(marginal.values()) == expected
    report['pools'][pool['id']] = dict(containers=count, count_weights=c, expected_items=float(expected),
                                      item_probability={id:float(p) for id,p in marginal.items()})
assert len(all_ids) == 21
assert (items['search_graphics_card']['grid_w'], items['search_graphics_card']['grid_h']) == (2,1)
lines += ['', f'31个入口全部首次搜完的理论平均为 **{float(total_items):.2f}件**；实际每次地牢有波动。', '']
for pool in data['pools']:
    lines += [f"## {names[pool['id']]}", '', '| 物品 | 稀有度 | 占格 | 每柜出现概率 | 抽取权重 |', '| --- | --- | --- | ---: | ---: |']
    for entry in pool['entries']:
        item=items[entry['id']]
        p=report['pools'][pool['id']]['item_probability'][entry['id']]
        lines.append(f"| {item['name']} | {rarities[item['rarity']]} | {item['grid_w']}×{item['grid_h']} | {p*100:.4f}% | {entry['weight']} |")
    lines.append('')
lines += ['## 存档与联机', '',
    '- 每次地牢运行、每个容器独立保存；尚未生成内容的容器首次搜索由服务器抽取1～3件并落盘。已经搜索过的旧结果（包括此前抽到的空箱）保留；重复打开、客户端重连、取空不重抽。新运行使用新的运行种子与储物键。',
    '- 多人查看同一份库存；取物使用库存版本校验。两人争取同一件物品时，旧版本操作被拒绝并刷新清单。首次抽取和物品转移沿用共享世界交易日志与角色回执。',
    '- 请求及回包都校验玩家距离、遮挡与生存状态；客户端不能指定种子或物品结果，未搜索不能直接提交移动。',
    '- 旧版空柜在第一次搜索时补一次初始投放；已有物品保留，不叠加奖励。单人旧档转联机且柜内仍有房主私有物品或领取记录时，由房主先打开一次完成原子迁移。',
    '- 搜索箱不是跨运行仓库：结束的单人运行中遗留箱内物品，在再次使用对应箱时清理；取入背包的物品不受影响。',
    '- 这次实现投放与共享取物；不代表新增制作配方或出售系统已经完成。实际双客户端联机体验由用户测试。', '',
    '本次概率调整与后台构建记录见 `SourceAssets/FacilitySearchLootGuaranteed20261013/Receipts/`。上一版0～2件的测试记录位于 `SourceAssets/FacilitySearchLoot20261013/Receipts/`，不作为本版测试结果。', '']
for tier in read('Content/ColdSteelData/dungeon_loot.json')['tiers']:
    for entry in tier['entries']:
        # This adjacent check only covers the two repaired IDs; currency/ammo have other registries.
        if entry['id'].startswith('enchant_scroll_'): assert entry['id'] in items, entry['id']
report['checks'] = ['31 exact authored bindings', '21 existing item definitions', 'icon and model assets exist',
                    'weight and count bounds', 'exact marginal probabilities', 'GPU 2x1 footprint', 'adjacent chest JSON and repaired IDs']
report['expected_total_items'] = float(total_items)
(TASK/'Receipts/data-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'Docs/Gameplay/facility-search-loot-20261013.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(dict(checks=report['checks'], expected_total_items=float(total_items)),ensure_ascii=False))
