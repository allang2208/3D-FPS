# 地牢周期卡顿：HUD 更新归因（2026-09-23）

## 结论与状态

在已恢复硬件光追和 Lumen 的地牢 PIE 中，周期性慢帧主要落在 `UColdSteelHUDWidget::NativeTick`。先前面板归类为 Slate 窗口绘制的耗时包含这个游戏 HUD 更新，不能直接认定为编辑器外壳开销，也不能当成光追耗时。

已完成一次用户授权的在线采集和离线分析。第一批优化与细分计时源码已完成 **FPSGAMEEditor Win64 Development 常规后台构建并写入基础 DLL**。尚未运行修改后的游戏，**尚未测得优化收益**。最初 Live Coding 因 229 项待构建操作超过 100 项上限而取消；用户随后保存关闭 UE，常规构建已成功。未重新打开编辑器或启动游戏。

## 采集与计算范围

- 原始记录：`Saved/SlateStall20260923/20260923-201603/capture.utrace`，76,510,127 字节。
- 元数据：同目录 `capture.json`。北京时间 20:16:05–20:16:20，约 15.026 秒。
- 场景 `/Game/GameMaps/UEDPIE_0_L_Dungeon_Randomized`，视口 2552×1222；522 次前台回调，后台 0 次。
- `r.RayTracing=1`、`r.Lumen.HardwareRayTracing=1`、GI/ReflectionMethod 均为 1；VSync 与 MaxFPS 均为 0。未修改画质、光照或关卡。
- 相机起点约 `(-9666,-5541,265)` cm，终点约 `(-11163,-3872,-814)` cm；角色没有始终站定，不能用于与旧录制做严格光追 A/B。
- Trace 含开始录制前的环形缓存。报告保守选取 trace 时间 **400.0–413.5 秒**的内部窗口；只计完整结束的事件，排除缓存前段和结尾未关闭的 `+inf` 事件。
- 基于 `GameThread` 的逐事件导出重新聚合。没有用混有 GPU 事件的全局同名计时汇总，也没有将 CPU 与 GPU 时间相加。
- 分析脚本：`Tools/Performance/analyze_slate_trace.py`。输出同目录 `analysis.json` 与 `frame-hud.csv`。

## 核心数据

内部窗口包含 469 个完整主线程帧；帧平均 28.77 ms（约 34.76 FPS），P95 49.73 ms、P99 57.06 ms。

| 帧组 | 帧数 | 平均帧时间 | 同帧 HUD 更新 |
|---|---:|---:|---:|
| 慢帧（≥33.34 ms） | 243 | 45.24 ms | 34.31 ms |
| 快帧 | 226 | 11.07 ms | 0.046 ms |

窗口内 470 次完整 HUD Tick 累计 8.347 秒，占 13.5 秒墙钟窗口约 61.8%；其最大单次 53.21 ms。该比例是耗时占比，**不是预期 FPS 提升百分比**。

其次，`FPSGAMECharacter` 主线程计时 469 次累计 2.249 秒，平均约 4.80 ms，可作为下一阶段细分对象。`Slate::Prepass` 平均约 0.62 ms，`FPSWeatherManager` 平均约 0.114 ms，当前优先级低于 HUD。

本次证明了 HUD 更新是此窗口的主要 CPU 热点；尚未用细分探针测出其中 JSON、技能公式、每个 UI 刷新各占多少。并不据此宣称光追无开销、关闭光追完全无效，或已修复全部卡顿。

## 第一批源码改动

1. `ColdSteelHUDWidget.cpp`：50 ms 刷新分支原先依次调用 `RefreshAmmo()` 和 `RefreshQuickBar()`，但前者内部已刷新快捷栏。删除外层重复调用，保留原刷新频率和其他调用方的行为；增加弹药、顶部状态、时钟刷新 CPU 标记。
2. `ColdSteelInventoryRules.cpp`：`Text/Number/Flag` 与格子尺寸查询使用私有、线程内、最多 128 项的只读 JSON 缓存。键是完整 `Item.Data` 字符串，采用显式区分大小写的匹配（UE 的 FString 默认比较忽略大小写）；改造/附魔/换配件后即使命名与实例 ID 不变也会读取新值。缓存不存技能结算或角色数值；默认值规则保持原样。
3. 可变 JSON 仍独立解析：`Compatible()` 会删除身份字段后比较，继续使用独立对象，避免污染只读缓存；物品合法性检查路径同样保持原解析逻辑。
4. `ColdSteelQuickSlot.cpp`、`CombatItemFormula.cpp` 增加 CPU 标记，供后续确定技能刷新和战斗属性读取的成本；没有修改战斗公式、冷却、存档结构或反射布局。

源文件改动前备份在 `Saved/SlateStall20260923/source-before-instrumentation`，不作为整文件覆盖回退的授权。保留当前文件中的其他工作。

## 构建与后续

20:22:47 尝试现有编辑器 `LiveCoding.CompileSync`；UBT 报 `LiveCodingLimitError`，229 项超过 100 项限制。桥返回仅表示脚本返回，不代表编译成功。日志副本：`Saved/SlateStall20260923/instrumentation-build-limit.log`。

用户保存关闭 UE 后，后台构建 `FPSGAMEEditor Win64 Development`，239 项操作成功，182.54 秒。补充缓存大小写匹配后再增量构建 4 项操作成功，11.20 秒；最终日志 `Saved/SlateStall20260923/editor-build-final.log`，基础模块 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已落盘。没有提高热编译限制，没有构建或运行独立打包游戏。

构建完成后保持编辑器关闭，由用户测试；下一次用户同意采集时，在同一地牢、固定位置、同分辨率和画质下比较 HUD Tick、慢帧比例与 P95，并继续定位剩余战斗公式解析成本。编译成功不等于玩法回归或帧率验收通过。

在这条 CPU 路径处理并复测之前，不再次整体剔除光追或要求逐关卡重做光照。后续模型、阴影灯距离、纹理驻留优化各自以实际瓶颈为依据。
