# 皮肤巨手三视图

2026-09-26。用户指定 Meshy 模型管线，拓扑完成后由本地制作专用手部骨架和蒙皮；本页保留三视图阶段记录。后续用户要求开始出模型，已使用绿色 V02 制作首版模型、四边面拓扑与本地绑定，最新产物见 `../README.md`。

## 当前候选 V02：绿色皮肤

用户要求改为绿色皮肤，并参考现有突变体皮肤材料。

- 图片：`FleshHand_ThreeViews_v02_Green.png`。保留 V01 的手型与掌面正视、侧视、手背后视布局，改为低饱和灰苔绿色皮肤。
- 生成方式：内置 `imagegen` 编辑 V01；完整提示词：`FleshHand_ThreeViews_v02_Green.prompt.txt`。
- 第二张图像参考：`D:/FPS3D/FPSGAME/SourceAssets/MonsterStyleV1/mutant/Textures/T_StyleV1_mutant_Mesh0_0_BaseColor.png`。只借鉴其中的皮肤斑驳与肤色，不复制其 UV、衣物或身体结构。
- 材料依据：`Docs/Monsters/Mutant3FeralPublication20260923.md`、`SourceAssets/Mutant3SurfacePolish20260923/install_surface.py` 与 `installation.json`。现行记录中的 `MI_Mutant3_SurfacePolish` 使用共享母材质 `M_InfectedSurface_V1`，其四张专用纹理由 StyleV1 源纹理复制；因此上述 BaseColor 是当前表面制作链中的源图，不把旧 StyleV1 材质实例当作当前实例。
- 表面方向：绿色斑驳干皮、掌纹/指节深浅变化、细皮纹与局部克制的湿润反光。当前图片是视觉参考，尚未制作巨手自身的 PBR 贴图或 UE 材质。
- 内置输出原件：`C:/Users/allan/.codex/generated_images/01a0dd38-87b0-7fe2-9faa-cbfdf463529e/exec-753cf9e4-54e9-49c4-8f18-8bf3f07d34cf.png`，已复制到本目录并保留原件。
- 本轮读取现有制作资料与贴图并生成用户要求的三视图修订；未启动 UE、运行游戏或进行测试。未提交 Meshy 三维任务。

## 历史候选 V01

- 图片：`FleshHand_ThreeViews_v01.png`，从左到右为掌面正视、侧视、手背后视。作为造型候选，尚未获得本图认可或进行三维重建。
- 生成方式：内置 `imagegen`，使用本地原蝇手轮廓与手脑皮肤外观参考。
- 完整提示词：`FleshHand_ThreeViews_v01.prompt.txt`。
- 轮廓参考：`E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/enemies/flyhand/idle.png`。
- 皮肤/形体风格参考：`D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/surface_v07/Baked_check.png`；灰绿/灰褐配色沿当前 MonsterStyleV1 方案。
- 内置输出原件：`C:/Users/allan/.codex/generated_images/01a0dd38-87b0-7fe2-9faa-cbfdf463529e/exec-024a1b64-2a2f-45ca-ba6c-003bf73a2a36.png`，已复制到当前项目，保留原件。

三视图阶段没有调用 Meshy 三维任务。后续建模已将 V02 拆成独立单视图，输入保存在 `MeshyInputs/`，没有把整张拼图作为单个模型输入；已在四边面拓扑上制作本地专用手部绑定，没有调用人形自动绑骨。本页为三视图阶段记录；2026-09-27 已完成 UE 资产和游戏接入，最新状态见 `../README.md`。

密钥不写入本文件、提示词或版本库；后续 Meshy 调用只通过 `MESHY_API_KEY` 环境变量读取。
