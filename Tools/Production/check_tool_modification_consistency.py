# -*- coding: utf-8 -*-
"""采集工具改造目录一致性自检（离线，不启动游戏）。

口径 = skills/ue5-weapon-workflow/references/attachment-standard.md「配件数值与说明分工」
＋ references/modular-melee.md「栏目 ≠ 网格」、references/harvesting-tools.md「采集与自卫分开」。
被检目录：Content/ColdSteelData/tool-gunsmith.json（伐木斧、矿镐四栏：握把／握柄／改件／主部件）。

断言：
  0. 结构：四栏键名与中文名固定；栏目内 id 去重；必备字段齐全；weapons 只允许
     production_tools.json 里登记且可改造的工具（tool_axe / tool_pickaxe）；
     每把工具在每一栏都至少有一个可选项（含 factory）；traits 必备。
  1. stats 键全部在登记口径内，且与 C++ 加载器实际读取的键集合逐字一致
     （键名打错会静默失效，因此直接反查 Source/FPSGAME/Weapons/ToolGunsmith.cpp）。
  2. description 不含可推导数字（%、增减+数字、时长、次数、厘米）。
  3. effects 由 stats 反推生成后逐字比对：行名＝登记行名、数字＝stats 推导值、
     正负号＝变化方向、benefit＝「变化方向 XOR 越小越好」；一个 stats 键恰好一行。
  4. 同 (栏, id) 不得出现两份不同定义（跨工具共用项由加载器复制，天然逐字一致）。
  5. 数值边界：单项命中减免不得把出厂 3 次降到 1 次以下；每栏最多装一件，
     全栏最省配置也必须保留 ≥2 次有效命中（采集节奏下限）；倍率与几率在合理区间。
  6. 与 production_tools.json 互相核对：工具的物品定义就在该文件（不在 items.json），
     name/category/desc/ue_icon 与 tool_mesh、节奏、距离、melee_damage 必须齐全，
     否则工作台与浮窗会读到默认值。

Usage: python Tools/Production/check_tool_modification_consistency.py [catalog.json]
Exits 1 when a PROBLEM is found. 报告写 Saved/Production/tool-modification-report.txt。
"""
import io
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'Content' / 'ColdSteelData' / 'tool-gunsmith.json'
TOOLS = SRC.parent / 'production_tools.json'
LOADER = ROOT / 'Source' / 'FPSGAME' / 'Weapons' / 'ToolGunsmith.cpp'

# 四栏固定顺序与中文名：与 UGunsmithSystem::ToolSlotKeys / ToolCategoryNames 一致。
COLUMNS = [('grip', '握把'), ('shaft', '握柄'), ('fitting', '改件'), ('head', '主部件')]
FACTORY_HITS = 3          # FProductionResource::RequiredHits
MODIFIABLE = {'tool_axe', 'tool_pickaxe'}

# stats 键 → (登记行名, 数值类型, 越小越好)
LABELS = {
    'harvest_yield_mult': ('采集产出', 'mult', False),
    'harvest_hits_add': ('所需有效命中', 'hits', True),
    'harvest_reach_mult': ('采集距离', 'mult', False),
    'harvest_radius_add_cm': ('命中宽容半径', 'cm', False),
    'bonus_harvest_chance': ('额外产出几率', 'chance', False),
    'damage_mult': ('自卫伤害', 'mult', False),
    'attack_speed_mult': ('挥砍速度', 'mult', False),
    'stamina_mult': ('体力消耗', 'mult', True),
    'combat_reach_mult': ('攻击范围', 'mult', False),
    'toughness_damage_mult': ('韧性伤害', 'mult', False),
    'crit_chance_add': ('暴击率', 'points', False),
}
FORBIDDEN = ['耐力消耗', '采集产量', '产出倍率', '攻击距离', '挥动速度', '采集范围']

problems, infos = [], []


def expected_effect(key, value):
    """由 stats 反推唯一合法的 effect 行（行名、数字、符号、benefit）。"""
    label, kind, lower = LABELS[key]
    if kind == 'mult':
        delta = value - 1.0
        number = '%d' % round(abs(delta) * 100)
        unit, up = '%', delta > 0
    elif kind == 'hits':
        number = '%d' % abs(int(value))
        unit, up = ' 次', value > 0
    elif kind == 'cm':
        number = '%d' % round(abs(value))
        unit, up = ' cm', value > 0
    elif kind == 'chance':
        number = '%d' % round(abs(value) * 100)
        unit, up = '%', value > 0
    else:  # points
        number = '%d' % round(abs(value))
        unit, up = '%', value > 0
    sign = '+' if up else '-'
    benefit = 1 if up != lower else -1
    return {'text': '%s %s%s%s' % (label, sign, number, unit), 'benefit': benefit}


def check_option(where, op):
    st = op.get('stats') or {}
    desc = op.get('description') or ''
    eff = op.get('effects') or []
    for req in ('id', 'name', 'description', 'effects', 'stats'):
        if req not in op:
            problems.append('%s: 缺字段 %s' % (where, req))
    for k in sorted(set(st) - set(LABELS)):
        problems.append('%s: 未登记 stats 键 %s' % (where, k))
    if not st:
        problems.append('%s: stats 为空（数值改造必须至少一项）' % where)
    # ---- description：不得手写可推导数字 ----
    if '%' in desc:
        problems.append('%s: description 含百分号（数字应由 stats 推导，只写在 effects 里）' % where)
    if re.search(r'(增加|减少|提高|降低|缩短|加长)\s*[0-9]', desc):
        problems.append('%s: description 手写增减数字' % where)
    if re.search(r'[0-9]+(?:\.[0-9]+)?\s*(?:%|次|厘米|cm|米|m|秒|s|ms)\b', desc):
        problems.append('%s: description 手写规格数字：%r' % (where, desc))
    for kw in FORBIDDEN:
        if kw in desc:
            problems.append('%s: description 用非登记同义词 %r' % (where, kw))
    # ---- effects：由 stats 反推后逐字比对 ----
    want = [expected_effect(k, v) for k, v in st.items() if k in LABELS]
    got = [{'text': e.get('text', ''), 'benefit': e.get('benefit', 0)} for e in eff]
    for w in want:
        match = next((g for g in got if g['text'] == w['text']), None)
        if match is None:
            near = next((g for g in got if g['text'].split(' ')[0] == w['text'].split(' ')[0]), None)
            if near is None:
                problems.append('%s: stats 键缺对应 effect 行，应为 %r' % (where, w['text']))
            else:
                problems.append('%s: effect %r ≠ 由 stats 推导的 %r' % (where, near['text'], w['text']))
        elif match['benefit'] != w['benefit']:
            problems.append('%s: %r benefit=%s，应为 %s（变化方向与「越小越好」不符）'
                            % (where, w['text'], match['benefit'], w['benefit']))
    for g in got:
        if g['text'] not in [w['text'] for w in want]:
            problems.append('%s: effect %r 无法由 stats 推导' % (where, g['text']))
    for kw in FORBIDDEN:
        for g in got:
            if kw in g['text']:
                problems.append('%s: effect 用非登记同义词 %r（登记行名见 LABELS）' % (where, kw))
    # ---- 数值边界 ----
    hits = st.get('harvest_hits_add', 0)
    if FACTORY_HITS + hits < 1:
        problems.append('%s: 所需有效命中降到 %d（最少 1 次）' % (where, FACTORY_HITS + hits))
    for k, v in st.items():
        if k.endswith('_mult') and not 0.5 <= v <= 2.0:
            problems.append('%s: %s=%g 超出 0.5～2 倍区间' % (where, k, v))
        if k == 'bonus_harvest_chance' and not 0.0 <= v <= 1.0:
            problems.append('%s: bonus_harvest_chance=%g 超出 0～1' % (where, v))
        if k == 'crit_chance_add' and not 0.0 <= v <= 50.0:
            problems.append('%s: crit_chance_add=%g 超出 0～50 百分点' % (where, v))
    return st


d = json.load(io.open(SRC, encoding='utf-8'))
raw = io.open(SRC, encoding='utf-8').read()

# 0) 结构
if re.search(r'。 [^"\n]', raw):
    problems.append('存在「。 」拼接残句')
cols = d.get('columns') or []
got_keys = [(c.get('key'), c.get('name')) for c in cols]
if got_keys != COLUMNS:
    problems.append('栏目顺序或中文名不符：%s（应为 %s）' % (got_keys, COLUMNS))
tools = json.load(io.open(TOOLS, encoding='utf-8')) if TOOLS.exists() else {}
weapons = {w['id']: w for w in (d.get('weapons') or [])}
for wid in weapons:
    if wid not in MODIFIABLE:
        problems.append('weapons 含不可改造工具 %s（铁铲等没有目录条目）' % wid)
    if tools and wid not in tools:
        problems.append('weapons %s 不在 production_tools.json' % wid)
for wid in sorted(MODIFIABLE - set(weapons)):
    problems.append('缺 weapons 条目 %s（浮窗没有 traits 来源）' % wid)

shared = defaultdict(set)
per_weapon = defaultdict(lambda: defaultdict(int))
hits_best = defaultdict(lambda: defaultdict(int))
for c in cols:
    key = c.get('key')
    for req in ('key', 'name', 'default', 'description', 'options'):
        if req not in c:
            problems.append('栏目 %s 缺字段 %s' % (key, req))
    ids = [o.get('id') for o in (c.get('options') or [])]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        problems.append('栏目 %s 重复 id %s' % (key, sorted(dup)))
    if 'false' in ids:
        problems.append('栏目 %s 不得自带 id=false（factory 由加载器生成）' % key)
    for o in c.get('options') or []:
        where = '%s/%s' % (key, o.get('id'))
        st = check_option(where, o)
        shared[(key, o['id'])].add(json.dumps(
            {'n': o.get('name'), 'd': o.get('description'), 's': st, 'e': o.get('effects')},
            sort_keys=True, ensure_ascii=False))
        targets = o.get('weapons') or sorted(weapons)
        for t in targets:
            if t not in weapons:
                problems.append('%s: weapons 限定 %s 不在目录' % (where, t))
                continue
            per_weapon[t][key] += 1
            hits_best[t][key] = min(hits_best[t][key], st.get('harvest_hits_add', 0))

# 4) 同 (栏, id) 只能有一份定义
for (key, oid), variants in sorted(shared.items()):
    if len(variants) > 1:
        problems.append('%s/%s 有 %d 份不同定义（跨工具共用项必须逐字一致，或改用不同 id）'
                        % (key, oid, len(variants)))

# 0) 每把工具每栏都要有可选项
for wid in sorted(weapons):
    for key, _ in COLUMNS:
        if per_weapon[wid][key] < 1:
            problems.append('%s: 栏目 %s 没有可用选项' % (wid, key))
    # 5) 节奏下限：每栏最多装一件，取各栏最省的命中减免求和；
    #    砍倒／开采至少 2 次有效命中，否则采集节奏与镜头反馈被改造抹平。
    fastest = FACTORY_HITS + sum(hits_best[wid].values())
    if fastest < 2:
        problems.append('%s: 全栏最省配置只需 %d 次有效命中（节奏下限 2 次；命中减免只允许一个来源）'
                        % (wid, fastest))
    infos.append('%s: 最快配置 %d 次有效命中' % (wid, fastest))
    tr = weapons[wid].get('traits') or []
    if not tr:
        problems.append('%s: 缺 traits（浮窗没有「特殊性质」）' % wid)
    for t in tr:
        if not t.get('text'):
            problems.append('%s: traits 有空行' % wid)
        if t.get('icon') not in ('mechanic', 'neutral', 'magic', 'special', 'drawback'):
            problems.append('%s: traits icon %r 不在已知集合' % (wid, t.get('icon')))
    infos.append('%s: 可用选项 %s' % (wid, {k: per_weapon[wid][k] for k, _ in COLUMNS}))

# 1) stats 键集合必须与 C++ 加载器逐字一致
used = set()
for c in cols:
    for o in c.get('options') or []:
        used |= set((o.get('stats') or {}).keys())
if LOADER.exists():
    src = io.open(LOADER, encoding='utf-8').read()
    loaded = set(re.findall(r'TryGetNumberField\(TEXT\("([a-z_0-9]+)"\)', src))
    if loaded != used:
        problems.append('加载器读取键 %s ≠ 目录使用键 %s' % (sorted(loaded), sorted(used)))
    unknown = used - set(LABELS)
    if unknown:
        problems.append('目录使用未登记键 %s' % sorted(unknown))
else:
    problems.append('找不到加载器 %s（无法核对 stats 键）' % LOADER.relative_to(ROOT))

# 6) 与 production_tools.json 互检：工具的物品定义就在这个文件里
#    （UColdSteelStatusModel::LoadProductionDefinitions 直接并进 Definitions），
#    不在 items.json，因此只核对同一份文件里的物品字段与数值字段。
REQUIRED_FIELDS = ['name', 'category', 'desc', 'ue_icon', 'tool_mesh', 'tool_kind',
                   'swing_seconds', 'contact_seconds', 'harvest_reach_cm',
                   'harvest_sweep_radius_cm', 'combat_reach_cm', 'melee_damage']
for wid in sorted(weapons):
    entry = tools.get(wid) or {}
    for f in REQUIRED_FIELDS:
        if f not in entry:
            problems.append('%s: production_tools.json 缺 %s（工作台与浮窗会读到默认值）' % (wid, f))
    if entry.get('category') != 'tool':
        problems.append('%s: category 应为 tool（IsEquippedProductionTool 依据它判定）' % wid)

print('=== PROBLEMS (%d) ===' % len(problems))
for p in problems:
    print('  ! ' + p)
print('=== INFO (%d) ===' % len(infos))
for i in infos:
    print('  - ' + i)
report = ROOT / 'Saved' / 'Production' / 'tool-modification-report.txt'
report.parent.mkdir(parents=True, exist_ok=True)
try:
    source = str(SRC.relative_to(ROOT))
except ValueError:
    source = str(SRC)
with io.open(report, 'w', encoding='utf-8') as f:
    f.write('# %s 生成，由 Tools/Production/check_tool_modification_consistency.py 覆盖写入\n'
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
