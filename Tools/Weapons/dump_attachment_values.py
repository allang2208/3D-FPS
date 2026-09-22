# -*- coding: utf-8 -*-
"""Generate a numeric-tuning reference for all firearm attachment options."""
import json, math, collections

SRC = r'D:\FPS3D\FPSGAME\Content\ColdSteelData\gunsmith.json'
OUT = r'D:\FPS3D\FPSGAME\Docs\Weapons\attachment-values-20260921.md'

d = json.load(open(SRC, encoding='utf-8'))
slots = d['slots']; cats = d['categories']; defaults = d['defaults']
common = d.get('common_options', {})

SHORT = {'ue_m4a1': 'M4A1', 'ue_akm': 'AKM', 'ue_qbz191': 'QBZ-191', 'ue_m1911': 'M1911',
         'ue_dan_wesson715': 'DW715', 'ue_ash12': 'ASH-12', 'ue_m16a2': 'M16A2',
         'ue_a762': 'A762', 'ue_pkm': 'PKM'}
weapons = d['weapons']
wby = {w['id']: w for w in weapons}

# merge common_options the same way UGunsmithSystem::Initialize does
merged = {}
for w in weapons:
    own = w.get('options', {}) or {}
    m = {}
    for s in slots:
        arr = list(own.get(s, []))
        have = {o['id'] for o in arr}
        for o in common.get(s, []):
            if o['id'] not in have:
                arr.append(o)
        if arr:
            m[s] = arr
    merged[w['id']] = m

STAT_KEYS = ['ads_percent', 'ads_seconds', 'recoil_mult', 'shake_mult', 'stability_mult',
             'hip_spread_mult', 'bullet_speed_mult', 'fire_interval_mult', 'range_mult',
             'reload_mult', 'mag_delta', 'mag_mult']

def statstr(o):
    st = o.get('stats') or {}
    if not st:
        return '—'
    ks = [k for k in STAT_KEYS if k in st] + [k for k in st if k not in STAT_KEYS]
    return ' '.join('`%s=%s`' % (k, ('%g' % st[k]) if isinstance(st[k], float) else st[k]) for k in ks)

def adsm(base):
    return math.log(20.0) / base['ads_smooth'] * 1000.0

L = []
A = L.append
A('# 枪械改造件数值总表（调参用）')
A('')
A('生成日期 2026-09-21。数据源 `FPSGAME/Content/ColdSteelData/gunsmith.json`（`version: 1`），')
A('由 `UGunsmithSystem::Initialize` 在启动时读入，并把顶层 `common_options` 合并进**每一把**武器。')
A('所有面板、实战与物品提示都读同一个 `UGunsmithSystem::Calculate`，改 JSON 即同时改三处显示。')
A('')
A('## 1. 结算口径（`UGunsmithSystem::Calculate`）')
A('')
A('```')
A('ADSPercent += ads_percent            （百分比相加，可跨槽位累加）')
A('ADSSeconds += ads_seconds            （绝对秒，与百分比同时叠加）')
A('RecoilMultiplier *= recoil_mult      ShakeMultiplier *= shake_mult')
A('StabilityMultiplier *= stability_mult（基础值 base.stability_mult 也在乘积里）')
A('Capacity += mag_delta')
A('Interval *= fire_interval_mult       Reload *= reload_mult')
A('                                    EmptyReload *= empty_reload_mult（缺省 = reload_mult）')
A('Speed *= bullet_speed_mult           Range *= range_mult      Spread *= hip_spread_mult')
A('')
A('ADS = max(0.001, base.ADS × (1 + Σ ads_percent) + Σ ads_seconds)   [秒]')
A('base.ADS = ln(20) / base.ads_smooth                                [秒]')
A('Handling = FWeaponHandling::FromIndices(Recoil × RecoilMultiplier,')
A('                                          Shake  × ShakeMultiplier, StabilityMultiplier)')
A('最终 Recoil / Shake = Handling.RecoilIndex / Handling.ShakeIndex（各自 clamp 0–400）')
A('```')
A('')
A('- **乘性**：`recoil_mult` / `shake_mult` / `stability_mult` / `hip_spread_mult` / `bullet_speed_mult`')
A('  / `fire_interval_mult` / `range_mult` / `reload_mult` —— 多件相乘。')
A('- **加性**：`ads_percent`（百分比）与 `ads_seconds`（秒）；`mag_delta` 为绝对发数。')
A('  2026-09-21 起目录全部改用 `ads_percent` 表达开镜耗时，已无条目写 `ads_seconds`；')
A('  代码仍保留 `ads_seconds` 解析路径，需要绝对秒时可直接使用。')
A('- 面板显示口径：ADS 行直读 `ads_percent×100`（`-` 为增益/绿色），乘性行取 `最终/原值−1`，')
A('  弹匣容量显示绝对值。`description` 不写数字，数字只出现在详情行；`effects` 必须与 `stats` 同义同数。')
A('- 改一件配件要同步 `stats`、`description`、`effects` 三处；三者冲突时以 `Calculate` 结果为准。')
A('')
A('### 1.1 基础 ADS 与装激光后的 ADS')
A('')
A('| 武器 | `ads_smooth` | 基础 ADS | 装 `laser` 后 ADS（`ads_percent=-0.2` → 基础×0.8） |')
A('| --- | --- | --- | --- |')
for w in weapons:
    b = w['base']; base_ms = adsm(b)
    if 'tactical' in w.get('allowed', []):
        addeff = '%.0f ms' % (base_ms * 0.8)
    else:
        addeff = '（无战术挂件槽）'
    A('| %s | %g | %.0f ms | %s |' % (SHORT[w['id']], b['ads_smooth'], base_ms, addeff))
A('')
A('> 2026-09-21 把 `laser` 从 `ads_seconds=-0.2` 改成比例 `ads_percent=-0.2`：')
A('> 旧写法对 M1911（基础 180 ms）会算到 −20 ms 并被 `.001` 下限截断成 1 ms，等于免费瞬镜；')
A('> 现在各枪统一按基础耗时的 80% 结算，M1911 不再触底。')
A('')
A('### 1.2 腰射锥与准星内缘（准星规则）')
A('')
A('```')
A('GetHipSpread() = 2 × (0.0175 + 连射bloom + 移动 + 腾空) × base.spread_mult × Π hip_spread_mult   [rad/轴]')
A('射击方向 = 相机前向 + 右向量 × U(-1,1)×GetHipSpread() + 上向量 × U(-1,1)×GetHipSpread()')
A('准星内缘 = GetCrosshairHalfExtent()：把当帧锥的左右/上下边界用当前投影矩阵投到 HUD（无夹值）')
A('```')
A('')
A('- 动态项（`FPSGAMECharacter.cpp`）：连射每发 bloom `+0.003`、上限 `0.018`，停火 0.18 s 后按 `0.018/s` 恢复；')
A('  移动 = 速度(m/s) × `0.004`、上限 `0.020`；腾空 `0.025`。ADS 在随机分支前返回瞄具方向，零散布。')
A('- 静止参考锥（系数 1）= `0.0175 rad/轴`，即 10 m 处每轴 35 cm。`base.spread_mult` 与配件 `hip_spread_mult`')
A('  连乘后**同时**放大真实锥角和准星内缘，所以改系数不需要动准星代码。')
A('- 四线样式（长 9、半宽 1.5，按 1080p 缩放）只画在线外缘之外，与扩散无关；')
A('  2026-09-11 已取消旧的固定间隙与 28 单位上限，准星始终等于当帧锥的投影边界。')
A('')
A('| 武器 | 腰射系数 | 静止 | 移动 | 腾空 | 移动+腾空 | 满 bloom+移动+腾空 |')
A('| --- | --- | --- | --- | --- | --- | --- |')
def cone_cm(mult, bloom=0.0, move=0.0, air=0.0):
    return 2 * (0.0175 + bloom + move + air) * mult * 1000.0
for w in weapons:
    s = w['base'].get('spread_mult', 1)
    A('| %s | %g | %.0f cm | %.0f cm | %.0f cm | %.0f cm | %.0f cm |' % (
        SHORT[w['id']], s, cone_cm(s), cone_cm(s, move=0.020), cone_cm(s, air=0.025),
        cone_cm(s, move=0.020, air=0.025), cone_cm(s, bloom=0.018, move=0.020, air=0.025)))
A('')
A('> 单位是「10 m 处每轴最大偏移」。两个轴独立均匀采样，是方形锥不是圆形高斯。')
A('')
A('## 2. 槽位与分类')
A('')
A('| # | slot | 分类 | 默认项 | 共享/独占 |')
A('| --- | --- | --- | --- | --- |')
for i, s in enumerate(slots):
    shared = '共享（`common_options`）' if s in common else '各枪自带'
    A('| %d | `%s` | %s | %s | %s |' % (i, s, cats[i], defaults[i], shared))
A('')

A('## 3. 各枪基础数值与开放槽位')
A('')
A('| 武器 | id | 弹药 | 弹匣 | 射击间隔 | 伤害 | 弹速 | 有效射程 | 换弹/空仓 | 后坐力 | 抖动 | 基础稳定性 | 腰射系数 | 开放槽位 |')
A('| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |')
for w in weapons:
    b = w['base']
    A('| %s | `%s` | `%s` | %g | %g s | %g | %g | %g | %g / %g s | %g | %g | %s | %s | %s |' % (
        w['name'], w['id'], b['ammo_item_id'], b['mag_size'], b['fire_interval'], b['damage'],
        b['bullet_speed'], b['effective_range'], b['reload_time'], b.get('empty_reload_time', b['reload_time']),
        b['recoil'], b['camera_shake'], b.get('stability_mult', 1), b.get('spread_mult', 1),
        ', '.join('`%s`' % s for s in w.get('allowed', [])) or '**无（不可改造）**'))
A('')
A('额外的每枪基础键：M16A2 `burst_count=3`、`burst_delay=0.18`、`hit_stagger=false`；')
A('A762 `stability_mult=1.25`（只有它有基础稳定性倍率）；七把长枪 `spread_mult=2`（腰射系数，见 §1.2）。')
A('')

A('## 4. 全部改造件数值（按槽位）')
A('')
A('同一 ID 的多枪 `stats` 完全一致，合并为一行；`适用枪型` 只列开放该槽位的武器。')
A('')
for s in slots:
    cat = cats[slots.index(s)]
    groups = collections.OrderedDict()
    blocked = set()
    for w in weapons:
        usable = s in w.get('allowed', [])
        for o in merged[w['id']].get(s, []):
            key = (o['id'], o['name'], json.dumps(o.get('stats') or {}, sort_keys=True))
            if usable:
                groups.setdefault(key, [])
                if SHORT[w['id']] not in groups[key]:
                    groups[key].append(SHORT[w['id']])
            else:
                blocked.add(SHORT[w['id']])
    if not groups:
        # slot exists in the catalog but is not open on any weapon
        if blocked:
            A('### 4.%d `%s`（%s）' % (slots.index(s) + 1, s, cat))
            A('')
            A('**没有任何武器开放这个槽位。**目录里为 %s 列了条目，但 `allowed` 里都没有 `%s`，'
              % (', '.join(sorted(blocked)), s))
            A('`UGunsmithSystem::Option()` 先检查 `allowed`，所以游戏里一件都选不了。')
            A('')
        continue
    A('### 4.%d `%s`（%s）' % (slots.index(s) + 1, s, cat))
    A('')
    A('| id | 名称 | **可选**枪型 | 当前 stats |')
    A('| --- | --- | --- | --- |')
    for (oid, name, _), ws in groups.items():
        o = next(o for w in weapons for o in merged[w['id']].get(s, [])
                 if o['id'] == oid and o['name'] == name)
        A('| `%s` | %s | %s | %s |' % (oid, name, ', '.join(ws), statstr(o)))
    A('')
    if blocked:
        A('> %s 的目录里也有 `%s` 条目，但该槽位不在它们的 `allowed` 中，**实际不可选**。'
          % (', '.join(sorted(blocked)), s))
        A('')

A('## 5. ASH-12 专属改造件')
A('')
A('### 5.1 独占 ID（其他枪没有这三个 ID）')
A('')
A('| id | 名称 | 槽位 | 当前 stats | 当前 effects 文本 |')
A('| --- | --- | --- | --- | --- |')
for w in weapons:
    for s in slots:
        for o in merged[w['id']].get(s, []):
            if o['id'].startswith('ash12_'):
                eff = '；'.join(e['text'] for e in o.get('effects', [])) or '—'
                A('| `%s` | %s | `%s` | %s | %s |' % (o['id'], o['name'], s, statstr(o), eff))
A('')
A('### 5.2 ASH-12 的槽位与条目（含复用共享 ID 的 ASH 专用几何）')
A('')
A('| 槽位 | 条目 id | 名称 | stats |')
A('| --- | --- | --- | --- |')
for s in slots:
    if s not in wby['ue_ash12'].get('allowed', []):
        continue
    for o in merged['ue_ash12'].get(s, []):
        A('| `%s` | `%s` | %s | %s |' % (s, o['id'], o['name'], statstr(o)))
A('')
A('- ASH 开放槽位只有 `optic` / `muzzle` / `magazine` / `underbarrel` / `stock` / `tactical`；')
A('  没有后握把、枪管、扳机、装填装置。')
A('- ASH 弹匣只有原厂 + `ext_mag`（**没有 `large_drum`**）。`ext_mag` 是沿 ASH 原厂 12.7 mm')
A('  弧形弹体加长的专用件，数值与共享 `ext_mag` 相同（`mag_delta=10`、`reload_mult=1.25`、`ads_percent=0.05`）。')
A('- ASH 枪口没有共享的 `brake` / `tactical_suppressor` / `titanium_brake`，只有 `false`、`true`（通用消音器）')
A('  以及两个 ASH 专用件。')
A('- `ash12_tactical_suppressor` 在代码里被识别为“已消音”')
A('  （`FPSGAMECharacter.h`：`MuzzleVariant==TEXT("ash12_tactical_suppressor")`），')
A('  `ash12_tactical_brake` **不是**消音件。改这两个 ID 会影响音效/枪口表现分支。')
A('- 其余 ASH 条目（5 个瞄具、5 个前握把、`laser`/`flashlight`、`true`）都复用共享 ID，')
A('  但模型/材质/安装座是 ASH 专属版本；数值与共享条目一致。')
A('')

A('## 6. 调参时必须一起看的三处代码耦合')
A('')
A('这些数值不在 JSON 里，改 JSON 时不要误以为它们会跟着变：')
A('')
A('1. **M4A1 大弹鼓换弹时长**：`Source/FPSGAME/Weapons/M4DrumReloadTiming.h`')
A('   `NormalDurationScale=0.846360229`、`EmptyDurationScale=0.817263946`，')
A('   在 `Calculate` 里对 `ue_m4a1` + `magazine=large_drum` 额外相乘（叠在 `reload_mult=1.75` 之上）。')
A('   面板显示的是 `reload_mult × 该系数`（约 ×1.48 / ×1.43）。')
A('2. **DW715 速装器**：`Source/FPSGAME/Weapons/DanWesson715WeaponAssets.h`')
A('   `EmptyReload=3.85f`；`Calculate` 里装 `dw715_speedloader` 时把普通与空仓换弹**直接改写为 3.85 s**，')
A('   `stats` 为空、不参与倍率。DW715 的基础换弹时间在 `Initialize` 里另从动画片段长度读取。')
A('3. **M1911 基础换弹**：`Initialize` 里从 `M1911WeaponAssets::AnimationPath("reload"/"reload_empty")`')
A('   的 `GetPlayLength()` 覆盖 JSON 的 `reload_time`，改 JSON 的这两个值对 M1911 无效。')
A('')
A('## 7. 数值变更记录与遗留项')
A('')
A('### 7.1 2026-09-21 本轮已调整')
A('')
A('| 条目 | 调整前 | 调整后 |')
A('| --- | --- | --- |')
A('| `ash12_tactical_brake`（ASH 枪口） | `ads_percent=0.1111111111111111`（旧 `1/0.9−1` 写法）`recoil 0.75` `stab 1.15`，无腰射项 | `ads_percent=0.05` `recoil 0.75` `stab 1.25` `hip_spread 0.8` |')
A('| `laser`（8 把枪） | `ads_seconds=-0.2`（绝对秒，M1911 触底 1 ms） | `ads_percent=-0.2`（基础耗时×0.8，全枪型同比例） |')
A('| `ash12_tactical_suppressor`（ASH 枪口） | `ads 0.05` `recoil 0.75` `stab 1.25` `speed 0.8`（与共享战术消音器完全相同） | `ads 0.1` `recoil 0.7` `stab 1.3` `speed 0.8` |')
A('| `ash12_cheek_rest`（ASH 枪托） | `stats: {}`、`effects: []`，纯外观件 | `ads 0.05` `recoil 0.95` `stab 1.15` |')
A('| 空仓换弹倍率（源码） | `Reload *= reload_mult; EmptyReload *= reload_mult;` | 新增目录键 `empty_reload_mult`，缺省 = `reload_mult`；现有条目行为不变 |')
A('')
A('第 1 项（`0.1111` 归一）与第 4 项指向同一件 `ash12_tactical_brake`，按第 4 项给出的完整新值落地，')
A('旧遗留值随之消失；全目录已无其它 `1/x−1` 写法的残留值。')
A('`effects` 与 `stats` 已逐条核对：`py Tools/Weapons/check_attachment_consistency.py` 报告 0 不一致。')
A('')
A('### 7.2 用户决定暂不处理（2026-09-21）')
A('')
A('| 项 | 现状 |')
A('| --- | --- |')
A('| M1911 枪口没有 `titanium_brake` | 只有四项，其余步枪五项。 |')
A('| `Normalize()` 的 `stock: "true" → "compact"` | 遗留映射，目录已无 `compact` 条目，旧存档该值被静默丢弃。 |')
A('| `barrel` 槽「列了但没开」 | 除 DW715 外都不在 `allowed` 里，`short`/`long` 实际不可选。 |')
A('')
A('### 7.3 仍有待处理的口径问题（本轮未动）')
A('')
A('| 项 | 说明 |')
A('| --- | --- |')
A('| `common_options` 枪管文案措辞不同 | `short`/`long` 的 effect 写「ADS瞄准耗时减少/增加20%」，与新口径文案「开镜耗时」不一致；数值本身正确。 |')
A('| `description` 普遍含数字 | 目录中 85 处 `description` 含数字（`1×`、`80米`、`30 发`、型号名等），与「描述不写数值」的规则不符，属既有现状。 |')
A('')
A('### 7.4 编译期审计重新对齐（2026-09-21 续）')
A('')
A('大弹鼓合同在 2026-09-17 由 `SourceAssets/ExtMagUniversal20260917/README.md` 记录的旧 Godot 合同（容量 +20 → 50 发、换弹 ×1.75、开镜速度 ×1.15）')
A('改为 +30 → 60 发、换弹 ×1.75 再乘 `M4DrumReloadTiming`（现目录 `ads_percent=0.1`、`mag_delta=30`），但五个手工验收夹具仍按旧合同断言。本轮把它们对齐到当前目录：')
A('凡是能从目录读出的量都改为按 `Calculate` 推导，只有夹具自身的备弹/溢流算术保留显式规则式，避免下次调参再一起失效。')
A('')
A('| 文件 | 原断言（旧合同） | 现断言（当前目录） |')
A('| --- | --- | --- |')
A('| `UI/GunsmithWorkbenchAudit.cpp` | 容量终值 `50 发`、ADS 终值 `209 ms` 且 `Benefit==1`、工厂对比增量 `+20 发`、关闭工作台后容量 `==50` | 四项全部改为按 `Calculate(Definition, Factory/Draft/Installed)` 推导；ADS 收益方向修正为 `-1`（大弹鼓使开镜变慢） |')
A('| `UI/M4DrumAudit.cpp` | 容量 `50`、ADS `0.24/1.15`、换弹 `2.1/2.7 ×1.75`、溢流 20 发、备弹 107/90/110/160、10.5 s 与 17.1 s 两个「仍在换弹」窗口 | 容量/ADS/换弹改为按目录推导；备弹与溢流改为 `140−(容量−17)`、`140−容量`、`140+溢流` 等规则式；两个窗口改为 `7+Reload−0.4` 与 `13+EmptyReload−0.5` 秒 |')
A('| `DrumGripAudit.cpp` | `MagazineCapacity==50`；17→满消耗 33、空仓消耗 50 | `==60`；消耗 43 / 60 |')
A('| `ForegripAudit.cpp` | AKM 弹鼓 `MagazineCapacity==50` | `==60` |')
A('| `MuzzleMigrationAudit.cpp` | 枪口+弹鼓+全息 `Combo.Capacity==50` | `==60` |')
A('')
A('`ReloadTimingAudit.cpp`（第 90 行起已按 `Calculate` 与运行时对比）与 `SkeletonStockAudit.cpp`（校验 −20% ADS 时尚未装大弹鼓）本就无此问题，未改。')
A('五个夹具都是手动开启的（`IsAudit()` + 存档/命令行开关），本轮只改断言，未编译、未运行。')
A('')
A('### 7.5 腰射扩散翻倍（2026-09-21 续二）')
A('')
A('用户要求：**除手枪外所有枪械腰射扩散翻倍**，准星按规则同步。落地方式是把「腰射散布系数」变成每枪基础键：')
A('')
A('| 项 | 调整前 | 调整后 |')
A('| --- | --- | --- |')
A('| `weapons[].base.spread_mult` | 该键不存在，所有枪静默取 1 | 六把长枪（M4A1 / AKM / QBZ-191 / ASH-12 / M16A2 / A762）= `2`；M1911 与 DW715 不写键，保持参考值 1 |')
A('| `Initialize` 解析（源码） | `Base.Spread` 恒为 1 | 新增 `W.Base.Spread=Num(B,TEXT("spread_mult"),1);` |')
A('| 静止锥（10 m 每轴） | 长枪与手枪同为 35 cm | 长枪 70 cm，手枪仍 35 cm |')
A('| 准星内缘 | 35 cm 的投影 | 自动变为 70 cm 的投影（代码未改，规则见 §1.2） |')
A('')
A('`Calculate` 以 `R=W->Base` 起算，`R.Spread` 再乘各配件 `hip_spread_mult`，所以：')
A('')
A('- 面板「腰射散布系数」行（`M4GunsmithOverview.cpp`）对长枪显示 `2.00×`，手枪仍 `1.00×`；')
A('- 配件详情与物品提示的腰射百分比取 `After/Before−1`，基础系数在分子分母上抵消，**各配件百分比不变**（激光仍是 −20%）；')
A('- 双持手枪走 `PistolDualWieldCombat` 的 `DualPistolSpread::BaseHipSpread`（0.0175）与各自 `Stats.Spread`，两把手枪基础值为 1，因此双持手感不变；')
A('- 后坐力负载 `RecoilLoad` 用的是未乘系数的 `CurrentSpread+MoveSpread+AirSpread`，本次不动，纯散布变化；')
A('- `SkeletonStockAudit.cpp` 的 `S.Spread==1` 改为 `S.Spread==Base.Spread`（原本要验的是"枪托不改变散布"，工厂值不再是 1）；')
A('- `BallisticPresentationAudit.cpp` 在测量前把 `HipSpreadMultiplier` 显式置 1 并按 0.035 建立参考，因此该夹具不受基础系数影响，仍可原样运行。')
A('')
A('**未编译、未运行**；扩倍后的实际观感与准星大小由用户实测。')
A('')
A('## 8. 修改位置')
A('')
A('- 数值：`FPSGAME/Content/ColdSteelData/gunsmith.json`')
A('  - `weapons[].options[<slot>][]`：该枪自带条目；`common_options.barrel[]`：所有枪共享的枪管条目。')
A('  - 同一个 ID 在不同枪里是**多份独立拷贝**：改共享件要逐枪改（或改 `common_options`）。')
A('- 基础数值：`weapons[].base`（`ads_smooth`、`fire_interval`、`damage`、`bullet_speed`、')
A('  `effective_range`、`mag_size`、`recoil`、`camera_shake`、`reload_time`、`empty_reload_time`、')
A('  `stability_mult`、`spread_mult`）。改 `spread_mult` 会同时改真实腰射锥和准星内缘（§1.2）。')
A('- 每改一件配件，同步 `stats`、`description`（不写数字）、`effects`（与 stats 同义同数）。')
A('- 新增可选键：`empty_reload_mult`（只影响空仓换弹，缺省等于 `reload_mult`）；')
A('  `ads_seconds`（绝对秒，与 `ads_percent` 同时叠加）仍受支持但当前目录未使用。')
A('- 核对工具：`py Tools/Weapons/check_attachment_consistency.py`（结构 + effects/stats 数值一致性，')
A('  报告写入 `Tools/Weapons/consistency-report.txt`）。')
A('')
A('## 9. 覆盖统计')
A('')
A('| 武器 | 开放槽位数 | 可选条目（合并后，含默认项） |')
A('| --- | --- | --- |')
for w in weapons:
    n = sum(len(merged[w['id']].get(s, [])) for s in w.get('allowed', []))
    A('| %s | %d | %d |' % (w['name'], len(w.get('allowed', [])), n))
A('')
A('全目录合并后共 226 条（含每枪重复的共享条目）；独占 ID 只有 6 个：')
A('`ash12_cheek_rest`、`ash12_tactical_brake`、`ash12_tactical_suppressor`、')
A('`dw715_lightweight_fast`、`dw715_speedloader`、`m1911_lightweight_fast`。')

open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('wrote', OUT, len(L), 'lines')