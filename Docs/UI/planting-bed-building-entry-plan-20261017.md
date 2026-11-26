# 种植地 V2 建筑条目接入（2026-10-17）

用户入口：在当前已开放建筑功能的场景中，按 **B → 其他 → 种植地**，左键放置、R 每次旋转 90°、右键拆除。完整名称为“种植地（2米×2米）”，稳定条目 ID 为 `planting_bed`。

## 实施范围与数据合同

本次沿用 `UVoxelBuildWidget` 的现有分类、卡片、详情、焦点、滚动与关闭流程。活动目录仍为 `/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette`。按用户“后台编译，不启用 UE”的限制，仅在该资产的 `UVoxelBuildPalette::PostLoad` 中追加缺失条目；没有改写 `.uasset`，没有启动编辑器、commandlet、游戏或 PIE。

注册只影响活动调色板，保留已有条目及顺序。已有同 ID 定义优先；同网格已被其他条目引用时不再添加，避免重复。新增条目放在目录末尾，`Material=None`，因此属于一级“其他”，不会进入木材等材质栏目。目录未增加科技或解锁条件，场景开放限制与现有建筑系统一致。

| 字段 | 本次定义 |
| --- | --- |
| 模型 | `/Game/Building/PlantingBed20261017/SM_PlantingBed_2m_V2` |
| 修复版 SHA256 | `11a8a7c6a343a64b5abdb3bdb58978547cb0a867ec39f8f052633290ebe4ec22` |
| 实际外形 | 约 200 × 200 × 29.6 cm，底部中心原点 |
| 格网占位 | 10 × 10 × 2 格，每格 20 cm，即 200 × 200 × 40 cm 的占位范围 |
| 放置方式 | `Free`，保留原有地面／结构支撑及占位冲突判定 |
| `PivotOffsetCm` | `(0, 0, -5.2)` |
| `ActorClass`／`Surface` | 空；使用通用静态构件和模型原有六个材质槽 |
| 碰撞 | 通用构件 `BlockAll`；沿用模型五个凸碰撞体和 SimpleAndComplex |

现有 `ComputeTransform` 将网格包围盒居中于占位体积。40 cm 占位比模型高 10.4 cm，因此下移 5.2 cm，使模型底面与格网基底重合。预览和实际放置共用同一公式；四种旋转的静态计算底面误差均约 −1.91e−7 cm。高度 40 cm 是占位范围，模型没有被拉高。任意地形上的接触仍沿用现有格网与支撑规则。

图标复用 `UVoxelBuildIcons`，从修复版模型和自身材质生成现有 256² 缩略图；保留既有队列、缓存、占位及失败回退。本任务未生成新的图标资产，也未执行实际缩略图渲染。

费用沿用 `Docs/Building/voxel-build-workflow.md` 已明确的构件免料约定及当前 `PlacePrefab` 路径，不新增材料、产出、科技或经济数值。没有播种、生长、收获或专用交互面板。

保存沿用 `FVoxelBuildPrefabInstance` 的 ID、格坐标、旋转和占位数据；读档通过同一个调色板 `FindComponent` 恢复。拆除、撤销及失去支撑后的处理沿用普通构件路径。没有迁移或改写存档，源码审阅不代表这些操作已实际运行。

## 修改与保护

- `Source/FPSGAME/Building/VoxelBuildPalette.h`：声明 `PostLoad`。
- `Source/FPSGAME/Building/VoxelBuildPalette.cpp`：增加活动目录的唯一条目注册。
- `Config/DefaultGame.ini`：仅新增种植地资源目录的 `DirectoriesToAlwaysCook`，使代码软引用的资产有明确打包收集范围；未执行打包。
- 本文与 `SourceAssets/PlantingBed20261017/PanelIntegration20261017/`：任务备份、精确差异、脚本及回执。

没有改其他建筑分类、UI 布局、通用放置代码或存档格式。原调色板文件和种植地全部 16 个模型／材质／贴图资产哈希保持不变。`Receipts/task-only.patch` 仅记录本次相对开始时工作区的修改，不混入原有并行改动。

## 验证范围

后台编译结果：`FPSGAMEEditor Win64 Development` 已成功，完成时间 `2026-10-17T12:59:41.7267617Z`。日志包含 `Result: Succeeded`，普通 `UnrealEditor-FPSGAME.dll` 已落盘，源码哈希与构建记录一致。未运行 Game 目标或打包构建。

`Receipts/static-readback.json` 记录源码定义回读、分类规则、四向放置公式计算及资产哈希核验。它不是 UE 运行时条目回读。

后台编译通过项目入口 `Tools/Build/Build-Editor.ps1`，先等待既有 UE／编译批次并取得共享互斥锁。结果见 `Receipts/build-result.json` 和 `build-console.log`；构建等待或执行中时不可视为通过。新代码在下一次正常加载新模块和活动调色板时生效，本任务不打开或重启 UE。

未验证实际运行的 UI、缩略图、放置、碰撞交互、存档往返或联机行为；未启动任何 UE 进程，未提交或推送 Git。
