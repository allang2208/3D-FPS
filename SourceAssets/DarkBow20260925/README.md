# Dark Bow：当前作者源

当前表现是 **ContactV9**，共享 **ArmsV4** 原生 Skeleton 和装备。详细恢复及归档说明见 [V9 发布记录](../../Docs/Weapons/dark-bow-publication-v9-20260925.md)。本目录保留可重建当前结果的输入与关键失败对照，不能按版本号整体清空。

| 阶段 | 作者入口 | 本机输入／输出 |
| --- | --- | --- |
| 原弓与动作来源 | `Scripts/`，`ArmsV2/export_authoring_inputs.py` | 原 Fab dark bow、Paragon Sparrow；输出 `bow_surface.json`、`sparrow_motion.json` |
| 木箭与静态分件 | Blender `ArmsV2/author_arrow.py`，UE `ArmsV2/import_parts.py` | `WoodArrow_Editable.blend`、`Export/SM_Bow_WoodArrow.fbx`；保留原握把，只去除 124 个旧弦三角 |
| 正确参考骨架 | `ArmsV4/author_actions.py`、`import_assets.py`、`bind_outfits.py` | ArmsV4 可编辑源、FBX、Skeleton 与 Outfits；当前 V9 不另建 Skeleton |
| 左手完整抓握 | Blender `GripV5/read_grasp_reference.py`，Python `convert_grasp_reference.py` | 已认可 M4 VRE 源动作、原生 M4 骨架；输出 `grasp_reference.json`、`grasp_native.json` |
| 接触输入 | Blender `ContactV9/read_hand_authoring.py` | `reference_hand_frame.py` 仅定义参考手部空间，输出 `hand_authoring_input.json` |
| 掌面与右手拟合 | Python `ContactV9/fit_hand_contact.py`（NumPy/SciPy） | 输出 `bow_closed_surface.json`、`hand_contact.json`、`surface_repair.json` |
| 当前动画 | Blender `ContactV9/author_actions.py` | 新手模、八段动作、完整 `.blend`、FBX 与 `authoring.json` |
| UE 接入 | `ContactV9/import_assets.py` | 导入 ContactV9，使用现有 ArmsV4 Skeleton；保存九个资产并写回执 |

本机共同输入仍需 `SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/M4.json`、`BareArmsFamilyV6/Sources/M4.json`、`SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json`，以及 `SourceAssets/MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend` 和该脚本声明的握把坐标来源。

Blender 脚本用 `blender --background --python <脚本绝对路径>` 制作。UE 无既有进程时可用 `Scripts/run_headless.ps1`；已有编辑器时通过 `Tools/AssetPipeline/mcp_call_codex.ps1` 整批互斥执行。导入前指定自己的输出目录、对应导出位置和新回执；不要将本机旧回执复制到干净工程后直接跳过导入。

公开仓库仅保留制作脚本与文字。密集 JSON、Blend、FBX、导入包及第三方素材从本机或合法来源恢复，不能靠克隆重建。制作完成和保存回执不等于用户认可；本次未运行游戏测试。
