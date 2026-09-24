# 裸皮感染犬 Meshy V2：口腔、动作与 UE 接入

2026-09-24，用户要求继续完成工作。本轮延续已保存的 Meshy 重拓扑与本地绑定，补齐攻击器官、动作和角色接入；没有重新抽取模型，也没有恢复被否决的旧狼皮肤或 Gallop V3。

## 制作源文件

- `InfectedDog_MeshyV2.blend`：四边面身体、独立下颌、口腔和骨架的可编辑母版。
- `InfectedDog_MeshyV2_Animated.blend`：包含 21 个已烘焙 Action 的动画母版。
- `SK_InfectedDog_MeshyV2.fbx`、`SK_InfectedDog_MeshyV2.glb`：绑定模型，皮肤/口腔/牙齿三材质槽。
- `Animations/*.fbx`：21 个目标骨架动作，含待机、走跑、左右转向、普通/奔跑/飞扑咬击、三向受击、嚎叫、卧下/休息/起身、睡眠和死亡。
- `Textures/`：原候选 PBR 纹理副本。Blender 文件包含打包纹理。
- `wolf_motion_sources.json`：从实际现役 WolfV1 动作及 WolfV2 BiteWeightShift 导出的世界空间源关键帧。
- `mouth_authoring.json`、`animation_authoring.json`、`installation.json`：分别记录本地制作、动画来源/参数和实际 UE 保存进度。最终引擎接入状态以 `installation.json.state` 为准。
- `Before/BP_InfectedDog.uasset` 与 `appearance_before.json`：本轮外观接入前的恢复点。

## 本轮制作

在 V1 的 39 骨上增加 `jaw` 和非变形兼容挂点 `Wolf_-Head`，共 41 骨。沿原模型口吻切开 89 点唇线，保留后部脸颊连接并平滑过渡下颌权重；补上颚内壁、下口腔、舌头以及 36 枚牙齿。口腔和牙齿由本地制作，不冒充 Meshy 原模型已带的内部结构。身体仍使用同一只 Meshy 裸皮犬，没有隐藏或替换成另一张脸。

通过旧狼实际权重位置确认 `Wolf_-Ponytail1` 覆盖下口吻后，采用其动作时序驱动新下颌；新模型的闭口参考与源动作闭合角校准，最大张口暂限 42 度。不是依据骨名直接猜下颌。

动作以每秒 60 帧重定向：在新参考姿态上应用源世界旋转差值，使用新体型的骨盆高度、1.06 倍前后步幅，以及保留后跗关节的腿链求解。四足接触点以新脚掌参考位置为基准；保留源时长、动作顺序和原伤害窗口。耳朵随头部继承，没有用通用正弦摆动替代源动作。

原 WolfV1 Run/RunTurnLeft/RunTurnRight 继续作为动作来源；WolfV2 BiteWeightShift 继续作为普通咬击来源。生成的新动作属于该裸皮犬自身的骨架，不与原 Wolf Skeleton 强行共用。

## UE 接入设计

目标资源目录为 `/Game/Monsters/InfectedDog/MeshyV2`，沿用正式入口 `/Game/Monsters/InfectedDog/BP_InfectedDog` 和 F6 稳定 ID `InfectedDog`。

皮肤使用 Meshy 基础色、法线和粗糙度，增加轻量 Subsurface Profile；法线按 glTF/OpenGL 来源在 UE 翻转绿色通道，皮肤设为非金属且不接入发光贴图。口腔和牙齿各用独立材质。纹理继续流送，颜色/法线最大 4K、粗糙度最大 2K。

新目标骨架生成自己的 PhysicsAsset，供现有受击查询和死亡布娃娃使用；不借用旧狼骨名不兼容的碰撞体。LOD0 保留近景模型，另制作约 45% 和 16% 三角面预算的两级远距 LOD。降低的是远景网格预算，没有修改全局光照或纹理池。

复制现有 AnimationSet 的完整动作合同，只替换各槽为新骨架动作，并以 1.06 步幅比例调整动画参考速度。角色追击速度、六维、感染三阶段比例、命中判定逻辑、存档/F6 身份均不因外观替换而重写。

## 完成与验收边界

制作、导入、保存与实际画面认可分别记录。按用户规则，本轮不启动交互 UE 编辑器，不运行 PIE、游戏测试、动作预览或验收渲染。`installation.json` 的保存结果不代表已验证没有穿模、足滑或布娃娃问题，视觉和实机表现由用户测试。

生产入口：

1. `Tools/InfectedDog/export_meshy_animation_sources.py`：UE 后台导出动作输入。
2. `Tools/InfectedDog/complete_meshy_mouth.py`：Blender 后台制作下颌和口腔。
3. `Tools/InfectedDog/retarget_meshy_canine.py`：Blender 后台烘焙目标动作和 FBX。
4. `Tools/InfectedDog/install_meshy_completed.py`：UE 后台导入、生成 LOD/物理资产、保存并绑定正式入口。

## F6 不可见修复

2026-09-24 用户反馈生成成功但不可见，已确认 FBX 动画根缩放为 1、绑定根缩放约 100，导致模型随动画缩小 100 倍。`meshy_animation_units.py` 在 UE 导入后恢复丢失的容器单位转换，已接入上面的安装脚本；使用原 FBX 时须通过此安装流程导入。

全部 21 个动作已修复并保存，回执 `f6_scale_repair.json`，修复前动作包保存在 `BeforeF6RootScale/`。独立后台进程重新读取源数据和运行时压缩数据的起点/中点/终点，共 126 个采样，根缩放均与绑定一致。此项定位并消除了 1/100 缩小问题；未进行完整游戏或视觉验收。

## 后续奔跑覆盖记录

后续用户否定 Fox 跑姿，改用 GodotRunFitV2，并在反馈有所改善后继续细化为 [GodotRunNaturalV3](../GodotRunNaturalV3/README.md)。若重做全量安装，最后使用 `Tools/InfectedDog/install_godot_run_natural.py`；下文 Fox 接入仅为历史记录。

2026-09-25 用户认可 NaturalV3 为犬科奔跑基线，并继续要求升级攻击及狩猎 AI。重做全量安装时，在 NaturalV3 之后执行 `Tools/InfectedDog/install_hunting_upgrade.py` 保存狩猎参数；该脚本需要包含新字段的常规 Editor 构建。详情见 [狩猎升级记录](../../../Docs/Monsters/InfectedDogHunting20260925.md)。

2026-09-24 用户选择 Mesh2Motion Fox Run，只替换奔跑。当时感染犬的 Run / RunTurnLeft / RunTurnRight 改用单独保存的 FoxRunV1 动作，随后已被 GodotRunNaturalV3 替换，其他 CompletionV2 动作继续使用。来源、可编辑母版和实际保存回执见 本机 `trash/infected-dog-retired-20260925/SourceAssets/InfectedDogMeshy20260924/FoxRunV1/README.md`。

本目录保留原 21 动作基线；Fox 候选及专用安装脚本已归档，共用导入逻辑已提取为 `Tools/InfectedDog/install_canine_run.py`。日常调整奔跑使用当前独立奔跑安装入口，不执行全量模型安装。

2026-09-25：重建动作清单已独立保存为 `source_action_bindings.json`；导出器不再读取退役的 RealisticSkinV2。全量安装直接从现役 Wolf 动作合同创建数据集，缺失时创建 InfectedDog 原生类的 BP，不需要先安装旧换皮。
