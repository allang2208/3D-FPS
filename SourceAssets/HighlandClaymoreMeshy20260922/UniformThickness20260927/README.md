> 本目录为历史记录。2026-09-27 整理时，已被替代／未选中的作者脚本、模型和导出移入本机 `trash/sword-publication-20260927/SourceAssets/HighlandClaymoreMeshy20260922/UniformThickness20260927/`，可按归档清单恢复。当前制作从 [后继入口](../JunctionBlendV5_20260927/README.md) 开始。下文描述历史版本，不是重建入口。

# 高地双手剑：统一厚度 V3

**后续状态：用户反馈剑身表面糊、破碎反光，本版已被 [表面重做 V4](../SurfaceRepairV4_20260927/README.md) 替代。不要重新执行本版导入器恢复 V3 引用。以下为当时的制作记录，不代表视觉合格。**

2026-09-27，用户要求修正剑身下方与护手衔接处的厚度不一致，并明确覆盖全部剑身改造、保留突出宝石。

## 本版制作

- 原装、延锋、重脊、轻羽、阔锋五种剑身，共用 **12 mm 金属主体厚度**。保留各自 X/Z 轮廓、长度、宽度、原 UV 和材质；刃口保留磨刃面，最后 22 mm 剑尖收薄。
- 原装、壁垒、反击、轻量、裂角五种护手同步调整中央连接部位；护翼外段、握把接触端和配重保持原几何。
- 剑身和护手的 V 形切口共用未拆分母版的变形场，不冻结旧的厚接缝，也不增加遮挡接缝的套圈。
- 宝石按原模型菱形轮廓保留四面体积；镶边设计突出金属面 1.5 mm，宝石中心设计突出金属面约 8 mm。宝石跨越剑身与护手的上尖同步处理，两侧表面连续。
- 法线按完整局部变形梯度转换；保留原材质槽、贴图、裂角护手嵌纹与顶点色。网格拓扑保持源结构，不增加细分或运行时厚度计算。
- 完整剑模型由本版原装模块合并制作，用于物品目录的整剑后备引用。

这里的厚度是作者设计尺寸；本轮未运行游戏、验收渲染、截图或几何验收脚本，视觉效果由用户测试。

## 源文件与制作入口

- `Highland_UniformThicknessV3_Editable.blend`：原装、四种常规护手及四种常规剑身。
- `Highland_Broadblade_UniformThicknessV3_Editable.blend`：阔锋重刃与修正后的原装护手。
- `Highland_ClovenGuard_UniformThicknessV3_Editable.blend`：裂角护手与修正后的原装剑身。
- `Export/`：11 个 FBX，含五种剑身、五种护手和一把完整原装剑。
- `read_author_inputs.py` / `author_inputs.json`：本次制作所用的原模型尺寸和宝石轮廓资料。
- `author_uniform.py` / `author_receipt.json`：后台制作、导出与保存记录。
- `import_uniform.py` / `import_receipt.json`：UE 后台导入、保存和目录接入记录；`complete` 表示保存与引用更新完成，不表示测试通过。

制作输入沿用 `Integration/`、`BroadbladeThicknessV2_20260922/`、`ClovenGuard20260922/` 的原可编辑源。没有以已恢复旧模型的 `RicassoSeat20260924` 失败修订为几何输入，也没有覆盖上述源文件。

## UE 接入与恢复

新资产独立保存在 `/Game/Weapons/HighlandClaymore20260922/UniformThickness20260927`，名称以 `_UniformV3` 结尾。

本轮已通过无界面 Python commandlet 导入并保存 11 个 UE 静态网格，完成两份目录的对应引用更新，进程退出码为 0。`import_receipt.json` 的 `complete`、`catalog_saved`、`item_fallback_saved` 均已写为 `true`；`tested` 保持 `false`。

导入器先保存全部新资产，再更新 `Content/ColdSteelData/highland-claymore-modules.json` 中五种剑身、五种护手的 `mesh`，以及 `items.json` 中 `ue_highland_claymore.world_mesh`。保留改造 ID、属性、动作、安装原点、攻击端点、存档与其他物品数据；重新读取当前目录后合并，修改前的目录保存在 `Before/<时间>/`。

现有材质和 Nanite/LOD 制作设置沿用当前资产。旧 UE 网格仍保留；需要恢复时只按 `Before` 中本剑的旧模型路径合并回来，不用整个旧目录文件覆盖后续其他修改。

未重新生成静态目录图标：本轮修改厚度，X/Z 剪影与贴图不变；运行时模型预览采用更新后的模块引用。未修改 C++，无需原生代码构建。未启动交互 UE 编辑器或游戏。

来源和许可继续沿用 [高地剑原接入记录](../Integration/README.md)，未公开发布模型或贴图。
