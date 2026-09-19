# 参考骨架枪托 / 5080 模型候选

**2026-09-14 用户明确新模型命名为“核心枪托”，需独立于已有骨架枪托。当前制作入口为 [CoreStock20260914/README.md](../CoreStock20260914/README.md)，其中记录原枪托恢复、新属性及前段重建。**

用户在可用性检查后已授权继续修整。最新制作与三枪接入文件见 [Refined/README.md](Refined/README.md)；下文为初次生成阶段记录，`UsabilityReview` 中的图片为修整前实模。

用户要求参考附图，继续使用既定模型管线生成对应模型。当前阶段为独立外观候选生成，后续选型和游戏接入另行推进。

当前结果：5080 任务返回 `execution_success`，完成三视角生成，用时约769.05秒（12分49秒）。原始 GLB、纹理母版、独立参考视角和条件图均已下载；Blender 5.1.2 已完成导入与打包保存可编辑源文件。这里的成功是生成和文件制作完成，不是造型、细节、装配或游戏验收结论。

主要交付：

- [带纹理模型](seed_91379/textured_master_00001_.glb)
- [Blender 可编辑源](seed_91379/SkeletonStock_5080_Candidate_Editable.blend)
- [原始几何](seed_91379/raw_00001_.glb)
- 原带贴图位于 `seed_91379/Textures/`；导入制作回执为 `seed_91379/editable_source_receipt.json`。

## 参考与造型

- `reference_original.png`：用户提供的骨架枪托截图，原始文件 `codex-clipboard-87f426e5-2b4c-4263-9711-1b92bf243ddf.png`。
- 核心身份：横向上壳、前端开口、中央大镂空、斜向细支撑、后部厚托板和侧面圆形细节。
- `three_views.png`：内置 imagegen 根据原图制作的同对象三视图；`reference_prompt.txt` 为完整提示词。这是生成条件参考图，不是模型渲染。
- 未见侧与端面属于设计推断；没有真实制造尺寸、螺纹或内部机构。本轮不指定目标枪型、物理尺寸或运行挂点。
- 参考图由用户提供，权利人和公开再分发许可未提供。文件保存在本机工作目录，本任务未执行公开发布。

## 5080 生成设置

通过当前服务 `http://192.168.3.142:8188` 执行，服务记录保存为 `service_at_submission.json`，节点接口为 `generator_node_info.json`。提交前队列为空；仅提交本任务一个候选。

| 项目 | 值 |
| --- | --- |
| 模型 | microsoft/TRELLIS.2-4B |
| 节点 | Trellis2MeshWithVoxelMultiViewGenerator |
| pipeline / 结构分辨率 | 1024_cascade / 64 |
| 结构、形状、纹理采样步数 | 16 / 32 / 24 |
| 纹理 / 母版导出面数目标 | 4096 / 500000 |
| fill_holes / keep_only_shell | false / false |
| seed | 91379 |
| prompt_id | 744db6bf-b914-4b56-99d2-647ea03bbc5f |

实际运行环境由服务返回：RTX 5080、ComfyUI 0.30.0、Python 3.11.9、PyTorch 2.9.1+cu128。节点源文件和读取到的版本信息存于 `PipelineSnapshot/`；没有节点提交号时不声称已锁定仓库版本或模型权重修订。

1536×1024 三视图在生成图中按各视角边界分别裁切，之后独立前景处理。上左侧面 → front_image/+Z；上右反面 → back_image/-Z；下中前端 → left_image/-X。具体像素区域见 `view_mapping.json`。这些方向是采样条件映射，不能直接当作导出网格的已测量轴向。

`generate.py submit` 负责提交，已有回执时不重复提交；`status` 只读取本任务状态，`fetch` 仅获取完成后的原始几何、纹理母版和分离参考/条件图，不会启动渲染、游戏或其他任务。

## 文件与阶段

`seed_91379/workflow.json` 和 `request.json` 保留完整生成工作流与请求；回执为 `receipt.json`。已保存 `history.json`、`downloads.json`、原始 `raw_00001_.glb` 和 `textured_master_00001_.glb`。

`make_editable.py` 将纹理母版导入 Blender，保留原几何、UV、材质、法线及生成坐标，提取贴图并打包保存 `SkeletonStock_5080_Candidate_Editable.blend`。它不触发减面、自动修整、渲染或游戏测试。原始 GLB 导出节点保留其90度重定向设置，不假定 raw 与纹理母版坐标可直接互换。

本轮不替换游戏中的现有骨架枪托，不改配件属性或稳定性优化代码。候选选定后的游戏低模、结构烘焙、宿主连接面适配和引擎接入属于后续阶段。

生成交付时未测试。后续用户明确要求“帮我检查是否可用”，已完成网格、UV、贴图和 Blender 实际模型预览检查，结论为可修整母版、尚不宜直接用作正式游戏低模。详见 [可用性报告与实模预览](UsabilityReview/README.md)。尚未做本候选的 UE 导入、装配或游戏测试；生成执行成功不等于游戏验收通过。
