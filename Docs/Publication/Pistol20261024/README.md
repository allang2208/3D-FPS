# 手枪制作与联机修复发布交接（2026-10-24）

本次为**部分源码发布**：可独立接入的枪械动画图基础、制作脚本、历史记录和 SKILL 已纳入本次提交；完整第三人称与弹药权威接入仍在本机工作区。下面的待接入补丁没有应用到公开运行模块，不能把本次 Git 推送当成完整手枪功能发布或新一次游戏验收。

## 本次直接发布

- `Source/FPSGAME/Weapons/` 下的 `FPSGunplayAnimInstance.cpp/.h`、`PistolDualAimNode.h`、`PitViper2011WeaponAssets.h`、`LonePistolTwoHandAssets.h`：瞄具对齐、动作独立握点和左主手资产路径等基础接口。角色调用方仍有未发布差量。
- `SourceAssets/` 下的 Pit Viper／五枪左主手作者脚本、Twinblast 重定向、选定 GitHub 单持源转换与独立绑定修复、六段换弹 FK 精修和保存脚本。脚本不是资产本体，也不代表新机器已完成导入。
- [动画源与接触](../../../skills/ue5-fps-arms-animation/references/pistol-third-person-source.md)、[弹药权威](../../../skills/ue5-save-load-replication/references/pistol-ammo-authority.md)、[检查夹具经验](../../../skills/ue5-debug-validation/references/multi-process-runtime-evidence.md)。个人技能与工程镜像仅同步本次新增内容。
- [归档清单](archive-manifest.json)、[源码及历史证据清单](manifest.json) 与以下待接入材料。

## 未直接接入的源码

公共基线为 `0b7aa07821123310ffa5e684f5f127d34178c9e9`。其中 `ColdSteelPlayerState.h` 已声明 `bool ApplyGuestProfile(..., bool bFromNetwork=false)`，但对应 `.cpp` 仍是 `void ApplyGuestProfile(const FColdSteelProfile&)`；头文件档案上传 RPC 已含 `SourcePawn`，实现与调用仍是旧参数。工作区中补齐这些接口的实现同时包含其他系统的未发布改动。本次没有为发布手枪而整文件带走这些内容。

| 文件 | 用途与边界 |
| --- | --- |
| [pending-new-files.patch](pending-new-files.patch) | 26 个本轮手枪专用源文件的新增补丁，包括完整源动作层、弹匣／左轮表现和权威／检查代码；需要共享类成员和调用方一起接入。 |
| [pending-authority-repair.patch](pending-authority-repair.patch) | 最后一轮真实补弹、取消和回执修复。基线是本机 `SourceAssets/PistolAuthorityRepair20261024/Before/` 的各文件，**不是公共 HEAD**。清单记录原始及换行归一后的 SHA256；已经排除同期弯刀改动。 |
| [pending-campfire-hooks.patch](pending-campfire-hooks.patch) | 对公共基线可定位的营火上行版本、断线结算钩子；仍依赖手枪权威成员。 |
| [pending-config.json](pending-config.json) | 当前 20 个 `DualPistol.*`／`SinglePistol.*` 角色、保存资产散列和必要 Cook 目录。消费者未完整发布，因此本次没有单独覆盖公共 `player_body.json`。 |
| `manifest.json/shared_files_retained_local` | 36 个共享消费者／诊断入口的本机文件散列。它们不是完整源码备份，且不表示全部差量已包含在上述补丁。 |

恢复接入时先发布获准的共享基线，再逐文件重放；必须同时带齐角色、双持执行器、身体动作层、弹道身份、档案所有上行入口与配置。不要直接对公共 HEAD 执行整包 `git apply`，不要把暂存用裁剪文件覆盖回真实工作区。诊断还依赖本机共享 `ShotgunAttachmentAuditCommandlet`／`ShotgunWireAudit`；本次不夹带其其他枪械功能。

## 资源与制作顺序

单持源为用户选择的 [ThirdPersonShooter-AnimationSets](https://github.com/ZenXChaos/ThirdPersonShooter-AnimationSets)，固定版本 `f19adc2ece4cab0f89c9236223abb97d4d2badea`，许可副本为 [UPSTREAM-LICENSE.txt](../../../SourceAssets/GitHubSinglePistol20261022/UPSTREAM-LICENSE.txt)。原 FBX、转换后骨架载体及密集姿态数据保留本机；脚本需 UE 配套 FBX SDK、NumPy 和项目作者工具。

双持使用用户已加入工程的 Paragon: Twinblast；Jason 身体、枪体和其派生动画沿用本地已许可内容。该批二进制、第三方插件和密集源轨道不公开再分发。按 [GitHub 制作记录](../../../SourceAssets/GitHubSinglePistol20261022/README.md) 与 [Twinblast 制作记录](../../../SourceAssets/DualPistolReference20261022/README.md) 恢复输入。

单持顺序为转换／导入 → 分离特殊绑定 → 重定向 → 初始角色发布 → `SinglePistolRefinement20261023/refine_source.py` → `save_refined.py`。后者发布最终六段换弹键；不要在它之后重跑初始 `GitHubSinglePistol20261022/publish.py` 覆盖精修结果。左主手第一人称生产输入仍保留原枪族与原生握点，不能用第三人称相机坐标替代。

## 废案归档

`trash/PistolPublication20261024/` 保存 50 个条目、216 个文件（91,783,171 字节）及 4 个目录链接。已验证原路径位于本次工程范围、无对应活动进程引用，并逐文件比对移动前后 SHA256。目录链接只搬迁链接，未遍历或移动目标资产。

包括失败／中断的 `RuntimeBuilt25`、`RuntimeBuilt27`、被替代的构建尝试、`wire-01/03/04` 及一次性等待脚本。原始历史记录中的路径不重写，凭归档清单查找新位置。保留 `RuntimeBuilt21/24/26/28`、最终 Editor 06／Game 08 构建、`authority-01/02`、关键失败 `wire-02` 和最终 `wire-05`，以及 `Before`、源资产与作者依赖。仍被调用的旧制作输入不按日期误判为废案。

## 证据边界

[弹药修复记录](../../Weapons/pistol-authority-repair-20261024.md) 中的 92 项隔离检查、36 个 UDP 场景和成功构建，都是本机完整工作区此前完成的结果。它们不证明本次裁剪后的公共提交可独立构建，也不覆盖完整档案心跳、同档重连、死亡／换图、专服、打包、公网或渲染观感。

本次只进行用户要求的归档、许可／差异／语法和推送检查；没有启动 UE、游戏或重新运行动作、联机测试。
