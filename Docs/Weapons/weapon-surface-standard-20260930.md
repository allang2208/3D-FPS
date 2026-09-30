# 枪械表面标准 WS1（2026-09-30）

用户于 2026-09-30 确定：自研枪械统一采用写实金属与聚合物表面；以 M4、AKM、HK416 为参考；**按材质类型分别选主参考，不对三位作者取平均**；物理身份统一，旧化程度做成参数，默认档位为 **HK416 的干净档**。首个试点为 A762，记录见 [A762 表面标准试点](a762-surface-standard-20260930.md)。

本标准只适用于新制或自研枪械。M4、AKM、HK416 及已认可的 715 Chrome 保持原材质，作为参考源，不迁移。

## 1. 参考测量

方法：在运行时 LOD0 源模型上按面积均匀采样，读取各材质实际采样的贴图；底色换算为线性；每个贴图集做 k-means 分簇。入口：`SourceAssets/WeaponSurface20260930/{dump_mesh_geometry.py, export_reference_sources.py, measure_references.py}`，结果为 `inspect/reference_measurements.json`。

| 参考 | 部位 / 簇 | 线性底色 | 金属度 | 粗糙度 P10/50/90 | 磨损 |
|---|---|---|---|---|---|
| HK416 | 上机匣主簇（40% 面积） | .017/.020/.018 | .95 | .27/.32/.39 | 占 2%–4% 面积，底色约 .12，粗糙度约 .30–.37 |
| HK416 | 聚合物（枪托／握把） | 棕褐色涂装 | ≈0 | .23/.29/.47 | 有颗粒法线 |
| AKM | 钢件簇（42%） | .058 中性 | 1.0 | .29/.34/.47 | 占 14%，底色 .22，粗糙度 .29 |
| AKM | 胶木簇（24%） | .038/.0052/.0018 | 0 | .33/.36/.45 | — |
| AKM | 内部簇（34%） | ≈.001 | — | ≈.80 | — |
| M4 | 握把／枪托（作者原图） | .019 / .010（托垫） | — | .49 / .64–.71 | — |

- **M4 的运行时效果**（读取引擎函数 `MF_PhongToMetalRoughness` 的连线得到）：BaseColor 等于漫反射图；Metallic 等于 AmbientColor 的均值，M4 上为 0；Specular 等于 SpecularColor 的均值，为 0.2；Roughness = (2/(clamp(Shininess,2,1000)+2))^0.25。因为 Shininess 被钳到至少 2，**M4 所有槽的粗糙度恒为 0.841**，作者画的粗糙度图完全不起作用。游戏里看到的 M4 就是"非金属、低高光、均匀哑光"的样子。表中 M4 行是作者原图的数值。
- HK416 的颜色取自《少女前线》404 主题涂装（棕褐色聚合物），只参考它的表面响应，不采用其颜色。

## 2. 材质卡预设（`surface_card.json`）

资产：`/Game/Weapons/WeaponSurface/Presets/MI_WS_<名称>`，父材质 `/Game/Weapons/WeaponSurface/Master/M_WeaponSurface`。

| 预设 | 主参考 | 底色 | 金属度 | 粗糙度 | 边缘磨损 |
|---|---|---|---|---|---|
| AnodizedAluminum | HK416 上机匣 | .018/.020/.019 | 1 | .34 | .12，露底 .12 |
| BluedSteel | AKM 钢件 | .058 | 1 | .36 | .12，露底 .22 |
| PolishedSteel | AKM 露钢响应 | .20 | 1 | .30 | .15，露底 .34 |
| Polymer | HK416 表面响应，M4 黑色 | .019 | 0 | .44 | .10，边缘不变金属，只抛光 |
| Rubber | M4 托垫 | .0103 | 0 | .70 | 0 |
| Interior | AKM 内部 | .004 | 0 | .75 | 0 |
| Bakelite | AKM 胶木 | .038/.0052/.0018 | 0 | .36 | .10 |
| **MatteCoated** | M4 运行时机匣 | .052 | 0（Specular .2） | .84 均匀 | 0，只留 .03 的边缘抛光 |
| **MattePolymer** | M4 运行时握把／枪托 | .019 | 0（Specular .2） | .84 均匀 | 0，轻微点纹 |

**用户实测后的选择（2026-09-30）**：A762 第一版用的是 HK416／AKM 的金属身份（金属度 1），实机看起来像"脏金属"：深色金属反射天空，斑驳的粗糙度和 Meshy 图集颜色也被放大。用户要求改成 M4 的聚合物哑光质感，所以增加了 MatteCoated 和 MattePolymer 两个预设：非金属，Specular .2，粗糙度 .84 且均匀，不做程序化磨损，大块斑驳降到 .02。用户随后反馈这组哑光和改动前看不出区别，于是又增加了 **Clean 金属组**（CleanSatinSteel：.034–.037，粗糙度 .42；CleanAnodized：.021，粗糙度 .46；CleanPolishedSteel：.16，粗糙度 .30；CleanPolymer：.019，非金属，粗糙度 .55）。规则是：保留金属度 1，底色比 AKM 暗，避免亮场景下的反射把枪面染色；去掉大块颜色和粗糙度斑驳、细划痕、握持抛光，以及生成图集的颜色和粗糙度；只保留亚毫米细纹和连续、不打碎、只略亮的加工边线。**A762 当前用 Clean 金属组（第 3 版，待用户实测）。** 后续自研枪默认先用这一组；哑光组和带磨损的金属组保留，供风格需要时使用。

原则：
- 阳极铝、发蓝钢这类金属按金属度 1 处理；漆、聚合物、胶木、橡胶按金属度 0 处理。
- 只有露出的底材（边缘磨损、细划痕）才变成金属。
- 禁止使用 0.3–0.9 这类中间金属度。

干净档：`EdgeWear` 约 .10–.15（HK416 磨损只占 2%–4% 面积），`ScratchAmount` .03–.08。A762 试点把 `CavityDarken` 上限定为 .2，`AOStrength` 定为 .7（原因见第 5 节）。

## 3. 母材质结构

- **源细节（UV0）**：`SourceBaseColor`（按 `SourceColorWeight` 混入）、`SourceRoughness`（`SourceRoughnessWeight`／`Pivot`），以及保持不变的结构法线 `SurfaceNormal`。
- **材质层**：`FinishColor`、`Metallic`、`Roughness`、`Specular`。
- **细纹**：`GrainTexture`（`T_WS_Grain`：R 细颗粒，G 大块斑驳，B 细划痕，A 点状纹理）。在蒙皮前局部坐标中做三平面投影，尺度用 `GrainTileCm` 按厘米设定，只影响底色、粗糙度和点纹，不增加颗粒法线。
- **磨损遮罩**：`SurfaceMask` 为 RGBA，R 凸边，G 凹腔，B AO，A 暴露度（1 − 凹腔）；`MaskUVChannel` 为 0 表示 UV0，为 1 表示 UV1。据此计算边缘露底（`EdgeWear`／`EdgeColor`／`EdgeMetallic`／`EdgeRoughness`）、边缘抛光（`EdgeHighlight`）、凹腔（`CavityDarken`／`CavityRoughness`）、握持抛光（`HandlingPolish × A`）和细划痕（`ScratchAmount`）。
- **淋湿**：内置 `WeaponWetness`，响应沿用 HK416 的水膜和水珠效果。水珠用 UV0 乘 `BeadScale`（每厘米约 2.42 个水珠格，数值 = 2.42 ÷ 该槽 UV0 每厘米的 UV 单位）。原公式在干燥时仍会留下少量水珠，这里加了覆盖系数，干燥时完全隐藏。
- 天气组件通过 `WeaponSurfaceStandard::SelfWetSource`（`Source/FPSGAME/Weapons/WeaponSurfaceStandard.h`）识别基于本母材质的实例，直接把实例本身当湿润材质。**不需要干湿成对材质，也不需要登记湿润材质表。**

着色代码：`SourceAssets/WeaponSurface20260930/hlsl/*.hlsl`。后台工具只做材质图转换，着色代码用 `validate_hlsl.py` 离线跑 fxc（SM5）和 dxc（SM6）编译，2026-09-30 全部通过。

**版本约定**：母材质图版本记在元数据 `WeaponSurfaceGraph`（当前 `WS1-g1`）。`build_master.py` 只就地更新着色代码、参数默认值和预设实例。要改连线结构，必须新建资产名，不要重建已被网格引用的母材质图。修改预设或母材质会影响所有已接入的枪。

## 4. 新枪接入步骤

1. **导出几何**：用 `dump_mesh_geometry.py` 导出运行时 LOD0 几何（skeletal FBX 在无界面 commandlet 中会断言）。
2. **分析 UV**：用 `analyze_uv.py` 查看 UV 是否重叠、密度多少。UV0 唯一时直接烘焙到 UV0；UV0 平铺时需要一套唯一的 UV1。
3. **核对已有 UV 通道**：先查网格的 UV 通道数，以及手臂材质（`M_BareNative_Default`／`M_BareFamily_*`）是否已占用 UV1–3。**只改枪体三角形**，手臂三角形的 UV 保持原值。
4. **烘焙遮罩**：边缘用 Bevel 法线偏差，再乘上网格二面角得到的凸边门控；凹腔和 AO 在每个顶点做射线，射线起点离开表面 0.5 mm，用来跳过换弹用的重合重复壳。**遮蔽必须在就位姿态下计算**：先导出逐顶点主骨骼，再按待机动作第 0 帧，把弹匣、枪机、扳机等非根骨骼零件移到实际位置（A762 见 `seated.py`、`bake_a762.py` 中的 `seat_bake_copy`）。A762 第 1 版在绑定姿态下烘焙，枪机被误判为大面积遮蔽，已重烘。几何缺陷的排查也要在这个姿态下做。注意：Blender 在编辑／物体模式切换后，RNA 引用会失效，必须重新获取 UV 层。
5. **写入网格**：用 Geometry Script 写 UV1。保存前比较写入前后的指纹：所有 UV 通道、手臂 UV1、法线、骨骼权重、位置和材质槽，任何一项不一致就不保存。写之前先备份 `.uasset`。
6. **建实例并绑定**：每个槽建一个材质实例，父材质为对应预设，逐槽绑定并读回核对；再按第 5 节检查可见表面的遮罩统计。
7. **几何细节（按需，A762 第 5 版为样板）**：
   - 生成件表面起伏时，只对平整面板做双边法线去噪，并限制位移（`plan_denoise.py`）。
   - 重建的硬表面件：二面角超过 40° 的边改成 0.35 mm 双段圆角，法线用按角度平滑加面积加权（`rebuild_slots_blender.py`）。
   - 粗分段的曲面壳做一级带折边的细分。
   - 铆钉等特征用射线贴到就位姿态的表面上。
   - 以上都一次写入网格（`apply_a762_geometry.py`），写入后必须重新导出、重做 UV1 并重烘遮罩。
8. **配件**：每个配件槽建自己的实例，遮罩走 UV0，参考 `plan_accessories.py` / `install_accessories.py`。
   - 不能复用枪体实例：枪体实例采样的是 UV1 上的枪体遮罩。
   - UV0 不重叠的配件烘焙遮罩，并经 `qa_accessory_masks.py` 检查；遮蔽大面积误判的改用中性遮罩。
   - 玻璃、分划、半透明材质和遮罩混合外壳保持原材质。

## 5. 已知限制

- 凹腔和 AO 是逐顶点计算的（这样才能避开重合壳）。为了不在低模大面上被抹开，烘焙副本先把长边加密到约 2 mm 再取样（`bake_a762.py` 中的 `densify`）。预设仍压低了 `CavityDarken` 和 `AOStrength`。
- 低面数的曲面会被识别成"边缘"（A762 弹匣），这类槽要关掉或降低 `EdgeWear` 和 `EdgeHighlight`。
- 写入的 UV1 只存在于 UE 资产的源模型里。**如果之后从旧 FBX 重新导入这个网格，UV1 会丢失**，必须重跑接入步骤 2–5。
- A762 的 24 个配件已接入（第 5 版）。其他枪的配件还没有。
- 项目共用的远程执行桥（`Tools/AssetPipeline/ue_python_exec.py`）按名字里是否含 "FPSGAME" 挑编辑器，分不清 FPSGAME 和 FPSGAME-mp。本标准的运行入口 `run_ue.ps1` 只认 `D:/FPS3D/FPSGAME/FPSGAME.uproject`：两个工程同时开着时直接拒绝，不向任何编辑器发送调用。

## 6. 状态

本轮已完成：测量；母材质、预设和纹理的制作与保存（后台 commandlet）；着色代码离线编译；天气识别的 C++ 改动（当前 Editor DLL 已包含该符号）。**未运行游戏、未做渲染或视觉验收**，效果由用户测试。
