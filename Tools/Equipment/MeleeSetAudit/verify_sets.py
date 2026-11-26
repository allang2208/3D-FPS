# -*- coding: utf-8 -*-
"""最终验证：重复给付是否清零、工装成长、法师物防/魔防、整体不被打坏。"""
import json, io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

BASE = Path(__file__).resolve().parents[3] / "Content/ColdSteelData"
def load(n):
    with io.open(os.path.join(BASE, n), encoding='utf-8') as f: return json.load(f)

items, src = load('items.json'), load('source-combat-items.json')
print(f'JSON 解析正常：items={len(items)}  source={len(src)}')

def merged(i, b):
    d = dict(b); s = src.get(i)
    if isinstance(s, dict):
        for k, v in s.items():
            if k not in d: d[k] = v
    return d

# 与 SetEffect 真正同键的字段 —— 按套装分别定义，避免跨套误报
SET_DUPKEYS = {
 'ranger_field':    {'crit', 'critDamageBonus'},
 'st6_tactical':    {'reloadSpeed', 'adsPercent', 'sprintStaminaCost'},
 'blue_mage':       {'magicAttackPercent', 'castRangePercent'},
 'steel_chainmail': set(),      # 套装只给 defense%
 'workwear':        set(),      # 套装只给 stamina/speed/survival
}

print('\n' + '='*96)
print('① 重复给付复查（按各套 SetEffect 实际键判定）')
print('='*96)
total = 0
for s in ['workwear','ranger_field','steel_chainmail','st6_tactical','blue_mage']:
    mem = sorted((i, merged(i, v)) for i, v in items.items()
                 if isinstance(v, dict) and merged(i, v).get('armorSet') == s)
    keys = SET_DUPKEYS[s]
    hits = []
    for i, v in mem:
        for k, val in (v.get('bonusStats') or {}).items():
            if k in keys:
                hits.append(f'{i}.{k}={val}')
    total += len(hits)
    status = '✔ 干净' if not hits else '✘ ' + ', '.join(hits)
    print(f'  {s:<18} {status}')
print(f'\n  剩余重复项 = {total}')

CAP = 10
print('\n' + '='*96)
print(f'② 物理防御（护甲强化上限 +{CAP}）')
print('='*96)
for s in ['steel_chainmail','blue_mage','workwear','ranger_field','st6_tactical']:
    mem = sorted((i, merged(i, v)) for i, v in items.items()
                 if isinstance(v, dict) and merged(i, v).get('armorSet') == s)
    tb = tm = 0
    for i, v in mem:
        d = v.get('defense') or {}
        b = float(d.get('base', 0) or 0); pe = float(d.get('perEnhance', 0) or 0)
        tb += b; tm += b + pe*CAP
    print(f'  {s:<18} base合计={tb:>6.1f}   满+{CAP}合计={tm:>7.1f}')

print('\n' + '='*96)
print('③ 法师套明细（物理 + 魔法防御）')
print('='*96)
mem = sorted((i, merged(i, v)) for i, v in items.items()
             if isinstance(v, dict) and merged(i, v).get('armorSet') == 'blue_mage')
print(f"{'ID':<26}{'物base':>8}{'物per':>8}{'物满10':>8}{'魔base':>8}{'魔per':>8}{'魔满10':>8}")
tp = tm = 0
for i, v in mem:
    d = v.get('defense') or {}
    pb = float(d.get('base', 0) or 0); pp = float(d.get('perEnhance', 0) or 0)
    mb = float(d.get('magicBase', 0) or 0); mp = float(d.get('magicPerEnhance', 0) or 0)
    pf, mf = pb + pp*CAP, mb + mp*CAP
    tp += pf; tm += mf
    print(f"{i:<26}{pb:>8.1f}{pp:>8.2f}{pf:>8.1f}{mb:>8.1f}{mp:>8.2f}{mf:>8.1f}")
print(f"{'合计':<26}{'':>8}{'':>8}{tp:>8.1f}{'':>8}{'':>8}{tm:>8.1f}")
print(f'\n  锁子甲满+10物防基准 = 198.0 ；法师套物防 = {tp:.1f}  → {"✔ 对齐" if abs(tp-198)<1 else "✘ 偏差"}')
print(f'  法师套魔防 = {tm:.1f}（设计目标 240）')

print('\n' + '='*96)
print('④ 其他套装未被误改（防御仍为原值）')
print('='*96)
expect = {'ue_steel_armet':(24,2), 'ue_chainmail_shirt':(34,3),
          'ue_ranger_feather_hat':(6,0.6), 'ue_st6_tactical_helmet':(10,1.5)}
for i,(eb,ep) in expect.items():
    d = items[i].get('defense') or {}
    b = float(d.get('base',0) or 0); p = float(d.get('perEnhance',0) or 0)
    ok = abs(b-eb)<1e-9 and abs(p-ep)<1e-9
    print(f'  {i:<26} base={b:<5} per={p:<5} {"✔" if ok else "✘ 期望 %s/%s"%(eb,ep)}')
