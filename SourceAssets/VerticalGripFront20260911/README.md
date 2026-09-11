# 垂直握把：横向收拢的拇指对握

本轮按用户最新要求，先完成 M4 与 AKM 的垂直握把。上一版把拇指沿手背向前伸出的理解已被用户拒绝，源汇总和报告保留在 `RejectedForwardThumb/`，不作为视觉接受结果。阻手器等小改造件后续采用用户参考图的握拳姿态整体包裹，允许内部穿模，不再以精确贴合配件表面作为阻碍。本次小配件运行路径恢复到之前的 Ergonomic 分支。

## 查看结果

- [M4 玩家视点三版比较](OpposedDelivery/M4_Player_Before_After.png)：原姿态、已拒绝的伸拇指、当前闭合对握。
- [M4 / AKM 正面近景](OpposedDelivery/M4_AKM_Player_Views.png)
- [M4 / AKM 腕肘近景](OpposedDelivery/M4_AKM_Wrist_Views.png)
- [M4 实机动作视频](OpposedDelivery/m4_vertical.mp4)、[AKM 实机动作视频](OpposedDelivery/akm_vertical.mp4)

图片均为实际 UE 渲染。近景使用玩家眼睛位置及 30° FOV，视线对准各自手腕/拇指的位置；因此不是完全固定朝向的像素配准图。视频按截图日志的实际时间间隔组装，为静音视觉证据。

## 修改方式

拇指根部沿用原动作的轴向朝向作为参考，受限摆向握把，分别弯曲 MCP / IP，让拇指横向收拢、弯向上部手指外侧。没有再用指尖最近距离迫使根部扭转，也没有把拇指向前伸直。四指待机局部旋转保持原值，保留原有并拢抓握。退握时先让拇指移开，再展开四指，随后混入原换弹动作。

前臂沿原动作肩肘关系重建支撑，保持骨长、缩放，分配前臂 twist。最终姿态的同 rig 腕轴指标记录在 `pose_quality.json`；该指标不等同于医学关节角，也不能替代实际画面。右手、枪根、机械轨道、原取弹/插入/拉栓主要接触段及业务时长保留。配件模型、数值和音效没有改变。

## 可编辑源与运行资产

| 枪 | 汇总源（9 个 Action） | UE 动画目录 |
| --- | --- | --- |
| M4 | [M4_vertical_Family_Editable.blend](m4/vertical/M4_vertical_Family_Editable.blend) | `/Game/Weapons/M4VerticalGripOpposed/Vertical` |
| AKM | [AKM_vertical_Family_Editable.blend](akm/vertical/AKM_vertical_Family_Editable.blend) | `/Game/Weapons/AKMIntegration/SovietFab/GripOpposed/vertical` |

各目录还包含 9 条单动作 Blend 和 FBX：idle、aim、fire、aim_fire、equip、reload、reload_empty、drum_reload、drum_reload_empty。总计 18 条动画，38 个本机可编辑/导出文件的大小与 SHA-256 见 [opposed_delivery_manifest.json](opposed_delivery_manifest.json)。

旧动画被正在打开的编辑器占用，因此本轮导入独立 Opposed 目录。新进程已用于实际检查；当前旧编辑器需要先保存工作，再重启，以加载新原生模块和新路径。

## 验证与限制

[opposed_acceptance.json](opposed_acceptance.json) 记录 18 条动画的骨架、时长、压缩读回，两个独立实机回归及采样结果。实机覆盖装配、移除、切枪、保存、ADS、射击、装备与四种换弹回握。源动作验证检查非目标骨骼、原主要换弹接触、局部位置和缩放。

1375 个手指/握把表面采样没有刚性配件交叉。待机、瞄准、装备的指间采样无交叉；退握/回握时拇指与食指有短暂表面交叠，已单独记录，并不宣称整个动作零自接触。原换弹动作还保留既有指间接触。额外拇指检查覆盖可见主枪身及工厂弹匣，不包含独立弹鼓网格；检查范围是采样时刻而非连续时间。

原生模块 `2026096304` 构建成功。导入与压缩读回脚本的 PASS、进程退出码及游戏运行分别记录；Commandlet 的已有 GameFeatureData 配置错误/HTTP 端口争用可导致退出码 1。前一次重建还遇到并行攀爬源文件尚未加入时的链接错误，在该源文件完成后重新构建成功，未修改攀爬功能。当前新姿态尚待用户视觉评价。

## 复现与公开边界

使用本轮最终本机 `fit_final.json`、`release_profile.json` 和 AKM 修正参数，运行 `build_m4.py -- vertical`，再运行 `build_akm.py -- vertical` 和 `refresh_release.py -- akm vertical`。`fit_opposed.py`、`fit_release_front.py`、`fit_akm_clearance.py`、`fit_akm_transition.py` 记录拟合过程；重新拟合需要重新检查视觉效果。`fit_front.py`、`prepare_build.py` 和 `build_all.ps1` 属于已拒绝的前伸拇指尝试，不是当前生产入口。

用 `run_opposed.ps1` 先导入两支枪全部 18 条动画、压缩读回，再分别运行两支枪（运行检查包含互相切枪）；`verify_assets.py` 读回当前 18 条动画。`check_geometry.py`、`check_thumb_gun.py`、`validate_m4.py`、`compare_source_self.py` 做相应测量；`assemble_editable.py` 汇总源动作，`make_opposed_delivery.py` 生成本轮交付。

`ReferenceWorkflow` 冻结前一轮作者逻辑；本机依赖包含已许可的 M4Infima/Manny、AKM 源模型和动作。原始资源、完整 pose 矩阵、FBX、Blend、UE 二进制、用户照片和媒体保留本机，不公开再分发。

Git 发布本轮作者逻辑、测量摘要、说明及 `runtime-integration.patch`。补丁针对本轮开始时的本机基线，包括垂直握把新路径、cook 目录与玩家视点近景。基线中的 AKM / ForegripAudit 框架仍含其他本机任务尚未统一发布的修改；该补丁不是完整远端 AKM 工程，应用前需核对 [integration_baseline_manifest.json](integration_baseline_manifest.json)。本机运行文件已直接修改并验证。
