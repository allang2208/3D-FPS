# 弯刀改造迁移为传奇后缀附魔（2026-10-30）

按用户要求，尼泊尔弯刀的「狂战士符文」与原名「霜鸦符文」（水晶鹰头）退出改造目录，分别改为传奇后缀「血狼」与「霜鸦」。按用户后续调整，两者限定单手刀／剑，同后缀互斥。原有其他改造、前缀及武器属性不变。

- 血狼：`bloodWolf` / `enchant_scroll_blood_wolf`。物理伤害+10%；12 次成功出手命中后激活 20s，免本武器攻击及武技体力，攻击速度+25%、攻击伤害+25%、按实际直接伤害吸血10%、移动速度+15%。
- 霜鸦：`frostHawk` / `enchant_scroll_frost_hawk`。对应武器攻击暴击率+20%；8 次成功出手命中后激活霜狱 16s，韧性伤害+35%、每次出手对命中目标叠加4层寒冷，原冻结与寒冷计时规则不变。暴击仍进入本武器的近战修正，不扩展到持武器时施放的魔法。
- 双持共享充能、单刀归属、激活当次出手、切换和死亡清除继续复用原组件。触发入口改读实例的附魔效果；不再识别旧改造字段。

四处卷轴目录已接入：`enhancement.json`、`items.json`、`dungeon_loot.json` 与 `tooltip-reference.json`。卷轴复用现有正式外观，价格8000、堆叠99、附魔粉尘1600及掉落档位/权重沿用同级苍龙卷轴。强化台、物品浮窗与图鉴提供名称、限制和效果。

刀面六款材质映射移到 `kukri-modules.json` 的 `enchantment_surfaces`，持握、世界装备、预览和资源准备读取同一映射，视觉缓存包含附魔身份。狼首、水晶鹰头、能量条、粒子与所有现有材质资产继续复用，无需重新导入。两套现行美术发布脚本及作者目录同步使用附魔映射，不再添加旧改造。

`ColdSteelFrostRunes::Upgrade` 将旧的 `berserker_rune` / `frost_raven_rune` 归为空；现有档案加载通过原 A/B 存档事务清除对应 `blade_2` 字段。旧改造不自动变成新附魔，不替换玩家已有后缀，不修改其他槽位或直接改写磁盘存档。未重新加载的磁盘存档仍保留旧字段，加载后才迁移。

交付为源码、目录及现有资产引用。`FPSGAMEEditor Win64 Development` 最终构建成功，13 项动作并完成 `UnrealEditor-FPSGAME.dll` 链接；日志为 `Saved/KukriEnchantment20261030/build-editor-final.log`。

`FPSGAME Win64 Development` 未完成：本次修改的翻译单元已编译，但全目标被 `RuneSwordWhirlwind.cpp` 缺少 `ZhufengSecondaryWhirlwind.h`，以及 `WarhammerShockwave.cpp` 的 `ThunderStatus` / `ApplyThunderStatus` 等实现与声明不一致阻塞。保留这些其他功能的现场，没有补占位实现或回退源码；日志为同目录 `build-game.log`。本轮未运行游戏、审计、截图或运行测试，实际体验由用户测试。

## 后续范围调整：单手刀／剑

两张卷轴限制键改为 `oneHandedBlade`：近战武器、非双手、类型为 `kukri` / `knife` / `sword`。强化台可用性、效果读取、霜鸦命中、单手暴击快照、配对武器与浮窗共用该范围；双手刀剑、钝器、采集工具和远程武器不在其中。现有附魔 ID、传奇后缀、数值、充能、持续时间及旧改造取消规则保持不变。当前已有目录中的对应武器为尼泊尔弯刀；未新增武器或动作资产。

本次范围调整后，Editor 与 Game 两个目标均已后台构建成功，分别完成编辑器模块与 `Binaries/Win64/FPSGAME.exe` 链接。日志为 `Saved/KukriEnchantment20261030/one-handed-editor.log`（21.96s）和 `one-handed-game.log`（213.52s）。此前记录的 Game 构建阻塞已不再阻止本轮构建；本轮没有修改那些无关武器源码，没有启动编辑器、游戏或运行测试。
