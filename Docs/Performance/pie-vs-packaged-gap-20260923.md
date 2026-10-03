# PIE 与打包版的性能差距（2026-09-23）

> **一句话**：打包版至今**不存在**，所以「打包后和 PIE 差多少」目前没有数据可答；
> 本轮把打包 profile 固化了，并在第一次真 Cook 时撞到一个**已知但只修了一半**的资产缺陷。

本轮范围：读 SKILL／性能记录／7 份实测导出、核对打包配置与引擎默认值、固化打包 profile、
跑第一次 `BuildCookRun`。未启动编辑器、未结束他人进程、未运行游戏。

## 1. 判定口径

| 项 | 值 | 来源 |
| --- | --- | --- |
| 目标帧率 | 60 FPS / 16.67 ms | 性能面板 `target_fps=60`、`SlowFrameThresholdMs=33.34` |
| 慢帧阈值 | 33.34 ms（2 倍预算） | 同上 |
| 合格线（用户 2026-09-23 确认） | 原生 2560×1440 + 当前画质 + **平均/中位 ≥ 60 FPS** | 本次对话 |

`Docs/Performance/performance-panel-review-plan-20260922.md:190` 已写明 16.67 ms 是暂定预算，不擅自改用户目标。

## 2. PIE 侧唯一可用数据

7 份导出全部是 **PIE**（`/Game/GameMaps/DayNight_Lighting`、D3D12、2552×1222、FOV 107.5、
`ScreenPercentage=0`（默认即 100%）、VSync=0、MaxFPS=0、无暂停/后台帧），时间跨度 9/22 13:15 → 9/23 00:16。

| 指标 | 要求 | A：9/22 23:33 | B：9/23 00:16 |
| --- | ---: | ---: | ---: |
| 窗口 / 帧数 | — | 8.62 s / 233 | 10.03 s / 481 |
| 平均 FPS | 60 | 27.03 | 47.97 |
| 帧时间 P50 | ≤16.67 | 36.04 | **10.84（≈92 FPS，达标）** |
| P95 / P99 | ≤16.67 | 47.01 / 93.21 | **42.92 / 51.82（超标）** |
| 超 16.67 ms 占比 | 0% | 96.57% | 38.88% |
| 超 33.34 ms 占比 | 0% | 69.96% | 37.01% |
| GPU0 P50 / P95 | ≤16.67 | 30.51 / 33.51 | 11.28 / **17.02（压线）** |
| 渲染线程 P50 | — | 34.96 | 6.60 |

**读法（决定后续优化方向）**：B 的中位数已经进预算，差距**全在尾部**——约 37% 的帧冲到 2 倍预算以上。
这不是「整机算力不够」，是「一半时间正常、一半时间卡」。B 的 GPU P95 已经压到 17.02 ms，
GPU 余量比 CPU 侧小得多。

两份 session 的相机位置/朝向不同、A 中铺装尚无 LOD 链，因此**不能当作受控的前后对照**。

## 3. 9/23 的优化确实在盘上（两条独立印证）

回执 `SourceAssets/MainScenePerformance20260923/Receipts/`：

- `scene.json`：`paving_components=78`、`forced_lod_model=2`、`target_lod_index=1`、
  `clusters=82`、`eligible_actors=528`、`components_removed=426`、`saved=true`、`runtime_tested=false`
- `assets.json`：4 个连续性材质清除不适用的骨骼 usage；4 个广场构件启用 Nanite（显式切线、完整回退几何、
  碰撞不变）；2 个构件材质补 instanced/nanite 使用标志；`remaining=0`、`runtime_tested=false`

主地图二进制（`Content/GameMaps/DayNight_Lighting.umap`，2,365,156 B）字符串计数：
`PlazaPaving`×78、`PlazaInstance`×83、`RomanColumn`×17、`Nanite`×15、`ForcedLodModel`×1。
与回执一致，说明优化不是只写在脚本里。

**但这批改动一次都没被测过**：最后一份导出是 9/23 00:16，而修复批次 07:00–09:00 才落盘
（最终 Editor 构建 `Saved/PerformanceDiagnosis20260923/build-main-scene-5.log`，185 actions，退出码 0）。

## 4. PIE → 打包：现在能给出的只有边界，不是结论

### 4.1 编辑器侧（打包版不吃这笔）

B 中帧时间 ≥33.34 ms 的 178 帧（占 37%）：平均帧 **38.97 ms**，其中
`Slate.TickAndDrawWidgets` 平均重叠 **29.70 ms**、`World.Tick` 5.82 ms、
`Viewport.Draw` 0.21 ms、`Icon.Tick` 0.08 ms；对照 <16.667 ms 的 294 帧平均 9.94 ms、Slate 仅 1.59 ms。

即慢帧里约 **76%** 的时长落在 Slate 区间。该区间是**进程级**的（`SlateApplication.cpp` 覆盖所有窗口的
Prepass/绘制与绘制缓冲获取），打包版不付这笔钱——**但数据没有把 29.7 ms 拆成控件布局/编辑器其他窗口/
渲染线程回压**，所以只能作为「打包版 CPU 侧应明显更好」的强候选，不能当结论。

### 4.2 GPU 侧（打包版要吃更多像素）

打包全屏 2560×1440 = 3,686,400 px，PIE 视口 2552×1222 = 3,118,544 px，**+18.2%**。
按一阶线性外推：GPU0 P50 11.28 → **≈13.3 ms**，P95 17.02 → **≈20.1 ms**。
这是估算（阴影深度、体积云等 pass 不完全按像素缩放），**不是实测**。

### 4.3 结论

两侧方向相反：CPU 侧打包版占优、GPU 侧打包版吃亏，净结果**不可预测，必须实测**。
另外要注意打包版默认画质与 PIE 是否一致：工程没有 `DefaultScalability.ini`/`DefaultDeviceProfiles.ini`，
PIE 侧当前 `Saved/Config/WindowsEditor/GameUserSettings.ini` 是 `sg.*=3`（Epic）+ `sg.ResolutionQuality=0`，
打包版走引擎默认。**对比前必须把两侧画质档位固定并记录**（SKILL 的 Constraint）。

## 5. 本轮固化的打包 profile

`Config/DefaultGame.ini` 末尾新增显式段（此前该段只有 `DirectoriesToAlwaysCook/NeverCook`，
没有 `MapsToCook`/`BuildConfiguration`/`UsePakFile`/`bUseIoStore`，即**隐式范围**）：

| 键 | 值 | 理由 |
| --- | --- | --- |
| `BuildTarget` | `FPSGAME` | 显式 |
| `BuildConfiguration` | `PPBC_Development` | 本次要能测量：F6 性能页/`stat`/CSV profiler 只在非 Shipping 存在 |
| `UsePakFile` / `bUseIoStore` | `True` / `True` | 发行容器策略显式化 |
| `bUseZenStore` | `False` | 本地可复现的 Pak/IoStore 落盘；Zen 输出按 SKILL 只当迭代库 |
| `bCompressed` | `True` | 引擎默认，显式写出 |
| `bGenerateChunks` / `bCookAll` / `bCookMapsOnly` | `False` / `False` / `False` | 只烤显式地图，不做隐式全量 |
| `+MapsToCook` | 6 张 | 见下 |

Cook 范围取游戏实际能打开的图（依据 `SceneTestPortal.cpp`、`DungeonAssembler.cpp`、
`FPSPreloadAssetRegistry.gen.h`、`Content/ColdSteelData/dungeon/*.json`）：
`DayNight_Lighting`（主场景）、`L_TemperateHills_Initial`、`L_Dungeon_Prototype`、
`L_Dungeon_Generated`、`L_Dungeon_Randomized`、`L_Dungeon_AuthoredExpansion`。

**未纳入**（独立范围决策，不是遗漏）：`L_MilitaryTrench_FPS_Test`（源内容 10.53 GB）、
`L_Normandy_FPS_Test`（3.84 GB）——两张 Fab 第三方测试图。

## 6. 打包阻塞（P0）：Cook 断言——`SK_Harvest_Pickaxe_Skeleton` 缺失

### 现象

`BuildCookRun` 的**编译阶段成功**，**Cook 阶段崩溃**：
`Error_UnknownCookFailure`、`AutomationTool exiting with ExitCode=25`、
`UnrealEditor-Cmd.exe ExitCode=3`，Cook 运行 3m19s（其中大部分是着色器编译），
Cook 进度停在「Cooked packages 6 / Total 5698」。

```
LogWindows: Error: appError called: Assertion failed: !Hash.IsZero()
  [File:.../Engine/Private/Animation/AnimSequence.cpp] [Line: 2172]
```

### Cook 侧证据（比断言本身清楚）

```
LogCook: Display: Package /Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Pickaxe_Equip
        has a dependency on package .../SK_Harvest_Pickaxe_Skeleton which does not exist.
```

同一句重复 **6 次**：`A_Harvest_Pickaxe_Equip` / `_HitRecover` / `_Idle` / `_Swing` / `_Walk`
以及 `SK_Harvest_Pickaxe` 本身。压缩阶段还有
`Animation Compression request for A_Harvest_Pickaxe_* failed, Skeleton == nullptr` 与
`Zero key hash compressed animation data ... requested platform Windows`。

### 根因

`/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Pickaxe_Skeleton` **整个 D 盘都不存在**
（`SK_Harvest_Pickaxe.uasset` 与 5 条镐动画都硬引用它）。9/13 的导入回执
（`SourceAssets/ProductionToolGrip20260913/import_receipt.json`）保存了 15 个包，
**其中没有任何 Skeleton 包**——导入器只在内存里建了骨架，从未保存。

### 为什么现在才暴露：这是已知缺陷，只修了一半

- `Docs/Weapons/battle-axe-replacement-20260919.md:44`（9/19）当时就写明：
  「顺带修复既有缺陷：`SK_Harvest_Axe_Skeleton` 自 2026-09-13 首次导入起从未保存到磁盘……
  **未改动的矿镐同样如此**」，并保存了斧头骨架（101 骨）。
- `SourceAssets/BattleAxeReplace20260919/skeleton-probe.json` 当时读到**两个骨架都** `exists: false`。
- 教训已进 SKILL：`skills/ue5-fps-arms-animation/references/single-hand-tools.md` 第 67 节
  「骨架资产要确认真的落盘」，并要求「凡按槽位/骨架导入骨骼资产，交付前都要在新进程里读回骨架是否非空」。
- **斧头按这条做了，矿镐没有。** 编辑器里不会立刻报错，所以一直没暴露；
  第一次真 Cook 才把它变成硬失败。

### 修复方案

1. **推荐**：按斧头 9/19 的同一修法补 `SK_Harvest_Pickaxe_Skeleton` 并显式保存。
   作者源齐全：`SourceAssets/ProductionToolGrip20260913/Export/SK_Harvest_Pickaxe.fbx`
   + 5 条动画 FBX + `Pickaxe_SingleHand_Editable.blend` + `authoring.json`/`import_receipt.json`。
   路径名与动画引用的路径一致即可自动恢复绑定。属编辑器/命令集操作，需按项目后台 commandlet 方式执行。
2. **不推荐**：临时摘掉 `DirectoriesToAlwaysCook=(Path="/Game/Items/ProductionTools/GripMotion20260913")`
   换取一次测量包——会静默发出「镐没有动作」的包。
3. 修完应在新进程读回骨架非空，且**重跑一次 Cook** 确认断言消失。

### 复现

```powershell
# 编译成功、Cook 必失败（退出码 25）
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Build-Package.ps1 `
  -Configuration Development -Profile core-measurement
```

日志：`Saved/BuildPackage/core-measurement-Development-20260923-182019.log`。

## 7. 复现入口（本轮新增）

| 文件 | 作用 |
| --- | --- |
| `Tools/Build/Build-Package.ps1` | Cook+Stage+Pak/IoStore 运行器；`-Maps` 必须与 ini 的 `+MapsToCook` 一致，否则拒绝执行；编辑器在跑时拒绝或排队（`-WaitForEditor`）；只对**编译**失败重试（`-RetryOnCompileFailure`），Cook 失败不重试 |
| `Tools/Performance/run_packaged_capture.ps1` | 打包版帧时间采集；**不用** `-RenderOffscreen`（该参数下 `-ResX/-ResY` 不生效，既往恒为 720p），并回读日志与 `GameUserSettings.ini` 报告**实际**分辨率 |

两个脚本的注释保持纯 ASCII：本机 PowerShell 5.1 按 ANSI 读取无 BOM 的 `.ps1`，中文注释会破坏解析。

## 8. 未做 / 未测

- **打包版从未产生**：`Saved/StagedBuilds` 下无有效产物，无 Cook 成功记录。
- 9/23 优化**未经任何运行时验证**（回执 `runtime_tested=false`，导出数据早于修复）。
- 打包版 2560×1440 帧时间：**未测**。
- PIE 与打包版画质档位是否一致：**未验证**。
- `Slate.TickAndDrawWidgets` 内部构成（控件布局/编辑器其他窗口/渲染回压）：**未拆**。
- 旧导出中未归因的长帧与历史 4.1 s / 3.5 s 级空白：**仍未归因**。
- 既有的 `1400×900`／1440p 独立采集不可信：`-ResX/-ResY` 改不动（恒 720p），
  且同参数重复运行有 ±3 倍波动（`Docs/Backlog.md` 已记录），**不能用于评价本次改动**。

**不得声称**：已达 60 FPS、已消除卡顿、打包版优于或劣于 PIE。