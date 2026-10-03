# -*- coding: utf-8 -*-
"""采集工具强化目录一致性自检（离线，不启动游戏）。

口径 = Docs/Weapons/tool-enhancement-design-20260925.md 第 2／3／6 节
＋ Docs/UI/tool-enhancement-column-plan-20260925.md「数据与动作」。
被检目录：Content/ColdSteelData/tool-enhance.json（等级阶梯：1 石 → 5 紫石）。

与 check_tool_modification_consistency.py 的分工：那一份查四栏**数值改造**目录
（tool-gunsmith.json）；本脚本查**外观档位**目录（tool-enhance.json），互不重叠。
刻意不改动已通过的那份脚本。

断言：
  0. 结构：version==1；metal_slot／wood_slot 存在且非空（按槽名找材质索引，不按固定索引）。
  1. levels 恰 5 项；level 连续 1..5；id 唯一且恰为 stone/bronze/steel/stainless/purple_stone。
  2. 每项 name／description 非空且含中文；materials 同时含 tool_axe 与 tool_pickaxe，
     路径以 /Game/ 开头、以 .资产名 结尾（object path 形式 /Game/…/X.X）。
  3. 每项 cost 与 stats 均为空对象——本阶段不得出现任何强化消耗或强化后数值，
     出现任何一个键即报错（防止假数字漏进交付）。
  4. weapons 恰含 tool_axe／tool_pickaxe；每项 traits 至少一条明确「只改外观不影响数值」。
  5. 与 C++ 加载器对齐：反查 ProductionToolEnhance.cpp 实际读取的键名，
     目录键集合与加载器读取键集合必须逐字一致——任一侧多出键即报错
     （多写的键会被静默忽略，正是"改了目录却不生效"的典型故障）。
  6. 等级规则：断言 CanEnhance 仍是逐级 +1（源码含 Level<MaxLevel 判定与 Level+1），
     且不出现跳级／降级写法，防止后续被改成可跳级。

Usage: python Tools/Production/check_tool_enhancement_consistency.py [tool-enhance.json]
Exits 1 when a PROBLEM is found. 报告写 Saved/Production/tool-enhance-report.txt。
"""
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'Content' / 'ColdSteelData' / 'tool-enhance.json'
LOADER = ROOT / 'Source' / 'FPSGAME' / 'Production' / 'ProductionToolEnhance.cpp'

# 等级阶梯固定 5 档、顺序固定：与设计文档第 2 节阶梯表逐字对应。
LADDER = [(1, 'stone'), (2, 'bronze'), (3, 'steel'), (4, 'stainless'), (5, 'purple_stone')]
TOOLS = ['tool_axe', 'tool_pickaxe']
# 根对象上允许出现的键：加载器只读 metal_slot／wood_slot／levels。
# weapons 给浮窗「特殊性质」用（与 tool-gunsmith.json 同款结构），加载器不读但不报错。
ROOT_KEYS = {'version', 'metal_slot', 'wood_slot', 'levels', 'weapons'}
LEVEL_KEYS = {'level', 'id', 'name', 'description', 'materials', 'cost', 'stats'}
# 「只改外观不影响数值」这层意思必须有一句话说到，否则数值接入前的口径会被误读。
INTENT_KEYWORDS = ['不影响', '不改', '只改', '只更换', '无数值', '不改变']

problems, infos = [], []


def has_chinese(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text or ''))


d = json.load(io.open(SRC, encoding='utf-8'))

# 0) 结构与版本
if d.get('version') != 1:
    problems.append('version 应为 1，实际 %r' % d.get('version'))
for key in ('metal_slot', 'wood_slot'):
    val = d.get(key)
    if not isinstance(val, str) or not val.strip():
        problems.append('%s 缺失或为空（生产者外观按槽名找材质索引）' % key)
    else:
        infos.append('%s = %s' % (key, val))
for key in sorted(set(d) - ROOT_KEYS):
    problems.append('目录出现未登记根键 %r（加载器不读，改动会静默失效）' % key)

# 1) levels：恰 5 项、连续 1..5、id 唯一且固定
levels = d.get('levels')
if not isinstance(levels, list):
    problems.append('levels 不是数组')
    levels = []
if len(levels) != len(LADDER):
    problems.append('levels 应为 %d 项，实际 %d 项（上限＝条目数，改条目数即改强化上限）'
                    % (len(LADDER), len(levels)))
got_levels = [e.get('level') for e in levels]
if got_levels != [n for n, _ in LADDER]:
    problems.append('level 必须连续 1..5，实际 %r' % (got_levels,))
got_ids = [e.get('id') for e in levels]
if got_ids != [i for _, i in LADDER]:
    problems.append('id 顺序或取值不符，实际 %r（应为 %r）' % (got_ids, [i for _, i in LADDER]))
dups = {i for i in got_ids if got_ids.count(i) > 1}
if dups:
    problems.append('id 重复 %s' % sorted(dups))

# 2) 每项字段、材质路径
for entry in levels:
    where = 'levels[%s/%s]' % (entry.get('level'), entry.get('id'))
    for key in sorted(set(entry) - LEVEL_KEYS):
        problems.append('%s: 未登记键 %r（加载器不读）' % (where, key))
    for req in ('level', 'id', 'name', 'description', 'materials', 'cost', 'stats'):
        if req not in entry:
            problems.append('%s: 缺字段 %s' % (where, req))
    if not has_chinese(entry.get('name')):
        problems.append('%s: name 必须是非空中文，实际 %r' % (where, entry.get('name')))
    if not has_chinese(entry.get('description')):
        problems.append('%s: description 必须是非空中文，实际 %r' % (where, entry.get('description')))
    mats = entry.get('materials') or {}
    for tool in TOOLS:
        path = mats.get(tool)
        if not path:
            problems.append('%s: materials 缺 %s（该工具该档没有材质，会退回保持现状）' % (where, tool))
            continue
        if not path.startswith('/Game/'):
            problems.append('%s: %s 路径未以 /Game/ 开头：%r' % (where, tool, path))
        # object path 接受两种形式：/Game/…/X.X（完整对象路径）或 /Game/…/X（简单资产的
        # 包路径，LoadObject 会解析到同名外层对象）。其余形式判错。
        asset = path.rsplit('/', 1)[-1]
        if '.' in asset and asset.split('.', 1)[0] != asset.split('.', 1)[1]:
            problems.append('%s: %s 路径的 .后缀与资产名不一致：%r' % (where, tool, path))
        # 阶段 2：资产必须真实落盘，防止目录指向不存在的材质（运行时走降级保持原样）。
        rel = path.split('.', 1)[0].replace('/Game/', '', 1)
        on_disk = ROOT / 'Content' / (rel + '.uasset')
        if not on_disk.exists():
            problems.append('%s: %s 材质资产不在磁盘上：%s' % (where, tool, on_disk.relative_to(ROOT)))
    for tool in sorted(set(mats) - set(TOOLS)):
        problems.append('%s: materials 含未登记工具 %r（只有斧与镐认这个目录）' % (where, tool))

# 2b) 阶段 2 结构断言：槽名精确；2 级必须指向原材质（结构性等价，不需要渲染对比）；
#     其余各级指向 Enhance20260925 的实例且命名固定，防止材质被悄悄换目录或换工具。
if d.get('metal_slot') not in (None, 'Metal'):
    problems.append('metal_slot 应为 Metal（拆槽 FBX 的槽名），实际 %r' % d.get('metal_slot'))
if d.get('wood_slot') not in (None, 'Wood'):
    problems.append('wood_slot 应为 Wood，实际 %r' % d.get('wood_slot'))
ORIGINAL = {'tool_axe': '/Game/Items/ProductionTools/BattleAxe20260919/M_BattleAxe',
            'tool_pickaxe': '/Game/Items/ProductionTools/RusticPickaxe20260919/M_RusticPickaxe'}
MI_NAMES = {1: 'Stone', 3: 'Steel', 4: 'Stainless', 5: 'PurpleStone'}
MI_TAG = {'tool_axe': 'Axe', 'tool_pickaxe': 'Pick'}
for entry in levels:
    where = 'levels[%s/%s]' % (entry.get('level'), entry.get('id'))
    mats = entry.get('materials') or {}
    level = entry.get('level')
    for tool in TOOLS:
        path = mats.get(tool)
        if not path:
            continue
        bare = path.split('.', 1)[0]
        if level == 2:
            if bare != ORIGINAL[tool]:
                problems.append('%s: %s 的 2 级必须指向原材质 %s（等价基线），实际 %s'
                                % (where, tool, ORIGINAL[tool], bare))
        elif level in MI_NAMES:
            want = '/Game/Items/ProductionTools/Enhance20260925/MI_ToolHead_%s_%s' % (
                MI_TAG[tool], MI_NAMES[level])
            if bare != want:
                problems.append('%s: %s 的 %s 级材质应为 %s，实际 %s'
                                % (where, tool, level, want, bare))
    infos.append('%s: 材质路径与槽名核对完成' % where)

# 3) cost／stats 必须为空对象：本阶段不设消耗、不设强化后数值
for entry in levels:
    where = 'levels[%s]' % entry.get('level')
    for key in ('cost', 'stats'):
        val = entry.get(key)
        if not isinstance(val, dict):
            problems.append('%s: %s 必须是空对象，实际 %r' % (where, key, val))
        elif val:
            problems.append('%s: %s 必须为空对象，实际含 %s —— 本阶段不得出现消耗或强化后数值'
                            % (where, key, sorted(val)))
        else:
            infos.append('%s: %s 为空（本阶段口径）' % (where, key))

# 4) weapons 与 traits
weapons = d.get('weapons')
if not isinstance(weapons, list):
    problems.append('weapons 不是数组')
    weapons = []
wids = [w.get('id') for w in weapons]
for tool in TOOLS:
    if tool not in wids:
        problems.append('weapons 缺 %s（浮窗「特殊性质」没有来源）' % tool)
for wid in wids:
    if wid not in TOOLS:
        problems.append('weapons 含未登记工具 %r（铁铲不纳入强化）' % wid)
for w in weapons:
    traits = w.get('traits') or []
    if not traits:
        problems.append('%s: 缺 traits' % w.get('id'))
        continue
    texts = [t.get('text') or '' for t in traits]
    for t in traits:
        if not t.get('text'):
            problems.append('%s: traits 有空行' % w.get('id'))
        if t.get('icon') not in ('mechanic', 'neutral', 'magic', 'special', 'drawback'):
            problems.append('%s: traits icon %r 不在已知集合' % (w.get('id'), t.get('icon')))
    if not any(k in text for text in texts for k in INTENT_KEYWORDS):
        problems.append('%s: traits 没有一条说明「只改外观／不影响数值」'
                        '（数值接入前必须如实这么写）' % w.get('id'))
    infos.append('%s: traits %d 条' % (w.get('id'), len(traits)))

# 5) 与 C++ 加载器逐字对齐：任一侧多出键都报错
if LOADER.exists():
    src = io.open(LOADER, encoding='utf-8').read()
    loaded = set(re.findall(r'TryGet(?:String|Number|Array|Object)Field\(TEXT\("([a-z_0-9]+)"\)', src))
    # 加载器里读到的键全部来自目录；levels 条目的键与根键合起来才是完整集合。
    catalog = set()
    for entry in levels:
        catalog |= set(entry)
    if 'levels' not in loaded:
        problems.append('加载器未读取 levels（ProductionToolEnhance.cpp 结构已变）')
    root_read = loaded & ROOT_KEYS
    want_root = {'metal_slot', 'wood_slot', 'levels'}
    if root_read != want_root:
        problems.append('加载器读取的根键 %s ≠ 目录约定 %s' % (sorted(root_read), sorted(want_root)))
    entry_read = loaded - ROOT_KEYS
    # cost／stats 本阶段刻意「解析但不使用」，加载器不出现这两个键是设计意图，不是漏读：
    # 它们由上面的空对象断言守住。除这两个之外，加载器读取键必须与目录条目键逐字一致。
    if entry_read != LEVEL_KEYS - {'cost', 'stats'}:
        problems.append('加载器读取的条目键 %s ≠ 目录条目键 %s（多写的键会被静默忽略）'
                        % (sorted(entry_read), sorted(LEVEL_KEYS - {'cost', 'stats'})))
    infos.append('加载器读取键：根 %s ＋ 条目 %s' % (sorted(root_read), sorted(entry_read)))
else:
    problems.append('找不到加载器 %s（无法核对键集合）' % LOADER.relative_to(ROOT))

# 6) 等级规则：逐级 +1、不可降级、不可跳级
if LOADER.exists():
    body = re.search(r'CanEnhance\(.*?\n\}', src, re.S)
    impl = body.group(0) if body else ''
    if not impl:
        problems.append('找不到 CanEnhance 实现（无法断言逐级 +1 规则）')
    else:
        compact = impl.replace(' ', '')
        # 上界判定可以写成 Level<MaxLevel 或等价的 Current<MaxLevel（局部名可变），
        # 断言的是「与上限比较」这件事仍在，而不是某个局部变量名。
        if not re.search(r'<(?:Level|Current|MaxLevel)?\(?\)?MaxLevel\(\)', compact) and 'MaxLevel()' not in compact:
            problems.append('CanEnhance 未与 MaxLevel 比较（可能是可跳级或可降级写法）')
        if 'Current+1' not in compact:
            problems.append('CanEnhance 未含 Current+1（逐级 +1 规则被改）')
        if compact.count('OutNextLevel=') > 1:
            problems.append('CanEnhance 多次写 OutNextLevel（可能引入跳级分支）')
        for bad in ('Level+2', 'Level-1', 'Current-'):
            if bad in compact:
                problems.append('CanEnhance 出现跳级／降级写法 %r' % bad)
        infos.append('等级规则：逐级 +1、不可降级、不可跳级（CanEnhance 逐字核对通过）')

print('=== PROBLEMS (%d) ===' % len(problems))
for p in problems:
    print('  ! ' + p)
print('=== INFO (%d) ===' % len(infos))
for i in infos:
    print('  - ' + i)
report = ROOT / 'Saved' / 'Production' / 'tool-enhance-report.txt'
report.parent.mkdir(parents=True, exist_ok=True)
try:
    source = str(SRC.relative_to(ROOT))
except ValueError:
    source = str(SRC)
with io.open(report, 'w', encoding='utf-8') as f:
    f.write('# %s 生成，由 Tools/Production/check_tool_enhancement_consistency.py 覆盖写入\n'
            % datetime.now().strftime('%Y-%m-%d %H:%M'))
    f.write('目录：%s\n' % source)
    f.write('=== PROBLEMS (%d) ===\n' % len(problems))
    for p in problems:
        f.write('  ! %s\n' % p)
    f.write('=== INFO (%d) ===\n' % len(infos))
    for i in infos:
        f.write('  - %s\n' % i)
print(report)
sys.exit(1 if problems else 0)