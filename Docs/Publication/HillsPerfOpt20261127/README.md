# 温带丘陵与村庄开放世界性能、远景夜灯及 HUD 缓存专项交付（`HillsPerfOpt-R50 ～ R57`）

本批公开 2026-11-26 至 2026-11-27 围绕 `L_ForestPathVillage` 与 `TemperateHills` 开放世界完成的七轮渲染/GPU/HUD/骨骼性能与远景夜灯接地剪影优化（`R50`、`R52`、`R53`、`R54`、`R55`、`R56`、`R57`），包含已沉淀的跨会话 SKILL 规范、共享宿主适配补丁索引与本次冗余清理摘要。

---

## 1. 公开交付范围

1. **GPU / 体积雾 / 光追剔除 / Nanite 与 TSR 质量预设（`R50`、`R54`、`R56`、`R57`）**
   - `Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp`：`fps.Hills.QualityPreset`（`0=Epic 原生 / 1=默认均衡 / 2=流畅软件 Lumen`），使用 `ECVF_SetByPluginLowPriority` + Tag 在切换和离场时完整卸载恢复；关闭高耗 `r.VRS.ContrastAdaptiveShading` 与 `r.VRS.EnableSoftware`（实测 `5.52 -> 0.00 ms`）；收紧 `r.RayTracing.Culling=3`（`Radius=15000/10000`、`Angle=2.0/3.0`）与 `LandscapeGrass=0`；启用 `r.LocalFogVolume.HalfResolution=1`、UE 5.8 High TSR (`r.TSR.History.UpdateQuality=2`、`r.TSR.RejectionAntiAliasingQuality=1`)，并仅在 2 档开启 `r.Nanite.MaxPixelsPerEdge=1.5`。
   - `Source/FPSGAME/WorldGeneration/ForestVillageMistComponent.cpp`：新增 `fps.Hills.ForestMistRangeCm`（默认 `18000 cm`，`<= 0` 恢复 `24500 cm`）。
   - `Config/DefaultEngine.ini`：`r.Nanite.Streaming.StreamingPoolSize=512`。
2. **VSM 阴影缓存、灯光滞回预算与远景接地夜灯剪影（`R50`、`R53`、`R55`、`R56`、`R57`）**
   - `Source/FPSGAME/FPSUDSBridgeComponent.cpp`：新增 `fps.UDS.SkyClockStepUnits=0.5`（约 `0.45 s` 步进），避免每帧微动太阳角击穿 VSM 静态阴影页。
   - `Source/FPSGAME/WorldGeneration/VillageInteriorLighting.h/.cpp`、`VillageRoadLamp.h/.cpp`、`Building/BronzeTorch.h/.cpp`、`HillsTavernSite.cpp`：室内点光默认关影（`fps.Hills.InteriorLightShadows=0`）；室外路灯与外立面火把按 `fps.Hills.RoadLampShadowDistCm=2200` + `400 cm` 滞回调度动态阴影，关闭体积阴影并通过 `ManagesOwnShadowBudget()` / `bInteriorLightingManaged` 保护子类及商店室内灯。
   - `Source/FPSGAME/WorldGeneration/VillageDistantGlow.h/.cpp`、`TemperateHillsWorld.h`、`ForestVillage.cpp`、`TemperateVillageStreetLighting.cpp`、`Tools/WorldGeneration/ForestVillage/optimize_hills_perf_r55.py`：重构远景村庄夜灯，锚定真实流送/修复后室外灯具与修复建筑外窗（零悬空、44–48 m 平滑接力真实灯光、扁平逆光半穹顶 + 地形法线贴合暖光池 + 零贴图 `M_VillageWarmWindow`）。
   - `Source/FPSGAME/WorldGeneration/ForestVillage.cpp`：森林及村边乔木/榛灌 ISM 设 `EShadowCacheInvalidationBehavior::Rigid`，限制 WPO 距离（`3500 / 2200 cm`）并关闭 RT WPO 与矮灌木光追代理。
3. **骨骼 URO、离屏停算与光追代理裁剪（`R52`、`R54`、`R56`）**
   - `NPC/VillageResidentDetail.h/.cpp`、`NPC/ChapelNun.h/.cpp`、`Movement/StableRidingHorse.h/.cpp`、`Monsters/WildlifeDistanceActivity.h/.cpp`、`Monsters/FatZombie.h/.cpp`、`Monsters/HumanoidKnockdownComponent.cpp`、`Characters/FPSPlayerBodyAppearance.cpp`、`Characters/FPSArmJointCorrectiveComponent.h/.cpp`、`Weapons/SwordTasselMeshComponent.cpp`：按距离切换骨骼 URO 与 `OnlyTickPoseWhenRendered`，在 `18–22 m`（含滞回与骑乘例外）开关 3P RT 代理，关闭本地 1P `bOwnerNoSee` 发丝 Groom / 流苏物理，缓存武器/手臂矫正 Morph 目标。
4. **HUD `UInvalidationBox` 缓存隔离、全控件防击穿与公式版本键缓存（`R56`、`R57`）**
   - `UI/ColdSteelStatusModel.h/.cpp`、`UI/ColdSteelProfileRuntime.cpp`、`Skills/ColdSteelSpellMana.cpp`：按复合版本键缓存静态装备加成、`maxHp`/`maxMp` 与 `AdjustedManaCost` 乘区，去掉每帧堆分配。
   - `UI/ColdSteelHUDReadouts.cpp`、`UI/ColdSteelAmmoReadout.h/.cpp`、`UI/ColdSteelStaffReadout.cpp`、`UI/ColdSteelWorldClock.cpp`、`UI/ColdSteelHUDTimeline.cpp`、`UI/ColdSteelEventTimeline.cpp`、`UI/ColdSteelResourceMeter.cpp`：消除文本/颜色/显隐/坐标/画刷/按钮样式/Tooltip 重复标脏，量化日晷（`720` 步/日）、事件时间轴位移（`>= 0.002`）与连续资源条（`0.0025` 死区 + 边界穿透），折叠待机期停用呼吸脉冲。
   - 与并行重构交织或尚未于公开 `main` 收口的文件（`ColdSteelHUDWidget.h/.cpp`、`ColdSteelHUDConstruction.cpp`、`ColdSteelCrosshair.cpp`、`ColdSteelFireballHUD.cpp`、`ColdSteelTopVitals.cpp`、`FPSGAMECharacter.cpp`、`FPSGAMECharacterCamera.cpp`、`LumberMillWorkerActor.*`、`LumberMillTimberWagon.*`、`VillageLightningSpire.cpp`）以集成说明形式附于 [Integration/shared-host-hooks.md](Integration/shared-host-hooks.md)，未把未合并功能混入 `origin/main`。
5. **批量制作工具与着色器源码（`R48b`、`R50`、`R52` ～ `R55`）**
   - `Tools/WorldGeneration/ForestVillage/optimize_hills_perf_{r48b,r50,r52,r53,r54,r55}.py`
   - `Tools/WorldGeneration/ForestVillage/{trail_soil,cliff_surface,continuous_meadow}.ush`
6. **沉淀 SKILL**
   - [温带丘陵与村庄 GPU / 光照 / 骨骼性能优化规范](../../../skills/ue5-performance-packaging/references/hills-village-gpu-hud-perf.md)（接入 [ue5-performance-packaging](../../../skills/ue5-performance-packaging/SKILL.md) 与 [ue5-landscape-authoring](../../../skills/ue5-landscape-authoring/SKILL.md)）
   - [Cold Steel HUD InvalidationBox 缓存与防击穿规范](../../../skills/ue5-ui-umg-slate/references/hud-invalidation-caching.md)（接入 [ue5-ui-umg-slate](../../../skills/ue5-ui-umg-slate/SKILL.md)）

---

## 2. 本地内容依赖与编译/验证状态

- **UE `.uasset` 二进制资产（不随公开 Git 再分发）**：由 `optimize_hills_perf_r48b/r50/r52/r53/r54/r55.py` 就地生成或调整（含贴图 `max_texture_size` 封顶、Nanite/LOD 调整、地貌着色器短路、`M_VillageDistantBeacon` 与 `M_VillageWarmWindow`）；原包改前 SHA-256 备份与发布/编译回执均保留在本机 `F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R{50,52,53,54,55}/`。
- **实机对比证据（R53 → R56，`L_ForestPathVillage` 导出报告）**：均帧 `26.76 → 45.64 fps`、`gpu0 p50` `33.82 → 17.67 ms`、`draw p50` `36.11 → 17.21 ms`、`game p50` `16.67 → 12.14 ms`、`PrepareImageBasedVRS` `5.52 → 0.00 ms`、卡顿次数 `5 → 0`、VRAM `20.22 → 15.40 GB`。
- **最新构建状态**：R57 全部 19 份相关源码改动与回归修复已编入本机 `FPSGAMEEditor Win64 Development`（`BUILD_EXIT=0`，`UnrealEditor-FPSGAME.dll` `55.26 MB`，`2026-11-27 19:01:20`）。R57 实机 `F6` 复测与 Y 盘 NAS 备份由用户后续执行。

---

## 3. 清理归档

本次会话产生的一次性 `utrace_export*` CSV 导出、探针脚本与 `HillsPerfOpt` 中间运行/重试日志（共 `354` 个文件、`517.33 MB`）已逐文件核对 SHA-256 移入本机隔离区（D 盘 `trash/HillsPerfOpt-20261127/` 与 F 盘 `FPSGAMEData/trash/HillsPerfOpt-20261127/`），摘要见 [cleanup-summary.json](cleanup-summary.json)，完整散列清单保留于本机 `F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOptCloseout-20261127/cleanup-manifest.json`。
