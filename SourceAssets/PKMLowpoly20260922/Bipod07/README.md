# PKM 脚架、左手托握与 QBZ-191 金属表面

2026-09-22，按本轮用户请求制作。Refinement06 的左手位置和外观未获用户认可，本轮替换它们。

## 改动

- 从原始模型拆出 65、72、127、128、129 五个分件（脚架夹座、销轴、两腿及卡扣），导出独立 `Exports/SM_PKM_Bipod.fbx`；枪身 FBX 不再包含这些网格。
- 改造目录 `ue_pkm_lowpoly` 的 `underbarrel` 提供“无脚架”与 `pkm_bipod`（PKM 折叠脚架）。缺省为无脚架。沿用现有装配 JSON、存档、图标、枪匠预览及掉落外观的组件复制机制。当前仅收拢外观，没有新增展开/架枪动作和属性增益。
- 组件挂在 `WPN_root`，FBX 保留枪身 component bind 坐标，运行时抵消一次根骨参考变换，避免轴向重复变换；切枪销毁旧组件。
- 左手采用既有 VRE 整手抓握的 80% 闭合母版，改到机匣前下方。整体移动枪体并调整左肩肘来向，保持骨长、手指局部位置和缩放；不再将逐指目标拉到机匣上缘。普通/空仓换弹的离握、回握接到新手型，其他动作从更新后的 idle 制作。
- 当前 QBZ-191 材质来自 `/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny` 实际材质槽。直接复制其 Unified Body / Steel UE 材质图，保留涂层颜色遮罩、粗糙度、金属度及法线连接；替换为在 PKM 自有 UV 上重新烘焙的底色、ORM、法线。Body 4096，Steel 1024；未把 QBZ 整枪文字/接缝图案贴到 PKM。
- 枪身、枪管、脚架、弹箱为统一深灰金属；木制枪托/提把、聚合物后握把及弹药原有分区保留。材质替换不会自动增加原模型的轮廓细节。
- 保留 RestFix05 的机械骨参考轴修复及 Refinement06 的弹链烘焙动力学。普通换弹 6.5 秒，空仓 7.5 秒，其他业务时序不变。

## 文件

- `PKM_Gameplay_Editable.blend`：完整可编辑源，含隐藏的独立脚架；脚架源仍随枪根骨运动。
- `PKM_Manny_Reload_Editable.blend`：手臂与换弹作者源。
- `Exports/`：枪体、独立脚架和 12 个动作 FBX。
- `qbz_live_materials.json`：本轮实际读取的 QBZ 材质路径。
- `surface_manifest.json`、`surface_import.json`、`mesh_reimport.json`、`bipod_import.json`、`motion_import.json`：制作及导入保存记录。
- `PKM_07_NoBipod.png`、`PKM_07_WithBipod.png`、`PKM_07_IdleGrip.png`、`PKM_07_GripUnderside.png`、`PKM_07_MetalClose.png`：用户要求的 Blender 源模型渲染。不是游戏实测截图；手臂在 Blender 使用作者源材质，UE 沿用现用 Manny 材质。

## 制作入口

`author_reload.py` → `author_gameplay.py` → `render_delivery.py`；只迭代动作时使用 `refresh_motion.py` 复用本轮已烘焙表面。UE 使用项目桥调用 `integrate.py`，需要原生构建使脚架组件逻辑生效。

许可沿用根目录 `SOURCE.md`；抓握母版来源记录见 `SourceAssets/MannyGraspDonor20260912/README.md`。未调用 Meshy 或其他收费生成服务。

## 状态

模型、材质、独立脚架和最终 12 个动作均已导入保存，用户要求的渲染已完成。常规 Editor 目标构建成功，记录为 `Saved/pkm07-native-build.log`（`Result: Succeeded`；底层日志 `Saved/BuildEditor/build-20260922-153812.log`）。最终动作导入记录为 `Saved/pkm07-import-motion-final-01.txt` 与 `integration_complete.json`。未启动 PIE、未执行游戏测试，交由用户测试。
