# 随机地牢怪物卡顿：2026-10-12 实机采样与快捷栏修订

## 采样范围

用户保留了既有 PIE，采样于本地时间 12:58:10–12:58:30 完成。没有启动、停止或重启游戏，没有改变画质、怪物数量、AI 或资产。20.02 秒内 938 次前台 tick，后台 tick 为 0；结束后停止 trace 并恢复原有 trace channels。

- 地图：`/Game/GameMaps/UEDPIE_0_L_Dungeon_Randomized.L_Dungeon_Randomized`
- 视口：2552 × 1222，硬件光追与 Lumen 开启，阴影质量 3，无 VSync/帧率上限。
- 开始：27 只存活怪物（保安 13、接待员 11、研究员 3）；结束：22 只存活、5 具尸体。
- 两厅第一波各 14、13 只。场内总量与玩家当前看到的一厅数量不是同一个指标。
- 第一厅第二波实际触发于 12:58:40.488，晚于采样结束约 10 秒。第二厅第二波为 12:59:59.697。因此本轮覆盖第一波战斗，**没有直接捕获换波生成瞬间**。

原始数据位于 `Saved/MonsterPerfDiagnosis20261012/capture03/`：`capture.utrace`、`capture.json`、`analysis.json`、`thread-analysis.json`、`worker-analysis.json`、`gpu-analysis.json`。

## 实测结果

分析区间为 trace 时间 532.06–552.044 秒，排除启动 trace 前的尾部缓冲和结束时未完成的 frame scope。

| 指标 | 结果 |
| --- | ---: |
| 完整游戏帧 | 935 |
| 平均帧时间 | 21.348 ms（46.84 FPS） |
| 中位帧时间 | 20.558 ms |
| P95 / P99 帧时间 | 24.122 / 32.525 ms |
| 最长游戏帧 | 260.683 ms |
| HUD tick 平均 | 2.852 ms |
| HUD tick P95 / P99 | 8.241 / 10.963 ms |
| 单槽刷新调用 | 4755 次，累计 2371.05 ms |

### 已确认：长帧中的 GPU 等待链

最长游戏帧是 540.174725–540.435408。`Sync_RenderingThread` 占 246.873 ms，游戏世界 tick 为 8.536 ms。

对应渲染线程在 `WaitForVisibilityTasks` 等待 165.282 ms；工作线程的 `OcclusionCullPipe` 下存在 164.984 ms 的 `GPUBound_WaitingForGPUForOcclusionQueries_SeeGPUTrack` / `RHIGetRenderQueryResult_GPU_Wait`。

这明确表明该次长停顿包含“GPU 遮挡查询未返回 → 可见性任务等待 → 渲染线程等待 → 游戏线程等待”。不能将这 261 ms 全部记到生成怪物、寻路或 AI 计算上。

GPU 队列同一段也有长帧，但 GPU scope 的时间跨度可能包含队列依赖和等待。`FXSystemPreRender` 的长跨度不足以单独证明某个粒子 shader 执行了同等时长。GPU 图形/计算队列并行，不把它们的耗时相加，也未据此关闭光追、Lumen、阴影或降低模型精度。

当前证据定位到了阻塞链，**尚未定位使 GPU 查询延迟的具体资源/渲染工作，也未证明最近的加载修改导致这一等待**。后续需要对同一波次的生成前后做对齐采样，保留视口、相机、画质和怪物组成。

### 已确认：快捷栏只读状态重复计算完整战斗属性

317 轮快捷栏刷新 × 每轮 15 槽，与 4755 次单槽刷新一致。前六槽各平均约 0.95–1.49 ms，整轮快捷栏平均约 7.48 ms；未刷新时 HUD tick 中位约 0.113 ms。

`UColdSteelQuickSlot::Refresh` 原先调用整套 `FireballStats`、`IceSpikeStats`、`LightningStats` 等，最后只使用 `ManaCost` 判断图标是否置暗。整套计算还遍历了无关的伤害、暴击、六维属性、装备、锻造效果，构成周期性游戏线程负担。

本轮修订：

- 新增 `Skills/ColdSteelSpellMana.cpp` 的共享消耗查询。快捷栏只计算当前耗蓝；实际施法快照也调用同一消耗公式。
- 提取覆盖火球、冰锥、冰墙、暴风雪、闪电、圣光，以及两组扩展火系/电系法术。
- 保留技能等级、主手符文倍率、法杖工艺、连锁施法层数、魔法书专注以及原有 float/double 取整顺序。
- 不增加跨帧数值缓存，不降低刷新频率，不改变冷却、动作占用、资源扣除或图标语义。
- 保留 `ColdSteelQuickSlot_Refresh` trace scope，并增加 `ColdSteelSpellManaCost` scope，便于同场景复测。

改动前文件备份：`Saved/TaskBackups/QuickbarMana20261012/`。此次源码变化并不等于已测得帧率提升。

### 尸体和模型的证据边界

结束时 5 具尸体中 4 具 mesh tick 已关闭，1 具仍在物理阶段；当前样本不支持“所有旧尸体永久保持动画/物理”的结论。

先前静态读取确认三种职员模型只有一个 LOD，且仍参与光追/阴影。这说明群体渲染有优化空间，但面数本身不能证明本次卡顿根因。本批没有减面、替换资产或修改怪物波次。

## 构建与交付状态

快捷栏修订已保存并完成后台 Editor 构建。`Saved/BuildEditor/build-20261012-131513.log` 在源码保存后启动，逐项编译了 `ColdSteelQuickSlot.cpp`、`ColdSteelSpellMana.cpp` 和八个相关技能模型文件，并以 `Result: Succeeded` 结束（166.98 秒）。没有并发启动第二轮构建。

最终产物：`Binaries/Win64/UnrealEditor-FPSGAME.dll`，28,071,424 字节，本地时间 2026-10-12 13:17:58。必要的 ColdSteelNet 依赖也已链接。

未自动重启 UE，未进行修订后的游戏性能复测。换波峰值与 GPU 等待的进一步归因仍未完成，不能宣称整体怪物卡顿已经解决。

此前 Slate 闪退的控件生命周期修订属于独立问题，证据与构建记录在 `Saved/MonsterPerfDiagnosis20261012/diagnosis.json`；本次性能数据没有替代崩溃复现验证。
