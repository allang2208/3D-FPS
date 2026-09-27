# 近战检视、格挡与弓快速近战：整理与发布

2026-09-27。本次按用户要求整理本对话工作、沉淀 SKILL，并向
`https://github.com/allang2208/3D-FPS.git` 的 `main` 普通推送。
完整本机宿主仍为 `D:/FPS3D/FPSGAME`；源码发布与本机已保存资产分开记录。

## 当前保留版本

| 内容 | 本机最终入口 | 状态与边界 |
|---|---|---|
| 近战转刀 | `SourceAssets/RuneSword20260913/InspectFollowThroughV82/Final/` | V83 已按用户要求撤回，V82 保留较 V80 加速 25% 的转刀段，开发暂停 |
| 待机靠近身体与衔接 | `SourceAssets/SwordIdleClose20260926/` | 两套握柄动画已保存；源网格修复记录见 `source_grid_repair_receipt.json` |
| 格挡 | `SourceAssets/SwordGuardPalmPush20260926/` | V23 左手张掌抵剑，沿用 V22 画面平面的斜向横挡；两套三段正式动画已保存 |
| 格挡右臂入场 | `SourceAssets/SwordGuardRightStudy20260926/` | 只有针对性诊断与改善方案，尚未重做；不能表述为右臂僵硬已解决 |
| 弓快速近战 | `SourceAssets/BowQuickCombatRecover20260927/` | V7：左手持弓、右手张掌推击、自然腕部支撑与分步收手；240 Hz、源长 0.90 s |
| 弓速度与反馈 | `Source/FPSGAME/Weapons/Bow/BowQuickCombatMotion.h` | 本机约 0.571 s 空挥、0.606 s 命中；相机主冲量与余波同倍率控制 |
| 滑铲跳冲刺攻击惯性 | `Docs/Movement/dash-attack-slide-jump-inertia-20260927.md` | 本机实现及原生构建已完成，未游戏测试；运行代码有下述发布依赖 |
| 默认快速近战击退 | `Content/ColdSteelData/skills.json` → `quickCombat.knockbackCM` | 本对话将本机 50 cm 改为 100 cm，装备倍率仍单独结算。远端基线该字段本来就是 100，因此没有伪造数值差异或把其他技能平衡改动一起提交 |

弓正式动画仍是
`/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat`，
使用本机 `ContactV9/SK_Bow_BareArmsV7` 原生骨架派生。
V7 已于 2026-09-27 14:09 后台导入、压缩并保存；本次整理不重新导入。

## 归档与保留依赖

43 个已废弃文件（348.64 MiB）移入
`trash/melee-bow-iterations-20260927/`，移动前后 SHA-256 一致。
逐文件原路径、目标、大小、散列、原因和替代入口见
[归档清单](melee-bow-retired-20260927.json)。本机 trash 内同时保存清单。

- 归档 V83 完整作者目录、被撤回的两套包，V80/V81 的旧导出，以及 V1–V6 已被替代的弓导出。
- 归档已完成导入的一次性等待、结束 PIE、状态读取脚本、V81 一次性保存助手与过期 pending-save 标记。
- V83 的 `BeforeV83` 是历史 V82 回退副本，随废案一起可恢复地存入 trash；当前 V82 正式包与 `Final/` 不动。
- V22 格挡后台入口移除了已经完成的一次性 Inspect 回退分支，后续格挡制作不会隐式重装转刀。
- 保留所有当前 Blend、原包回退备份、密集拟合输入，以及 V4/V5 抓握与张掌关键对照；旧日期不构成废案理由。

弓当前制作链：V7 `author_recover.py` 读取 V6 定义并打开 V6 Blend；
V6 读取 V5 定义并打开 V5 Blend；V5 读取 V4 `generated_contact_v4.py`、
V4 `contact-fit.json` 与自身 `palm-fit.json`。V4 共用定义还读取
`BowSightContact20260926/generated_actions.py` 和
`Bow_SupportClearanceV11.blend`、原生手模/弓几何输入。
重新拟合 V5 还需要 V4 `contact-envelope.npz`。
V4/V3/V2 生成器分别读取上一版本的生成脚本，V1 为原始入口。
这些脚本和数据没有因旧导出被归档而删除。

剑 V80/V81/V82 共用 `InspectForwardSpinV54/spin_design.py`、
`InspectGripArcV46/inspect_arm_roll.py`、`RuneSwordWristLocked20260920`
作者解算与两套原生 Blend。V82 导入后的 Idle 接合还依赖
`SwordIdleClose20260926`；历史导入器还使用 V81 保存回执作基线闸门，不能在当前 V82 上直接盲跑。重导优先使用 V82 的完整 `Final`，不要使用旧目录的历史 Inspect 导出。

## Git 范围与并行运行依赖

公开本对话的作者/导入脚本、文字说明、归档清单、独立时间参数头文件，
以及能独立拆分的待机衔接代码：当前姿态捕获、格挡受击短混合、
普通起手与提前释放的接触窗口上限。个人 SKILL 和工程镜像同步更新。

以下本机运行改动与其他任务的未发布接口混合，保留工作区，不打包成一个
看似完整却缺接口的 main 版本，也不代为提交其他任务：

| 保留在工作区的内容 | 尚未一起发布的依赖 |
|---|---|
| `BowWeaponComponent.cpp/.h` 的快速近战入口、加载、采样、探针及姿态层 | 同文件未发布的 ADS/搭箭/移动姿态，以及角色动作优先级接口 |
| `FPSQuickCombatComponent.cpp/.h` 的弓分支、重定时与反馈 | 技能动作占用时钟 `CommitQuickCombatCast(Duration)` / `UpdateQuickCombatAction`，及其他任务的技能平衡改动 |
| `ColdSteelSkillModel.cpp` 的弓动作路由 | 同一技能模型中的未发布优先级、体力与冷却调整 |
| `FPSMeleeLungeMovement.cpp`、`FPSCharacterMovementComponent.cpp/.h`、`RuneSwordDashAttack.cpp` 的惯性链 | 未发布的角色移动锁定接口与空中冲刺就绪/释放逻辑 |
| 剑快速近战专用混合时长限制 | 未发布的 `RuneSwordPommelRhythm::QuickCombatTime` 节奏层；其余独立衔接修复已拆出 |
| `skills.json` 的本机快速近战说明与其余平衡字段 | 其他任务的完整无冷却/体力调整；本对话要求的击退 100 cm 已与远端基线一致 |

本机这些代码与已构建模块均保留。后续发布依赖方时，再精确提交对应运行
改动；不要用 main 覆盖完整本机工程。当前公开源码克隆不代表本机这整套
最终运行行为已经全部可重建。

## 合法素材与恢复

本批仅发布配方源码与文档；授权骨架/蒙皮/原生姿态、密集变换 JSON、
接触网格 NPZ、FBX、Blend、UE 包、截图、日志和导入回执均留在本机。
这些是资源恢复依赖，不是无条件可再分发素材。恢复需使用已合法取得的
原生手模、符文剑/长柄动画、V7 裸手及暗纹猎弓本机资产与作者输入，
见 [AssetSetup](../AssetSetup.md)。仅克隆 Git 不含这些输入，不能称为完整资产备份。

## 本次检查边界

仅执行用户要求的仓库整理与推送检查：精确暂存、差异/依赖范围、公开文件
许可与敏感信息、文本与脚本语法、归档散列和远端提交读回。
不启动 UE、不重新构建或导入、不运行游戏、动画测试、渲染或验收。
既有制作文档里的构建、保存和离线测量是历史记录，游戏手感交由用户测试。
