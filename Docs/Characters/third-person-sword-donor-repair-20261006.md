# 第三人称上挑、下劈：改用全身素材及修正刃向

用户否定上一版 `SwordActions20261006` 的自编上挑和冲刺竖劈，并指出下劈用剑身拍击。本轮以实际全身动画替换动作主体，适配目标骨架、双手共握和剑刃朝向。

## 动作来源与适配

使用 [Quaternius Universal Animation Library 2 Standard](https://quaternius.itch.io/universal-animation-library-2) 官方免费包里的 `Sword_Heavy_Combo`。原包和 CC0 1.0 许可位于 `SourceAssets/ThirdPersonSwordCandidates20261006`；实际 FBX、导入资产、重定向姿态与制作源位于 `SourceAssets/ThirdPersonSwordDonorRepair20261006`。没有使用付费 Source 包，也没有把第一人称攻击手臂用作全身动画。

这段素材原本是单手剑动作，并非可直接套用的原生双手剑动作：保留它的躯干、腿部、主手轨迹及肘部弯曲方向，重新适配 Jason 骨长与双手握点。通用重定向会改变主手举剑高度，因此手臂使用原素材的肩腕相对向量及手掌解剖坐标适配；副手跟随当前剑柄，双手共同进行可达范围修正。

| 动作 | 实际原素材片段 | 接入角色键 |
|---|---|---|
| 上挑 | Heavy Combo 0.96–1.17 秒；剑刃向前上方切出在 1.10–1.15 秒 | `Melee.FullBody.Uppercut` |
| 普通下劈 | Heavy Combo 最后一次过顶下劈及收势，2.23–4.30 秒 | `Melee.FullBody.Overhead` |
| 冲刺下劈 | 同一次过顶下劈，缩短举顶入口，2.40–4.30 秒 | `Melee.FullBody.DashOverhead` |

上挑并非倒放下劈，也不再以手腕上升时间代替剑刃切入时间。上挑截断点之后衔接既有双手待机；普通与冲刺下劈保留原片段的收势。进入与退出都做待机衔接。

## 刃向修正

实际模块剑的局部 `+Z` 为剑身长度方向，`X/Z` 为刃面，`Y` 为厚度。上一版自编竖劈只有俯仰和偏航，没有绕剑身转刃，因此不能保证刃面与运动平面一致。唐刀单刃模块的切削边位于局部 `-X`，本轮使用该边对齐挥砍的横向切线；双刃剑也适用。

在打击区间，按素材剑尖轨迹计算垂直于剑身的切削方向，将 `-X` 刃朝该方向旋转，保留素材本来的剑尖指向与主手移动。转刃在蓄力时进入、收势时退出；前臂承担大部分轴向转动，避免只扭手腕。骨长、头颈局部位置和缩放保持 Jason 的参考值。

## 制作与接入

- `Tools/PlayerBody/import_sword_donor_repair.py`：后台导入官方 FBX、保存骨架与全部依赖，建立重定向，读取原始与 Jason 姿态。
- `SourceAssets/ThirdPersonSwordDonorRepair20261006/adapt_donor.py`：剪辑原动作，适配双手、刃向和过渡；完整制作参数与来源时钟均在此。
- `Tools/PlayerBody/save_sword_donor_repair.py`：保存三个独立的 30 Hz AnimSequence，并写 `assets-saved.json`。
- `Tools/PlayerBody/publish_sword_donor_repair.py`：仅更新上述三个配置角色，记录 `published.json`，保留其他配置修改。

最终资产目录为 `/Game/Characters/JasonPlayer20261003/SwordDonorRepair20261006/Animations`，资产名为 `J_UAL2_Uppercut`、`J_UAL2_Overhead`、`J_UAL2_DashOverhead`。Contact/Release 标记继续由既有采样器映射到实际攻击时钟。普通三连复用首击、旋风、死亡、伤害和移动数值均未修改。

本轮只改动画资产、制作工具与三个配置引用，无原生 C++ 变更，不需要重编 Editor DLL。后台导入及保存完成情况以 `assets-saved.json`、`published.json` 和 `save.log` 为准。没有启动 UE 图形编辑器、游戏、PIE、渲染或自动测试；动作观感与穿模情况由用户实机体验，尚未验收。
