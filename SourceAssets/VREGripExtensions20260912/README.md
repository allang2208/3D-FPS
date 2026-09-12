# 45° 侧倾握把与棱镜阻手器：VRE 抓握迁移

2026-09-12。沿用用户认可方向的 [垂直握把 VRE 手型](../MannyGraspDonor20260912/README.md)，更新 M4、AKM 的 45° 侧倾握把和棱镜阻手器，各 9 条动画，共 36 条。用户于 2026-09-12 明确确认“成功了”，并要求沉淀为配件标准。

## 预览与编辑

- [同视角源模型修改前后](Delivery/Source_Before_After.png)
- [四组实机抓握](Delivery/Runtime_Grips.png)、[玩家视点](Delivery/Player_Views.png)、[腕肘](Delivery/Wrist_Views.png)
- 实机动作：[M4 45°](Delivery/m4_canted.mp4)、[M4 阻手器](Delivery/m4_prism.mp4)、[AKM 45°](Delivery/akm_canted.mp4)、[AKM 阻手器](Delivery/akm_prism.mp4)
- 可编辑源：[M4 45°](Final/m4/canted/M4_canted_VRE_Editable.blend)、[M4 阻手器](Final/m4/prism/M4_prism_VRE_Editable.blend)、[AKM 45°](Final/akm/canted/AKM_canted_VRE_Editable.blend)、[AKM 阻手器](Final/akm/prism/AKM_prism_VRE_Editable.blend)。相同目录有各动作的 Blend / FBX。

视频按 UE 截图日志时间间隔组成，为无声视觉证据，并非原生 30 fps 录屏或音效同步验证。玩家近景使用真实眼睛位置、FOV 30，另有普通持枪 idle / ADS 画面。实机沿用共享工程当前材质；源模型保留较早的花纹手套。此次没有改手套网格、材质或配件模型。

## 制作与保留范围

抓握来源仍为 VRE `GrabAnimation`，固定提交 `bf4c7ba554ecbbe614ed3d16669ef53d3f888f09`，来源和许可见上方垂直握把记录。没有新增第三方模型。保持拇指横向弯向食指上方、四指成组包握，不重新逐指猜角度。

45° 握把采用 80% 原始闭合幅度，先随真实倾斜本体定握点，再围绕握点调整整只手，使其接近原持枪手臂来向。严格让手指排列轴跟随握把轴的试验造成了过大前臂扭转，已弃用；最终整手方向采用原腕部朝向 75% 的混合，手指内部关系不变。M4 / AKM 静态腕轴折角约 2.03° / 1.36°，相对骨架参考的前臂 twist 约 28.62° / 26.34°。这些是本骨架诊断量，不是通用人体限位或独立外观验收线。

棱镜阻手器采用 90% 原始闭合幅度，由整只手包住短件。按用户要求，允许该小件内部穿模；优先手型、虎口、四指和腕臂轮廓，不为逐指贴合反复改变指节。45° 握把仍有内部表面接触/交叠，不宣称零穿模。

动作包括 idle、aim、fire、aim_fire、equip、reload、reload_empty、drum_reload、drum_reload_empty。保留各枪原有时长、采样率、骨长、rest、手指局部位置、缩放、右手及枪械机械轨道；只替换左臂持握、退握和回握区间。主要取弹、插入、压实、枪机接触段保持。没有修改配件属性数值、尺寸、安装变换、既有垂直握把或共振前握把。

M4 保留普通/空仓弯匣 2.1 / 2.7 秒及原弹鼓时序；AKM 保留普通/空仓 3.333333 / 4.291667 秒及原弹鼓规则。AKM 第 42–270 / 42–380 帧接触段保留，330 / 440 帧回到配件握姿。四元数 q 与 -q 表示同一旋转，连续符号改变不作为接触破坏。

## 接入与验证

M4 动画为 `/Game/Weapons/M4VREGripExtensions/{Canted,Prism}`；AKM 为 `/Game/Weapons/AKMIntegration/SovietFab/GripVREExtensions/{canted,prism}`。实际引用在 `M4CantedForegrip.cpp`、`VerticalGripAnimationFamily.h`、`AKMAttachmentVisual.h`，M4 新目录已登记 Cook。

[验证摘要](Final/validation.json)、[源文件合同](Final/source_validation.json)、[UE 保存后回读](Final/asset_validation.json)、[交付文件散列](Final/delivery_manifest.json)。36 条源动画和 36 条 UE 保存后回读通过；Native `9122820` 编译成功。游戏回归用四个独立 profile，新进程验证实际新路径、改造应用/保存重载、瞄准/开火、装备、四种换弹、回握、拆卸及跨枪切换；详情及检查计数见摘要，按帧重复检查不是独立场景数。

几何检查覆盖每组合的待机、瞄准、装备、弯匣普通/空仓退握与回握采样，M4 每组 59 次、AKM 每组 71 次；记录握把和指间表面交叠，不能当连续碰撞证明。源接触段、UE 读回与实际外观分别判断。导入/读回脚本完成时 commandlet 仍以 1 退出，日志含既有 GameFeatureData、HTTP 端口等环境错误，不抹去退出码；新游戏进程退出结果另列。没有新增音效，不以静音视频证明音画同步。

## 复现与发布边界

`fit_static.py → build_family.py → verify_source.py → import_assets.py → verify_assets.py → assemble_editable.py → run.ps1 → make_delivery.py`。几何记录由 `check_geometry.py -- <m4|akm> <canted|prism>` 生成。使用 Blender 5.1.2、UE 5.8.2；Blender 使用 `--python-exit-code 1` 区分脚本失败与正常退出。

`fits.json`、`Static/` 是当前静态作者源；过度扭臂的 `strict_axis_trial.json` 已归档至 `trash/grasp-workflow-20260912/SourceAssets/VREGripExtensions20260912/`；`audit_canted_clock.py` 与 `canted_clock_audit.json` 保留诊断方法和结果，不是当前姿态。`case.py` 指向原 CantedGripMigration / VerticalGripErgonomic 动作，`ReferenceWorkflow` 冻结整臂和渲染辅助脚本。完整原动作、手模、材质、握把、VRE 动作矩阵及二进制留本机，公开作者脚本、验证摘要与来源；仅克隆此目录不能独立恢复整个素材工程。

[运行接入补丁](runtime-integration.patch) 对应本轮 `IntegrationBaseline`，本机已应用。共享接入文件含其他未提交工作，不整体夹带进此次源码发布。不要关闭未保存的编辑器或恢复旧 `.modules` 清单来覆盖其他构建；用户已打开的旧编辑器与本轮新测试进程分别记录。

2026-09-12 标准化与归档见 [本轮整理记录](../../Docs/Weapons/grasp-standard-20260912.md)。当前 Final、所需原动作、冻结参考和许可保留；明确废案按清单移入任务 trash。
