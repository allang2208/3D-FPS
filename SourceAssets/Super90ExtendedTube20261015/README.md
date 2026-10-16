# SUPER90 加长管式弹仓

用户确认：容量增加 3 发（7 → 10），开镜耗时增加 10%。列为弹仓槽的特殊改造。用户同时确认，为加长弹仓制作兼容收束器、消音器外观，允许同时安装。

## 制作与装配

- `Super90_ExtendedTube_Editable.blend` 与 `author_tube.py` 保存可编辑模型及制作步骤。
- 从实际 SUPER90 枪体导出提取原厂端帽，保留 UV、自定义法线和 BarrelSteel 材质；新管体沿弹仓轴线延伸，端帽整体前移，原厂枪管、管体和前固定环保留。
- 原生骨骼模型仅增加 `S90_FactoryTubeCap_` 材质分组（两个完整岛，共 1996 面），供安装/拆卸时切换显示。未重新导入整枪、修改骨骼或替换动画。
- `CompatibleMuzzles/Choke` 和 `CompatibleMuzzles/Suppressor` 为组合安装制作扁平外壳，保留原枪口座、长度、发射位置、材质与游戏效果。
- 装上加长弹仓时自动选择兼容外壳；恢复原厂弹仓后自动恢复原枪口外观。鸟笼沿用原模型。
- 三套静态模型均导出 3 级 LOD。运行时使用现有附件、武器图标/预览、掉落与第三人称流程；原厂端帽隐藏状态也纳入第三人称装备快照。

## 装填与数值

- 逐发装填重复原来的最后一段进弹动作，可装至 10 发；每次接触分别结算弹药。
- 配合速装器时，每次动作最多装入速装器实际承载的 7 发；空仓装满需要 7 发后再执行一次装填，补足 3 发。客户端和服务端采用同一上限。
- 取消装填、空仓尾段和机械音效使用对应的进弹时钟。
- 容量与开镜耗时通过现有属性计算和物品存档生效。拆回原厂弹仓时，现有改造事务将超过容量的实体弹药退回弹药袋。
- 收束器、消音器数值及槽位保持既定设置；外壳切换不增加其他属性。

## 图标

通过内置 imagegen 编辑模式制作。采用已认可的金属方框母版和实际弹仓模型参考，输出为灰阶钢材部件图。完整提示词及输入记录在 `generation_prompts.json`；最终源图为 `magazine_super90_extended_tube.png`。

活动图标：`Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/magazine_super90_extended_tube.png`。同时保存共享 UI Texture2D 与本配件 UI Texture2D。

## 资产与交付记录

- UE 资产根目录：`/Game/Weapons/Super90/ExtendedTube20261015`。
- `install_receipt.json` 记录实际已保存的 3 个静态模型、独立管体材质、2 个图标及原生端帽材质分组。
- `catalog_receipt.json` 记录 SUPER90 新改造项和用户确认的数值。
- `Before/` 保存原生枪体和改造目录修改前备份；无需恢复或覆盖其他任务的资产。
- `build_*.json` / `livecoding_result_*.json` 记录实际构建结果。

没有启动试玩、自动截图、整枪预览或运行测试。装配视觉、ADS、装填、存档以及联机效果由用户在游戏中测试；资产保存和编译结果不代表运行验收。

2026-10-16 完成常规构建：`FPSGAMEEditor Win64 Development` 与 `FPSGAME Win64 Development` 均为 `Succeeded`、退出码 0。用户同意关闭 UE 后继续编译；开始本次构建时编辑器已经退出，构建后没有重开。构建日志与回执分别保存于 `build_FPSGAMEEditor.log` / `build_FPSGAMEEditor_receipt.json` 和 `build_FPSGAME.log` / `build_FPSGAME_receipt.json`。

## 2026-10-16 整理记录

本目录已确认退役的备份、候选或一次性操作已移至本机 `trash/weapon-attachments-retired-20261016/SourceAssets/Super90ExtendedTube20261015`。原文的 Before/旧候选路径属于历史记录；当前恢复依赖已保留。准确清单、替代物及本轮发布边界见 [整理发布说明](../../Docs/Publication/WeaponAttachments20261016/README.md)。
