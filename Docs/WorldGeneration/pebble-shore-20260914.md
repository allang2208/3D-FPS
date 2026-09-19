# 丘陵世界：鹅卵石滩厚度与起伏（2026-09-14）

用户反馈河岸鹅卵石地面过于平坦。本次把整体地形、近景石缝和真实石子轮廓分开构建，共用同一河岸范围与沉积斑块。

| 层次 | 接入内容 | 作用 |
| --- | --- | --- |
| 地形 | 河岸沉积隆起与浅凹槽，默认起伏强度 22 cm | 改变石滩轮廓和实际行走地形 |
| 材质 | 现有扫描素材的高度图与 AO，近景视差遮蔽、按高度混合粗细石子 | 补出石子间的凹陷，减少两个石面贴图直接混合的重影 |
| 实体卵石 | 7–22 cm 圆石，随机长宽高与旋转，部分埋入地面 | 从贴地角度提供真正的几何轮廓 |
| 水草衔接 | 低洼处更湿润；石子密集斑块中草量适当减少 | 让草、细砾石与大卵石交错，不形成规则整条铺装 |

## 地形与放置

`TemperateHillsRiver.cpp` 中的 `FPlan::Height` 叠加约 7 m 与 3.2 m 波长的连续噪声，形成堆积与冲刷感。起伏只在水线外逐渐出现，并在外岸回到丘陵时平滑消失。`RiverBankReliefCm=22` 是公式强度，并非实测高差；实际位移还受噪声、岸边距离和地形混合权重影响。

地形渲染、地形碰撞、植物与石子位置读取同一高度函数，保留当前近处 1 m 的河岸地形网格。没有把每颗纹理石子都细分成碰撞几何。

`TemperateRiver::PebbleCover` 提供确定性的沉积斑块，写入地表顶点色 B 通道，同时控制实例卵石和岸草退让。顶点色 R 保留河岸混合，G 改为按实际地表相对水面的高度计算湿润程度。天气仍使用现有 `Wetness` 参数。

`TemperateHillsPebbleShore.cpp` 使用现有草层 PCG 的 16 m 单元与 2 m 分帧条带。实例无采集身份和逐石碰撞，候选 ID 使用独立的 `0x60` 低字节范围。小石子的来源是项目已有圆石网格 `/Game/WaterMaterials/Meshes/SM_River_Rock`，制作了湿润、灰色、暖灰三份独立材质变体；靠水优先湿润变体。网格有 3 级 LOD，使用现有草层的距离裁剪与阴影设置，不新增逐石动态阴影。

石子长轴 7–22 cm，宽度约为长轴的 62–92%，高度约为长轴的 30–52%；生成时补偿源网格底部中心，再埋入高度的 22–38% 和 1 cm。候选平均间距 85 cm、保留概率上限 0.78，最终密度受沉积斑块和坡面条件影响。

## 材质

独立目录：`/Game/WorldGeneration/TemperateHills/PebbleShore`。

使用本机已下载的 `Shoreline_Beach_Rocks-1a759058` 与 `Small_Pebbles_Ground-a0e6a70f`。两套扫描的元数据均标注 2 × 2 m，本次沿用相应世界坐标纹理比例，并导入先前未使用的 Displacement 与 AO，数据贴图关闭 sRGB。源网格、源材质和已下载图片不改写。

新地表材质复制当前丘陵地表，保留河岸遮罩以外的坡地／草地／泥土与天气图，只替换河岸分支。新增视差射线步进为 8–20 步，默认虚拟凹凸深度 5 cm，在 9–18 m 渐隐，并在非常贴地的视角收敛，避免无限拉长采样。

视差修改材质采样位置，属于近景视觉深度，不改变碰撞、网格剪影或写入 Pixel Depth Offset。真实剪影由起伏地形和实体卵石提供。有关视差与高度图的机制参见 [Epic：Using Bump Offset](https://dev.epicgames.com/documentation/unreal-engine/using-bump-offset-in-unreal-engine)。本次实现采用多步高度搜索，而非该页演示的单步 Bump Offset。

## 参数与制作入口

当前配置仍是 `/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming`。

- `RiverBankReliefCm`：石滩起伏强度，默认 22，范围 0–40 cm。
- `RiverPebbleSpacingCm`：实体小石子采样间距，默认 85 cm。
- `RiverPebbleCoverage`：实体小石子保留概率上限，默认 0.78。
- `PebbleReliefDepthCm`：新地表材质里的视差深度，默认 5 cm。
- `PebbleNormalStrength`：新地表法线强度，默认 1.10。
- `Tools/WorldGeneration/build_pebble_shore.py`：导入高度／AO，制作独立地表与圆石变体，保存上述配置。

原生构建日志：`Saved/PebbleShore-NativeBuild-20260914.log`。
资产制作日志：`Saved/PebbleShore-Authoring-20260914.log`。
资产清单：`Saved/PebbleShore20260914/authoring.json`。

本次必要原生构建完成（`Result: Succeeded`，模块后缀 `914031720`）。资产制作脚本完整执行，保存了 4 张高度／AO 图、独立地表材质、3 份圆石网格及材质和丘陵配置；日志包含 `PEBBLE_SHORE_AUTHORING_COMPLETE` 与 `Python script executed successfully`。Commandlet 因工程既有的 `GameFeatureData` 扫描条目缺失返回 1，该错误未阻止本次资产保存。

按用户全局规则，本次不运行游戏、画面渲染、截图或性能测试；最终画面、行走感受和性能由用户重启编辑器后测试。
