# 温带丘陵统一生态配置

沿用现有 PCG 运行时分层生成和自定义高度场，不接入 BiomeCore。树种比例、植物密度、坡度与林缘过渡现在由 `Config/DefaultGame.ini` 中的 `[TemperateHills.Ecology]` 统一驱动。默认配置延续本轮之前的生成配方，不在配置整理阶段统一加密树林或重做地形。

## 修改入口与生效方式

- 作者配置：`Config/DefaultGame.ini` 的 `[TemperateHills.Ecology]`，通过 UE 的 `GGameIni` 配置层级加载，随 Game 配置部署。若平台／用户 Game.ini 显式覆盖同名键，遵循 UE 原有覆盖顺序。
- 实现：`Source/FPSGAME/WorldGeneration/TemperateEcologyConfig.h/.cpp`。原生默认值与当前项目配置一致；缺失键沿用默认值，非法非有限数值沿用默认，正常数字限制在字段允许范围内。
- 第一次进入丘陵前在游戏线程初始化进程级只读快照；之后 PCG、远景树和地形工作线程共享这些值，不逐点读取配置，不新增 Tick、文件轮询、资源同步加载或运行时热切换。
- 修改配置后正常关闭并重新启动编辑器／游戏进程生效；无需为参数修改重新编译 C++。本轮没有主动启动图形编辑器或游戏。

## 树种和密度

`PoplarShareMin=0.10`、`PoplarShareMax=0.20` 控制各个带固定种子的林分中黑杨的选择概率，其余选择山毛榉。当前主树调色板仍使用黑杨 0–3、其后山毛榉的既有槽位合同。约 85% 山毛榉／15% 黑杨是默认选择概率的整体期望，不是最终可见实例计数保证；局部林分、支持筛选与资产可用性会影响数量。

| 配置前缀 | 当前 Density | 范围／含义 |
| --- | ---: | --- |
| Trees | 1.00 | 主树既有出现概率的倍率 |
| Shrubs | 1.00 | 普通静态灌木配方的倍率 |
| Saplings | 1.00 | 山毛榉幼树生境权重系数 |
| Hazel | 0.45 | 林下榛树生境权重系数 |
| Ferns | 0.88 | 蕨类生境权重系数 |
| Grass | 0.94 | 低草覆盖系数 |
| GrassAccents | 0.50 | 高草／点缀草覆盖系数 |
| MeadowFlowers | 0.40 | 草地花卉覆盖系数；未配置模型时不生成 |
| RiverGroundCover | 0.96 | 河岸低矮地被覆盖系数 |
| RiverReeds / RiverGrass / RiverUnderstory / RiverShrubs | 0.95 | 各河岸层独立覆盖系数 |

所有 `*Density` 接受 0–2，0 关闭该层；它们乘在原有生境／斑块概率上，最终仍经过坡度、道路、水位、贴地及邻居避让。增加系数不会越过候选集合或安全约束，也不等于按比例增加最终数量。各层基准不同，应相对各自当前值调节，例如 `FernsDensity` 从 0.88 调到 0.70 表示降低蕨类生境中的出现概率。

旧 `UTemperateHillsAssets` 的 `GrassCoverage`、`GrassAccentCoverage`、`MeadowFlowerCoverage`、`RiverPlantCoverage`、`RiverGroundCoverCoverage` 为保存旧资产与制作脚本兼容性继续保留，**运行时已不读取这些密度字段**。旧重建脚本再写它们也不会覆盖统一配置。模型引用、候选间距、模型尺寸、风动和生长时长仍由原有资产／代码管理，未新增第二套生成器。

## 坡度

每层使用 `*MinNormalZ` 和 `*FullNormalZ`。`NormalZ = cos(坡度角)`，数值越大越平坦。小于 Min 时拒绝；从 Min 到 Full 平滑增加密度；相等时为硬阈值。这种表示保留原有阈值，不需要每个候选计算反三角函数。

| 植物 | MinNormalZ → FullNormalZ | 最大坡度约值 |
| --- | --- | --- |
| 主树 | 0.87 → 0.87 | 29.5° |
| 普通灌木 | 0.83 → 0.95 | 33.9° |
| 幼树、榛树 | 0.90 → 0.97 | 25.8° |
| 蕨类 | 0.86 → 0.97 | 30.7° |
| 草、点缀草、花卉 | 0.83 → 0.93 | 33.9° |
| 河岸地被、草、林下植物 | 0.78 → 0.90 | 38.7° |
| 芦苇 | 0.86 → 0.98 | 30.7° |
| 河岸灌木 | 0.84 → 0.84 | 32.9° |

根部多点支撑、允许高差和水位规则继续生效，因此“坡度允许”不代表一定保留该候选。

## 林缘、空隙与过渡

- `WoodlandStart/End`：历史林冠噪声转为森林覆盖的渐变范围。
- `GapsStart/End`、`GapScaleCm`、`GapStrength`：林隙阈值、空间尺度与削弱强度。默认尺度 26 m，强度 0.72。
- `EdgeEnterStart/End`、`EdgeLeaveStart/End`：从开阔地进入林缘、再从林缘进入密林的覆盖权重范围；这些是 0–1 权重，不是世界坐标距离。
- `ShadeStart/End`：林下阴生权重；与林缘共同驱动灌木、蕨类及幼树原有配方。
- `GrassShadeStart/End` 和三个 `*ShadeSuppression`：低草、高草与花卉在林冠下的渐变抑制。
- `MoistureScaleCm`、`UnderstoryPatchScaleCm`、`CohortScaleCm`：湿润斑块、林下斑块和邻近植物形态群落的空间尺度；单位 cm。

主生成、林下植物、地面草、远景树林与地表落叶共用 `TemperateForestHabitat`，该函数族读取同一只读配置。地表落叶会跟随同一林冠／林隙和林下斑块变化，避免配置仅改植物而地表仍沿用旧区域。

## 采集、存档与运行边界

保持既有种子、随机盐、候选 XY、枚举间距、资源 ID、地形算法和存档结构。树木／矿脉采集与生长状态继续走现有系统；上一阶段的多点贴地和跨层避让继续位于最终输出路径。

配置调整会改变候选是否出现，以及同一主树候选选中的树种；保留 ID 并不意味着改变参数后画面数量和树种保持不变。配置不是逐存档或逐玩家设置，联机参与者应使用同一发布配置。本轮不加入运行时配置复制或旧存档外观迁移。

## 制作与构建记录

源码／配置修改前备份位于 `SourceAssets/TemperateEcologyConfig20261111/Backups`；后台构建脚本与回执位于该批次目录及 `Receipts`。`FPSGAMEEditor Win64 Development` 于 2026-11-11 11:39:51（北京时间）构建成功，退出码 0，完成本轮源文件编译和编辑器模块链接。回执为 `Receipts/FPSGAMEEditor-build.json`，日志为 `Receipts/FPSGAMEEditor-20261111-113839.log`。

本轮没有制作或保存地图、模型、材质，不需要新增资源；没有使用 computer use，没有启动游戏、截图、运行测试或画面／性能验收。最终效果由用户进场检查。
