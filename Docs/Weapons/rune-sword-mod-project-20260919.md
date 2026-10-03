# 苍蓝星辉·双手符文剑：专属改造项目设计

状态：设计方案（未制作、未接入，待确认后进入制作）。参考已验收的寒晶双手剑改造项目（[发布记录](frost-sword-modular-publication-20260919.md)、[模块化作者源](../../SourceAssets/FrostSwordModules20260915/README.md)）。

## 背景与目标

2026-09-19 符文剑模块化完成后，改造栏五个栏目中的十二款改造项全部借用寒晶方案（同一选项 ID、同一数值、同一外形），符文剑只有原装件体现自身身份。本方案为符文长剑设计**完全专属**的十五款改造件：五个部件各三款，每款有独立机械特色，并与寒晶的款式在机制、数值曲线和视觉语言上错开。

- 物品与存档沿用 `ue_rune_sword` 与 `gunsmith_parts`，接口沿用 `azure_hilt_v1`（刃根/护手切口 Z=12.5、护手/握把 Z=−4、握把/配重锤 Z=−19.5，单位 cm，剑尖 +Z）。
- 全部改造效果只使用 [MeleeGunsmith.cpp](../../Source/FPSGAME/Weapons/MeleeGunsmith.cpp) 已解析的 stats 字段（含 `combo_second/third_damage_mult`、`heavy_damage_mult/add`、`knockback_mult`、`rune_*`、`parry_window_mult`、`riposte_*`、`magic_*`），**不新增 C++、不改求值器、不加存档字段**。
- 剑身Ⅰ三款为纯数值项，沿用原装刃外形并在界面注明（与既有约定一致）；剑身Ⅱ为刃面符文覆盖层（仅覆盖独立剑刃）；护手、握把、配重锤各三款独立实体模块，从 `SM_RuneSword_<槽>_factory` 复制安装端制作外侧造型。

## 栏目分工（与寒晶错开的机制族）

| 栏 | 寒晶已占用 | 符文剑专属方向 |
| --- | --- | --- |
| 剑身Ⅰ | 范围+伤 / 伤+硬直 / 速度+耐力 | 后两段终结、范围+击退、重击倍率 |
| 剑身Ⅱ | 冷却、智精追加、增伤+易伤 | 曲线全部重排并各有代价，符文色由银白改苍蓝 |
| 护手 | 格挡+弹反窗 / 6s 弹反激励 / 轻量 | 纯防御（缩弹反窗）、宽弹反+8s 低激励、施法导流 |
| 握把 | 耐力+速度 / 速度+连段 / 加长+距离伤 | 附魔法值续航、两段专速、加长改走"重压伤"曲线 |
| 配重锤 | 重击+击退 / 冷却+耗减 / 增伤+耗增 | 更重的终结砧、苍蓝晶核高振幅、提速轻尾（重击受损） |

## 一、剑身Ⅰ（三款，沿用原装外形）

1. **贯星刃** `star_pierce` — 后段终结刃。延展第三段收束路径，突刺与柄尾砸击共用同一强化窗口。
   - 第三段突刺与第四段柄尾砸击伤害 +20%（`combo_third_damage_mult: 1.2`，第四段沿用第三段倍率为既有规则）
   - 攻击范围 +5%（`range_mult: 1.05`）；攻击速度 −5%（`attack_speed_mult: 0.95`）
2. **裂空锋** `sky_rend` — 距离压制刃。宽弧开面，以节奏和消耗换空间控制。
   - 攻击范围 +20%（`range_mult: 1.2`）；攻击造成击退 +15%（`knockback_mult: 1.15`）
   - 攻击速度 −10%（`attack_speed_mult: 0.9`）；耐力消耗 +8%（`stamina_mult: 1.08`）
3. **蓄芒刃** `charge_edge` — 蓄力增幅刃。刃面聚能沟槽放大释放瞬间的倍率。
   - 重击伤害倍率 ×1.15（`heavy_damage_mult: 1.15`，面板倍率 2.50 → 2.88；与配重锤加值项先乘后加叠加）
   - 攻击速度 −8%（`attack_speed_mult: 0.92`）；格挡减伤 −10%（`block_reduction_mult: 0.9`）

## 二、剑身Ⅱ（三款苍蓝符文覆盖层）

新增材质 `M_AzureRuneSurface`（沿用银白符文的组件空间投影/仅剑体槽机制，发色改苍蓝星辉），三张纹样按 `MeleeRuneMods20260915` 的 image_gen → 提取笔画 → 周期动效管线制作：星点蚀痕闪烁、符环呼吸、星尘纵向流动。

1. **灼星符文** `star_mark` — 追加伤害转化。每次近战命中追加魔法伤害：智力×15% + 精神×5%（`rune_intelligence: 0.15`、`rune_wisdom: 0.05`）；魔法值消耗 +10%（`magic_cost_mult: 1.1`）。追加口径沿用侵蚀符文规则（不随动作倍率二次放大、与本体共用一次暴击与受击结算）。
2. **星环符引** `star_ring` — 施法续航。魔法技能冷却 −20%（`magic_cooldown_mult: 0.8`）；作为代价，单次魔法伤害 −8%（`magic_damage_mult: 0.92`）。
3. **星冕回路** `star_crown` — 易伤增幅。命中施加魔法易伤 +15%·持续 6 秒，重复命中刷新（`rune_vulnerability: 0.15`、`rune_vulnerability_seconds: 6`）；魔法伤害 +10%（`magic_damage_mult: 1.1`）；耐力消耗 +8%（`stamina_mult: 1.08`）。

## 三、护手（三款独立模块，保留中央剑座与宝石安装座）

1. **坚壁符盾护手** `bulwark_guard` — 纯防御翼面。
   - 格挡减伤 +45%（`block_reduction_mult: 1.45`）；弹反判定时间 −10%（`parry_window_mult: 0.9`，与寒晶"格挡+弹反双修"错位）
   - 攻击速度 −7%（`attack_speed_mult: 0.93`）；耐力消耗 +6%（`stamina_mult: 1.06`）
2. **镜辉反制护手** `mirror_guard` — 弹反窗口与长效激励。双叉上挑护翼抛光如镜。
   - 弹反判定时间 +15%（`parry_window_mult: 1.15`）
   - 成功弹反获得「镜辉激励」：期间攻击速度 +10%、耐力消耗 −10%、持续 8 秒，再次弹反刷新（`riposte_attack_speed_mult: 1.1`、`riposte_stamina_mult: 0.9`、`riposte_seconds: 8`；寒晶为 6 秒 +20%/−20%，本作取"更长更温和"曲线）
3. **符能导流护手** `flow_guard` — 攻防一体的施法护手，翼面镂刻导流回路与小颗苍蓝宝石。
   - 魔法伤害 +12%（`magic_damage_mult: 1.12`）；魔法值消耗 −8%（`magic_cost_mult: 0.92`）
   - 格挡减伤 −15%（`block_reduction_mult: 0.85`）

## 四、握把（三款独立模块，两端接口与双手握点合同不变）

1. **静心缠柄** `meditation_wrap` — 苍蓝细缠绳，偏攻耐与法力续航。
   - 耐力消耗 −15%（`stamina_mult: 0.85`）；魔法值消耗 −10%（`magic_cost_mult: 0.9`，握把槽首次承载法力词条，与寒晶握把机制零重叠）
2. **逐星快柄** `astral_swift` — 镂空轻柄，突出第二段横斩的抢攻节奏。
   - 攻击速度 +12%（`attack_speed_mult: 1.12`）；第二段横斩伤害 +15%（`combo_second_damage_mult: 1.15`）
   - 格挡减伤 −12%（`block_reduction_mult: 0.88`）
3. **崩岳长柄** `sunder_long` — 外扩双手位。外形直接沿用已验收的长柄几何（+2.8 cm），因此**复用现有 `pommel_offset_cm: [0,0,-2.8]` 与左手动画家族** `FrostCrystalSword20260915/Grips20260919/LongGripAnimations`，不再重做动作。
   - 伤害 +6%（`damage_mult: 1.06`）；攻击范围 +8%（`range_mult: 1.08`）
   - 攻击速度 −4%（`attack_speed_mult: 0.96`）；耐力消耗 +5%（`stamina_mult: 1.05`；寒晶长柄是"速度无损"曲线，本款用轻微降速换更高单次伤）

## 五、配重锤（三款独立模块，保留原装柄尾接口）

1. **陨星锤首** `starfall_ballast` — 粗粝陨铁砧形，终结重压。
   - 重击伤害倍率 +0.20（`heavy_damage_add: 0.2`，口径同硬化配重：单独累加的加值项，面板倍率 2.50 → 2.70）
   - 攻击造成击退 +20%（`knockback_mult: 1.2`，基础击退 20 cm → 24 cm）
   - 攻击速度 −12%（`attack_speed_mult: 0.88`）；耐力消耗 +12%（`stamina_mult: 1.12`）
2. **凝碧星核** `azure_core` — 银色三爪支架包覆苍蓝半透明晶核（独立零金属度半透明材质，先例见魔力球配重）。
   - 魔法伤害 +15%（`magic_damage_mult: 1.15`）；魔法值消耗 +20%（`magic_cost_mult: 1.2`）
3. **疾星配重** `swift_ballast` — 短尾流线配重，挥速优先。
   - 攻击速度 +12%（`attack_speed_mult: 1.12`）；重击伤害倍率 ×0.9（`heavy_damage_mult: 0.9`，柄端更轻、释放更软：面板倍率 2.50 → 2.25）

## 数据与迁移合同

- 寒晶现有全部改造项（含五栏十二款与三个共用剑身项）在 `melee-gunsmith.json` 中补 `"weapons": ["ue_frost_crystal_sword"]` 过滤，行为不变；符文剑十五款新项标 `"weapons": ["ue_rune_sword"]`。栏目 `description` 与卡面文案按新方案改写。
- 符文剑旧存档中已保存的借用选项 ID（`bastion_guard` 等）经 `Normalize` 静默回落为原装显示，无需迁移、不报错；寒晶侧存档不受影响。
- 新 ID 与既有 ID 全部不冲突；`rune-sword-modules.json` 按槽登记十五款中的九件实体模型路径与安装位置，剑身Ⅰ沿用 `factory` 的 `trace_base_cm/trace_tip_cm/rune_dimensions_cm`，剑身Ⅱ符文仍仅覆盖剑体槽。
- 攻击端点、命中采样、第四段走廊与单目标合同不变；`trace_from_animation` 保持。

## 制作流水线（确认方案后执行）

1. `RuneSwordModules20260919/author_variants.py` 扩展：从 `SM_RuneSword_<槽>_factory` 复制安装端制作九件新变体（三款护手改外侧护翼，保留中央剑座；崩岳长柄复用既有长柄几何；苍蓝缠绳/水晶槽用独立材质），保存可编辑 Blend、`Export/*.fbx`、`interfaces.json` 与真实部件 RGBA 菜单图标。
2. `import_variants.py` 编辑器内导入 → 更新 `rune-sword-modules.json`；`merge_workbench.py` 合并 `melee-gunsmith.json`（保留寒晶条目与改造 ID 语义）。
3. 剑身Ⅱ：三张 image_gen 纹样 → `azure_runes.hlsl` 笔画提取与周期动效 → `M_AzureRuneSurface` 材质导入，登记打包引用。
4. 退役九件借用造型（`SM_RuneSword_*_{bastion_guard,riposte_guard,light_guard,shock_wrap,swift_grip,long_twohand,ballast_hardened,ballast_rune,ballast_magic_orb}`）：目录摘除引用，文件按惯例归档 `trash/`，不删除，可回退。
5. 纯数据 + 资产接入，预计无需原生编译；如工作台文案触及 UI 源脚本，按既有规则走编辑器内 Live Coding。

## 数值口径（沿用寒晶已验收合同）

- 耐力倍率覆盖攻击（含重击）与防御受击；奔跑、闪避、弹反规则不变。
- 击退距离与硬直时间独立；一次挥击只推退一次。
- 重击加值项单独累加，乘算项作用于动作倍率而非面板伤害。
- 攻速走 `RuneSwordRhythm` 原时钟与 0.2–4 倍动作速率限制；蓄力门槛、突刺位移与 100 cm 跨步不随改造变化。
- 符文追加伤害与易伤结算口径与侵蚀/导魔符文完全一致，仅曲线不同。
- 组合示例（自洽性检查）：贯星刃 + 陨星锤首 + 崩岳长柄时，第四段伤害 ≈ 面板 × 1.06 × 1.2 × 1.2 ×（第三段倍率），攻速总乘 0.87 —— 高代价高终结，符合"重压流"定位；导流护手 + 凝碧星核 + 灼星符文 + 星环符引构成法武双修流，冷却 −20%、耗 −18%、魔伤 +27% 净值。

## 验收要点（交由用户实机）

- 九件新模块切换、安装缝与材质过渡；崩岳长柄左手腕位与柄尾联动；苍蓝符文仅覆盖剑体且随动作投影贴合；十五张真实模型图标；右侧实值/差值与组合计算；旧存档回落为原装显示。
