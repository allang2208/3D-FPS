# M870 整理与源码发布 · 2026-10-17

本次发布 M870 Tactical 的泵动玩法、UC 动作适配工具、当前握姿与 R3 快速近战、SUPER90 冲刺及快速装填适配、通用瞄具/前握把/后托、战术挂件、专属改造、图标与第三人称剔除，以及相关联机修复。SVCh、Saiga12K、步枪消音声音、战锤、天气、怪物与其他任务的并行修改留在工作区。

## 当前制作入口

| 内容 | 本机当前源 | 恢复注意 |
| --- | --- | --- |
| 枪体、材质与工作台装配 | `SourceAssets/M870Tactical20261015` | 保留原模型、UV、机械分件和独立来源归因 |
| UC 装备、射击、泵动及普通装填参考 | `M870UrbanAnimations20261015` | `draw` 已进入 `A_M870_equip`，源长 0.60 s，装备状态默认按约 0.72 s 播放；不要覆盖后续握姿 |
| 左手整手抓握、支撑 | `M870AKMGrip20261016` → `M870AKMArmSupport20261016` | 复用 AKM 已有手型，原生骨长；旧 SurfaceFit Blend 和 GripADS 工具前缀仍是活动前置 |
| 原始装填接触、腕臂 | `M870ReloadSource20261016` | 保留掌弹同源关系；较早 ReloadContact、ReloadWrist 的输入/工具仍参与继承链 |
| 右手扳机、最终基础左肘腕 | `M870TriggerGrip20261016` → `M870LeftArm20261016` | 最终基础 13 条动画、M870 私有表面；保留当前 V7 原生绑定 |
| 战术冲刺 | `M870Super90Sprint20261016` | SUPER90 三段参考，已合入最终基础母版 |
| 快速近战 | `M870QuickMeleeElbowR3_20261017` | 五条可编辑动作、原厂序列及四种 Profile；R1/R2 仅保留仍被读取的 helper 脚本 |
| 通用配件 | `M870CommonOptics20261016`、`M870CommonFurniture20261016` | 后握把改造已取消；后托切分中的原厂颈部仍为有效安装依赖 |
| 战术挂件、延长管 | `M870TacticalFit20261017`、`M870ExtendedTube20261017` | 模型与光源方向共用安装座，延长管特殊改造 +3 发 |
| 轻量扳机 | `M870LightweightTrigger20261017` | 间隔 ×0.75，后坐力 ×0.95，稳定性 ×1.05 |
| 快速装填器 | `M870Speedloader20261016` | 继承 SUPER90 R27，保留本枪接触与空仓泵动尾段 |
| 图标、第三人称、ADS、腰射位置 | `Tools/Weapons/M870*`、`M870HipFraming20261017` | 共用手臂分区剔除、可见轮廓取框，ADS 与腰射构图独立 |

以上短目录均位于 `SourceAssets/`。原厂和四类前握把的近战 Profile 仅更新 `quick_melee` 条目，不能用早期 13 动作全量导入覆盖已认可 R3。

## 源码与本机资源边界

原创 C++、目录中 M870 的独立条目、作者/导入脚本、文档和 SKILL 发布至原路径。共享文件的候选从 Git HEAD 构造，仅重放本次差分；并行工作区文件保持原样。共用霰弹枪散布/机械时钟使用已经公开的 SUPER90 配件实现，必要接线随本次进入根源码。

快速近战检查夹具的增量放在 `Integration/quick-melee-audit.patch`，前置散列见 `audit-prerequisites.json`。它针对本机完整共享夹具，不能直接按本次 Git HEAD 盲套；恢复已有夹具及其前置后再合入。`M870QuickMeleeAudit.inl` 与历史检查说明一起保存，不自动执行。

Blend、FBX、GLB、UE 包、图标/音频、原始下载、密集姿态、网格采样、缓存、日志和第三方 Python 库留在本机，均不随 Git 上传。枪体、V7 手臂、SUPER90 参考、UC 动作和声音分别有独立来源；详见两个制作源的 `CREDITS.md`。UC 所选源未确认授予独立游戏再分发许可，原始和派生动画不公开。仅此源码提交不能恢复完整可运行游戏。

## 归档

317 份确认废案与一次性旧备份，共 711,948,844 字节，已移入 `trash/m870-retired-20261017`，移动后逐文件 SHA-256 一致。详情见 `retired-files.json`：包括被 AKM 整手替代的 ThumbEdge/NaturalThumb、未接入的 ThumbRootSwing，以及被 R3 替代的近战 R1/R2 输出。

R1 `author_motion.py`、R2 `author_right_arm.py` 的函数前缀仍被 R3 读取，因此留在原位置；基础动作的旧日期输入、有效工具和参考母版同样保留。生产 Content 未移动。恢复单文件按清单原路径操作并避免覆盖新版本，不能整包回放旧安装流程。

## 已有证据与本次执行范围

用户于 2026-10-17 确认 R3 近战动作“基本合格”。随后完整本机工程完成 34 项资产读回、80 项离线权威/资产用例以及 Editor/Game 构建，见 `SourceAssets/M870QuickMeleeAudit20261017/coverage.md`。这些是历史完整宿主结果，不是本次发布子集的独立构建或真实联网测试。

本次只进行归档读回和 Git 发布检查，包括暂存差分、文件范围、大小、二进制、凭据、来源边界及远端状态；不启动 UE、不运行游戏、不追加玩法或联机验收。实际延迟、丢包、重连及完整死亡重生仍需用户测试。

个人与工程 SKILL 同步新增 [动作与抓握](../../../skills/ue5-fps-arms-animation/references/m870-source-motion-and-grip.md) 和 [泵动枪接入](../../../skills/ue5-weapon-workflow/references/m870-pump-integration.md)，保留后台制作、不主动测试、不跨任务协调的边界。
