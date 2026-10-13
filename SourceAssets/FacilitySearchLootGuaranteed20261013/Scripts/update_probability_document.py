"""Render exact new probabilities into the existing document; does not run audits/tests."""
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
data = json.loads((ROOT/'Content/ColdSteelData/scene_search_loot.json').read_text(encoding='utf-8-sig'))
items = json.loads((ROOT/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
path = ROOT/'Docs/Gameplay/facility-search-loot-20261013.md'
old = path.read_text(encoding='utf-8-sig')
names = dict(visitor_daily='访客寄存柜（6个）', ppe_daily='防护用品柜（6个）', office_documents='文件抽屉（15个）',
             maintenance_parts='检修工具箱（2个）', server_hardware='服务器柜（2个）')
rarities = dict(common='普通', uncommon='优质', rare='稀有', epic='史诗', mythic='神话', legendary='传说')
lines = [old.split('先抽空箱')[0].split('首次搜索必出')[0].rstrip(), '',
    '首次搜索必出1～3件：1件70%、2件25%、3件5%。先抽件数，再按权重不放回抽取具体物品；每件数量为1。同一箱不重复品类；不同箱允许相同物品。下表物品概率是“首次打开一个该类容器至少获得一次”的概率，不能直接相加当成100%。', '',
    '| 容器 | 1件 | 2件 | 3件 | 平均件数 |', '| --- | ---: | ---: | ---: | ---: |']
expected_total = Fraction(0)
probabilities = {}
for pool in data['pools']:
    c = pool['count_weights']
    expected = sum(Fraction(n*w,100) for n,w in enumerate(c))
    expected_total += expected * sum(b['pool']==pool['id'] for b in data['bindings'])
    lines.append(f"| {names[pool['id']]} | {c[1]}% | {c[2]}% | {c[3]}% | {float(expected):.2f} |")
    total = sum(e['weight'] for e in pool['entries'])
    rows = {}
    for entry in pool['entries']:
        id, w = entry['id'], entry['weight']
        one = Fraction(w,total)
        two = one + sum(Fraction(a['weight'],total)*Fraction(w,total-a['weight']) for a in pool['entries'] if a['id']!=id)
        three = two + sum(Fraction(a['weight'],total)*Fraction(b['weight'],total-a['weight'])*Fraction(w,total-a['weight']-b['weight'])
            for a in pool['entries'] for b in pool['entries'] if a['id']!=id and b['id']!=id and a['id']!=b['id'])
        rows[id] = Fraction(c[1],100)*one + Fraction(c[2],100)*two + Fraction(c[3],100)*three
    probabilities[pool['id']] = rows
lines += ['', f'31个入口全部首次搜完的理论平均为 **{float(expected_total):.2f}件**；实际每次地牢有波动。', '']
for pool in data['pools']:
    lines += [f"## {names[pool['id']]}", '', '| 物品 | 稀有度 | 占格 | 每柜出现概率 | 抽取权重 |', '| --- | --- | --- | ---: | ---: |']
    for entry in pool['entries']:
        item = items[entry['id']]
        p = probabilities[pool['id']][entry['id']]
        lines.append(f"| {item['name']} | {rarities[item['rarity']]} | {item['grid_w']}×{item['grid_h']} | {float(p)*100:.4f}% | {entry['weight']} |")
    lines.append('')
footer = '## 存档与联机'+old.split('## 存档与联机',1)[1]
footer = footer.replace('同一运行内首次搜索由服务器抽取并落盘，空箱也记录。', '尚未生成内容的容器首次搜索由服务器抽取1～3件并落盘。已经搜索过的旧结果（包括此前抽到的空箱）保留；')
footer = footer.replace('代码检查与后台构建记录见 `SourceAssets/FacilitySearchLoot20261013/Receipts/`。自动化为内存中的代码测试，不读写玩家存档、不启动地图游玩。',
    '本次概率调整与后台构建记录见 `SourceAssets/FacilitySearchLootGuaranteed20261013/Receipts/`。上一版0～2件的测试记录位于 `SourceAssets/FacilitySearchLoot20261013/Receipts/`，不作为本版测试结果。本轮未运行测试，由用户体验。')
path.write_text('\n'.join(lines)+footer,encoding='utf-8')
print(f'Probability document updated; expected total {float(expected_total):.2f} items.')
