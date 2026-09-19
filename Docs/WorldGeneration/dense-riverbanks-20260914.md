# 丘陵世界：密集河岸植物（2026-09-14）

本次把河岸从稀疏的高草点缀改为短草铺底、上层植物成丛、外岸灌木衔接。沿用现有水系、河石与树木再生系统。

## 生成配置

| 层次 | 模型数 | 候选平均间距 | 植物高度 | 分布 |
| --- | ---: | ---: | ---: | --- |
| 贴岸底草 | 6 | 52 cm | 24–44 cm | 水线至外岸，核心草带维持较高密度，向坡地渐疏 |
| 芦苇／高穗草 | 4 | 95 cm | 110–195 cm | 浅水边及近岸成丛，允许少量茎根入水 |
| 中层穗草／花草 | 6 | 115 cm | 48–103 cm | 草带中混生，填充低草与高草之间的高度 |
| 低矮阔叶／莲座叶 | 4 | 180 cm | 32–64 cm | 潮湿岸边，林缘比例略高 |
| 现有灌木 | 3 | 约 375 cm | 70–145 cm | 距水线约 4.5–24 m，稀疏成组 |

候选间距是生成采样密度，不是规则方格种植间距；最终密度还受水深、坡度、岸边距离和斑块权重影响。配置中的 `RiverGroundCoverCoverage=0.96` 是候选保留概率上限，不代表实测地表覆盖率。上层使用 `RiverPlantCoverage=0.95`。

短草密度使用 `0.80 + 0.20 × 斑块权重` 的底值，不再让多重噪声连续相乘清空整段岸边。两岸使用不同斑块，植物种类在扭曲的 7 m 区域间渐变混合，20% 混入其他种类。干燥路径边界平滑退让，水线处不再被抽象道路走廊整带排空；保留出生区 24 m 空间。

尺寸根据各模型包围盒高度归一化，并补偿根部高度。高草保持直立，底草略随坡面倾斜。不开新的植物 Tick；生成仍走现有 PCG 草层的 16 m 单元、分帧 2 m 条带和实例化渲染，灌木走现有灌木层。新增软引用纳入分阶段加载和材质预热。性能和画面由用户测试。

## 已接入素材

独立资产目录：`/Game/WorldGeneration/TemperateHills/RiverEcologyDense`。
当前丘陵数据资产：`/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming`。

来源是本机已有的 [PN 草库](https://www.fab.com/listings/8b68642e-35f4-438e-82b4-799fc2228303) 与 [PN 地被植物](https://www.fab.com/listings/ef6db212-dfcf-4a50-8ade-fbca49963240)，复制后的 20 个模型使用独立河岸材质，保留源网格、纹理、LOD 与叶片风动数据。热带包只采用小型带状叶、披针形叶和莲座叶，通过尺寸与数量控制作为岸边下层植物；这里按形态使用，不声称完成温带植物学物种还原。

外岸复用现有 `UnrealNormandy` 的 3 种灌木。源包不改写。本次不下载或购买新的商城资源。

如果继续增加辨识度，优先补香蒲的柱状花序；[Cattails set mid poly game ready](https://www.fab.com/listings/8d022d02-bfb1-47dd-aff1-aa85fd987338) 的商家说明提供 8 个模型、UE LOD 和风动，适用于河岸湿地。它目前只是后续候选，尚未购买或接入。再往后可补真实蕨类与少量漂木，分别丰富背阴岸边与水线杂物层。

## 开发入口与交付边界

- `TemperateHillsRiverEcology.cpp`：四层植物、外岸灌木、尺寸与分布。
- `TemperateHillsWorld.h`：新增底草数组、密度、间距设置。
- `TemperateHillsWorld.cpp`：灌木层接入。
- `TemperateHillsStreaming.cpp`：底草资源加载与预热。
- `Tools/WorldGeneration/build_dense_riverbanks.py`：制作独立植物资产并保存当前数据资产，不修改水材质或树木周期。

必要原生构建与资产制作记录分别写入 `Saved/RiverbankDense-NativeBuild-20260914.log`、`Saved/RiverbankDense-Authoring-20260914.log` 与 `Saved/RiverbankDense20260914/authoring.json`。

本次原生构建完成（`Result: Succeeded`，模块后缀 `914021550`）。资产制作 Python 完整执行并保存了 20 个模型、独立材质和当前丘陵配置。Commandlet 因工程既有的 `GameFeatureData` Asset Manager 扫描条目缺失返回 1；日志同时记录 `Python script executed successfully`，该配置错误未阻止本次资产保存。

按照用户全局规则，未运行场景测试、性能测试、截图或视觉验收。重启编辑器后重新进入丘陵世界，由用户测试最终草带密度、形态及性能。

鹅卵石滩的后续起伏、近景凹凸与实体石子接入见 [鹅卵石滩升级](pebble-shore-20260914.md)。石子沉积斑块会让局部草丛略微退让。
