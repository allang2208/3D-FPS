# 配方手册书壳切线修复

## 原因

V9 书壳导入出现“退化的切线基础”和“近零的副法线”两条警告。书皮和纸叠的主 UV 正常；后加入的金属护角、书脊衬条使用 Blender 本地化名称 `UV贴图`，合并到书壳后与原有 `UVMap` 并存。这些新增面的主 UV 全为 `(0,0)`，实际展开仍在第二个通道里。

定位范围：`ManualAntiqueBrass` 的 1,504 个三角面及 `ManualLeatherBinding` 的 188 个三角面，共 1,692 个三角面；Blender 切线计算发现 72 个近零副法线。没有零面积几何面。

## 修复

- 只将上述两个材质区的原始展开从 `UV贴图` 复制到主通道 `UVMap`，涉及 882 个多边形、3,456 个 loop。
- 保留全部几何、法线、材质与其他表面的 UV；书壳仍为 4,124 个顶点、8,184 个三角面。
- 保留 UE 的 MikkTSpace 和切线重算；不关闭计算或隐藏警告。
- 单独保存 V10 书壳并修改运行时引用，骨骼纸页仍使用 V9，书签与翻页行为保持现有实现。
- 原可复用纸页作者脚本同步调用同一 UV 修复函数，避免后续导出重新引入问题。

作者目录：`SourceAssets/AlchemyManualBindingTangents20261016/`。
资产：`/Game/Building/PotionWorkbench20261015/ManualV10/Meshes/SM_AlchemyManualBinding`。

## 结果范围

源模型修复后的退化 UV、零切线、零副法线均为 0。UE 后台导入返回 `Success - 0 error(s), 0 warning(s)`，修正后的资产已保存到主工程。Editor/Game 构建状态以本目录 `delivery.json` 引用的回执为准；本轮仅处理指定导入警告，没有运行游戏、交互回归或视觉验收。

当前恢复链、退役文件归档和最终检查状态见 [手册收尾发布](../Publication/AlchemyManual20261016/README.md)。本文所述阶段结果保留为历史记录；本次整理未重新运行测试。
