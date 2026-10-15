# 战锤三款通用柄尾配重：建模与接入

按 [设计方案](common-hammer-pommels-design-20261014.md) 与其三款并排概念图制作。制作目录为 `SourceAssets/CommonHammerPommels20261014/BuildV1`。

## 模型与材质

| 名称 | 选项 ID | 形体 | LOD0 三角形 |
| --- | --- | --- | ---: |
| 八棱镇击配重 | `octagonal_impact` | 八棱实体、收窄上肩、宽倒角底盖 | 9,720 |
| 镂笼灵巧配重 | `caged_agility` | 六根实体弧肋、贯通纵窗、封闭底盘 | 22,240 |
| 双盘平衡配重 | `twin_disc_balance` | 两枚厚盘、实体短芯、环形间距 | 23,340 |

保留原装柄尾上端 12 mm 接合段及其 UV／面角法线，下切环连接到新主体。安装点保持 Z=-8.5 cm；新尾件总长约 8.75 cm，原装约 7.50 cm，长度变化向柄尾延伸。原装与三款新包覆的接口、握点和包覆长度均保持原位。

实体主体复用通用锤头钢材、暗部复用中央锤座钢材，原接口使用原装材质。新增底盖车纹材质带 1024 像素法线和 ORM，适用于静态附件。可编辑 Blender 文件、FBX、作者脚本和尺寸记录均已保存。

## 图标与改造槽

正式图标从本轮实际模型生成素材，采用统一灰阶、厚金属方框、四角铆钉、银色内环和深灰底板；内置 image_gen 负责套用现有框体样式。可编辑图标作者场景和完整提示词保存在制作目录。概念图不作为正式图标。

共享图标键为 `pommel_octagonal_impact`、`pommel_caged_agility`、`pommel_twin_disc_balance`，目录 `Content/ColdSteelData/AttachmentIcons20260913`。共享选项目录为 `common-hammer-pommels.json`，宿主 `warhammer-gunsmith.json` 的 `pommel.options_library` 引用它；模型路径在 `warhammer-modules.json` 的 `slots.pommel` 中。

现有通用模块装配读取各槽模型和 `gunsmith_parts`，共享模型配方供手持、改造草案、物品预览和掉落使用；本轮沿用该数据入口。原装 `factory` 保留。三款属性及能力说明已按下表写入，`special_effects` 保持为空。

## 当前数值

以下为用户最终确定的数值，替代初版配置。

| 柄尾配重 | 物理伤害 | 攻击速度 | 攻击体力消耗 | 韧性伤害 | 武技冷却时间 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 八棱镇击配重 | +5% | -5% | +5% | +10% | — |
| 镂笼灵巧配重 | -5% | +10% | -10% | — | — |
| 双盘平衡配重 | — | — | -20% | -10% | -20% |

“—”表示该属性不变。伤害、攻速、体力、削韧使用既有属性字段；双盘新增 `martial_cooldown_mult: 0.8`，只缩短武技冷却时间。大旋风及上挑的冷却计算使用 `SkillCooldown * MartialCooldown`，沿用各自的服务端提交、冷却时长快照、同步和界面倒计时。与共鸣符文同时装备时，乘积为 `0.85 * 0.8 = 0.68`。法术不消费武技冷却字段，普通攻击时钟及武技动作时长不因该字段缩短。

作者源 `BuildV1/catalog.py` 与正式 `common-hammer-pommels.json` 已同步，改造详情、总览、物品浮窗与摘要补充武技冷却行。当前变更记录在 `SourceAssets/CommonHammerPommels20261014/BalanceV2`，`Balance20261014` 为初版历史。该数值修改不需要重导模型或图标。

模型导入阶段没有 C++ 改动；本次新增武技冷却字段需要原生构建，进度及实际结果见 `BalanceV2` 的构建记录。改造目录及模块缓存随新的游戏实例载入；不主动重启当前游戏或编辑器。

## 保存状态

已在后台完成导入与保存：3 个静态模型、1 个车纹材质、2 张表面纹理、3 张图标 Texture2D，共 9 个 UE 资源。`import_receipt.json` 为 `complete: true`，`commandlet_receipt.json` 退出码为 0；导入过程完成材质编译与资源保存。正式共享目录及战锤柄尾模型／选项引用已由导入脚本合并发布，原配置快照保存在制作目录 `Before/`。

模型制作与导入阶段未启动 GUI 编辑器或游戏。后台保存结果与实际游戏装配效果分别对待；后续数值代码的构建结果单独记录。

最终数值更新的 Game 原生构建已成功。Editor 目标最初因后台 UE 资源进程占用而推迟；同日后续符文柄面调整已取得当前 Editor 目标 `Succeeded`／`Target is up to date` 结果，待构建事项已解除，回执位于 `SourceAssets/WarhammerCommonRunes20261014/ShaftWrapV2/editor-build-receipt.json`。

未运行游戏、联机测试、回归或验收渲染，实际装配与视觉效果交由用户测试。
