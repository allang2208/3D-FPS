# M66 焚骸：用户 Meshy 绑定模型接入 V01

后续状态：已在 [LocomotionV02](../LocomotionV02/README.md) 完成待机、行走、左右转身、现有大体型导航和原蓝图升级，并实际构建/保存。下文保留 V01 模型绑定阶段的历史记录；原蓝图路径沿用，当前已不是静态角色。攻击、受伤、死亡和首领遭遇仍未制作。

2026-10-14。输入为用户已减面、已绑骨的 `C:/Users/allan/Downloads/Meshy_AI_Character_output (3).glb`，本次只完善背部绑定并导入项目，不重新生成或再次减面，不制作战斗与移动动画。

## 原件和制作结果

- 原件副本：`Inputs/M66_user_rig.glb`，SHA-256 `ff380884f2697701ade0fece19af671d464d06d106e288a092bf15e40cbe8840`。下载目录原件未改动。
- 源结构：74 根 SmartRig 骨骼、161,840 个导入顶点、197,023 个三角面、1 个材质槽；没有动画。GLB 的 UV/法线分界保留了重复位置的顶点，不进行焊接或重拓扑。
- 制作文件：`Authoring/M66_back_completed_v01.blend`。修订 GLB：`Export/M66_back_completed_v01.glb`。UE 输入：`Export/SK_M66_BackCompleted_V01.fbx`。
- 原始模型高约 1.7 m；按前一版设计统一缩放到 3.8 m。网格和骨架等比例缩放，UV、三角面、原有骨名、骨段方向及四肢结构保留。

## 背部绑定

原始主体没有零权重顶点，主要问题是后背大面积依附少数通用短骨、排热突起缺少独立骨链。原始绑定布局和后背分区数据保存在 `Records/source_structure.json` 与 `Records/back_fields.json`。

在原 74 根骨骼上新增 14 根，总共 88 根制作骨骼：

- 地面根骨 `M66_Root`；原根 `Bone_000` 改挂此骨，其余原有父子关系保留。
- `M66_BackAnchor`：胸部骨的后背支撑子骨。
- `M66_SacUpper_L/R`、`M66_SacLower_L/R`：四个背囊控制区。
- `M66_Vent_High/Rear/Front/Lateral_Base/Tip`：四组两段排热突起控制链。实物网格含三处高突起和一处较短的侧向突起，保留模型实际形态，不按概念图强删。

42,032 个背部相关顶点重新分配渐变权重，119,808 个顶点沿用原权重；背部 UV 接缝上的重合顶点统一权重但保留分裂网格，调整区最多 8 个骨影响。靠骨盆、肩和囊体边界平滑过渡；原前臂、手指和腿脚位于修订区之外。新增骨骼尚未制作呼吸、开腔或排热动画。

## 已保存到 UE

- `/Game/Monsters/IncineratorBossM66/RigV01/SK_M66_BackCompleted`
- 同目录的 `SK_M66_BackCompleted_Skeleton` 和 `SK_M66_BackCompleted_PhysicsAsset`
- `RigV01/Textures/`：原有 BaseColor、Normal、MetallicRoughness。法线按 OpenGL 源在 UE 翻转绿色通道；遮罩使用线性采样。
- `RigV01/Materials/M_M66_Body`：当前项目 Substrate 材质，沿用源 PBR 图，不另加未经制作的火焰特效。
- `/Game/Monsters/IncineratorBossM66/BP_M66RigPreview`：可放入关卡的静态模型绑定蓝图，3.8 m 高，双足落地基准，角色胶囊半高 190 cm、半径 90 cm。开启 Actor/移动复制，不启用 AI 或攻击。

真实保存回执为 `Records/ue_import.json`，本次通过现有编辑器连接导入，没有主动启动编辑器。物理资产为导入器生成的基础形体，尚未制作专用死亡布娃娃。

F6 目录已加入 `IncineratorBossM66Rig`，显示为“焚骸 M-66（模型绑定）”；打包目录已加入 `DefaultGame.ini`。用户保存关闭编辑器后，等待既有后台构建和资产导入结束再执行必要 Editor 构建。首轮遇到并行法术书模块调用受保护接口的编译错误；该文件随后已有公开接口修订，本任务未覆盖它。最终 `Saved/BuildEditor/build-20261014-172716.log` 返回 `Result: Succeeded`、目标已是最新，基础 DLL 已落盘。记录为 `Records/build_completion.json`。未启动编辑器或游戏进行验收。

## 重建入口

1. Blender 后台运行 `read_source.py` 保存原件与源场景；`map_back.py` 读取用于绑骨的几何分区。
2. 运行 `complete_back_rig.py`，从原始场景重建局部绑定、提取贴图并导出 FBX/GLB；不覆盖下载原件。
3. 通过工程桥 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript <import_to_ue.py 绝对路径>` 导入并保存。这份导入脚本会复用已保存资产，不默默重导入覆盖；后续修订需要新版本或明确重导入范围。

未启动游戏、播放测试动作、进行联机测试或生成验收渲染，变形效果由用户后续测试。本次不是完整首领行为交付，也未接入焚化区遭遇。
