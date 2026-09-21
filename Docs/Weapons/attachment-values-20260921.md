# 枪械改造件数值总表（调参用）

生成日期 2026-09-21。数据源 `FPSGAME/Content/ColdSteelData/gunsmith.json`（`version: 1`），
由 `UGunsmithSystem::Initialize` 在启动时读入，并把顶层 `common_options` 合并进**每一把**武器。
所有面板、实战与物品提示都读同一个 `UGunsmithSystem::Calculate`，改 JSON 即同时改三处显示。

## 1. 结算口径（`UGunsmithSystem::Calculate`）

```
ADSPercent += ads_percent            （百分比相加，可跨槽位累加）
ADSSeconds += ads_seconds            （绝对秒，与百分比同时叠加）
RecoilMultiplier *= recoil_mult      ShakeMultiplier *= shake_mult
StabilityMultiplier *= stability_mult（基础值 base.stability_mult 也在乘积里）
Capacity += mag_delta
Interval *= fire_interval_mult       Reload *= reload_mult
                                    EmptyReload *= empty_reload_mult（缺省 = reload_mult）
Speed *= bullet_speed_mult           Range *= range_mult      Spread *= hip_spread_mult

ADS = max(0.001, base.ADS × (1 + Σ ads_percent) + Σ ads_seconds)   [秒]
base.ADS = ln(20) / base.ads_smooth                                [秒]
Handling = FWeaponHandling::FromIndices(Recoil × RecoilMultiplier,
                                          Shake  × ShakeMultiplier, StabilityMultiplier)
最终 Recoil / Shake = Handling.RecoilIndex / Handling.ShakeIndex（各自 clamp 0–400）
```

- **乘性**：`recoil_mult` / `shake_mult` / `stability_mult` / `hip_spread_mult` / `bullet_speed_mult`
  / `fire_interval_mult` / `range_mult` / `reload_mult` —— 多件相乘。
- **加性**：`ads_percent`（百分比）与 `ads_seconds`（秒）；`mag_delta` 为绝对发数。
  2026-09-21 起目录全部改用 `ads_percent` 表达开镜耗时，已无条目写 `ads_seconds`；
  代码仍保留 `ads_seconds` 解析路径，需要绝对秒时可直接使用。
- 面板显示口径：ADS 行直读 `ads_percent×100`（`-` 为增益/绿色），乘性行取 `最终/原值−1`，
  弹匣容量显示绝对值。`description` 不写数字，数字只出现在详情行；`effects` 必须与 `stats` 同义同数。
- 改一件配件要同步 `stats`、`description`、`effects` 三处；三者冲突时以 `Calculate` 结果为准。

### 1.1 基础 ADS 与装激光后的 ADS

| 武器 | `ads_smooth` | 基础 ADS | 装 `laser` 后 ADS（`ads_percent=-0.2` → 基础×0.8） |
| --- | --- | --- | --- |
| M4A1 | 12.4822 | 240 ms | 192 ms |
| AKM | 9.98577 | 300 ms | 240 ms |
| QBZ-191 | 12.4822 | 240 ms | 192 ms |
| M1911 | 16.643 | 180 ms | 144 ms |
| DW715 | 13.617 | 220 ms | 176 ms |
| ASH-12 | 14 | 214 ms | 171 ms |
| M16A2 | 10.699 | 280 ms | 224 ms |
| A762 | 9.98577 | 300 ms | 240 ms |
| PKM | 6.65718 | 450 ms | （无战术挂件槽） |

> 2026-09-21 把 `laser` 从 `ads_seconds=-0.2` 改成比例 `ads_percent=-0.2`：
> 旧写法对 M1911（基础 180 ms）会算到 −20 ms 并被 `.001` 下限截断成 1 ms，等于免费瞬镜；
> 现在各枪统一按基础耗时的 80% 结算，M1911 不再触底。

### 1.2 腰射锥与准星内缘（准星规则）

```
GetHipSpread() = 2 × (0.0175 + 连射bloom + 移动 + 腾空) × base.spread_mult × Π hip_spread_mult   [rad/轴]
射击方向 = 相机前向 + 右向量 × U(-1,1)×GetHipSpread() + 上向量 × U(-1,1)×GetHipSpread()
准星内缘 = GetCrosshairHalfExtent()：把当帧锥的左右/上下边界用当前投影矩阵投到 HUD（无夹值）
```

- 动态项（`FPSGAMECharacter.cpp`）：连射每发 bloom `+0.003`、上限 `0.018`，停火 0.18 s 后按 `0.018/s` 恢复；
  移动 = 速度(m/s) × `0.004`、上限 `0.020`；腾空 `0.025`。ADS 在随机分支前返回瞄具方向，零散布。
- 静止参考锥（系数 1）= `0.0175 rad/轴`，即 10 m 处每轴 35 cm。`base.spread_mult` 与配件 `hip_spread_mult`
  连乘后**同时**放大真实锥角和准星内缘，所以改系数不需要动准星代码。
- 四线样式（长 9、半宽 1.5，按 1080p 缩放）只画在线外缘之外，与扩散无关；
  2026-09-11 已取消旧的固定间隙与 28 单位上限，准星始终等于当帧锥的投影边界。

| 武器 | 腰射系数 | 静止 | 移动 | 腾空 | 移动+腾空 | 满 bloom+移动+腾空 |
| --- | --- | --- | --- | --- | --- | --- |
| M4A1 | 2 | 70 cm | 150 cm | 170 cm | 250 cm | 322 cm |
| AKM | 2 | 70 cm | 150 cm | 170 cm | 250 cm | 322 cm |
| QBZ-191 | 2 | 70 cm | 150 cm | 170 cm | 250 cm | 322 cm |
| M1911 | 1 | 35 cm | 75 cm | 85 cm | 125 cm | 161 cm |
| DW715 | 1 | 35 cm | 75 cm | 85 cm | 125 cm | 161 cm |
| ASH-12 | 2 | 70 cm | 150 cm | 170 cm | 250 cm | 322 cm |
| M16A2 | 2 | 70 cm | 150 cm | 170 cm | 250 cm | 322 cm |
| A762 | 2 | 70 cm | 150 cm | 170 cm | 250 cm | 322 cm |
| PKM | 2 | 70 cm | 150 cm | 170 cm | 250 cm | 322 cm |

> 单位是「10 m 处每轴最大偏移」。两个轴独立均匀采样，是方形锥不是圆形高斯。

## 2. 槽位与分类

| # | slot | 分类 | 默认项 | 共享/独占 |
| --- | --- | --- | --- | --- |
| 0 | `optic` | 瞄具 | 原厂瞄具 | 各枪自带 |
| 1 | `muzzle` | 枪口 | 标准枪口 | 各枪自带 |
| 2 | `magazine` | 弹匣 | 标准弹匣 | 各枪自带 |
| 3 | `barrel` | 枪管 | 标准枪管 | 共享（`common_options`） |
| 4 | `reargrip` | 后握把 | 原厂后握把 | 各枪自带 |
| 5 | `stock` | 枪托 | 原厂枪托 | 各枪自带 |
| 6 | `trigger` | 扳机 | 标准扳机 | 各枪自带 |
| 7 | `tactical` | 战术挂件 | 无战术挂件 | 各枪自带 |
| 8 | `underbarrel` | 前握把 | 无前握把 | 各枪自带 |
| 9 | `reload_device` | 装填装置 | 逐发装填 | 各枪自带 |

## 3. 各枪基础数值与开放槽位

| 武器 | id | 弹药 | 弹匣 | 射击间隔 | 伤害 | 弹速 | 有效射程 | 换弹/空仓 | 后坐力 | 抖动 | 基础稳定性 | 腰射系数 | 开放槽位 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M4A1 | `ue_m4a1` | `ammo_556` | 30 | 0.08 s | 30 | 350 | 70 | 2.1 / 2.7 s | 100 | 100 | 1 | 2 | `optic`, `magazine`, `muzzle`, `underbarrel`, `stock`, `reargrip`, `tactical` |
| AKM | `ue_akm` | `ammo_762` | 30 | 0.1 s | 35 | 350 | 100 | 3.33333 / 4.29167 s | 100 | 100 | 1 | 2 | `optic`, `magazine`, `muzzle`, `underbarrel`, `stock`, `reargrip`, `tactical` |
| QBZ-191 | `ue_qbz191` | `ammo_58` | 30 | 0.09 s | 32 | 350 | 85 | 2.1 / 2.73333 s | 100 | 100 | 1 | 2 | `optic`, `magazine`, `muzzle`, `underbarrel`, `stock`, `reargrip`, `tactical` |
| M1911 | `ue_m1911` | `ammo_45acp` | 7 | 0.18 s | 36 | 253 | 50 | 1.75 / 2.25 s | 110 | 95 | 1 | 1 | `optic`, `muzzle`, `trigger`, `tactical` |
| Dan-Wesson 715 | `ue_dan_wesson715` | `ammo_357` | 6 | 0.32 s | 68 | 420 | 65 | 6.8 / 8.8 s | 155 | 125 | 1 | 1 | `trigger`, `barrel`, `reload_device`, `optic`, `tactical` |
| ASH-12 | `ue_ash12` | `ammo_127` | 20 | 0.13 s | 48 | 300 | 80 | 2.4 / 3.3 s | 145 | 135 | 1 | 2 | `optic`, `magazine`, `muzzle`, `underbarrel`, `stock`, `tactical` |
| M16A2 | `ue_m16a2` | `ammo_556` | 30 | 0.08 s | 34 | 350 | 110 | 2.35 / 2.95 s | 90 | 85 | 1 | 2 | `optic`, `magazine`, `muzzle`, `underbarrel`, `stock`, `reargrip`, `tactical` |
| A762 | `ue_a762` | `ammo_762` | 30 | 0.0666667 s | 33.25 | 350 | 100 | 3.33333 / 4.29167 s | 75 | 100 | 1.25 | 2 | `optic`, `magazine`, `muzzle`, `underbarrel`, `stock`, `reargrip`, `tactical` |
| PKM | `ue_pkm` | `ammo_762x54r` | 100 | 0.1 s | 45 | 90 | 150 | 5.8 / 6.8 s | 130 | 120 | 1 | 2 | **无（不可改造）** |

额外的每枪基础键：M16A2 `burst_count=3`、`burst_delay=0.18`、`hit_stagger=false`；
A762 `stability_mult=1.25`（只有它有基础稳定性倍率）；七把长枪 `spread_mult=2`（腰射系数，见 §1.2）。

## 4. 全部改造件数值（按槽位）

同一 ID 的多枪 `stats` 完全一致，合并为一行；`适用枪型` 只列开放该槽位的武器。

### 4.1 `optic`（瞄具）

| id | 名称 | **可选**枪型 | 当前 stats |
| --- | --- | --- | --- |
| `false` | 原厂机械瞄具 | M4A1, AKM, QBZ-191, M1911, DW715, ASH-12, A762 | — |
| `holographic` | 全息瞄准镜 | M4A1, AKM, QBZ-191, M1911, DW715, ASH-12, M16A2, A762 | — |
| `panoramic_red_dot` | 全景薄框红点瞄具 | M4A1, AKM, QBZ-191, M1911, DW715, ASH-12, M16A2, A762 | — |
| `prism_scope_2x` | 紧凑型二倍棱镜瞄具 | M4A1, AKM, QBZ-191, ASH-12, M16A2, A762 | `ads_percent=0.05` |
| `lpvo_1_6x` | 1–6× 低倍可变瞄准镜 | M4A1, AKM, QBZ-191, ASH-12, M16A2, A762 | `ads_percent=0.1` |
| `false` | 提把机械瞄具 | M16A2 | — |

### 4.2 `muzzle`（枪口）

| id | 名称 | **可选**枪型 | 当前 stats |
| --- | --- | --- | --- |
| `false` | 原厂枪口 | M4A1, AKM, QBZ-191, M1911, ASH-12, A762 | — |
| `true` | 消音器 | M4A1, AKM, QBZ-191, M1911, ASH-12, M16A2, A762 | `recoil_mult=0.9` `stability_mult=1.1` `bullet_speed_mult=0.85` |
| `tactical_suppressor` | 战术消音器 | M4A1, AKM, QBZ-191, M1911, M16A2, A762 | `ads_percent=0.05` `recoil_mult=0.75` `stability_mult=1.25` `bullet_speed_mult=0.8` |
| `brake` | 枪口制退器 | M4A1, AKM, QBZ-191, M1911, M16A2, A762 | `ads_percent=0.1` `recoil_mult=0.85` `stability_mult=1.15` |
| `titanium_brake` | 钛金制退器 | M4A1, AKM, QBZ-191, M16A2, A762 | `ads_percent=0.15` `recoil_mult=0.7` `stability_mult=1.2` |
| `ash12_tactical_suppressor` | ASH 战术消音器 | ASH-12 | `ads_percent=0.1` `recoil_mult=0.7` `stability_mult=1.3` `bullet_speed_mult=0.8` |
| `ash12_tactical_brake` | ASH战术制退器 | ASH-12 | `ads_percent=0.05` `recoil_mult=0.75` `stability_mult=1.25` `hip_spread_mult=0.8` |
| `false` | 原厂消焰器 | M16A2 | — |

### 4.3 `magazine`（弹匣）

| id | 名称 | **可选**枪型 | 当前 stats |
| --- | --- | --- | --- |
| `false` | 原厂弹匣 | M4A1, AKM, QBZ-191, ASH-12, A762 | — |
| `large_drum` | 大弹鼓 | M4A1, AKM, QBZ-191, M16A2, A762 | `ads_percent=0.1` `reload_mult=1.75` `mag_delta=30` |
| `ext_mag` | 扩容弹匣 | M4A1, AKM, QBZ-191, ASH-12, M16A2, A762 | `ads_percent=0.05` `reload_mult=1.25` `mag_delta=10` |
| `false` | 30 发原厂弹匣 | M16A2 | — |

### 4.4 `barrel`（枪管）

| id | 名称 | **可选**枪型 | 当前 stats |
| --- | --- | --- | --- |
| `false` | 标准枪管 | DW715 | — |
| `short` | 轻型短枪管 | DW715 | `ads_percent=-0.2` `recoil_mult=1.15` `stability_mult=0.85` `hip_spread_mult=0.5` `range_mult=0.8` |
| `long` | 重型长枪管 | DW715 | `ads_percent=0.2` `recoil_mult=0.85` `stability_mult=1.15` `hip_spread_mult=1.5` `range_mult=1.25` |

> A762, AKM, ASH-12, M16A2, M1911, M4A1, PKM, QBZ-191 的目录里也有 `barrel` 条目，但该槽位不在它们的 `allowed` 中，**实际不可选**。

### 4.5 `reargrip`（后握把）

| id | 名称 | **可选**枪型 | 当前 stats |
| --- | --- | --- | --- |
| `false` | 原厂后握把 | M4A1, AKM, QBZ-191, M16A2, A762 | — |
| `phantom_reargrip` | 幻影后握把 | M4A1, AKM, QBZ-191, M16A2, A762 | `ads_percent=0.15` `recoil_mult=0.9` `hip_spread_mult=1.1` |
| `stable_antislip_reargrip` | 稳固防滑后握 | M4A1, AKM, QBZ-191, M16A2, A762 | `ads_percent=0.1` `recoil_mult=0.8` `stability_mult=1.15` |
| `balanced_reargrip` | 均衡后握把 | M4A1, AKM, QBZ-191, M16A2, A762 | `recoil_mult=0.9` `stability_mult=1.1` |

### 4.6 `stock`（枪托）

| id | 名称 | **可选**枪型 | 当前 stats |
| --- | --- | --- | --- |
| `false` | 原厂枪托 | M4A1, AKM, QBZ-191, A762 | — |
| `skeleton` | 骨架枪托 | M4A1, AKM, QBZ-191, M16A2, A762 | `ads_percent=-0.2` `recoil_mult=1.15` `stability_mult=1.1` |
| `core_stock` | 镂空轻型枪托 | M4A1, AKM, QBZ-191, M16A2, A762 | `recoil_mult=0.9` `stability_mult=1.05` |
| `qr_performance` | 高性能后托 | M4A1, AKM, QBZ-191, M16A2, A762 | `recoil_mult=0.8` `stability_mult=1.15` `hip_spread_mult=0.7` |
| `tactical_telescopic` | 战术伸缩枪托 | M4A1, AKM, QBZ-191, M16A2, A762 | `ads_percent=-0.05` `recoil_mult=0.85` `stability_mult=1.15` `hip_spread_mult=1.25` |
| `false` | 原厂后托 | ASH-12 | — |
| `ash12_cheek_rest` | ASH-12 贴合式托腮板 | ASH-12 | `ads_percent=0.05` `recoil_mult=0.95` `stability_mult=1.15` |
| `false` | 原厂固定枪托 | M16A2 | — |

### 4.7 `trigger`（扳机）

| id | 名称 | **可选**枪型 | 当前 stats |
| --- | --- | --- | --- |
| `false` | 标准扳机 | M1911 | — |
| `m1911_lightweight_fast` | 轻型快速扳机 | M1911 | `fire_interval_mult=0.75` |
| `false` | 原厂双动扳机 | DW715 | — |
| `dw715_lightweight_fast` | 轻型快速扳机 | DW715 | `fire_interval_mult=0.8` |

### 4.8 `tactical`（战术挂件）

| id | 名称 | **可选**枪型 | 当前 stats |
| --- | --- | --- | --- |
| `false` | 无战术挂件 | M4A1, AKM, QBZ-191, M1911, DW715, ASH-12, M16A2, A762 | — |
| `laser` | 红色激光镭射 | M4A1, AKM, QBZ-191, M1911, DW715, ASH-12, M16A2, A762 | `ads_percent=-0.2` `hip_spread_mult=0.5` |
| `flashlight` | 战术手电筒 | M4A1, AKM, QBZ-191, M1911, DW715, ASH-12, M16A2, A762 | — |

### 4.9 `underbarrel`（前握把）

| id | 名称 | **可选**枪型 | 当前 stats |
| --- | --- | --- | --- |
| `false` | 无前握把 | M4A1, AKM, QBZ-191, ASH-12, A762 | — |
| `canted_foregrip` | 45°侧倾握把 | M4A1, AKM, QBZ-191, ASH-12, M16A2, A762 | `recoil_mult=0.85` `stability_mult=0.85` `hip_spread_mult=0.8` |
| `tactical_vertical_foregrip` | 战术垂直握把 | M4A1, AKM, QBZ-191, ASH-12, M16A2, A762 | `ads_percent=-0.25` |
| `vertical_foregrip` | 垂直握把 | M4A1, AKM, QBZ-191, ASH-12, M16A2, A762 | `ads_percent=0.05` `recoil_mult=0.9` `stability_mult=1.1` |
| `prism_handstop` | 棱镜阻手器 | M4A1, AKM, QBZ-191, ASH-12, M16A2, A762 | `ads_percent=-0.1` `recoil_mult=0.95` `stability_mult=1.25` `hip_spread_mult=0.95` |
| `angled_foregrip` | 共振二代前握把 | M4A1, AKM, QBZ-191, ASH-12, M16A2, A762 | `ads_percent=0.1` `recoil_mult=0.85` `stability_mult=1.15` |
| `false` | 原厂护木 | M16A2 | — |

### 4.10 `reload_device`（装填装置）

| id | 名称 | **可选**枪型 | 当前 stats |
| --- | --- | --- | --- |
| `false` | 逐发装填 | DW715 | — |
| `dw715_speedloader` | 六发速装器 | DW715 | — |

## 5. ASH-12 专属改造件

### 5.1 独占 ID（其他枪没有这三个 ID）

| id | 名称 | 槽位 | 当前 stats | 当前 effects 文本 |
| --- | --- | --- | --- | --- |
| `ash12_tactical_suppressor` | ASH 战术消音器 | `muzzle` | `ads_percent=0.1` `recoil_mult=0.7` `stability_mult=1.3` `bullet_speed_mult=0.8` | 后坐力降低30%；枪械稳定性提高30%；子弹速度降低20%；开镜耗时增加10% |
| `ash12_tactical_brake` | ASH战术制退器 | `muzzle` | `ads_percent=0.05` `recoil_mult=0.75` `stability_mult=1.25` `hip_spread_mult=0.8` | 开镜耗时增加5%；后坐力降低25%；枪械稳定性提高25%；腰射随机散布减少20% |
| `ash12_cheek_rest` | ASH-12 贴合式托腮板 | `stock` | `ads_percent=0.05` `recoil_mult=0.95` `stability_mult=1.15` | 开镜耗时增加5%；后坐力降低5%；枪械稳定性提高15% |

### 5.2 ASH-12 的槽位与条目（含复用共享 ID 的 ASH 专用几何）

| 槽位 | 条目 id | 名称 | stats |
| --- | --- | --- | --- |
| `optic` | `false` | 原厂机械瞄具 | — |
| `optic` | `holographic` | 全息瞄准镜 | — |
| `optic` | `panoramic_red_dot` | 全景薄框红点瞄具 | — |
| `optic` | `prism_scope_2x` | 紧凑型二倍棱镜瞄具 | `ads_percent=0.05` |
| `optic` | `lpvo_1_6x` | 1–6× 低倍可变瞄准镜 | `ads_percent=0.1` |
| `muzzle` | `false` | 原厂枪口 | — |
| `muzzle` | `true` | 消音器 | `recoil_mult=0.9` `stability_mult=1.1` `bullet_speed_mult=0.85` |
| `muzzle` | `ash12_tactical_suppressor` | ASH 战术消音器 | `ads_percent=0.1` `recoil_mult=0.7` `stability_mult=1.3` `bullet_speed_mult=0.8` |
| `muzzle` | `ash12_tactical_brake` | ASH战术制退器 | `ads_percent=0.05` `recoil_mult=0.75` `stability_mult=1.25` `hip_spread_mult=0.8` |
| `magazine` | `false` | 原厂弹匣 | — |
| `magazine` | `ext_mag` | 扩容弹匣 | `ads_percent=0.05` `reload_mult=1.25` `mag_delta=10` |
| `stock` | `false` | 原厂后托 | — |
| `stock` | `ash12_cheek_rest` | ASH-12 贴合式托腮板 | `ads_percent=0.05` `recoil_mult=0.95` `stability_mult=1.15` |
| `tactical` | `false` | 无战术挂件 | — |
| `tactical` | `laser` | 红色激光镭射 | `ads_percent=-0.2` `hip_spread_mult=0.5` |
| `tactical` | `flashlight` | 战术手电筒 | — |
| `underbarrel` | `false` | 无前握把 | — |
| `underbarrel` | `canted_foregrip` | 45°侧倾握把 | `recoil_mult=0.85` `stability_mult=0.85` `hip_spread_mult=0.8` |
| `underbarrel` | `tactical_vertical_foregrip` | 战术垂直握把 | `ads_percent=-0.25` |
| `underbarrel` | `vertical_foregrip` | 垂直握把 | `ads_percent=0.05` `recoil_mult=0.9` `stability_mult=1.1` |
| `underbarrel` | `prism_handstop` | 棱镜阻手器 | `ads_percent=-0.1` `recoil_mult=0.95` `stability_mult=1.25` `hip_spread_mult=0.95` |
| `underbarrel` | `angled_foregrip` | 共振二代前握把 | `ads_percent=0.1` `recoil_mult=0.85` `stability_mult=1.15` |

- ASH 开放槽位只有 `optic` / `muzzle` / `magazine` / `underbarrel` / `stock` / `tactical`；
  没有后握把、枪管、扳机、装填装置。
- ASH 弹匣只有原厂 + `ext_mag`（**没有 `large_drum`**）。`ext_mag` 是沿 ASH 原厂 12.7 mm
  弧形弹体加长的专用件，数值与共享 `ext_mag` 相同（`mag_delta=10`、`reload_mult=1.25`、`ads_percent=0.05`）。
- ASH 枪口没有共享的 `brake` / `tactical_suppressor` / `titanium_brake`，只有 `false`、`true`（通用消音器）
  以及两个 ASH 专用件。
- `ash12_tactical_suppressor` 在代码里被识别为“已消音”
  （`FPSGAMECharacter.h`：`MuzzleVariant==TEXT("ash12_tactical_suppressor")`），
  `ash12_tactical_brake` **不是**消音件。改这两个 ID 会影响音效/枪口表现分支。
- 其余 ASH 条目（5 个瞄具、5 个前握把、`laser`/`flashlight`、`true`）都复用共享 ID，
  但模型/材质/安装座是 ASH 专属版本；数值与共享条目一致。

## 6. 调参时必须一起看的三处代码耦合

这些数值不在 JSON 里，改 JSON 时不要误以为它们会跟着变：

1. **M4A1 大弹鼓换弹时长**：`Source/FPSGAME/Weapons/M4DrumReloadTiming.h`
   `NormalDurationScale=0.846360229`、`EmptyDurationScale=0.817263946`，
   在 `Calculate` 里对 `ue_m4a1` + `magazine=large_drum` 额外相乘（叠在 `reload_mult=1.75` 之上）。
   面板显示的是 `reload_mult × 该系数`（约 ×1.48 / ×1.43）。
2. **DW715 速装器**：`Source/FPSGAME/Weapons/DanWesson715WeaponAssets.h`
   `EmptyReload=3.85f`；`Calculate` 里装 `dw715_speedloader` 时把普通与空仓换弹**直接改写为 3.85 s**，
   `stats` 为空、不参与倍率。DW715 的基础换弹时间在 `Initialize` 里另从动画片段长度读取。
3. **M1911 基础换弹**：`Initialize` 里从 `M1911WeaponAssets::AnimationPath("reload"/"reload_empty")`
   的 `GetPlayLength()` 覆盖 JSON 的 `reload_time`，改 JSON 的这两个值对 M1911 无效。

## 7. 数值变更记录与遗留项

### 7.1 2026-09-21 本轮已调整

| 条目 | 调整前 | 调整后 |
| --- | --- | --- |
| `ash12_tactical_brake`（ASH 枪口） | `ads_percent=0.1111111111111111`（旧 `1/0.9−1` 写法）`recoil 0.75` `stab 1.15`，无腰射项 | `ads_percent=0.05` `recoil 0.75` `stab 1.25` `hip_spread 0.8` |
| `laser`（8 把枪） | `ads_seconds=-0.2`（绝对秒，M1911 触底 1 ms） | `ads_percent=-0.2`（基础耗时×0.8，全枪型同比例） |
| `ash12_tactical_suppressor`（ASH 枪口） | `ads 0.05` `recoil 0.75` `stab 1.25` `speed 0.8`（与共享战术消音器完全相同） | `ads 0.1` `recoil 0.7` `stab 1.3` `speed 0.8` |
| `ash12_cheek_rest`（ASH 枪托） | `stats: {}`、`effects: []`，纯外观件 | `ads 0.05` `recoil 0.95` `stab 1.15` |
| 空仓换弹倍率（源码） | `Reload *= reload_mult; EmptyReload *= reload_mult;` | 新增目录键 `empty_reload_mult`，缺省 = `reload_mult`；现有条目行为不变 |

第 1 项（`0.1111` 归一）与第 4 项指向同一件 `ash12_tactical_brake`，按第 4 项给出的完整新值落地，
旧遗留值随之消失；全目录已无其它 `1/x−1` 写法的残留值。
`effects` 与 `stats` 已逐条核对：`py Tools/Weapons/check_attachment_consistency.py` 报告 0 不一致。

### 7.2 用户决定暂不处理（2026-09-21）

| 项 | 现状 |
| --- | --- |
| PKM 没有任何改造件 | `allowed: []`、`options: {}`；`Option()` 先检查 `allowed`，游戏里一件都选不了。 |
| M1911 枪口没有 `titanium_brake` | 只有四项，其余步枪五项。 |
| `Normalize()` 的 `stock: "true" → "compact"` | 遗留映射，目录已无 `compact` 条目，旧存档该值被静默丢弃。 |
| `barrel` 槽「列了但没开」 | 除 DW715 外都不在 `allowed` 里，`short`/`long` 实际不可选。 |

### 7.3 仍有待处理的口径问题（本轮未动）

| 项 | 说明 |
| --- | --- |
| `common_options` 枪管文案措辞不同 | `short`/`long` 的 effect 写「ADS瞄准耗时减少/增加20%」，与新口径文案「开镜耗时」不一致；数值本身正确。 |
| `description` 普遍含数字 | 目录中 85 处 `description` 含数字（`1×`、`80米`、`30 发`、型号名等），与「描述不写数值」的规则不符，属既有现状。 |

### 7.4 编译期审计重新对齐（2026-09-21 续）

大弹鼓合同在 2026-09-17 由 `SourceAssets/ExtMagUniversal20260917/README.md` 记录的旧 Godot 合同（容量 +20 → 50 发、换弹 ×1.75、开镜速度 ×1.15）
改为 +30 → 60 发、换弹 ×1.75 再乘 `M4DrumReloadTiming`（现目录 `ads_percent=0.1`、`mag_delta=30`），但五个手工验收夹具仍按旧合同断言。本轮把它们对齐到当前目录：
凡是能从目录读出的量都改为按 `Calculate` 推导，只有夹具自身的备弹/溢流算术保留显式规则式，避免下次调参再一起失效。

| 文件 | 原断言（旧合同） | 现断言（当前目录） |
| --- | --- | --- |
| `UI/GunsmithWorkbenchAudit.cpp` | 容量终值 `50 发`、ADS 终值 `209 ms` 且 `Benefit==1`、工厂对比增量 `+20 发`、关闭工作台后容量 `==50` | 四项全部改为按 `Calculate(Definition, Factory/Draft/Installed)` 推导；ADS 收益方向修正为 `-1`（大弹鼓使开镜变慢） |
| `UI/M4DrumAudit.cpp` | 容量 `50`、ADS `0.24/1.15`、换弹 `2.1/2.7 ×1.75`、溢流 20 发、备弹 107/90/110/160、10.5 s 与 17.1 s 两个「仍在换弹」窗口 | 容量/ADS/换弹改为按目录推导；备弹与溢流改为 `140−(容量−17)`、`140−容量`、`140+溢流` 等规则式；两个窗口改为 `7+Reload−0.4` 与 `13+EmptyReload−0.5` 秒 |
| `DrumGripAudit.cpp` | `MagazineCapacity==50`；17→满消耗 33、空仓消耗 50 | `==60`；消耗 43 / 60 |
| `ForegripAudit.cpp` | AKM 弹鼓 `MagazineCapacity==50` | `==60` |
| `MuzzleMigrationAudit.cpp` | 枪口+弹鼓+全息 `Combo.Capacity==50` | `==60` |

`ReloadTimingAudit.cpp`（第 90 行起已按 `Calculate` 与运行时对比）与 `SkeletonStockAudit.cpp`（校验 −20% ADS 时尚未装大弹鼓）本就无此问题，未改。
五个夹具都是手动开启的（`IsAudit()` + 存档/命令行开关），本轮只改断言，未编译、未运行。

### 7.5 腰射扩散翻倍（2026-09-21 续二）

用户要求：**除手枪外所有枪械腰射扩散翻倍**，准星按规则同步。落地方式是把「腰射散布系数」变成每枪基础键：

| 项 | 调整前 | 调整后 |
| --- | --- | --- |
| `weapons[].base.spread_mult` | 该键不存在，所有枪静默取 1 | 七把长枪（M4A1 / AKM / QBZ-191 / ASH-12 / M16A2 / A762 / PKM）= `2`；M1911 与 DW715 不写键，保持参考值 1 |
| `Initialize` 解析（源码） | `Base.Spread` 恒为 1 | 新增 `W.Base.Spread=Num(B,TEXT("spread_mult"),1);` |
| 静止锥（10 m 每轴） | 长枪与手枪同为 35 cm | 长枪 70 cm，手枪仍 35 cm |
| 准星内缘 | 35 cm 的投影 | 自动变为 70 cm 的投影（代码未改，规则见 §1.2） |

`Calculate` 以 `R=W->Base` 起算，`R.Spread` 再乘各配件 `hip_spread_mult`，所以：

- 面板「腰射散布系数」行（`M4GunsmithOverview.cpp`）对长枪显示 `2.00×`，手枪仍 `1.00×`；
- 配件详情与物品提示的腰射百分比取 `After/Before−1`，基础系数在分子分母上抵消，**各配件百分比不变**（激光仍是 −20%）；
- 双持手枪走 `PistolDualWieldCombat` 的 `DualPistolSpread::BaseHipSpread`（0.0175）与各自 `Stats.Spread`，两把手枪基础值为 1，因此双持手感不变；
- 后坐力负载 `RecoilLoad` 用的是未乘系数的 `CurrentSpread+MoveSpread+AirSpread`，本次不动，纯散布变化；
- `SkeletonStockAudit.cpp` 的 `S.Spread==1` 改为 `S.Spread==Base.Spread`（原本要验的是"枪托不改变散布"，工厂值不再是 1）；
- `BallisticPresentationAudit.cpp` 在测量前把 `HipSpreadMultiplier` 显式置 1 并按 0.035 建立参考，因此该夹具不受基础系数影响，仍可原样运行。

**未编译、未运行**；扩倍后的实际观感与准星大小由用户实测。

## 8. 修改位置

- 数值：`FPSGAME/Content/ColdSteelData/gunsmith.json`
  - `weapons[].options[<slot>][]`：该枪自带条目；`common_options.barrel[]`：所有枪共享的枪管条目。
  - 同一个 ID 在不同枪里是**多份独立拷贝**：改共享件要逐枪改（或改 `common_options`）。
- 基础数值：`weapons[].base`（`ads_smooth`、`fire_interval`、`damage`、`bullet_speed`、
  `effective_range`、`mag_size`、`recoil`、`camera_shake`、`reload_time`、`empty_reload_time`、
  `stability_mult`、`spread_mult`）。改 `spread_mult` 会同时改真实腰射锥和准星内缘（§1.2）。
- 每改一件配件，同步 `stats`、`description`（不写数字）、`effects`（与 stats 同义同数）。
- 新增可选键：`empty_reload_mult`（只影响空仓换弹，缺省等于 `reload_mult`）；
  `ads_seconds`（绝对秒，与 `ads_percent` 同时叠加）仍受支持但当前目录未使用。
- 核对工具：`py Tools/Weapons/check_attachment_consistency.py`（结构 + effects/stats 数值一致性，
  报告写入 `Tools/Weapons/consistency-report.txt`）。

## 9. 覆盖统计

| 武器 | 开放槽位数 | 可选条目（合并后，含默认项） |
| --- | --- | --- |
| M4A1 | 7 | 31 |
| AKM | 7 | 31 |
| QBZ-191 | 7 | 31 |
| M1911 | 4 | 12 |
| Dan-Wesson 715 | 5 | 13 |
| ASH-12 | 6 | 22 |
| M16A2 | 7 | 31 |
| A762 | 7 | 31 |
| PKM | 0 | 0 |

全目录合并后共 226 条（含每枪重复的共享条目）；独占 ID 只有 6 个：
`ash12_cheek_rest`、`ash12_tactical_brake`、`ash12_tactical_suppressor`、
`dw715_lightweight_fast`、`dw715_speedloader`、`m1911_lightweight_fast`。
