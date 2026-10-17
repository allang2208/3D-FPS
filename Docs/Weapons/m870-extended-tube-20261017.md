# M870 弹仓延长管

用户要求参考 SUPER90 加长弹仓，为 M870 增加专用延长管，容量增加 3 发。

## 改造项目

- 弹仓槽特殊改造：`m870_tube_extension`，显示名「弹仓延长管」。
- 仅 `mag_delta: 3`，原厂 7 发改为 10 发。没有增加开镜耗时或其他数值代价。
- 改造卡沿用已认可的 SUPER90 灰阶金属框延长管图标；M870 模型独立制作。
- 容量采用既有 GunsmithSystem 评估、实例存档与网络弹药结算。逐发装填依当前剩余容量循环；拆除时由现有改造事务退回超出容量的实体弹药，弹药袋无法接收时拒绝整个改造事务。

## 模型与接合

制作目录：`SourceAssets/M870ExtendedTube20261017`。可编辑源为 `M870_ExtendedTube.blend`，作者入口为 `author_tube.py`。

以当前 `SK_M870_V7` 原厂弹仓轴线和端面制作：直径沿用原管，前端相对原厂延伸 16.53 cm。尾部套环从原管前方 45 cm 处承接，原厂端面约 46.30 cm，延长后端面约 62.83 cm。端盖从保留的原模型提取，保留原生 UV；新管体使用现有 M870 AdapterSteel 表面。端盖材质单独复制为静态用途，关闭骨骼、衣物及 morph 用途。

三级 LOD 分别为 1920、960、480 三角面。新管体具备封闭后端和端盖；实际接头避开泵动护木及前方固定战术夹具。

原生枪体仅将前端盘的 24 个三角面分到 `M870_FactoryTubeCap`，供安装隐藏、拆卸恢复。通过 GeometryScript 修改材质 ID，保留顶点、UV、法线、蒙皮、骨架以及原有材质显示名和导入名；不重导手臂或动画。

静态附件以完整逆参考变换挂到 `WPN_root`，抵消源骨骼比例；逐发装填和泵动时保持枪身连接，不走弹鼓掉落逻辑。原厂端盖隐藏状态纳入第三人称装备快照。配件路径加入按配方异步准备和预加载注册表；枪匠、装备图标及世界物品沿用现有附件捕获流程。

## 源码入口

- `Weapons/M870TubeMagazineAssets.h/.cpp`：模型路径、安装、端盖隐藏和恢复。
- `Weapons/M4DrumVisual.cpp`：M870 弹仓改造及装填期间可见性。
- `Weapons/GunsmithModificationTier.h`：专用特殊改造分类。
- `UI/ColdSteelIconResources.cpp`、`UI/M4GunsmithLayout.cpp`：配方准备与共享图标映射。
- `Characters/FPSPlayerBodyEquipment.cpp`：第三人称端盖分区。
- `Content/ColdSteelData/gunsmith.json`：容量与选项；M870 注册脚本保留已接入的各槽改造。

## 附带更正既有扩散误改

之前图标与扩散任务误匹配相同数值段，实际误改了 SUPER90。此次使用明确武器 ID，仅将 M870 的基础腰射扩散 2.25 改为 1.2375（原值 55%），并将误改的 SUPER90 1.2375 恢复为 2.25。备份和改动记录在本制作目录 `Before/gunsmith.json` 与 `catalog_receipt.json`。

## 交付状态

后台导入保存和构建回执由制作目录内 `import_receipt.json`、`build_editor.log` 记录。未启动游戏、截图、渲染或运行测试；外观、装填、拆装、存档和联机效果由用户测试。

2026-10-17 已完成实际保存：三级静态模型 `SM_M870_ExtendedTube`、静态端盖材质 `M_M870_ExtTube_NativeCap`、原生枪体 `SK_M870_V7` 的可切换端盖分区。导入回执 `completed: true`，原生变更范围为 24 面材质 ID。

Editor 正常构建返回 `Succeeded`：`Saved/BuildEditor/build-20261017-100418.log`。本轮构建判定当前产物已是最新（0 个待执行动作）；新 `M870TubeMagazineAssets.cpp` 已有对应 Editor 编译对象，当前 `UnrealEditor-FPSGAME.dll` 于 10:02:45 落盘。没有为重复构建而清理对象或启动游戏。
