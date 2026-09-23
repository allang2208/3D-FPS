# -*- coding: utf-8 -*-
"""怪物六维↔表面属性关联核查（迁移自原 gamedev enemy-base-stats.js 公式口径）。

复算内容：
 1) MonsterCoreStats.cpp 注册表六维 → 原版公式推导 Def/Mdef/CritRes/Atk，断言与
    现行表面值（狼/护士 UPROPERTY、手脑/巫婆显式覆盖、迁移审计表记录）逐位一致；
 2) deriveEnemyCombatLevel 复算（配置等级同表输出）；
 3) goldDrop/压级倍率边界抽查（等级×4+1..10 → ×.5 → rank 倍率）。
用法: python -X utf8 Tools/Monsters/check_monster_core_stats.py
"""
import io, math, re, sys, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CORE = io.open(os.path.join(ROOT, 'Source/FPSGAME/Monsters/MonsterCoreStats.cpp'), encoding='utf-8').read()

def attrs_of(key):
    m = re.search(r'Cast<' + key + r'>\(Target\)\)\{A=\{([0-9,\.]+)\}', CORE)
    assert m, key
    return tuple(float(x) for x in m.group(1).split(','))

R = lambda x: math.floor(x + .5)
def derive(a):
    s, d, i, c, w, l = a
    return dict(atk=R(.5 * s + .5 * d), def_=math.floor(1.5 * c + .3 * s),
                matk=math.floor(.5 * i + .5 * w), mdef=math.floor(1.2 * w + .3 * i),
                crit=math.floor(2 + l), critres=math.floor(c))

# 期望（含迁移审计文档与现行为准）：direct=表面覆盖，不要求等于推导值。
SPEC = {
 'AHandBrainMonster':    dict(a=(50,25,30,40,20,10), level=12, rank='Lord',  hp=1500, atk=(50,'direct'),  mdef=(65,'direct'), def_=(75,'derived'), critres=(40,'derived')),
 'APoisonMaggotMonster': dict(a=(7,13,24,22,24,13),  level=4,  rank='Elite', hp=800,  matk=(24,'direct'), mdef=(36,'derived'), def_=(35,'derived'), critres=(22,'derived')),
 'AWolfMonster':         dict(a=(16,28,3,5,6,8),     level=5,  rank='Normal',hp=220,  atk=(22,'bite'),    mdef=(8,'uprop'),    def_=(12,'uprop'),   critres=(5,'uprop')),
 'AFatZombie':           dict(a=(18,6,3,20,3,5),     level=4,  rank='Normal',hp=600,  atk=(25,'contact'), critres=(20,'derived'),def_=(35,'derived'), mdef=(4,'derived')),
 'AMutant3':             dict(a=(50,30,5,40,10,6),   level=9,  rank='Elite', hp=750,  atk=(40,'contact'), def_=(75,'derived'), critres=(40,'derived'), mdef=(13,'derived')),
 'AWitchMonster':        dict(a=(20,15,30,33,25,13), level=8,  rank='Lord',  hp=1300, matk=(70,'direct'), mdef=(55,'special'), def_=(55,'derived'), critres=(33,'derived')),
 'ANurseZombie':         dict(a=(3,27,3,0,0,3),      level=3,  rank='Normal',hp=120,  atk=(15,'contact'), def_=(0,'derived'),  critres=(0,'derived'), mdef=(0,'derived')),
}
GOLD_RANK = {'Normal': 1, 'Minor': 1, 'Elite': 2, 'Lord': 3, 'Boss': 3}
EXP_RANK = {'Normal': 1, 'Minor': 1, 'Elite': 2, 'Lord': 4, 'Boss': 20}
COMBAT_BONUS = {'Normal': 0, 'Minor': 1, 'Elite': 3, 'Lord': 5, 'Boss': 7}

problems = []
rows = []
for key, spec in SPEC.items():
    reg = attrs_of(key)
    if reg != tuple(float(x) for x in spec['a']):
        problems.append(f'{key}: 注册表六维 {reg} != 预期 {spec["a"]}')
    dv = derive(reg)
    checks = {'atk': 'atk', 'def_': 'def_', 'mdef': 'mdef', 'critres': 'critres'}
    # 表面关联断言：direct/uprop/special/bite/contact 允许不等于推导；derived 必须相等。
    for field in ('def_', 'mdef', 'critres', 'atk', 'matk'):
        if field in spec:
            want, mode = spec[field]
            if mode == 'derived' and dv[field] != want:
                problems.append(f'{key}: 推导 {field}={dv[field]} != 表面 {want}')
    # 战斗等级（原版 deriveEnemyCombatLevel，速度按原版 px 口径未知→以 UE cm/s 记录显示）
    s, d, i, c, w, l = spec['a']
    raw = 1 + s * .08 + d * .08 + c * .10 + i * .08 + w * .08 + l * .04
    raw += min(8.0, max(0.0, math.sqrt(spec['hp'] / 100) * 1.5))
    cl = max(1, R(raw + COMBAT_BONUS[spec['rank']]))  # 速度项按 0 记录（UE cm/s 口径另计）
    lo = math.floor((spec['level'] * 4 + 1) * .5) * GOLD_RANK[spec['rank']]
    hi = math.floor((spec['level'] * 4 + 10) * .5) * GOLD_RANK[spec['rank']]
    rows.append((key[1:], spec['level'], spec['rank'], cl, f'{lo}~{hi}',
                 ' '.join(str(int(x)) for x in spec['a'])))

def mult(pl, ml, rank):
    diff = pl - ml
    if diff > 5:
        return max({'Normal': .01, 'Elite': .03, 'Lord': .05, 'Boss': .1}[rank], 1 - .15 * (diff - 5))
    if diff < -5:
        return min(1.5, 1 + .1 * (-diff - 5))
    return 1.0
# 边界抽查：压级到下限 / 越级封顶 / 区间内恒 1
for (pl, ml, rank), want in [((20, 4, 'Normal'), .01), ((12, 4, 'Normal'), 1 - .15 * 3),
                             ((1, 12, 'Lord'), 1.5), ((12, 12, 'Elite'), 1.0), ((99, 3, 'Normal'), .01)]:
    if abs(mult(pl, ml, rank) - want) > 1e-9:
        problems.append(f'倍率抽查 ({pl},{ml},{rank}): {mult(pl, ml, rank)} != {want}')

print(f"{'怪物':22}{'Lv':>3} {'rank':6} {'战斗等级*':>6} {'金币/杀':>8}  六维 str/dex/int/con/wis/luck")
for r in rows:
    print(f'{r[0]:22}{r[1]:>3} {r[2]:6} {r[3]:>6} {r[4]:>8}  {r[5]}')
print('* 战斗等级未含移速项（原版按 px/s，UE 为 cm/s，运行时 CombatLevel() 现算）')
print('* HP 列为配置表面值；运行时另有全局成长层 HealthMultiplier=2（2026-09-23 全员翻倍，BeginPlay 应用）')
print('=== PROBLEMS (%d) ===' % len(problems))
for p in problems:
    print(' !', p)
sys.exit(1 if problems else 0)
