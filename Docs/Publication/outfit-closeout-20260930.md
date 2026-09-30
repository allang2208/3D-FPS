# 衣物、锁子甲与手臂续修：整理发布（2026-09-30）

用户反馈当前野行长袖“没什么问题了”，并授权将废案移入 trash、整理 SKILL 和推送 `allang2208/3D-FPS`。此反馈记录为当前版本认可；SVD 首次空仓色块先前未复现的历史记录仍如实保留，不把认可扩写为自动全武器回归。

## 当前状态和发布范围

- 野行长袖：全部 22 个第一人称绑定使用 `FieldSweaterNativeFamily20260930`，Body 使用 `FieldSweaterSurfaceRepair20260930`，专属身体覆盖为 `[0,1,3,4]`。本次提交配置的 22 条 FP 引用、原生袖身制作/导入/发布配方和 LOD 参数入口。
- 炭灰短袖：保留 `CharcoalGarmentRepair20260930/BodyV4`、`TraversalV2`、`PickupsV3` 及其余 `CharcoalCameraRepair20260930` 分支；发布现有制作源和依赖说明。
- 锁子甲：保留活动 `ChainmailCameraClearance20260929` / InsetBinding 网格、CameraFade 材质、SVD 换弹臂链和法杖两段施法／攀爬隐藏修复；补齐该对话的制作配方、图标入口、诊断工具和记录。
- 本轮相关运行 C++ 已存在于当前 main 基线。没有为整理夹带其他任务的 C++、技能动作、工作台、冰墙、图标或地牢修改。

## 归档

已将 **247 个文件，约 647.78 MiB** 移入本机 `trash/outfit-closeout-20260930/`。没有永久删除。原路径、目标、大小、SHA-256、替代来源及移动后散列见 [归档清单](OutfitCloseout20260930/archive-manifest.json)。

包括失败的通用长袖作者输出/保存快照、退役发布入口、炭灰 Body/BodyV2/BodyV3/Traversal 和 Pickups/PickupsV2 候选、旧装备图标备份、已经执行完毕的分批/结束游玩包装脚本、过程日志与 Python 字节码缓存。12 个旧 UE 包在 Asset Registry 中没有候选集合外的硬引用、软引用或管理引用，当前装备/物品目录也不指向它们。

以下旧文件**仍是制作依赖，保留原位**：

- `FieldSweaterCameraRepair20260930/Before/*/skin.json` 与 `paths.json` 是最新 capture 的原生采样缓存；`Authored/Traversal.json` 仍被历史 Body/Traversal 作者入口读取。
- `Content/.../FieldSweaterCameraRepair20260930` 的旧衣袖以及旧 SurfaceRepair Traversal 仍是当前已保存安装/来源散列的输入。虽然已退出活动装备引用，不能在未拆除制作依赖时当作可移动废案。
- `FieldSweaterKnit20260929` 的材料、高模、完整衣身与展示源；ChainmailInterlace/Relief/SharedSway/InsetBinding 链；SVD 和法杖原生绑定、密集动作、可编辑 Blend；新候选的 Before 和导入回执。

归档脚本先解析并限定工作区内的绝对路径，再读取源散列；UE 包须可独占读取，移动使用原生 PowerShell `Move-Item -LiteralPath`，目标读回散列一致。无关闭或重启他人编辑器，无跨对话协调消息。

## 公开和本机恢复边界

公开 Git 只包含本轮源代码/制作脚本、装备引用、说明、归档散列与 SKILL。每个新作者目录的 `.gitignore` 只放行脚本和说明；原生顶点/权重、动作采样 JSON、导入回执、贴图、Blend/FBX、UE 包及 trash 实体留本机，不以 JSON 扩展名规避素材再分发限制。

恢复完整工程需恢复 `Content/Characters/ModularOutfit20260924`、对应原生枪械/手模/动作、`Content/ColdSteelData/Icons` 与上述作者输入。Git 克隆不能单独恢复完整游戏视觉。已归档文件按清单回到原路径后可追溯旧方案，不直接重跑旧 publisher 覆盖当前绑定。

## SKILL 与检查边界

个人及项目 `ue5-fps-arms-animation` 同步沉淀：跨绑定从实际原生表面重建、骨骼影响判侧、内外层/接缝共用字段、开口只接厚度、连续肘部 UV、按预算保护近景 LOD，以及按衣缘重建 Body 可见皮肤。案例数据留在项目文档，避免把本轮面数和距离写成全装备固定规则。

本轮仅执行用户要求的引用/归档散列、仓库差异、脚本语法、敏感信息、公开许可边界与远端历史检查。不重新运行游戏、渲染、动作或性能测试，也不重新构建运行 C++。
