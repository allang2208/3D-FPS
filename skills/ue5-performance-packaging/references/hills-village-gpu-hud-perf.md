# 温带丘陵与村庄开放世界 GPU / 光照 / 骨骼性能优化规范（UE 5.8）

提炼自 `L_ForestPathVillage` 专项性能与夜景优化批次（`HillsPerfOpt-R50` ～ `R57`）。适用于开放世界丘陵、林地 PCG、村镇实时灯光、远景夜灯剪影以及多 NPC/动物/坐骑场景。

---

## 1. 质量预设、CAS VRS、TSR 与局部体积雾（零/无感画质减负）

- **使用带 Tag 的低优先级 CVar 切换层**：在关卡Streaming控制器（如 `TemperateHillsStreaming.cpp`）中统一通过 `IConsoleVariable::Set(..., ECVF_SetByPluginLowPriority, Tag)` 注入预设，并在切换预设与最后一例离开关卡时先执行 `Unset(ECVF_SetByPluginLowPriority, Tag)`，确保 `2 -> 1 -> 0` 及回主神空间完全恢复原始设定，且不覆盖玩家/命令行手动覆盖值。
- **关闭 UE 5.8 高耗 AsyncCompute CAS VRS**：`L_ForestPathVillage` 实测 `PrepareImageBasedVRS` + `FinishImageBasedVRS` 在 AsyncCompute 上占 `5.52 ms` GPU。通过 `r.VRS.ContrastAdaptiveShading=0`、`r.VRS.EnableSoftware=0` 关闭后实测降至 `0.00 ms`。
- **收紧硬件光追场景剔除而非全局关光追**：保留硬件光追/Lumen 视觉基线，启用 `r.RayTracing.Culling=3`、`r.RayTracing.Culling.Radius=15000`（高帧 2 档 `10000`）、`r.RayTracing.Culling.Angle=2.0`（2 档 `3.0`）、`r.RayTracing.Geometry.LandscapeGrass=0`。
- **半分辨率局部体积雾与雾袋距离封顶**：
  - `r.LocalFogVolume.HalfResolution=1`（UE 5.8 验证有效）。
  - 对程序化散布的 `ULocalFogVolumeComponent` 雾袋提供 CVar 距离封顶（如 `fps.Hills.ForestMistRangeCm=18000`，`<= 0` 恢复 `24500 cm`），淡出起止按 `[0.7 * Range, Range]` 随动，避免远距屏幕空间外像素仍叠算体积雾边界。
- **UE 5.8 High 档 TSR 参数与 2 档 Nanite 分档**：
  - Preset 1/2 对齐 UE 5.8 `BaseScalability.ini` `[AntiAliasingQuality@2]` 官方参数：`r.TSR.History.UpdateQuality=2`、`r.TSR.RejectionAntiAliasingQuality=1`。
  - **1 档默认保真红线**：`r.Nanite.MaxPixelsPerEdge` 在 Preset 1 保持原生 `1.0`；仅 Preset 2（流畅高帧档）下探至 `1.5`。

---

## 2. VSM 静态阴影缓存与实时灯光预算

- **天空时钟步进防每帧全图 VSM 失效**：UDS 太阳角度每帧微移会不断作废 VSM 静态阴影页。使用 `fps.UDS.SkyClockStepUnits=0.5`（约 0.45 s 实机步进一次，`0.075°` 阈值，夜间平滑、白天零闪烁）保护静态阴影缓存复用。
- **大块林地 ISM 卫生配置**：在 PCG/生成实例创建阶段对林带乔木、榛灌及地被 ISM 设置 `EShadowCacheInvalidationBehavior::Rigid`，补充 WPO 禁用距离（乔木 `3500 cm`、灌木 `2200 cm`），关闭 `SetEvaluateWorldPositionOffsetInRayTracing(false)`，并对无需参与光追阴影的中小灌木/地被原地关闭 `bVisibleInRayTracing`（不改变实例化索引与种子）。
- **室外路灯与火把按距离滞回调度阴影**：
  - `AVillageRoadLamp` 与 `ABronzeTorch` 复用 `fps.Hills.RoadLampShadowDistCm=2200`（`+400 cm` 滞回，节流 `0.5 s`），关闭 `SetCastVolumetricShadow(false)`，仅近身开影路灯/火把保留微弱体积散射（`0.025–0.03f`），远距归 `0.0f`。
  - **距离判据陷阱**：未就绪或无视角时必须使用 `bHasView && Range <= Cutoff`（与路灯一致），不能在 `!bHasView` 时默认开影；且涉及继承体系（如 `AVillageRoadLamp` 继承 `ABronzeTorch`、`ConfigureShopInterior` 接入 `UVillageInteriorLighting`）时，必须通过虚函数 `ManagesOwnShadowBudget()` 与 `bInteriorLightingManaged` 状态位隔离，防止基类或室外预算反过来重新打开 `fps.Hills.InteriorLightShadows=0` 规定的无阴影室内灯。
  - 装饰性发光点光（如 `AVillageLightningSpire::CrownLight`）显式压低 `SetVolumetricScatteringIntensity(0.08f)` 并 `SetCastVolumetricShadow(false)`，避免默认 `1.0` 体积散射吃满局部雾预算。

---

## 3. 远景村庄夜灯接地剪影与防悬空规范（R55 模式）

远景城镇夜灯切忌在脚本里硬编码估算坐标（极易因地形起伏、建筑流送或未修复状态产生“鬼火悬空”）：

1. **锚定实景数据源**：在 `RebuildAnchors()` 中按建筑修复态采集真实室外光源坐标（路灯、已修复商铺外挂灯、外立面火把、`75 cm` 去重），绑定场景地表修订号与流送回调，而非静态坐标表。
2. **近中距交接不重影**：远景合批发光点（`ISM`）淡入延后至 `44–48 m`，无缝接力真实点/聚光灯的 `50 m` 淡出；最大远距放大倍率收敛至 `1.55×`，取消大幅前推偏移并配合铁帽上遮蔽与自适应 `DepthFade`。
3. **三层接地剪影**：使用底部嵌入地形的扁平宽逆光半穹顶（宽高比 `~3.7:1`）+ 随 `Height()` 4 点差分法线贴合地面的水平暖光池 + 压低至 `+6.5 m` 的泛光（照亮下立面而保持屋顶/尖顶对夜空的深色剪影反差），零新增实时阴影。
4. **物理嵌入型暖窗**：采用 0 贴图、无 WPO 的 Unlit Additive 窗片在 `< 30 m` 彻底淡出，仅点亮已修复建筑外窗及石窗凹槽。

---

## 4. 骨骼 URO、光追代理剔除与贴图/着色器优化坑点

- **NPC / 马匹 / 动物骨骼分级**：`> 14–16 m` 开启 `bEnableUpdateRateOptimizations` 与 `OnlyTickPoseWhenRendered`；3P RT 代理按 `18–22 m`（`+300 cm` 滞回，骑乘中恒开）切换 `SetVisibleInRayTracing`；1P 本地玩家 `bOwnerNoSee` 影分身与离屏挂件跳过物理（如 `USwordTasselMeshComponent` 对 `bOwnerNoSee` / `!WasRecentlyRendered` 跳过 `240 Hz` 迭代，同时对 commandlet/NullRHI 审计保持豁免）；1P 本地角色头饰/发丝 Groom 默认关闭渲染、投影、光追与 Niagara（`fps.body.FirstPersonHideGrooms=1`）。
- **贴图批量封顶命名陷阱**：批量按后缀跳过高度图/遮罩图时，切忌用宽泛的 `"mask"` 子串过滤而误放过 **8K 树叶/草地不透明度遮罩（Opacity Mask）**（R50 修复案例：`CommonHazel`/`EuropeanHornbeam` 8K 遮罩需单独封顶至 `2048`/`1024`，仅跳过真正的打包控制通道与查找表）。
- **地形与道路 HLSL 距离分支**：对远距不可辨别的法线/微浮雕、路肩落叶漂移（如 `roadside_leaves.ush` `distance < 4200`）及多材质三权重采样增加距离 `[branch]` 短路与权重提前裁剪，减少无收益纹理采样。

---

## 5. 证据边界与实测口径（严禁混用未测数据）

- **已实机 `F6` 对比验证（R53 → R56，`L_ForestPathVillage` 同地图导出报告，`1155` vs `875` 帧）**：均帧 `26.76 → 45.64 fps`、`gpu0 p50` `33.82 → 17.67 ms`、`draw p50` `36.11 → 17.21 ms`、`game p50` `16.67 → 12.14 ms`、`PrepareImageBasedVRS` `5.52 → 0.00 ms`、卡顿次数 `5 → 0`、VRAM `20.22 → 15.40 GB`。
- **R57 补充改动**：半分辨率 `LocalFogVolume`、UE 5.8 High TSR CVar、`ABronzeTorch` 阴影预算与剩余 HUD 缓存泄漏修复已通过 `FPSGAMEEditor Win64 Development` 编译与 DLL 符号校验，**尚待用户实机 `F6` 复测**，不得提前写出 R57 帧率收益数字。
