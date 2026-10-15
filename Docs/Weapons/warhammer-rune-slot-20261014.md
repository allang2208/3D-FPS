# 战锤：锤颈改造入口替换为符文

后续已接入剑类四种通用符文及战锤刻印、效果结算，见 [通用符文接入](warhammer-common-runes-20261014.md)。本页保留空槽阶段记录。

用户指定将原「锤颈套箍」改造栏换成「符文」。`warhammer-gunsmith.json` 第三栏键由 `neck` 改为 `rune`，显示名称为「符文」，默认选项为「无符文」，描述为「未刻印符文，保留战锤原有的金属表面」。仍保持六个工作台分类及原有顺序。

`warhammer-modules.json` 的实体 `module_slots` 仍包含 `neck`：它是锤座与长柄间的固定结构，没有从模型上删去。独立的 `slots.rune.factory.appearance` 仅供界面展示「未刻印符文 · 原有金属表面」，不加入实体模块列表，不创建虚构符文网格。

原套箍仅有原厂选项，没有需要迁移的非原厂改件。已有 `Normalize` 逻辑过滤不再允许的槽位及 `false` 值，保留锤头、中央锤座、柄杆、握持和柄尾改造；没有直接修改用户存档。

图标复用现有认可母图：

| 实际键 | 复用来源 | 含义 |
| --- | --- | --- |
| `category_rune` | `blade_2_resonance_rune.png` | 符文分类的代表符印，不表示装备共鸣效果 |
| `rune_false` | `FramedFirearms/bipod_false.png` | 通用中性圆圈减号，表示空槽 |

图标实际部署于既有 `Content/ColdSteelData/AttachmentIcons20260913` 根目录，使用共享键，保留原母图，未生成新的剑刃／套箍实物图。PNG 与对应 Texture2D 由 `SourceAssets/WarhammerRuneSlot20261014/install_rune_slot.py` 同步保存，UI 组、Editor Icon、sRGB、Never Stream、无 mip。旧套箍资产及原始拆分源仍保留。

当前新增的是符文槽及其空置状态，尚未新增可选符文、战斗效果或武器表面刻印。既有锤头和中央锤座数值保持不变。本轮无 C++ 改动，不需要原生构建；后台保存回执在同一作者目录。未运行游戏、UI 或联机测试。

后台导入完成：两个共享 PNG 与两个 Texture2D 已保存，目录和外观元数据已更新，回执 complete=true，commandlet 返回 0。
