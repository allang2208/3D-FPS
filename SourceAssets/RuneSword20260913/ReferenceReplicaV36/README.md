# V36：指定视频 76–78 秒动作重建

2026-09-15，用户恢复制作，指定唯一主参考为 [BV1hCJFzQEyR 的 1:16–1:18](https://www.bilibili.com/video/BV1hCJFzQEyR/)，要求逐帧拆解并复刻。

**母版状态：用户评价本版整体方向正确、约 80%，并在 V37/V38 失败后要求恢复。随后明确要求保持本版内部动作，将手与剑共同转向、衔接自然无停顿；当前接入 [V42](../OffscreenLeftInspectV42/README.md)，沿用共同转向、前移及 V41 上臂修正，移除检视中途左手入镜动作；此版未测试。本版原文件保持原样，继续作为母版与恢复来源。**

恢复入口为 `restore_v36.py`；读取 `../ShoulderOutsideInspectV37/Before/A_RuneSword_Inspect.uasset` 中的原 V36 文件。替换前的 V38 及恢复回执保存在 `Before/RestoreFromV38/`。

## 动作与文件

| 内容 | 交付 |
| --- | --- |
| 逐帧拆解 | [frame_breakdown.md](frame_breakdown.md)，30 fps，包含 76.000 与 78.000 两端共 61 帧 |
| 实际参考帧 | `Reference/source_007.png` 至 `source_067.png`；`frames_01.jpg` 至 `frames_08.jpg` 包含前后各约 0.2 秒上下文 |
| 可编辑源 | [AzureRunesword_ReferenceReplicaV36.blend](AzureRunesword_ReferenceReplicaV36.blend) |
| 两秒参考 Action | `A_RuneSword_Reference_76_78`，场景 120 fps，帧 0–240；原生姿态每 4 帧一组 |
| 两秒参考 FBX | [Export/A_RuneSword_Reference_76_78.fbx](Export/A_RuneSword_Reference_76_78.fbx) |
| 游戏检视 FBX | [Export/A_RuneSword_Inspect.fbx](Export/A_RuneSword_Inspect.fbx)，2.90 秒，120 Hz |
| 游戏资源 | `/Game/Weapons/AzureRunesword20260913/A_RuneSword_Inspect` |
| 引擎参考资源 | `/Game/Weapons/AzureRunesword20260913/ReferenceReplicaV36/A_RuneSword_Reference_76_78` |

检视时间映射：0.00–0.35 秒从原待机进入；0.35–2.35 秒对应视频 76.00–78.00 秒；2.35–2.90 秒回到原双手待机。两秒参考段保持原速，进入/退出不是参考视频内容。现有 `URuneSwordComponent::BeginInspect` 读取动画自身时长，仍不乘攻速、不提交攻击命中。

## 本轮制作方法

1. 读取原视频 30 fps 原生帧，未使用插帧或生成的参考图。观察到快速换握集中在 76.0–76.3 秒，后续为闭握侧持、左手短暂入镜和下放收势。
2. 快速段每帧分别记录腕部、掌部、护手、柄尾和可见指尖；闭握段按本机 OpenCV 跟踪已指定的柄尾、拳部与拇指纹理。模糊的关节中心、画外端点和深度在数据中明确为估计或重建。
3. 用这些画面位置制作每帧手掌/武器变换，逐根手指的屈曲、展开及拇指让位有独立帧参数。可见指尖参与姿态拟合；骨长、局部关节位置和蒙皮保持原模型。
4. 完整闭握段使用原已保留整手握持关系。松握段分别处理手与剑；前臂采用独立随动，肩臂衔接沿用 V21/V22 完整骨段经验，不采样任何 V24–V35 Inspect 轨道。
5. 作者模型来自 V23 的完整源，读取其装备结束姿态作为原待机；仅导出、导入新检视与参考 Action。V21 格挡、V22 蓄力、V23 装备和其他剑的资源未在本轮替换。

## 可编辑输入与重建入口

- `reference_annotations.json`：逐帧画面位置、遮挡标记、独立手指设姿和参考帧对应。
- `reference_poses.json`：由观察数据制作的 61 组手、剑和指骨局部变换；不是从原游戏提取的骨骼数据。
- `authoring_inputs.json`：现有 Manny 与符文剑骨架、原握持和模型输入。
- `extract_reference.py` → `annotate_reference.py` → `read_authoring_inputs.py`（Blender）→ `fit_reference_pose.py` → `author_replica.py`（Blender）→ `run_import.ps1`。
- `authoring.json` 记录动作与时间映射；`import_receipt.json` 是导入保存回执，不是视觉验收。
- `Before/A_RuneSword_Inspect.uasset` 保存替换前的 V35 文件；本轮未运行归档里的旧导入脚本。

## 已知边界

这是使用当前 Manny 手模与符文剑，对单机位视频进行的动作重建。原视频 FOV 未知，作者相机采用项目当前 75° 垂直 FOV；视频与项目的手套、手指比例、剑柄和护手形状不同。手指遮挡、接触压力与深度无法由此视频唯一恢复。新的姿态拟合和独立帧数据不等于已解决全部穿模、腕部自然度或画面一致性。

按用户规则，本轮没有启动游戏、渲染新模型或追加动画验收。由用户在符文剑 F 键检视中测试。原视频帧、Manny、模型与二进制作者文件仅留已授权本机，未公开上传。
