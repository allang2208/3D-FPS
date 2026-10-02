# 左拳撞门作者动作（2026-10-02，当前 V10）

当前 revision `2026100211`：左拳举起护在身前，保持 **0.30 秒**，直接恢复当前持械或空手动作。没有向前推搡、制动或回弹。`author_motion.py` 读取 `GuardWristThumbV8_20261002/authored-guard.json::Prepare` 的完整 27 骨姿态；空手首末帧示例来自 `SourceAssets/UnarmedLocomotion20261001/full-pose.json`。手型最初复用项目现有 `StaffQuickCombat20261001::Ready`，照片位于 `GuardPoseV4_20261002/Reference/`。

入场 0.06 秒；保持至 0.36 秒，成功开门、用户音效及屏幕抖动共用该事件；恢复 0.197 秒，总长 0.557 秒。当前保持段仅平移锁骨根，整臂跟随，子骨局部旋转与骨长保留：

| 时间（秒） | 侧向 Y（cm） | 上下 Z（cm） |
| --- | ---: | ---: |
| 0.060 | 0 | 0 |
| 0.135 | +0.56 | +0.20 |
| 0.210 | +0.08 | +0.40 |
| 0.285 | -0.32 | +0.16 |
| 0.360 | 0 | 0 |

`save_editable.py` 已保存 `DoorPush_LeftFist_V7_20261002.blend`，take `A_DoorPush_LeftFist_V7_20261002_GuardV10Sway300msRecover`，1000 Hz、558 帧。`full-pose.json` 与生成头 `Source/FPSGAME/Movement/DoorPushAuthored20261002.h` 同源；运行直接消费头文件，不需新增 AnimSequence。游戏入场捕获实际左链，恢复目标持续采样，不使用作者示例末帧强制回位。

`GuardWristThumbV8_20261002` 保留拇指与腕掌权重制作来源；其 `BeforeAuthored/full-pose.json` 仍是重制作输入，不能删除。`ThumbSurfaceContactV9_20261002` 保留当前拇指材质配方；`UserAudio20261002` 保留用户完整音频和导入配方。M16、ASH-12 的完整作者链适配及弓的空间交接见对应 Gameplay／Weapons 文档。

已否定的早期推搡、0.5 秒版本和外网候选音效归档到 `trash/fps-arms-door-20261002/`，原路径及 SHA-256 见 [归档清单](../FPSArmsPublication20261002/archive-manifest.json)。归档脚本仅保留历史，不直接执行。原生绑定、生成的密集姿态头、实际 Blend／WAV／UE 资产和局部回退快照继续留在本机，不随公开源码发布；公开脚本须配合合法本机输入生成所需动作表，恢复要求见 [资源恢复](../../Docs/AssetSetup.md)。

作者源、资产与必要 Game／Editor 构建已落盘。未启动 UE、游戏、试听或追加动作测试，交由用户自行测试；Git 发布检查不代表游戏视觉验收。
