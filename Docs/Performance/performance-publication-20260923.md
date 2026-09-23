# 主场景性能：整理与源码发布

本次整理承接 [主场景优化](main-scene-optimization-20260923.md)，按 `WORKFLOW.md` 第 4–8 节处理。发布目标为 `https://github.com/allang2208/3D-FPS.git` 的 `main`，普通非强制推送。

## 归档

57 个旧备份、一次性编辑器操作脚本、早期失败批次的传输日志及 Python 缓存移入本机 `trash/main-scene-performance-20260923/`，共 7,933,558 字节。原路径、目标、大小、SHA-256 和替代入口见 [归档清单](performance-archive-20260923.json)。移动后已逐文件比对散列。

保留正式 `apply_assets.py`、`apply_scene.py`、`plaza_instances.py`、`background_assets.py` 与 `run_background.ps1`。它们使用同一批次互斥并在项目引擎进程仍运行时保留现场；原始资产备份位置已改为上述 trash 中的 `Before`，以后重跑不覆盖首次备份。最终 `assets.json`、`scene.json`、`assets-5-engine.log` 保留在本机 Receipts，作为保存记录，不进入公开提交。

没有按日期批量移动其他任务的目录，没有删除正式生成器、当前地图/资产或仍需使用的制作输入。归档恢复只按需要取回指定文件，不整体覆盖当前 Source、Content 或个人技能。

## 发布范围与共享改动

- 发布性能采样/导出、性能页、图标异步准备与回读、定向刷新、包围盒复用、主场景分组工具、相关作者脚本及文档。
- 共享 C++、Build.cs、SKILL 与忽略规则采用从 HEAD 构造的候选内容精确暂存，工作区不回退。其他任务的怪物页排版、战斗数值界面和武器配件实现保留未提交。
- 图标预载需要 PKM 的网格路径函数，因此只发布该头文件的路径解析部分；本机完整附件实现保留原样。已由其他提交进入 HEAD 的展示初始化直接复用。
- 发布准备发现 HEAD 的库存文件在 includes 前有两条游离语句及已发布方法体；保留方法体原文并移至 includes 后，仅移除无合法函数上下文的游离语句，使本次回调接入不沿用该排版错误。工作区现有实现不改写。

## 内容恢复边界

公开仓库只含源码、制作配方、参数与文字说明，不包含 `.uasset`、`.umap`、DLL、日志、模型、贴图、字体或商用素材原包。

完整场景仍需本机 `/Game/GameMaps/DayNight_Lighting`、`/Game/Props/RomanColumn20260915`、已有铺装 LOD 与 `/Game/Weapons/ExtMagContinuity20260919` 四个材质图。它们依赖原有授权资源；未因本次优化获得公开再分发许可。图标需要当前各武器/模块资产和 `/Game/UI/GunsmithWorkbench/T_StudioEnvironment`。总原则见 [AssetSetup](../AssetSetup.md)。

实际保存结果：78 块铺装使用 LOD1；4 种构件配置 Nanite；508 个重复构件转换成 82 组，另 20 个单件组保留。组件减少 426 不等于 draw calls 减少 426，未测帧率增益。

## 技能沉淀

工程和个人技能镜像均新增对应参考及入口：

- `ue5-performance-packaging`：时间对齐、父子 scope、Slate 观察范围、LOD 编码和 SkyLight 漏项。
- `ue5-ui-umg-slate`：异步资源、分步图标准备、定向通知、包围盒复用与静态材质 usage 归因。
- `ue5-pcg-building`：局部实例化、物理配置复制、网格变更通知、Nanite 构建及 commandlet 保存边界。

## 构建与检查范围

此前完整工作区 Editor 构建成功：`Saved/PerformanceDiagnosis20260923/build-main-scene-5.log`，185 actions，退出码 0。这是包含并行工作的本机构建，不冒充精确发布候选的独立构建。

本轮只执行用户要求的归档和推送检查：暂存范围/完整差异、空白错误、文件大小、二进制、敏感信息、许可、直接源码依赖、远端分支和归档标签。没有启动 UE、运行游戏或性能/视觉验收。部分长帧归因及实际帧率仍待新运行数据；历史保存批次的非零退出和接口修复已在优化记录中说明。
