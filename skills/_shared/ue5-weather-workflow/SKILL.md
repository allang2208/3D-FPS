---
name: ue5-weather-workflow
description: Build or migrate UE5.6-UE5.8 day-night and weather systems using frame-rate-independent time, Niagara rain, wetness parameters, shelter attenuation, puddles, lightning, thunder, and evidence-based validation.
---

## 执行约定

**第一条（FPSGAME）　文件位置与引用路径。** 以含 `FPSGAME.uproject` 的当前工程根为准，先读 `Docs/Production/README.md` 和 `WORKFLOW.md` 第 4.1 节。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

遵守用户全局规则：后台制作、不主动测试、不跨对话协调。涉及 UE 构建或资产操作时，按需读取[后台开发与接入规则](../ue5-auto-assistant/references/editor-open-development.md)；已读则复用。 原因：制作授权不包含额外运行或验收，交付应保留未测试的实际状态。

## FPSGAME 性能开发约束（2026-09-23）

修改光照或新增大量局部灯时，读取 [性能开发约束](../ue5-performance-packaging/references/fpsgame-performance-development.md) 的灯光与归因部分。保留项目已恢复的硬件光追、Lumen 和昼夜配光基线；按实际耗时处理重复更新、局部灯距离及生命周期。 原因：动作未正常结束也会离开当前状态，资源占用、费用和待结算结果必须有明确收尾。

# UE5 weather workflow

Use this skill for the current Unreal migration when work touches the game clock,
sky/light transitions, rain, wetness, puddles, lightning, thunder, or weather
asset integration. Use the legacy Godot weather skill only when maintaining the
old Godot implementation. 原因：当前工程已迁移 UE，Godot 流程只适用于明确维护的旧实现。

## Project contract

- Advance world time with engine elapsed time (`DeltaSeconds`), never frame
  counts. For this project, one game day is `2160.0` real seconds (36 minutes).
- Keep one authoritative runtime weather manager. Spawn it from the active game
  mode only when no manager already exists, so authored map overrides remain
  possible and map travel does not create duplicates. 原因：唯一管理器保留地图作者覆盖并防止换图后产生重复时钟和天气写入者。
- Keep tuning exposed through the current configuration interface; retain runtime ownership in the weather manager and follow the current world/network clock contract. Reason: editable tuning does not transfer runtime authority, and the early single-player description is not a reliable statement of current network support.

主场景出现第二太阳、反向光晕或反射方向不一致时，读取 [天空高亮归因](references/sky-highlight-attribution.md)，先追实际 MID、相机覆盖与 SkyLight 方向。

## Effects integration

剑、法杖、工具或第三人称武器没有雨天湿润时，读取 [近战武器湿润接入](references/melee-weapon-wetness.md)：扩展真实武器分支、保留活跃 MID 指针和透明／发光参数，分离皮肤与物理武器槽。

下方云海粗糙、染色、黑屏或隐藏后又出现时，读取 [云海失败边界与持久配置](references/cloud-sea-failure-boundaries.md)。主神空间云海当前按用户要求隐藏，不能作为已认可方案自动恢复。 原因：「云海失败边界与持久配置」记录该任务的专属入口和边界，按主题引用可避免另写一套相互冲突的步骤。

For cloud/solar conflicts, coarse rain particles, pooled wet surfaces or transition
acceptance, read [storm and rain integration](references/storm-rain-integration.md).
For missing cloud textures, weak lightning, delayed thunder onset or inaudible mixes,
read [cloud, lightning and audio output](references/cloud-lightning-audio.md).

- Attach camera-local rain to the player view instead of filling the world with
  emitters. Ground-trace splash placement and cap spawn rates for scalability.
- Detect shelter with a periodic upward visibility trace. Smooth attenuation
  using `DeltaSeconds`; apply it consistently to rain particles and layered rain
  audio.
- Publish wetness, cloudiness, and lightning through one material parameter
  collection. Materials must consume those parameters before claiming a wetness
  system is visually integrated.
- Use deferred decals for puddles only on validated outdoor surfaces. Refresh
  them at a coarse interval and reuse existing decals instead of spawning every
  tick. 原因：水洼依赖真实室外支撑，低频复用可避免逐帧创建贴花的开销。
- Separate lightning flash timing from thunder playback delay. Randomize among
  licensed no-background thunder cues so rain ambience is not doubled. 原因：闪光与雷声传播延迟不同，带雨底噪的雷声还会重复叠加环境雨。

## Asset and licensing boundary

- Prefer MCP asset queries for class, parameter, dependency, and save checks.
  Do not require foreground editor clicks for checks that MCP can perform. 原因：具备后台查询能力时无需前台点击，读取对象信息也不应额外打开编辑器。
- Save only the owned packages; use a suitable isolated background authoring host if the available save operation would also write unrelated dirty assets. Reason: saving every dirty package can capture another task’s unsaved work and does not authorize closing the user’s editor.
- Keep import/configuration scripts, source audio provenance, license notices,
  and asset paths. Do not publish Fab binary assets unless redistribution rights
  are explicitly established. 原因：恢复与分发分别依赖作者输入和许可，商店二进制存在本机不代表可公开再分发。
- The reference snapshot and exact asset paths are in
  `../../unreal/weather-migration/README.md`.

## 交付与按需诊断

- 完成变更所需的后台构建、导入和保存，区分源码、产物和当前已加载状态。原因：单文件编译或旧 DLL 不能代表完整可加载结果。
- 用户明确要求检查时，按范围读取资源、保存结果或运行昼夜与雨暴时序；正常 2160 秒合同与加速时序分别记录。原因：加速观察不自动证明正常时间条件，文档也不授权默认运行完整周期。
- 画面、音频、联机和 Cook 结果分别陈述。原因：无渲染或无声音进程没有覆盖相应表现路径。
- Git 发布仅在本次用户授权时按项目 WORKFLOW 执行，保留作者输入、许可和精确退役清单。原因：制作授权不包含推送，受许可约束的二进制和仍被调用的旧源也不能随意公开或删除。

## 时钟驱动的世界道具（2026-09-18，柱廊青铜火把）

给场景道具加"黄昏/夜晚自动点亮"时，只读时钟、不另建计时器：

- **唯一权威时钟**仍只有 `AFPSWeatherManager`：`Hour = Frac(NormalizedDayTime) * 24`；日落段 16.5 起、
  日出段 6.0 结束（与 `TemperateHillsDayNightSky.cpp` 的相位边界同一套数字）。道具照这个窗口写即可，
  跳时/传送/跨午夜都不需要特殊分支（窗口跨午夜按"或"判断）。
- **两条时钟路径都要认**：有 `BP_FPS_DayNightManager.SunHeight`（0..2400 = 一天）的关卡里，管理器每帧从它
  同步时间、自身时钟被旁路。给道具/面板加"设置时间"能力时必须走管理器接口
  `AFPSWeatherManager::AdvanceGameTime(Hours)`：有天空时钟就推那个属性（`LastSkyTimeUnits` 不碰，
  跨午夜的日序交给既有回绕逻辑记一次），否则推内部 `WeatherClockSeconds`。
- **点火要有淡入淡出**：`IgnitionAmount` 按 `DeltaSeconds / IgnitionBlendSeconds` 夹到 0..1，火焰在 >0 时激活、
  点光强度 = 基准 × 点火量 × 闪烁；每支按世界坐标错开相位，整排不会同步闪。出生时直接取目标状态
  （`BeginPlay` 里 snap），否则进关卡先看 6 秒淡入。
- **点光别贪亮**：1600 lm 的火把贴在自己 30 cm 处会把铜杯和柱子一起打爆（近景一片白）。
  当前柔和档位：350 lm / 半径 500 cm / 默认不投影，SourceRadius 6 cm、SoftSourceRadius 8 cm、
  SpecularScale 0.6、雾贡献 0.08；亮度波动 ±4%，按位置错开平滑相位。旧 600 lm / 900 cm 默认值
  需迁移已放置实例；自定义值保留。要阴影时逐支打开（6 支阴影点光 = 6 张立方体阴影图）。
- **位置比亮度更容易错**：火焰原点要放在**容器口**（杯口 z≈42.6）而不是腔底（z≈16），否则火苗整团埋进
  27 cm 深的杯里，只剩灯可见——用户看到的正是"只有光没有火"。
