# 誓约符文交付

已接入高地双手剑的剑身 II 改造目录，类别为特殊。修改落在当前 UE 工程，正式 Editor 目标构建成功，9 项资产已实际导入和保存；未启动 GUI 编辑器或游戏。

被动为重击物理伤害 +15%、重击蓄力持续体力消耗 -20%。实际首次蓄满后的 0.35s 内出手触发「裁决时刻」：本次物理伤害再乘 1.35、韧性伤害再乘 1.5，首次有效命中返还实际出手耗体的 25%。普通第三段、冲刺突刺、横扫与没有实际蓄满的反击不触发裁决。

蓝色剑形誓印、三重开环逐次亮起、金白准心括角与倒计时、沿当前刀身汇向剑尖的三道细环、命中光屑及原创金属提示音均已接入。刀身誓印在裁决窗口与释放时提亮为亮蓝色。持有者提示按同一蓄力时钟预测；观察者读取服务器复制的充能／释放状态并绑定世界武器。实际伤害与首次命中返还在服务端计算，返还累计账本与档案镜像合并。

## 路径

- 设计／实现状态：`Docs/Weapons/highland-oath-rune-proposal-20261106.json`
- 制作源与说明：`SourceAssets/HighlandOathRune20261106/`
- 保存回执：`SourceAssets/HighlandOathRune20261106/saved-assets.json`
- 构建及导入日志：`Saved/HighlandOathRune20261106/`
- 正式素材：`/Game/Weapons/HighlandClaymore20260922/OathRune20261106/`
- 改造图标：`/Game/ColdSteelData/AttachmentIcons20260913/ue_highland_claymore_blade_2_highland_oath_rune`

## 验证边界

配色目标纠正：用户要求图标退回、剑身符文改蓝色。图标恢复 `SourceAssets/HighlandOathRune20261106/IconV2/OathRune_Framed_V2.png`；刀身常态、蓄力、就绪及释放均使用蓝色系，以亮度区分状态。HUD 窗口提示、独立释放光环、命中特效与数值保持原实现。本次后台导入和材质保存回执为 `SourceAssets/HighlandOathRune20261106/BladeBlueR1/saved-assets.json`。

已完成必要 C++ 与材质编译、正式资产保存。依用户当前规则，未运行游戏、实际联机、自动测试或截图验收。运行表现、打击手感和联机体验交由用户测试；未进行打包或 Git 推送。
