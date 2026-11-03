# 雷神之锤后续整理与发布（2026-11-03）

本批保存疾雷/贯雷 Meshy 接入、通用锤座 V7 与轻型座 V8 修正、贯雷落地嵌入、两枚握柄图标、录音随机分段蓄力，以及普攻/重击意图区分、联机改造回执、临界蓄力释放和重生修复。最新冷加载外观 V2 已本地编译，仍待用户实机确认。

## 源码与依赖边界

- [source-manifest.json](source-manifest.json) 列出专属源码、作者配方、精确配置字段、共享补丁和散列。两张雷神之锤表中只发布本轮外观字段及模型引用；其他工作的锤部材质栏和文字排版改动保留在本地工作副本。
- 共享角色、库存、战锤和枪匠文件包含其他在途改动。本批延续 [11 月 1 日发布](../ThunderHammer20261101/README.md) 的保存方式：本轮差量位于 [SharedHosts](SharedHosts/)，按 01 至 06 顺序记录，每个补丁要求清单中的准确前置版本（散列统一为 UTF-8/LF）。这些补丁尚未集成到公开主线共享文件，不能直接套在干净 HEAD 上，也不能用发布裁剪文件覆盖本机完整源码。
- 因此这是可追溯的开发源码与补丁发布，不是已独立构建通过的完整干净检出工程。原始 GLB、可编辑 Blender、PBR、音频、图标、姿态数据及 UE 包均留在本机；素材再分发未核准，不随 Git 推送。
- 本次主工程暂存区已包含另一批 Kukri 工作，且共享 PlayerState、忽略规则和技能文件存在实际索引冲突。依据 `WORKFLOW.md` 第 8 节例外，从已核对远端建立临时发布 worktree，只重放本批内容；原工作区和索引不改写。完成后将临时发布副本归档到本机 trash 并撤销该 worktree。

## 当前资源恢复入口

[当前接入索引](../../Weapons/thunder-hammer-current-20261102.md) 和 [本批资源依赖](asset-dependencies.json) 记录活动路径：贯雷 `GuanLeiClosedCrownV12/MeshyV13`，疾雷 `JiLeiInlaidLightningV14/MeshyV15`；厚壁/叠片座为 `CommonSeatsStructuralV7`，轻型座为 `LightSeatWindowFixV8`。两枚握柄图标使用真实 `ue_thunder_god_hammer_grip_*` 键；录音六片段由 `JiLeiRecordedCurrentV2/MS_JiLei_CurrentRandom` 播放。

Meshy 原件由用户提供，需与本机原厂安装端和作者输入一起保留。作者版本较旧不代表废弃；前置模型、贴图、Before 快照及联机证据仍保留。脚本存在不代表在另一台机器已恢复资产。

## 退役归档

已将 `JiLeiChargeAudioV1` 和未采用的 `JiLeiElectricAudition20261101` 共 **13 文件、5,005,282 字节（4.77 MiB）** 移入本机 `trash/thunder-hammer-retired-20261103/`。记录见 [cleanup-manifest.json](cleanup-manifest.json)，移动后逐文件 SHA-256 一致。历史 V5 批处理已停止导入旧电磁声，避免恢复时覆盖当前录音方案。

本次未移动 Content 包：旧 SoundWave 是否仍被历史资产引用尚未完成引用清理，不能仅凭当前播放路径将其删除。当前六段录音及原 MP3、所有活动模型、必要制作输入和已有检查证据继续保留。移动归档不等于释放磁盘空间。

## 历史结果与本次检查

此前完整本机工程的记录见 [全项状态](Evidence/full-review-status.json)：1,243 项原生检查、75 项资产读回、专服/监听服各 24/24 项实际 UDP、72/72 打包依赖，以及本地渲染和录音链路证据。专服使用 Editor-Cmd 权威端；均为同机专项场景，不等于公网或完整游戏发布验收。

这些运行证据均早于冷加载修复。V1 隐藏整个远端人物等待头部，后续复核发现会形成不可见目标，并遗漏衣物就绪。V2 改为显示完整可见的临时人形，待头部首帧及当前穿戴装配后一起切换，失败保留临时外观。见 [V2 交付](Evidence/cold-join-v2-delivery.json) 与 [构建回执](Evidence/cold-join-v2-build.json)：Editor/Game 本地构建成功，**没有 V2 实机通过证据**。旧截图只能确认冷加载缺头；正常召回前空手和模糊运动物不构成武器延迟或头部错位的证明。

本次仅执行用户要求的推送检查：完整暂存差异、补丁前后散列复原、文本语法、链接、大小、敏感信息与分发范围；结果见 [publication-checks.json](publication-checks.json)。未启动 UE、未运行游戏、未重新构建或做联机验收。推送提交及远端回读结果保存在本机 `Saved/Publication/ThunderHammer20261103/push-receipt.json`。

## 技能沉淀

个人维护源与工程镜像已同步本轮补充：

- [人物首次外观就绪与完整过渡外观](../../../skills/ue5-cpp-gameplay/references/initial-appearance-readiness.md)
- [改造回执、临界蓄力与重生](../../../skills/ue5-save-load-replication/references/replicated-terminal-events.md)
- [雷神之锤输入与生命周期](../../../skills/ue5-weapon-workflow/references/thunder-hammer-lifecycle.md)
- [用户录音与连续随机播放](../../../skills/ue5-weapon-workflow/references/weapon-audio.md)
- [生成模型安装端与开窗残片](../../../skills/asset-model-workflow/references/modular-part-interfaces.md)

本轮规则补充按任务经验限定范围；不把单个模型尺寸、250 ms 容差、Manny 临时模型或历史测试数字推广成通用标准。
