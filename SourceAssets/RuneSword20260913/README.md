# 双手符文剑 · 当前作者入口

本目录保存 2026-09-13 至 09-14 的符文剑制作资料。当前宿主为 `D:/FPS3D/FPSGAME`，物品 ID 为 `ue_rune_sword`，UE 内容目录为 `/Game/Weapons/AzureRunesword20260913`。

**用户已接受普通斩击、重击、第三段突刺及其一米跨步和范围扩大；格挡姿态 V18/V19 仍未满意，2026-09-14 暂停。当前 GuardPoseV19 是下次继续的版本，不是成功格挡母版。此次整理没有继续改动画或运行游戏测试。**

- [近战武器标准工作流](../../MELEE-WEAPON-WORKFLOW.md)
- [当前参数、接受状态与继续入口](../../Docs/Weapons/runesword-baseline-20260914.md)
- [本轮归档与公开发布边界](../../Docs/Weapons/melee-publication-20260914.md)
- [归档清单：路径、原因、替代物与 SHA-256](../../Docs/Weapons/runesword-archive-20260914.json)

## 作者依赖

完整作者源和 UE 二进制留本机。保留的主要依赖顺序是：

`WeightLeftV5 → DiagonalHeavyV6 → CompactRecoveryV8 → ChargedHeavyV12 → StrideThrustV16 → GuardParryV18 → GuardPoseV19`

V5 读取原始剑与当前 Manny/VRE 输入；V8 沿用 V6 空间轨迹，V12 增加重击，V16 增加当前突刺，V18/V19 增加及改写格挡。早期 ReachSweepV2 / WristRiftV3 / CompactNaturalV4 保留材质、握姿来源和失败对照；V3 的读取脚本仍引用 V2，不能按版本号整批移除。

根目录 `build_sword.py` / `import_sword.py` 是初始资产制作入口，**不会自动生成当前全部动作**。各版本脚本可能覆盖相同 UE 资产路径，应按目标版本及作者依赖执行。完整本机工程继续开发不需要依次重跑旧导入器。V5 的 `ImportHost` 是后续导入器的本地依赖。

## 归档和历史材料

已退役 V7、V15、旧 Before/NativeBuildSnapshot、多余格挡读取中间件、Python 缓存及临时 GitHub 参考克隆移到本机 `trash/runesword-melee-superseded-20260914`。原首版 README 同时归档，避免旧双段循环和旧距离被误当成当前参数。

保留 V18、V19 的 Before 和 V18 当前原生模块快照，供暂停后继续与恢复。早期 README、制作回执和报告是带版本的历史记录；其中 Before、快照等旧路径按归档清单恢复，不表示文件仍在原位，也不表示本轮重新检查通过。

## 来源和公开范围

用户指定的 Meshy Azure Starblade 模型、Manny 手臂、抓握输入、贴图、声音、Blend/FBX/uasset 和密集骨骼数据留本机。各类资产分别遵守来源许可，不能用单手参考动画的 CC0 覆盖其他资产。[Reference 说明](Reference/README.md) 和随附 LICENSE/COMMIT 保留来源记录。

Git 仅发布本轮选定的作者代码、参数说明、文档与技能；公开快照需要自行准备已授权输入。本轮没有发布与其他开发交叉的近战原生运行集成，不能仅凭这些作者脚本得到完整可运行的符文剑。
