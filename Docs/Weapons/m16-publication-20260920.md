# M16A2 发布与恢复（2026-09-20）

用户已确认最新换弹回位和枪托接口修复成功。本次整理发布本任务累计的 M16 源码、数据、作者脚本和记录；没有另做游戏测试、PIE 或验收渲染。历史制作记录中的构建错误、旧动作和旧路径不代表当前选择，恢复时以本文和实际 C++ 加载路径为准。

## 当前交付

- 物品 `ue_m16a2`，沿用 **F6 → 基本调参 → 生成物品**，进入现有背包、装备、枪匠与存档流程。未调用的静态模型生成原型已归档。
- 三连发、组内间隔与组间恢复共用枪匠/附魔间隔公式，物品、面板与实战沿用共享伤害和换弹公式。参数入口为 `Content/ColdSteelData/{items,gunsmith,combat-weapon-formulas}.json`。
- 原模型、材质和 13 个机械分件迁入 Manny 手臂体系；普通弹匣的拔匣、插匣与快速近战复用当前 M4 完整骨链，校准 M16 弹匣接触。空仓保留已认可的右手拉机柄复进。
- 换弹尾段按源动画时间线性回收视模展示偏移，结束时清除旧动作残留。四款枪托使用真实机匣切口轮廓封口，保留主体 UV、法线和材质。
- 通用配件具有 M16 专用装配，包含提把瞄具连接座、全息玻璃与 UV 通道修复、后握把接口、枪口替换、动态图标和天气材质。开火声使用用户提供的 `D:/FPS3D/资产/音效/M16-fire.mp3`。

运行主网格为 `/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny`。配件资源为 `/Game/Weapons/M16A2/UniversalAttachments20260920`；原声为 `/Game/Weapons/M16A2/OriginalAudio20260920/S_M16_OriginalFire`。原厂目录图标为 `Content/ColdSteelData/Icons/ue_m16a2.png`。所有这些二进制仍保留在本机。

## 作者依赖与恢复顺序

优先从本机合法备份恢复当前 `Content/Weapons/M16A2`、图标、上游手臂/动作、配件和材质，再构建源码。以下是需要重新制作时的依赖顺序；不是一键运行全部脚本的指令。旧目录中的导入器会覆盖同名资产，最后必须使用对应最终作者输出。

| 阶段 / 本机 SourceAssets 目录 | 保留内容与职责 |
| --- | --- |
| `M16A2Migration20260919` | Godot 模块母版、原 FBX、PBR 和机械分件；入口为 `Tools/AssetPipeline/export_m16a2_migration.py`、`import_m16a2_migration.py`。保留署名与来源链。 |
| `M16Gameplay20260919` | 基础 Manny 网格、12 条基础动作、机械骨骼与拉机柄动作；`build.py`、`import_assets.py`。`configure_catalog.py` 是最初接入记录，后续参数直接维护现行 JSON。 |
| `M16UniversalAttachments20260920` | 通用配件母版、各握把/弹鼓 Blend、纹理、68 条派生动作；制作/导入入口见其 README。旧 `install_runtime.py` 是一次性源码迁移记录，不对当前源码重复执行。 |
| `M16Refinement20260920` | `M16_Interfaces_Editable.blend`、瞄具/后握把 FBX、原声音频；`repair_models.py`、`prepare_audio.py`、`install.py`。其换弹 Blend 仍是下一阶段的输入。 |
| `M16M4Insert20260920` | `transplant.py`、`fit_variants.py` 和 `Animations/**/*.blend`：M4 插匣动作与 M16 弹匣注册，仍是最终动画的直接输入。 |
| `M16RemovalMelee20260920` | 最终 `author.py` → `Animations/` → `install.py`：10 条普通弹匣换弹、6 条快速近战，复用完整 M4 手指/腕/肘链。普通换弹保留第 43 帧起的插匣段，空仓保留第 35 帧起的插匣和拉柄段。 |
| `M16RecoveryStocks20260920` | 最终 `repair_stocks.py` → `M16_ClosedStockInterfaces_Editable.blend` / `Meshes/` → `install_stocks.py`。覆盖 skeleton、qr_performance、core_stock、tactical_telescopic 四个原目标路径。 |
| `M16Presentation20260920` | 共享武器目录图标生成入口；图标与现用配件组合保持一致。 |

`M16RemovalMelee → M16M4Insert → M16Refinement` 的作者链仍需全部保留。日期较早、导出被覆盖，不等于可编辑输入是废案。源几何、密集姿态和实际材质绑定 JSON（例如 `factory_geometry.json`、`stock_topology.json`、`runtime_sources.json`）不公开，但本地重建仍需要这些输入或相应读取脚本。

## 废案归档

根目录 `trash/m16-retired-20260920/` 保存 56 个文件/代码片段：42 个旧候选、覆盖备份、短按释放钮旧入口及旧记录；13 个无引用的失败导入包；1 份未调用的 F6 静态模型生成原型。移动前后记录路径、字节数和 SHA-256。当前资产和仍参与制作的作者源保留。

- [作者源归档清单](../../SourceAssets/M16Publication20260920/archive-sources.json)
- [无引用失败资产清单](../../SourceAssets/M16Publication20260920/archive-assets.json)
- [未调用原型清单](../../SourceAssets/M16Publication20260920/archive-prototype.json)
- [保留的恢复依赖](../../SourceAssets/M16Publication20260920/retained-recovery-dependencies.json)

`AuthoringRecovery` 中另有 8 个包仍被正式配件/材质包引用，已保留，不按临时名称直接删除。清单记录实际引用方；当前没有把这些引用认定为重定向器，也没有据此修改打包配置。此整理不包含打包验收。

## 公开范围与经验沉淀

公开仓库只包含 M16 运行代码、目录数据、制作/导入/诊断脚本、文档和归档清单。第三方模型、材质纹理、手臂、动作、音频、Blend/FBX/uasset、渲染和密集采样均留在本机，`trash` 也不上传；克隆源码不能恢复完整游戏素材。模型署名见 [ATTRIBUTION](../../SourceAssets/M16A2Migration20260919/ATTRIBUTION.md)，不从历史索引的许可标签推断整个源包可公开再分发。

个人技能和工程镜像同步补充了 [换弹收尾与待机衔接](../../skills/ue5-fps-arms-animation/references/reload-handoff.md) 及 [替换后露出的宿主切口](../../skills/asset-model-workflow/references/modular-part-interfaces.md)。发布只暂存本任务文件及共用文件中的 M16 片段，保留其他任务的工作区改动。

本轮按用户要求进行仓库、引用归档、暂存差异、体积和敏感信息检查；未启动游戏测试。清理未调用原型后的 Live Coding 请求超时，日志只记录编译开始，没有作为成功构建依据。该原型不参与现用生成流程；用户确认成功的 M16 动作/资产交付记录见 [回位与枪托修复](m16-recovery-stocks-20260920.md)。
