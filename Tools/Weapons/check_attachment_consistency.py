# -*- coding: utf-8 -*-
"""改造件目录一致性自检（离线，不启动游戏）。

口径 = skills/ue5-weapon-workflow/references/attachment-standard.md
「配件数值与说明分工」（2026-09-23 复审计径版）。断言：
  0. 结构：slots/allowed 引用、id 去重、必备字段；
  1. stats 键全部在登记口径内；
  2. description 无手写可推导数字（%、增减+数字、时长）；弹匣复制数字必须 =
     base.mag_size（或 +mag_delta）；放大倍率／口径／激光 80 米／型号名按白名单放行；
  3. effects 逐行规范措辞（无 后坐力控制／后坐力减少／枪械稳定性增加／ADS瞄准耗时／
     开镜时间 等旧同义词），数字可由同件 stats 推导，benefit 方向与动词一致，
     「；」只允许连接"不变"声明或规格×子句，换弹/装填行不含任何数字；
  4. 同 (slot, id) 跨枪 stats 与 effects 逐字一致（description 允许枪专属差异）；
  5. 禁用词与「。 」拼接残句清零；
  6. traits：必备；「可改造」槽位清单＝运行时实际槽集（含目录声明的 common_options）；数字回 base
     核对（射速/组速/开镜/容量/射程/弹速）；旧称「下挂」禁用；items.json 静态 物理攻击/容量
     与 base.damage/mag_size 一致。

Usage: python Tools/Weapons/check_attachment_consistency.py
Exits 1 when a PROBLEM is found. INFO 行只作提示。报告写 Saved/Weapons/consistency-report.txt。
"""
import io
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'Content' / 'ColdSteelData' / 'gunsmith.json'

KNOWN_KEYS = {'ads_percent', 'ads_seconds', 'recoil_mult', 'shake_mult', 'stability_mult',
              'hip_spread_mult', 'reload_mult', 'empty_reload_mult', 'fire_interval_mult',
              'range_mult', 'bullet_speed_mult', 'mag_delta'}
FORBIDDEN = ['瞄准耗时', 'ADS瞄准', '开镜时间', '后坐力控制', '后坐力减少', '枪械稳定性增加']
MODEL_TOKENS = ['QBZ-191', 'M1911', 'ASH-12', 'M16A2', 'A762', '715', 'SVD', 'PKM',
                'PSO-1', 'M4', 'M16', '5.56', '7.62', '5.45']
# 静态规格白名单；来源：80 米 = TacticalDeviceComponent.cpp `Range=8000.f`，
# 口径/倍率 = 瞄具与弹药物理规格，非 stats 可推导值。
SPEC_PATTERNS = [r'12\.7×55\s*mm', r'80\s*米',
                 r'[0-9]+(?:\.[0-9]+)?(?:～[0-9]+(?:\.[0-9]+)?)?\s*×',
                 r'[0-9]+(?:\.[0-9]+)?\s*倍']

VERB = {  # 行类: {规范动词: 期望 benefit}（+1 增益 / −1 代价 / 0 中性）
    'ads': {'增加': -1, '减少': 1, '缩短': 1, '不变': 0},
    'recoil': {'降低': 1, '增加': -1},
    'stability': {'提高': 1, '降低': -1},
    'hip': {'减少': 1, '增加': -1},
    'speed': {'降低': -1, '增加': 1},
    'range': {'增加': 1, '减少': -1},
    'interval': {'减少': 1, '增加': -1},
    'shake': {'降低': 1, '增加': -1},
    'cap': {'增加': 1},
    'reload': {'更长': -1, '不变': 0},
}
CLASS_OF_KEY = {'ads_percent': 'ads', 'ads_seconds': 'ads', 'recoil_mult': 'recoil',
                'stability_mult': 'stability', 'hip_spread_mult': 'hip',
                'bullet_speed_mult': 'speed', 'range_mult': 'range',
                'fire_interval_mult': 'interval', 'mag_delta': 'cap',
                'reload_mult': 'reload', 'empty_reload_mult': 'reload', 'shake_mult': 'shake'}

problems, infos = [], []


def strip_specs(text):
    for pat in MODEL_TOKENS:
        text = text.replace(pat, '·')
    for pat in SPEC_PATTERNS:
        text = re.sub(pat, '·', text)
    return text


def pct(v):
    return round(abs(v) * 100)


def derive(st):
    out = defaultdict(set)
    for k, v in st.items():
        cls = CLASS_OF_KEY.get(k)
        if cls is None:
            continue
        if k in ('ads_percent', 'ads_seconds'):
            out[cls].add(pct(v))
        elif k == 'mag_delta':
            out[cls].add(abs(int(v)))
        else:
            out[cls].add(pct(1 - v))
    return out


def classify(text):
    for key, words in [('ads', ('开镜',)), ('cap', ('容量',)), ('interval', ('射击间隔',)),
                       ('recoil', ('后坐力',)), ('stability', ('稳定性',)), ('hip', ('腰射',)),
                       ('speed', ('弹速', '子弹速度')), ('range', ('射程',)), ('shake', ('抖动',)),
                       ('reload', ('装填', '换弹'))]:
        if any(w in text for w in words):
            return key
    return None


def check(where, base, slot, op):
    st = op.get('stats') or {}
    desc = op.get('description', '') or ''
    eff = op.get('effects') or []
    for k in sorted(set(st) - KNOWN_KEYS):
        problems.append('%s: 未登记 stats 键 %s' % (where, k))
    # ---- description ----
    if '%' in desc:
        problems.append('%s: description 含 %%' % where)
    if re.search(r'(增加|减少|提高|降低)\s*[0-9]', desc):
        problems.append('%s: description 手写增减数字' % where)
    residual = strip_specs(desc)
    for m in re.finditer(r'([0-9]+(?:\.[0-9]+)?)\s*发', residual):
        n = int(float(m.group(1)))
        allowed = set()
        if isinstance(base, (int, float)):
            allowed.add(int(base))
            if 'mag_delta' in st:
                allowed.add(int(base) + int(abs(st['mag_delta'])))
        if n not in allowed:
            problems.append('%s: description 发数 %d 无法由 base.mag_size(±mag_delta) 推出：%r'
                            % (where, n, desc))
        residual = residual.replace(m.group(0), '·')
    m = re.search(r'[0-9]+(?:\.[0-9]+)?\s*(?:ms|毫秒|秒)', residual)
    if m:
        problems.append('%s: description 手写时长 %r' % (where, m.group(0)))
    leftover = re.findall(r'[0-9]+(?:\.[0-9]+)?', residual)
    if leftover:
        problems.append('%s: description 残留未白名单数字 %s：%r' % (where, leftover, desc))
    # ---- effects ----
    dv = derive(st)
    covered = set()
    for e in eff:
        t, b = e.get('text', ''), e.get('benefit', 0)
        for c in [x for x in t.split('；') if x]:
            ok_clause = ('不变' in c) or re.search(r'[0-9]+(?:\.[0-9]+)?×', c) \
                or classify(c) is None
            if '；' in t and not ok_clause:
                problems.append('%s: effect「；」合并了增减行：%r' % (where, t))
        cls = classify(t)
        if cls is None:
            if re.search(r'[0-9]+(?:\.[0-9]+)?\s*%|[0-9]+\s*发|[0-9]+(?:\.[0-9]+)?\s*(?:ms|毫秒|秒)', t):
                problems.append('%s: effect 无法归类行含数字：%r' % (where, t))
            continue
        covered.add(cls)
        if cls == 'reload' and re.search(r'[0-9]', t):
            problems.append('%s: 换弹/装填行含数字（应定性）：%r' % (where, t))
        vm = [v for v in VERB.get(cls, {}) if v in t]
        if '不变' in t:
            if b != 0:
                problems.append('%s: 「不变」行 benefit 应为 0：%r' % (where, t))
        elif not vm:
            if re.search(r'[0-9]+(?:\.[0-9]+)?\s*%', t):
                problems.append('%s: effect 无规范动词却带百分比：%r' % (where, t))
        else:
            exp = {VERB[cls][v] for v in vm}
            if b not in exp:
                problems.append('%s: benefit=%s 与动词 %s 期望 %s 不符：%r' % (where, b, vm, sorted(exp), t))
        for m in re.finditer(r'([0-9]+(?:\.[0-9]+)?)\s*%', t):
            if int(float(m.group(1))) not in dv.get(cls, set()):
                problems.append('%s: effect 数字 %s%% 不可由 stats 推导：%r vs %s'
                                % (where, m.group(1), t, json.dumps(st, ensure_ascii=False)))
        for m in re.finditer(r'增加([0-9]+)发', t):
            if int(m.group(1)) not in dv.get('cap', set()):
                problems.append('%s: effect 发数与 mag_delta 不符：%r' % (where, t))
    for k in st:
        need = CLASS_OF_KEY.get(k)
        if need and need not in covered:
            problems.append('%s: stats 键 %s 无对应 effect 行' % (where, k))


d = json.load(io.open(SRC, encoding='utf-8'))
raw = io.open(SRC, encoding='utf-8').read()
slots = d['slots']

# 0) 结构 + 5) 全局禁用词
for kw in FORBIDDEN:
    if kw in raw:
        problems.append('禁用词残留 %r' % kw)
if re.search(r'。 [^"\n]', raw):
    problems.append('存在「。 」拼接残句')
for w in d['weapons']:
    for s, arr in (w.get('options', {}) or {}).items():
        if s not in slots:
            problems.append('%s: slot %s 不在 slots 列表' % (w['id'], s))
        ids = [o['id'] for o in arr]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            problems.append('%s/%s: 重复 id %s' % (w['id'], s, dup))
        if s not in w.get('allowed', []):
            problems.append('%s: slot %s 有 options 但未 allowed' % (w['id'], s))
        for o in arr:
            for req in ('id', 'name', 'description', 'effects', 'stats'):
                if req not in o:
                    problems.append('%s/%s/%s: 缺字段 %s' % (w['id'], s, o.get('id'), req))

# 1-3) 逐件 + 4) 跨枪
shared = defaultdict(set)
for w in d['weapons']:
    mag_size = (w.get('base') or {}).get('mag_size')
    for s, arr in (w.get('options', {}) or {}).items():
        for o in arr:
            check('%s %s/%s' % (w['id'], s, o.get('id')), mag_size, s, o)
            shared[(s, o['id'])].add((json.dumps(o.get('stats'), sort_keys=True, ensure_ascii=False),
                                      json.dumps(o.get('effects'), ensure_ascii=False)))
for s, arr in (d.get('common_options') or {}).items():
    for o in arr:
        check('common_options %s/%s' % (s, o.get('id')), None, s, o)
for (slot, oid), variants in sorted(shared.items()):
    if len(variants) > 1:
        problems.append('跨枪不一致 %s/%s（%d 个版本）' % (slot, oid, len(variants)))

# 6) traits 断言：槽位清单 = 运行时实际槽集（options∪allowed∪common_options）、
#    旧称「下挂」禁用（UI 类别为「前握把」）、数字回 base 核对；items 静态 stats 与 base 一致。
LABEL2SLOT = {'瞄具': 'optic', '枪口': 'muzzle', '弹匣': 'magazine', '枪管': 'barrel',
              '后握把': 'reargrip', '枪托': 'stock', '扳机': 'trigger', '战术挂件': 'tactical',
              '前握把': 'underbarrel', '装填装置': 'reload_device', '脚架': 'bipod'}
import math


def check_traits(w):
    base = w.get('base') or {}
    tr = w.get('traits') or []
    if not tr:
        problems.append('%s: 缺 traits（浮窗没有「特殊性质」）' % w['id'])
        return
    runtime = set(w.get('options') or {}) | set(w.get('allowed') or []) | set(d.get('common_options') or {})
    slot_lines = [t for t in tr if '可改造' in t['text']]
    if not slot_lines:
        problems.append('%s: traits 缺槽位清单行' % w['id'])
    for t in slot_lines:
        if '下挂' in t['text']:
            problems.append('%s: traits 用旧称「下挂」（UI 类别是「前握把」）' % w['id'])
        got = {key for name, key in LABEL2SLOT.items() if name in t['text']}
        if got != runtime:
            problems.append('%s: traits 槽位清单 %s ≠ 实际 %s'
                            % (w['id'], sorted(got), sorted(runtime)))
    ads = round(math.log(20) / base['ads_smooth'] * 1000) if base.get('ads_smooth') else None
    for t in tr:
        txt = t['text']
        checks = [(r'射击间隔 (\d+) ms', base.get('fire_interval'), 1000.),
                  (r'组内间隔 (\d+) ms', base.get('fire_interval'), 1000.),
                  (r'组间隔 (\d+) ms', base.get('burst_delay'), 1000.),
                  (r'开镜耗时 (\d+) ms', ads, 1),
                  (r'(\d+)\s*发[^\d，。；]{0,3}弹[匣巢箱]', base.get('mag_size'), 1),
                  (r'有效射程 (\d+) 米', base.get('effective_range'), 1),
                  (r'弹速 (\d+) m/s', base.get('bullet_speed'), 1)]
        for pat, want, scale in checks:
            m = re.search(pat, txt)
            if m and want is not None and int(m.group(1)) != round(want * scale):
                problems.append('%s: traits %r 数字 %s ≠ 目录 %g'
                                % (w['id'], txt[:24], m.group(1), round(want * scale)))


for w in d['weapons']:
    check_traits(w)

ITEMS = SRC.parent / 'items.json'
if ITEMS.exists():
    its = json.load(io.open(ITEMS, encoding='utf-8'))
    for w in d['weapons']:
        entry = its.get(w['id'])
        if not entry:
            problems.append('%s: items.json 缺条目（浮窗没有名字/描述来源）' % w['id'])
            continue
        base = w.get('base') or {}
        for row in entry.get('stats') or []:
            if row.get('name') == '物理攻击' and base.get('damage') is not None:
                if float(row['value']) != round(base['damage'], 4):
                    problems.append('%s: items 物理攻击 %s ≠ base.damage %g'
                                    % (w['id'], row['value'], base['damage']))
            if row.get('name') in ('弹匣容量', '弹巢容量') and base.get('mag_size') is not None:
                if int(float(row['value'])) != int(base['mag_size']):
                    problems.append('%s: items %s %s ≠ base.mag_size %d'
                                    % (w['id'], row['name'], row['value'], base['mag_size']))

print('=== PROBLEMS (%d) ===' % len(problems))
for p in problems:
    print('  ! ' + p)
print('=== INFO (%d) ===' % len(infos))
for i in infos:
    print('  - ' + i)
report = ROOT / 'Saved' / 'Weapons' / 'consistency-report.txt'
report.parent.mkdir(parents=True, exist_ok=True)
with io.open(report, 'w', encoding='utf-8') as f:
    f.write('# %s 生成，由 Tools/Weapons/check_attachment_consistency.py 覆盖写入\n'
            % datetime.now().strftime('%Y-%m-%d %H:%M'))
    f.write('=== PROBLEMS (%d) ===\n' % len(problems))
    for p in problems:
        f.write('  ! %s\n' % p)
print(report)
sys.exit(1 if problems else 0)
