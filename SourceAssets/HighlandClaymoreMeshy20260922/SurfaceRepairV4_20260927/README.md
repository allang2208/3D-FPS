> 本目录为历史记录。2026-09-27 整理时，已被替代／未选中的作者脚本、模型和导出移入本机 `trash/sword-publication-20260927/SourceAssets/HighlandClaymoreMeshy20260922/SurfaceRepairV4_20260927/`，可按归档清单恢复。当前制作从 [后继入口](../JunctionBlendV5_20260927/README.md) 开始。下文描述历史版本，不是重建入口。

# 高地双手剑表面重做 V4

> 当前运行资产已由 [连接区 V5](../JunctionBlendV5_20260927/README.md) 原路径重导入更新。下文保留 V4 历史制作记录；不要重跑本目录导入脚本覆盖 V5。当前资产名仍带 `_SurfaceV4`，实际修订见资产元数据与 V5 导入回执。

2026-09-27，用户反馈 V3 剑身贴图糊，并提供了改造台截图：剑身与护手中央出现大片三角形破碎反光。本轮修正模型表面与着色基础，不将 V3 导入成功记录视为视觉合格。

## 本轮修改

- 从 `Integration`、`BroadbladeThicknessV2_20260922` 和 `ClovenGuard20260922` 的原始可编辑模型重新制作；不继承 V3 的法线。
- 移除逐三角形射线深度除法与微小射线差分法线转换。剑面使用连续的截面函数成形，避免射线命中/未命中切换向几何与法线传入噪声。
- 依据最终网格生成角度加权表面法线；模块封口单独保留硬法线，不将封口混入可见剑面。护翼未改变区继续保留原作者法线。
- FBX 只导出新法线，UE 使用新法线和原 UV 重新构建 MikkTSpace 切线，启用高精度切线基及完整精度 UV。使用明确的 FbxFactory 和导入参数。
- 保留五种剑身的轮廓、UV、原贴图与纹样、材质槽，保留 12 mm 主体厚度和突出宝石。没有通过模糊纹理、提高粗糙度或关闭金属反射遮盖问题。
- 五种剑身、五种护手与完整原装剑后备网格一起更新。武器数值、动作、改造 ID、安装点与攻击端点未改变。

## 已保存内容

三个可编辑 Blend、`Export/` 中 11 个 FBX、11 个 UE 静态网格已保存。UE 新目录为 `/Game/Weapons/HighlandClaymore20260922/SurfaceRepairV4_20260927`，网格后缀 `_SurfaceV4`。

`highland-claymore-modules.json` 中全部剑身与护手、`items.json` 的本剑整剑后备模型已切换到 V4。导入前目录备份位于 `Before/`，恢复时只合并本剑引用，不整文件覆盖其他工作的后续修改。

- `author_surface_v4.py`：后台制作与 FBX 导出。
- `import_surface_v4.py`：材质槽绑定、切线构建、保存与引用更新。
- `author_receipt.json`、`import_receipt.json`：制作和保存结果。
- `Highland_SurfaceV4_Editable.blend`、`Highland_Broadblade_SurfaceV4_Editable.blend`、`Highland_Cloven_SurfaceV4_Editable.blend`：可编辑源。

首次编辑器导入因正在 PIE 无法保存而中止；随后结束游玩，通过现有互斥桥完成 11 个网格保存和目录切换。未关闭或重启编辑器，未重新启动游戏。

本轮未进行游戏测试、截图或验收渲染；视觉效果交由用户测试。来源许可继续沿用 [原接入记录](../Integration/README.md)。

## 用户再次反馈外观未变：当前会话仍加载 V3

用户重新进入游玩后反馈“还是一样”。只读读取其已有会话的组件路径，`ModularSwordBlade` 与护手仍引用 `UniformThickness20260927/*_UniformV3`，记录为 `loaded_highland_paths.json`；没有启动新游戏或截图。

`Source/FPSGAME/Weapons/ModularSwordVisual.cpp` 的 `Catalog()` 使用函数静态 `SharedSixPartCatalogs`，按文件名命中后直接返回，既不在 PIE 结束时清空，也不读取目录修改时间。因而只更新 JSON 后退出再进入游玩，仍会复用旧路径。这次需完整退出并重新打开 UE 才会从磁盘读取 V4；此前“无需重启”的交付说明错误。V4 的视觉效果尚未由本次旧 V3 会话验证。未自行关闭或重启用户编辑器，未扩大为运行时代码改造。
