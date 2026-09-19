# 参考消音器 / 5080 候选

请求：按 2026-09-13 通用模型新规则，参考用户附图生成一个游戏消音器。

制作结果：5080 任务返回 `execution_success`，用时约 282.79 秒；原始 GLB、带纹理母版、三份分离视角和三份前景条件图已下载。Blender 5.1.2 已导入母版并保存可编辑文件与原带贴图。这里的成功指生成和文件制作完成，不是模型质量、装配或游戏验收通过。

本轮范围为独立模型候选制作。原图中的细长筒身、纵向凹槽、后部斜纹与深灰金属外观是身份依据。原图未展示的另一侧及端面细节是设计推断，没有真实制造尺寸或内部机构。未指定目标枪型，尚未进行任何宿主连接面适配。

## 来源与参考

- `reference_original.png`：用户提供的 305×93 参考图片，原文件名为 `codex-clipboard-31fff245-0c1d-41d1-9d51-e4029dd6dc72.png`。
- `reference_prompt.txt`：本次 imagegen 完整提示词。
- `three_views.png`：内置 imagegen 根据原图生成的同对象三视图；不是 5080 模型实物渲染。
- `view_mapping.json`：本张图的裁切矩形及多视图节点输入。上排侧面 → front_image / +Z；中排反面 → back_image / -Z；下排前端面 → left_image / -X。front/back 是采样器方向，不等同配件的前后端。
- 图片经过 ComfyUI ImageCrop 独立裁切，再分别进行前景处理，三个结果接入真正多视图节点。

参考图由用户提供，原作品权利人与再分发许可未提供。AI 衍生输出不自动取得原参考图的公开分发权。工作文件保留在本机工程；本轮不执行 Git 发布。

## 5080 生成

入口为本目录 `generate.py`，复用项目 `Tools/AssetPipeline/Mechanical3D/workflows/trellis_ss64.api.json` 后保存本次独立完整工作流。远端节点定义和服务状态另存 JSON。

本次服务回报 ComfyUI 0.30.0、Python 3.11.9、PyTorch 2.9.1+cu128、RTX 5080。`PipelineSnapshot/nodes.py` 与 `flow_euler.py` 保存本次读取的远端节点及多视角权重实现；部署目录没有可用的 Git HEAD 元数据，节点提交版本未确定。模型记录使用实际工作流名称，不声称锁定了权重仓库修订号。

- 模型：`microsoft/TRELLIS.2-4B`
- 节点：`Trellis2MeshWithVoxelMultiViewGenerator`
- 单个候选 seed：`91353`
- pipeline：`1024_cascade`，结构分辨率 `64`
- 结构 / 形状 / 纹理采样：`16 / 32 / 24`
- 纹理导出：`4096`，母版目标 `500000` 面（不是实际面数结论）
- `fill_holes=false`，`keep_only_shell=false`
- prompt_id：`bcea3ba1-0c17-41bd-aefc-7d2cd5dc173c`

`generate.py submit` 提交此候选；已有回执时不重复提交。`status` 读取生成任务状态；`fetch` 只下载本次输出，不触发渲染、游戏或验收。

## 交付层级

输出位于 `seed_91353/`。`raw_00001_.glb` 为原始几何，`textured_master_00001_.glb` 为带纹理母版。原始与纹理导出走不同导出节点，原始节点保留工作流的 90 度重定向设置；不要假定两者坐标未经变换即可相互覆盖。

`make_editable.py` 仅把带纹理 GLB 导入 Blender，保留网格、UV、法线、材质和生成坐标，另存打包纹理的 `Suppressor_5080_Candidate_Editable.blend`，并将模型原带贴图另存 `Textures/`。不添加摄影机、渲染、重建或减面。

当前为候选母版阶段；用户尚未选中。游戏低模、烘焙、目标枪型连接面、UE 导入和运行引用属于选型之后的接入阶段，本轮未执行，不替换现有枪械资产。

按用户全局规则，本轮不主动检查、测试、验收或制作验收渲染。完成状态以本轮实际生成历史与制作回执记录，未测试，交由用户测试。

## 用户后续要求图片参考

用户随后明确要求“发图给我参考”。`render_preview.py` 已使用候选 Blender 源制作 `seed_91353/Preview/side.png` 和 `angle.png` 两张实模图片，保留源几何、UV 和材质。仅临时添加拍摄相机与灯光，不覆盖作者 Blend。图片属于 Blender 源模型渲染，尚未进行 UE 接入或游戏测试。

用户进一步要求在原模型上优化粗糙斜纹，局部修整版位于 `KnurlRefinedV1/`。保留原筒身并重建尾部浅斜纹，独立交付 Blend、GLB 和同角度实模图片；具体制作范围见该目录 README。原始候选继续保留，未进行游戏测试。

## 后续游戏接入：战术消音器

用户已选用局部修整版并要求接入游戏。本次制作的四枪游戏网格、结构法线、安装适配、UE 材质/资产和枪匠图标位于 `GameIntegration/`，已接入 M4A1、AKM、QBZ-191、M1911。战术消音器属性为后坐力 -25%、稳定性 +25%、弹速 -20%、ADS 速度 -5%；原消音器调整为后坐力 -10%、稳定性 +10%、弹速 -15%，ADS 不变。上文“候选阶段”描述保留为早期制作历史，当前交付状态以 `GameIntegration/README.md` 为准。

必要编译已完成，UE 资产已保存；导入进程另外报告工程缺少 GameFeatureData 规则，详见接入说明。本轮未进行游戏测试或运行验收，交由用户测试。
