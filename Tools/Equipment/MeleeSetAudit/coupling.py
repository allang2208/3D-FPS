# -*- coding: utf-8 -*-
"""耦合方案对比：新增绝对值字段 vs 复用已有 mdefPercent 乘区。"""
import json, io, os, sys, math
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

BASE = Path(__file__).resolve().parents[3] / "Content/ColdSteelData"
def load(n):
    with io.open(os.path.join(BASE, n), encoding='utf-8') as f: return json.load(f)
items, src = load('items.json'), load('source-combat-items.json')

def M(i, b):
    d = dict(b); s = src.get(i)
    if isinstance(s, dict):
        for k, v in s.items():
            if k not in d: d[k] = v
    return d

# 玩家裸装 mdef（CoreCombatFormula::Player: wis*1.2 + int*0.3）
print('=== 玩家裸装 mdef（精神×1.2 + 智力×0.3）===')
for label, A in [('新手 10', 10), ('中档 30', 30), ('C档 60', 60)]:
    print(f'  {label:<10} mdef = {A*1.2 + A*0.3:.0f}')

CAP = 10
print('\n' + '='*92)
print('方案对比：让法师套满 +10 时总魔防达到某目标')
print('='*92)

TARGETS = [150, 200, 240]
for A in [10, 30, 60]:
    bare = A*1.2 + A*0.3
    print(f'\n裸装 {A} (mdef={bare:.0f})：')
    print(f"{'目标总mdef':>10}{'需装备绝对':>11}{'需装备%':>10}{'减伤(绝对)':>12}")
    for T in TARGETS:
        # 绝对方案：装备直接给 (T - bare)
        need_abs = T - bare
        # 百分比方案：mdefPercent 作用于裸装 → bare*(1+p) = T
        need_pct = (T/bare - 1)*100 if bare > 0 else 0
        red = 100*(1 - 60/(T+60))
        print(f'{T:>10}{need_abs:>11.0f}{need_pct:>9.0f}%{red:>11.1f}%')

print('\n' + '='*92)
print('关键差异：百分比方案的实际 mdef 随裸装属性漂移')
print('='*92)
PCT = 167.0   # 若按 C 档 90 → 240 反推
print(f'假设 mdefPercent = +{PCT:.0f}%（装备侧合计）：')
print(f"{'裸装':>8}{'实际mdef':>10}{'减伤':>9}{'偏离目标240':>13}")
for A in [10, 30, 60, 90, 120]:
    bare = A*1.2 + A*0.3
    got = bare*(1+PCT/100)
    print(f'{bare:>8.0f}{got:>10.0f}{100*(1-60/(got+60)):>8.1f}%{got-240:>+13.0f}')

print('\n' + '='*92)
print('绝对方案：不随属性漂移')
print('='*92)
ABS_TOTAL = 150.0
print(f'假设装备合计给 {ABS_TOTAL:.0f} 点静态魔防：')
print(f"{'裸装':>8}{'实际mdef':>10}{'减伤':>9}")
for A in [10, 30, 60, 90, 120]:
    bare = A*1.2 + A*0.3
    got = bare + ABS_TOTAL
    print(f'{bare:>8.0f}{got:>10.0f}{100*(1-60/(got+60)):>8.1f}%')
