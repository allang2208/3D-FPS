# 伏窥者 M-08：整理、源码发布与恢复（2026-10-05）

本次发布涵盖本对话完成的伏窥者模型制作配方、专用骨架／接触节点、墙面追击与跳跃、扑咬／空气炮、死亡支撑、预警和 AI 修复。推送目标为 `allang2208/3D-FPS` 的 `main`，遵守 `WORKFLOW.md` 第 8 节。没有再次运行游戏、动画验收或性能测试。

## 当前有效内容

| 范围 | 当前来源 | 保留的恢复输入 |
|---|---|---|
| 造型 | 背部 V02 连续贯通孔 | 用户 Meshy 原始 GLB、BackRebuildV01 的原始副本／孔壁贴图／编辑源、BackRebuildV02 |
| 骨架／皮肤 | CanineV03 的专用 70 骨与蒙皮 | ProductionV01 源、CanineRigV03 的骨表／皮肤源及本机 Quaternius 参考采样 |
| 基础动作／移动 | BoneheadV04 动作、M08 原生接触节点及 V08/V09 全身细调 | 骨表、原 FBX、V03 皮肤源；Bonehead MIT 文本与署名 |
| 飞扑／越障 | MotionV09 的 AttackPounce，PounceV05 的 TraverseJump | BoneheadV04、PounceV05、MotionV09 制作链 |
| 死亡前段 | DeathV10 接地动画 | MotionV09 完整源、死亡作者；后续尸体行为沿共享执行层 |
| 空气炮 | V07 蒙皮出口绑定、V11 1.5 s 蓄力／末 0.3 s 锁定预警 | AirCannonV06 的基础作者／弹体资源、RimSpeedV07 绑定、MotionV09 的修正姿态、AirWarningV11 |
| 追击 | PursuitV12 原生索敌／累计位移重规划／有界表面选路 | 原 AI 树、原蓝图；无新增资产导入 |

正式入口：`/Game/Monsters/LurkerM08/BP_LurkerM08` 和 `DA_M08_AnimationSet`，F6 ID 仍为 `LurkerM08`。移动 150／315／270 cm/s，飞扑速度系数 3；空气炮 48 物理、命中眩晕 3 s、冷却 20 s。模型与动画状态见 [制作记录](LurkerM08_20261004.md)。旧 V01/V03 动作曾被用户指出僵硬，保留恢复源不表示认可旧效果。

## 归档

45 份文件、374,334,880 字节已移至 `trash/lurker-m08-retired-20261005/`，包括前后结构冲突的三视图 V01 及提示词、旧蓝图／动作集备份、PreviousSource 源码快照、`.blend1` 上次保存和死亡接地点一次性定位文件。所有移动均限制在本次 M08 目录和对应 trash 目录，移动前后 SHA-256 一致；没有删除原始资源。

清单见 [归档清单](../Publication/LurkerM08_20261005/archive-manifest.json)，执行配方为 `Tools/Publication/archive_lurker_m08_20261005.ps1`。`Before`、`PreviousSource` 及 `before_references.json` 的旧说明指历史制作时的位置，现在按清单在 trash 恢复。

没有仅凭版本号清空旧目录：Back V01、Production V01、Canine V03、Pounce V05 和 Air V06 仍被后续作者或全量恢复入口读取。正式 `Content/Monsters/LurkerM08` 本轮不搬动，其历史导入包仍参与现有完整恢复链／骨架与材质依赖；不会在未重建该链时把中间版本资产误当成独立废案。

## 公开范围与许可

公开 M08 C++、必要的共享 Wolf／AI／F6 入口改动、原创 Blender/UE 作者和导入配方、少量建模参数、空气预警 HLSL、说明、归档元数据及两个技能参考。其余并行任务的未提交或已暂存内容不属于本次提交。

Meshy 原模型、用户概念图、生成图、Blender/FBX/GLB、贴图／音频、骨表与密集蒙皮／动作采样、UE 包、导入回执及日志保持本机。用户提供文件与本机可使用许可不自动构成公开再分发许可。Bonehead 两份参考代码和许可按 MIT 保留，见 [来源记录](../ThirdParty/Bonehead-M08.md)。Quaternius 供体采样不随此次公开 Git 分发。

## 恢复顺序

1. 在合法完整 UE 5.8.2 项目中恢复本机输入，尤其是原 Meshy GLB、当前皮肤／骨表、模型纹理、原共享四足模板、AI 树和 Quaternius 参考源。仅克隆公开 Git 不会获得上述二进制内容。
2. 制作链为 BackRebuildV01 → BackRebuildV02 → ProductionV01 → CanineRigV03 → BoneheadV04 → PounceV05 → AirCannonV06 → RimSpeedV07 → MotionV09 → DeathV10／AirWarningV11；使用各目录作者以及 `Tools/LurkerM08/author_*.py`。V09 会读取早期作者函数，不能提前删掉这些工具。
3. 按 `WORKFLOW.md` 在已有编译／编辑器释放后常规构建。全量安装入口 `Tools/LurkerM08/install_lurker.py` 依次恢复 V01、Traversal、Canine、Bonehead、Pounce、AirCannon、RimSpeed、MotionV09、DeathV10、AirWarningV11；不单跑旧阶段后把旧绑定当成最终版本。
4. 当前 V12 只需原生构建，原蓝图保持引用。动画根单位适配以匹配的源 FBX 散列为边界，仅在新导入时执行一次；不得对已修正动画重复乘根缩放。

## 构建与未测试边界

完整本机工作区 V09、V11、V12 常规构建已完成；V11 保存六个资产，V10 保存死亡动画和动作集。最新 V12 构建退出码 0，DLL 已链接落盘。这些是先前开发阶段的记录，不是本次公开提交重新运行的构建／游戏验收。当前源已保存和构建，不宣称 AI、穿插、墙面路线或性能已经通过用户测试。

本轮只做用户要求的仓库整理／推送检查：归档哈希、精确发布差异、大小／敏感内容／许可边界、远端及提交范围。检查回执留本机 `Saved/LurkerM08Publication20261005`，公开路径清单见 `Docs/Publication/LurkerM08_20261005/published-files.json`。
