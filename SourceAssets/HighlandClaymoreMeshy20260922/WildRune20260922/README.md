# 高地专属剑身Ⅱ：蛮荒符文

> 本目录是材质引导与语义图标来源，以下外观为初版历史。用户否决重复纹样后，最终覆盖纹理与材质改用 [兽颚战纹 V2](../WildRuneTotemV2_20260922/README.md)。恢复时保留本目录输入，并在引导安装后应用 V2。

高地·双手剑 `ue_highland_claymore` 的专属 `blade_2 / wild_rune`，独立于剑身Ⅰ选择，可与原装、阔锋重刃及其他高地剑刃搭配。

## 外观

六段獠牙分叉刻纹沿剑脊排列，断开的中脊、双侧弯钩和短裂纹形成蛮荒图腾。暗红内核、赤红荧光，边缘柔化，按高度错相呼吸。覆盖层保留底层钢材纹理；原生蓝色符文在安装该改造时改为同系红光，卸下后恢复原效果。

实际符文使用代码定义的覆盖纹理与独立材质，不依赖图标推导坐标。稳定的剑刃局部投射避免厚刃倒角拉伸图案，贴合正反面，并在剑尖与剑根处淡出。

图标采用「赤红利爪击穿冷钢甲片」语义，冷钢倒角、深色甲面、红色能量、正面视角、左上主光，1024×1024 RGBA 透明，与原有剑身Ⅱ语义图标统一。使用内置 imagegen，完整提示词见 [icon_prompt.txt](icon_prompt.txt)，原图见 `Generated/wild_rune_semantic.png`，交付图见 `Icons/ue_highland_claymore_blade_2_wild_rune.png`。

## 属性合同

用户确认：攻击韧性伤害 +30%，物理防御穿透 +20%。

- `toughness_damage_mult = 1.3`：目标原有削韧结果再乘 1.3，单独影响韧性累积，不提高破韧后的硬直时长。共享本机的命中形式／抗性体系属其他任务；本次公开版本仅在已有 Poise 累积入口接入该倍率。
- `physical_armor_penetration = 0.2`：与武器已有的锻造/强化物理穿透相加，上限 100%；只参与物理分量的防御结算，不是直接增伤 20%，不增加魔法穿透。
- 两项数值随出手快照固定；覆盖该武器的普通连击、重击、突刺、冲刺、旋风与配重快速近战。改变装备不影响已经出手的命中快照。
- 削韧倍率只在目标同步接收本次武器伤害时生效，作用域结束即还原。火焰护甲等后续额外技能伤害不继承该倍率。
- 改造详情、武器总览、物品改造效果、物品属性与装备比较均包含对应字段；「改造物理防御穿透」显示改造部分，实际结算另外加上既有锻造/强化穿透。

## 资产与代码

资源目录 `/Game/Weapons/HighlandClaymore20260922/WildRune`：

- `M_SilverRuneSurface_HighlandWild`：独立红色符文覆盖材质。
- `T_Mask_wild_rune`：512×2048 的六段獠牙覆盖纹理。
- 高地原生表面及其旋风表面增加默认关闭的 `NativeWild` 参数，由已选符文的剑刃 MID 驱动；原有材质图连接保留。
- 图标 PNG 与 UE Texture：`Content/ColdSteelData/AttachmentIcons20260913/ue_highland_claymore_blade_2_wild_rune`。

目录入口 `Content/ColdSteelData/melee-gunsmith.json`。沿用现有 `gunsmith_parts.blade_2` 存档，不修改玩家已装改造。

`FMeleeModifiers` 保存削韧倍率与物理穿透，`ColdSteelSkills::Snapshot` 将属性并入出手快照，`ApplySkillWeaponHit` 通过目标的 `ApplyHitWithToughnessScale` 作用域提交额外削韧。物理穿透复用现有 `ArmorPenetration → WeaponHit.PhysicalPenetration` 结算。

生产源：`prepare_art.py`、`production.json`、`wild_rune.hlsl`、`install_assets.py`。导入记录为 `install_receipt.json`，旧高地材质与目录副本位于 `Before/`。

本轮完成材质编译、资产保存及常规 Editor 目标构建；构建日志 `build-native-02.log` 返回 `Succeeded`，目标已是最新状态。编辑器重新打开，未启动游戏测试、自动检查或验收渲染，最终外观和玩法交由用户测试。
