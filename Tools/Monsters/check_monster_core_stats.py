# -*- coding: utf-8 -*-
"""怪物防御常量表核查（2026-09-28 六维剔除后）。

复算内容：
 1) MonsterCoreStats.cpp 常量表（Def/Mdef/CritRes/AttrWeight）↔ 历史六维（SPEC 留档，
    原 gamedev enemy-base-stats.js 公式口径）推导值逐位对照；mdef 字段覆盖
    （手脑65/大手30/小手55/巫婆55）按覆盖值断言；
 2) deriveEnemyCombatLevel 复算（AttrWeight + HP 项 + rank 加成，速度项按 0 记录）；
 3) goldDrop/压级倍率边界抽查（等级×4+1..10 → ×.5 → rank 倍率）。
用法: python -X utf8 Tools/Monsters/check_monster_core_stats.py
"""
import io, math, re, sys, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CORE = io.open(os.path.join(ROOT, 'Source/FPSGAME/Monsters/MonsterCoreStats.cpp'), encoding='utf-8').read()

def fills_after(pattern, count=1):
    """取 pattern 之后 700 字符窗口内的 count 个 Fill(...) 参数组（Def,Mdef,CritRes,Weight）。"""
    i = CORE.find(pattern)
    assert i >= 0, pattern
    got = re.findall(r'Fill\((\d+),(\d+),(\d+),([\d.]+)', CORE[i:i + 700])
    assert len(got) >= count, (pattern, got)
    return [(int(a), int(b), int(c), float(w)) for a, b, c, w in got[:count]]

# 历史六维 {力,敏,智,体,精,运}（2026-09-23~27 注册表原值，仅作推导基准留档）；
# mdef_override = 剔除前运行时字段覆盖（狼系字段与公式一致故不标）。
SPEC = {
 'AHandBrainMonster':    dict(a=(50,25,30,40,20,10), level=12, rank='Lord',  hp=1500, mdef_override=65, fills=1),
 'AFleshHandMonster':    dict(a=(55,25,10,45,15,10), level=12, rank='Lord',  hp=1500, mdef_override=30, fills=2, pick=1),  # [1]=大手(else 分支)
 'AFleshHandMinion':     dict(a=(20,30,5,10,10,10),  level=1,  rank='Minor', hp=80,   mdef_override=55, parent='AFleshHandMonster', pick=0),
 'APoisonMaggotMonster': dict(a=(7,13,24,22,24,13),  level=4,  rank='Elite', hp=1500),
 'AInfectedDogMonster':  dict(a=(24,32,4,18,10,6),  level=7,  rank='Normal',hp=220),
 'AWolfMonster':         dict(a=(16,28,3,5,6,8),     level=5,  rank='Normal',hp=220),
 'AFatZombie':           dict(a=(18,6,3,20,3,5),     level=4,  rank='Normal',hp=600),
 'AMutant3':             dict(a=(50,30,5,40,10,6),   level=9,  rank='Elite', hp=2000),
 'AWitchMonster':        dict(a=(20,15,30,33,25,13), level=8,  rank='Lord',  hp=1300, mdef_override=55),
 'ASpitterZombie':       dict(a=(22,38,10,20,6,5),   level=5,  rank='Normal',hp=120),
 'ANurseZombie':         dict(a=(3,27,3,0,0,3),      level=3,  rank='Normal',hp=120),
}
TAGS = {  # 标签回退分支 = 同类常量
 'FatZombie': 'AFatZombie', 'Mutant3': 'AMutant3', 'Witch': 'AWitchMonster',
}
GOLD_RANK = {'Normal': 1, 'Minor': 1, 'Elite': 2, 'Lord': 3, 'Boss': 3}
COMBAT_BONUS = {'Normal': 0, 'Minor': 1, 'Elite': 3, 'Lord': 5, 'Boss': 7}
R = lambda x: math.floor(x + .5)

def derive(a):
    s, d, i, c, w, l = a
    return dict(def_=math.floor(1.5 * c + .3 * s), mdef=math.floor(1.2 * w + .3 * i),
                critres=math.floor(c), weight=s * .08 + d * .08 + c * .10 + i * .08 + w * .08 + l * .04)

problems, rows = [], []
for key, spec in SPEC.items():
    src = spec.get('parent', key)
    got = fills_after('Cast<' + src + '>(Target)', spec.get('fills', 1))
    got = got[spec['pick']] if 'pick' in spec else got[0]
    dv = derive(spec['a'])
    want = (dv['def_'], spec.get('mdef_override', dv['mdef']), dv['critres'], round(dv['weight'], 6))
    if got != want:
        problems.append(f'{key}: 常量表 {got} != 六维推导 {want}')
    raw = 1 + dv['weight'] + min(8.0, max(0.0, math.sqrt(spec['hp'] / 100) * 1.5))
    cl = max(1, R(raw + COMBAT_BONUS[spec['rank']]))
    lo = math.floor((spec['level'] * 4 + 1) * .5) * GOLD_RANK[spec['rank']]
    hi = math.floor((spec['level'] * 4 + 10) * .5) * GOLD_RANK[spec['rank']]
    rows.append((key[1:], spec['level'], spec['rank'], cl, f'{lo}~{hi}',
                 f"def{got[0]} mdef{got[1]} critres{got[2]}", round(got[3], 2)))

for tag, cls in TAGS.items():
    got = fills_after(f'ActorHasTag(TEXT("{tag}"))', 1)[0]
    ref = fills_after('Cast<' + cls + '>(Target)', 1)[0]
    if got != ref:
        problems.append(f'标签 {tag}: {got} != 类分支 {ref}')

def mult(pl, ml, rank):
    diff = pl - ml
    if diff > 5:
        return max({'Normal': .01, 'Elite': .03, 'Lord': .05, 'Boss': .1}[rank], 1 - .15 * (diff - 5))
    if diff < -5:
        return min(1.5, 1 + .1 * (-diff - 5))
    return 1.0
for (pl, ml, rank), want in [((20, 4, 'Normal'), .01), ((12, 4, 'Normal'), 1 - .15 * 3),
                             ((1, 12, 'Lord'), 1.5), ((12, 12, 'Elite'), 1.0), ((99, 3, 'Normal'), .01)]:
    if abs(mult(pl, ml, rank) - want) > 1e-9:
        problems.append(f'倍率抽查 ({pl},{ml},{rank}): {mult(pl, ml, rank)} != {want}')

print(f"{'怪物':22}{'Lv':>3} {'rank':6} {'战斗等级*':>6} {'金币/杀':>8}  常量 def/mdef/critres  权重和")
for r in rows:
    print(f'{r[0]:22}{r[1]:>3} {r[2]:6} {r[3]:>6} {r[4]:>8}  {r[5]:22}{r[6]}')
print('* 战斗等级未含移速项（原版按 px/s，UE 为 cm/s，运行时 CombatLevel() 现算）')
print('* 常量为 MonsterCoreStats::Get 的 k=1 值；渐进感染减益时运行时整体乘系数')
print('* 历史六维仅存于本脚本 SPEC 作推导基准；HP 为类基础值，运行时 ×HealthMultiplier（现=1）')
print('=== PROBLEMS (%d) ===' % len(problems))
for p in problems:
    print(' !', p)
sys.exit(1 if problems else 0)
