# 丘陵地表材质：分层、凹凸与细节（2026-09-18 现行）

本次把温带丘陵的运行时地表材质从"三套贴图按噪声加权平均"重做成**分层的、按高度图混合的、带视差凹凸的近景地表**，并给 PCG 草层加了一层嵌入式碎石。目标效果是参考图那种有层次、有凹凸、有细颗粒细节的地面，而不是一张平铺的贴图。

旧图（`build_temperate_hills.py` 的三层版）和河岸图（`build_pebble_shore.py`）都已被本次重建取代；两个脚本保留为历史记录，**不要再重跑**，否则会把地表退回旧结构。

## 1. 交付物与资产路径

| 资产 | 作用 |
| --- | --- |
| `/Game/WorldGeneration/TemperateHills/M_TemperateGround` | 丘陵地表本体（四家族分层 + 视差 + 细节）。62 个材质表达式 |
| `/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround` | **数据资产实际指向的地表**：丘陵本体 + 河岸/卵石扫描混合。87 个表达式 |
| `DA_TemperateHillsStreaming.GroundMaterial` | 仍指向 `M_PebbleShoreGround`，路径未变，软引用不需要迁移 |
| `Tools/WorldGeneration/build_hills_ground_v2.py` | 幂等重建脚本（先备份两个材质再原地重建） |
| `Tools/WorldGeneration/dump_ground_hlsl.py` + `validate_ground_hlsl.ps1` | 离线编译校验（见第 6 节） |

重建脚本可以从任意状态重跑：它先复制两个 `.uasset` 到 `Saved/GroundMaterialUpgrade20260918/BeforeAuthoring-<时间戳>/`，再 `delete_all_material_expressions` + 重建 + `recompile_material` + 保存。脚本不会改动地图、关卡 Actor 或数据资产的其他字段。

## 2. 四个地表家族

原来的三层（草苔／草土／碎石路）纹理尺度统一、过渡只靠噪声梯度。现在四层各有自己的世界投影尺度，非整数比例错开以抑制平铺感：

| 家族 | 来源 | 投影尺度 | 高度图 | 负责的地面 |
| --- | --- | --- | --- | --- |
| 草 Grass | `PN_GrassLibrary/ground_I_*` | 5.6 m | 有 | 平坦、湿润、有草的缓地 |
| 土 Soil | `UnrealNormandy/T_LC_GroundSoilExcavated_00A_*` | 3.0 m | 有 | 默认的扰动土层 |
| 砾 Gravel | `UnrealNormandy/T_LC_MossyGravel_00A_*` | 2.1 m | 有 | 坡面、碎石带 |
| 干壳 Dry | `UnrealNormandy/T_LC_GroundDry_00A_*` | 7.5 m | **无** | 平坦偏干的苍白龟裂石质地面 |

干壳层就是参考图那种"苍白、龟裂、嵌石子"的观感来源，所以它虽然缺高度图也单独占一层：它只参与颜色/法线/粗糙度混合，高度固定取 0.5，并把高度混合权重让给有高度图的层。世界坐标投影自带每层独立的 UV 偏移常量，即使两层尺度相同也不会完全重叠。

家族权重由坡度 + 两个斑块噪声场（约 247 m 与约 55 m）算出，再归一化：

- 砾石随坡度上升，并在斑块噪声高处成片出现；
- 草在缓坡 + 湿润（`max(Wetness, 顶点色 G)`）处占优；
- 干壳在缓坡 + 斑块噪声低处 + 干燥处占优；
- 土是余量层，并保底 0.10 防止某处权重全零。

噪声哈希常量沿用旧图（`127.1 / 311.7 / 43758.5453`），所以同一世界种子的斑块布局与旧版一致，不会因为换材质而让整张地图的色块搬家。

## 3. 按高度图混合（层次感的来源）

四家族权重只是一组大尺度遮罩，直接归一化混合会得到"柔和的渐变"。本版在其后追加一次**高度加权**：

```
boost_i = saturate( (h_i - Bias) * Contrast + 1 )
w'_i    = w_i * boost_i ,  再归一化
```

`h_i` 是该家族自己的高度图采样（干壳固定 0.5），`Bias` 默认 0.34、`Contrast` 默认 2.4。效果是**每个家族在自己表面凸起的地方抢到地面**，交界沿各自的浮雕互相咬合，而不是一条软边——这是参考图层次感的主要来源。

## 4. 视差凹凸（凹凸感的来源）

近景的真实凹凸由有界的**视差遮蔽步进（POM）**提供，做法沿用本项目河岸那套已验证的实现：

- 在共享基础 UV 空间里步进，复合高度取土与砾两张高度图的加权（`Blend = w_gravel / (w_soil + w_gravel)`），因此一个像素内只多两次采样；
- 步数上限 `GroundReliefSteps`（默认 10，代码内 clamp 到 24），并随俯角降低；
- 循环外算 `ddx/ddy` 再传 `Texture2DSampleGrad`，避免"循环内求梯度"的编译错误；
- 距离渐隐：`GroundReliefFadeM`（默认 7 m）以内满强度，到 2.3 倍距离完全消失；再乘一个贴地视角门（`smoothstep(0.15,0.42,V.z)`）；
- **在河岸范围内乘 `(1 - 顶点色 R)`**：河岸已经有自己的卵石视差，两套不能叠加；
- 湿润时（`Wetness` 或顶点色 G）凹凸深度最多衰减 65%，湿地面看起来更平。

步进结果回乘世界尺度后再按家族尺度分别投影，因此各层尺度不同也不会让视差偏移错位。

## 5. 法线、细节与其余通道

- **法线用白噪混合（whiteout）**逐层串接：`normalize(float3(a.xy + b.xy*w, a.z*b.z))`。旧图是 `normalize(lerp(...))`，会把浮雕压平；新写法保留各层起伏。最后乘 `GroundNormalStrength`（默认 1.15）。
- **细颗粒**：再用一次砾石贴图，以 0.9 m 尺度采样，按亮度比例调制底色（`lerp(1, 0.78+0.44*luma, Strength*Fade)`），并混入法线。亮度比例法不改变色相，近距离时地面出现细砂颗粒，`GroundDetailFadeM`（默认 10 m）以外衰减。
- **宏观变化**：两个尺度的噪声（约 192 m 与约 48 m）同时调制底色（`GroundMacroStrength`，默认 0.10）与粗糙度，打断远处可见的平铺重复。
- **环境光遮蔽**：新增 `AMBIENT_OCCLUSION` 输出，由同一批高度图算空腔项 `lerp(1, cavity, GroundAOStrength)`。旧图在丘陵上没有 AO（只在河岸有），这是"层次+自阴影"观感的另一半。
- **粗糙度**：三套 Normandy 贴图的 RHAOM 的 R 通道（沿用旧图已验证的通道约定）+ 草的常量 `GroundGrassRoughness`，再被宏观噪声调幅、被湿润度压到 `GroundWetRoughness`（默认 0.26）。

顶点色契约未变，仍然是 `TemperateHillsStreaming.cpp:121` 写入的 `FVector4f(Bank, Wet, PebbleCover, 1)`：R 河岸、G 湿润、B 卵石滩。`Wetness` 标量参数名也未变，`ATemperateHillsWorld::Tick` 的天气驱动照旧生效。

## 6. 离线编译校验（本机可用）

commandlet 里没有渲染，材质着色器**不会**真正编译（`recompile_material` 在无渲染的 commandlet 里返回的是空错误表，不代表 HLSL 通过）。本机因此用两层离线校验：

**第一层：Custom 节点 HLSL**

1. `dump_ground_hlsl.py`（无头运行）把两个材质里每个 Custom 节点的代码连同**按连线推断出的输入类型**导出成独立 `.hlsl`，并补上 `Texture2DSampleGrad` 桩；
2. `validate_ground_hlsl.ps1` 用 `fxc /T ps_5_0` 与 `dxc -T ps_6_0` 各编一遍；
3. 51 个节点 × 2 个目标 = 102 次编译，当前 **0 失败**。

这条链路抓到两个真实问题：Custom 节点里**不能定义辅助函数**（材质编译器把节点代码包在函数体里，`float f(...){...}` 会报语法错误），以及 `float4(a,b,c,0.5)` 这类**参数个数**错误（贴图采样是 float4，必须写 `.r`）。两者在编辑器里只会表现为材质编译失败，靠肉眼看图很难定位。

**第二层：TextureSample 的采样器类型**

`check_ground_samplers.py` 遍历两个材质里全部 24 张贴图的每个采样节点，按 UE 的 `UTexture::GetMaterialType()` 规则（**先看压缩设置，sRGB 只区分 Color/LinearColor**）算出应该用的 `SamplerType` 并比对。

2026-09-18 首次实机验收时地面**整片变成默认棋盘格材质**，日志里就是这一条：

```
LogMaterial: Warning: [AssetLog] .../M_PebbleShoreGround.uasset:
  Failed to compile Material for platform PCD3D_SM6, Default Material will be used in game.
  (Node TextureSample) Sampler type is Linear Color, should be Masks for ground_I_height
  (Node TextureSample) Sampler type is Linear Color, should be Masks for T_LC_GroundSoilExcavated_00A_RHAOM
```

根因：建材质时按 `srgb` 猜采样器类型，而本工程的高程图与 RHAOM 是 **`TC_Masks`** 压缩（线性但必须按 Masks 采样），猜成了 LinearColor。采样器类型不匹配是**硬编译错误**，不是警告——症状就是整片地表退回默认材质。

现在 `build_hills_ground_v2.py` 不再猜：`required_sampler_type()` 直接按压缩设置映射，与 UE 规则同源，所以这类不匹配在生成阶段就不可能再出现；`check_ground_samplers.py` 作为回归闸门（当前 `verdict=OK mismatches=0`）。

**真编译的路子**：`UnrealEditor-Cmd.exe <uproject> -run=DerivedDataCache -fill` 会真的编译材质着色器并写入 DDC，失败时输出上面那条同样的日志。它遍历整个工程的资产，很慢（本机约 10 分钟到 /Game/Z*），但它是无头环境下唯一能拿到"真编译通过/失败"的手段。**记住：不要用"无头 commandlet 跑完没报错"当材质编译通过的证据。**

2026-09-18 修复后实跑结论（`Saved/GroundMaterialUpgrade20260918/ddc2.log`）：

```
LogMaterial: Display: Missing cached shadermap for .../M_PebbleShoreGround... in PCD3D_SM6 ... compiling.
LogMaterial: Display: Missing cached shadermap for .../M_PebbleShoreGround... in PCD3D_SM5 ... compiling.
LogMaterial: Display: Missing cached shadermap for .../M_TemperateGround...   in PCD3D_SM6 ... compiling.
```

两个材质在 SM6 与 SM5 上**都真编过了，全日志零 LogMaterial 错误**（该轮唯一失败的是无关的既有资产 `NiagaraExamples/M_SmokeAndFire_Sprites_Backup`，缺材质函数）。**着色器编译已证实，画面效果仍未验收。**

## 7. 美术可调参数

全部是标量参数，改完立即生效，不需要重编译 C++，也不需要重进地图：

**第一次看效果时按这个顺序调**（投影尺度是本次唯一"只能靠眼睛定"的数值，没有历史值可循）：

1. `GroundSoilTilingM` / `GroundGravelTilingM` / `GroundDryTilingM` / `GroundGrassTilingM`：先让每层贴图的细节大小看起来像"真实的土/砾/干壳/草"，再管其他。干壳层 7.5 m 是本次最不确定的一个（龟裂板块会显得偏大），偏大就往 5 m 收。
2. `GroundReliefDepthCm`：凹凸深度。9 cm 是按土块/砾石尺度取的，觉得"假"就降到 5–6，觉得"平"就升到 12。
3. `GroundHeightBias` / `GroundHeightContrast`：层次过渡的锐度。Bias 调低会让各层更"抢地"、过渡更碎。
4. `GroundAOStrength`：自阴影强度，影响层次感的读感。
5. `GroundMacroStrength`：远处平铺感是否还看得出来。

| 参数 | 默认 | 作用 |
| --- | --- | --- |
| `Wetness` | 0（天气驱动） | 湿润：压暗、压粗糙度、压凹凸 |
| `GroundBaseTilingM` | 3.4 | 共享投影尺度（视差在此空间步进） |
| `GroundReliefDepthCm` | 9 | 视差深度；设 0 等于关闭凹凸 |
| `GroundReliefFadeM` | 7 | 凹凸满强度距离（2.3 倍处消失） |
| `GroundReliefSteps` | 10 | 步进上限（代码 clamp 24） |
| `GroundHeightBias` / `GroundHeightContrast` | 0.34 / 2.4 | 高度混合的门槛与锐度 |
| `GroundNormalStrength` | 1.15 | 法线强度 |
| `GroundMacroStrength` | 0.10 | 大尺度色差/粗糙度变化 |
| `GroundDetailStrength` / `GroundDetailTilingM` / `GroundDetailFadeM` | 0.5 / 0.9 / 10 | 细颗粒强度、尺度、渐隐 |
| `GroundAOStrength` | 0.65 | 空腔遮蔽强度 |
| `GroundGrassRoughness` / `GroundWetRoughness` | 0.86 / 0.26 | 草层粗糙度、湿润粗糙度 |
| `GroundGrassTilingM` / `GroundSoilTilingM` / `GroundGravelTilingM` / `GroundDryTilingM` | 5.6 / 3.0 / 2.1 / 7.5 | 各家族投影尺度 |

河岸部分的参数（`PebbleReliefDepthCm`、`PebbleNormalStrength`）保持不变。

**开销**：固定采样 16 张（四家族 albedo 4 + normal 4 + 高度 3 + 粗糙度 3 + 细颗粒复用砾石 2），近景再按步数每步多 2 张高度采样，10 步时最坏约 36 张。相比旧版 9 张明显更重，但视差只在 7 m 内、贴地视角下发生，远处退回普通法线贴图。若需要降载，先把 `GroundReliefDepthCm` 调到 0（关掉步进循环）或把 `GroundReliefFadeM` 调到 4。

## 8. PCG：嵌入式碎石（`GroundDebris`）

草层 PCG（Layer 3）新增一趟 `GetGroundDebrisPlacements`（`TemperateHillsGroundDebris.cpp`），把碎石**用几何**补在材质干壳层看起来该有石头的地方：

- 复用已加载的 `Assets->Rocks` 网格，按**目标边长**反推缩放（`GroundDebrisSizeCm`，默认 20 cm，逐个 ±55% 抖动），所以换岩石包不会让石子尺寸跑掉；
- 按网格自身包围盒底心对齐再下沉（埋深为边长的 30–54%），是"嵌进地面"而不是"摆在地表"；
- 只出现在坡度缓于约 38°、**约 250 m 干燥斑块噪声**偏高、坡面中等、且离开道路 300 cm 以上的地面；出生点 1.6 km 内与河岸（`Bank > 0.30`）不生成；
- 走草层的 32 m 单元与 35/60 m 距离裁剪，`NoCollision`，不参与采集身份，候选 ID 用 `0x40` 低字节段（`0x60` 是河岸卵石、`0x80` 是草丛点缀）；
- 参数：`GroundDebrisSpacingCm`（默认 240，候选间距上限）、`GroundDebrisCoverage`（默认 0.30）、`GroundDebrisSizeCm`（默认 20）。

干燥斑块用的是**代码侧**的 250 m 噪声场，与材质里的 GLSL 哈希不同源，所以两者是"风格一致"而不是"逐像素对齐"。这是有意的：把着色器哈希复制到 C++ 会变成两处必须同步的隐式契约。

## 9. 未做 / 边界

- **着色器编译已证实**（SM6 + SM5，见第 6 节），但**画面效果没有验收**：构图、颜色、层次和疏密的实际观感按项目规则由用户实机测试。投影尺度是唯一"只能靠眼睛定"的数值，调试顺序见第 7 节。
- 地形的实际几何起伏没有变化：256 m 分块近段仍是 2 m 顶点间距，所有"凹凸"都来自材质视差。要走真几何凹凸需要提高网格密度或用 Nanite Landscape，而运行时 DynamicMesh 地形不支持 Nanite。
- 没有接 RVT（Runtime Virtual Texture）：PCG 摆的石头、道路贴花与地表的融合仍是"各自独立"。RVT 是把网格/贴花混进地表的正统做法，但它要求地形材质改成 Material Attributes 并铺设 RVT Volume，与运行时流送地形的边界管理叠加，属于下一步。
- 干壳层没有高度图（Normandy 的 `T_LC_GroundDry` 只有 RHAOM），所以它不参与视差，高度混合里固定 0.5。若以后要它参与凹凸，需要补一张高程图或从法线反推。
- `PN_GrassLibrary` 的另外 6 套地面贴图（`ground_II..VII`）本次未用；`ground_II` 的细密点状高程图适合做更细的砂砾层，需要时再加。
- 三层旧图与河岸图的作者脚本没有删除，但它们**不再能产出当前结构**；重建一律走 `build_hills_ground_v2.py`。
