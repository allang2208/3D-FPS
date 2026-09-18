# 罗马喷泉（蛋糕塔）水体改造：更像水 + 溢流落水（2026-09-18）

用户口径（本轮原文）："肯定是要更像水做啊。而且要做溢流和落水。从上往下进行流淌，水声用占位，可以接受为逻辑构建。"
**按 AGENTS.md 全局规则：本批未实机验收，进游戏测试由用户执行。**

前四轮（v1 悬空水盘 → v2 填满碗腔 → v3 换不透明水/抬水位/挪位 → v4 加中央基座）都在调**几何与结构**；
这轮按"水的运动 + 水的接触"重做，并把它升级成逻辑构件。

## 1. 诊断结论

| 症状 | 根因 | 本轮处理 |
| --- | --- | --- |
| 悬空 | ① 关卡里的水柱是**硬编码 z=720**，而喷泉 actor 在 z=−360、网格高 720 → 水柱比塔尖高 **360 cm**，真的浮在空中；② 水线与石头之间**没有任何接触线索**（无泡沫、无湿痕、无焦散）；③ 水是不透明平板，看不出深度 | ① 水柱改由**主网格包围盒**算到塔尖；② 加 3 级水线泡沫环 + 湿痕带 + 3 处穿出物（基座/柱墩/松果）接触环 + 3 处落点泡沫环；③ 水面换回**半透明**（`M_Water_Clean` 实例，带深度淡出与多层波浪），盆底加焦散衬底 |
| 僵硬 | 水完全不动：三级盘沿一滴水都不落、没有落点水花、水面没有波纹；只有塔尖一根引擎模板水柱 | 加**三级溢流水帘 + 台阶短帘**（自上而下：顶盘→中盘→大盘→台阶），泡沫/水痕自算柱面 UV 滚动（不依赖网格 UV），落点配泡沫环 |

## 2. 成品

### 2.1 材质（`/Game/Props/RomanFountain20260917/Materials/`）

| 资产 | 父级 | 说明 |
| --- | --- | --- |
| `M_FountainWaterFilm` | — | 工程自制水膜材质（Unlit + Translucent + TwoSided）。**自算柱面 UV**：从物体空间位置取 `atan2(y,x)` 与 `−z`，按 `FoamSize(cm)` 归一，所以泡沫尺寸是**世界尺寸**，与网格 XAtlas UV 无关；两层泡沫贴图反向滚动 + 对比度 + Fresnel 提亮 |
| `MIC_FountainFoam` | 上面那个 | 白泡沫（水线/落点/穿出物接触环）：FoamSize 55、OpacityBase 0.42 + OpacityFoam 0.5 |
| `MIC_FountainWet` | 上面那个 | 深色湿膜（水线以上到盘沿的湿痕带）：FilmColor (0.15,0.17,0.18)、OpacityBase 0.34、FresnelBoost 0.55 |
| `MIC_FountainCascade` | 上面那个 | 溢流水帘：FoamSpeed 0.22/0.38（快速向下）、OpacityBase 0.6、贴图用 `T_Waterfall_Foam_Directional` |
| `MIC_FountainWater` | 包 `M_Water_Clean` | 水面：Water_Colour_Light/Dark 青调、Opacity 0.55、Roughness 0.05、SamplingScale 3.0、Wave Height 0.35、Fresnel Power 4.0（**全部暴露参数，可在编辑器直接调**） |
| `MIC_FountainCaustics` | 包 `M_Caustics` | 盆底焦散衬底（Colour 青绿、SamplingScale 1.6） |

### 2.2 网格

| 资产 | 内容 |
| --- | --- |
| `SM_RomanFountain_20` | 主网格不变（960×960×720、23,808 tri、占格 48×48×36）；**slot1 从 `M_Water_Opaque` 换成 `MIC_FountainWater`**，slot0 仍是 `M_RomanStone_V2` |
| `SM_RomanFountain_WaterFX` | 新增：**20 件薄壁实体**（0 开放边、20 连通体、13,184 tri、bbox 958×958×552）。4 槽：泡沫 / 湿膜 / 溢流 / 焦散。包含 3 级水线泡沫环、3 条湿痕带、3 处穿出物接触环、**4 段溢流水帘**、4 处落点泡沫环、3 片盆底焦散衬底。**不带碰撞**（运行时组件为 NoCollision、不投影） |

尺寸按 1× 模型写、构建时 ×2，与 `build_fountain_20260917.py` 的 PROFILES 同源；水位（1×）74/206/282，盘沿 82/214/286。

### 2.3 逻辑构件与接入

| 项 | 内容 |
| --- | --- |
| `AColdSteelFountain`（新 C++） | 组件：`FountainMesh`（主网格，BlockAll）＋ `WaterFxMesh`（水效网格，挂主网格之下、NoCollision、不投影）＋ `Jet`（引擎 Niagara 模板 `FountainLightweight`，位置按包围盒算到塔尖）。`Configure(Surface)` **只覆盖 slot0 大理石**，水/泡沫槽保持自己的实例 |
| 质量开关 | `fps.Fountain.Quality`：0 = 只留主网格水面（关水膜/溢流/水柱/水声），1 = 默认，2 = 预留。0.25 s 内生效（actor 以 0.25 s 为 tick 间隔） |
| 占位水声 | 工程**没有水流循环声**（全量盘点过：192 SoundWave + 29 SoundCue，只有脚步水花）。按用户"水声用占位"的要求：玩家 18 m 内每 1.4–3.2 s 随机播一次 `S_splash1/S_splash2/S_splash1_deep`（音量 0.5、±8% 音高），可在 actor 上关掉或调参数 |
| 调色板 | `roman_fountain` 的 `ActorClass` → `/Script/FPSGAME.ColdSteelFountain`，显示名 → 「罗马喷泉（蛋糕塔·自带水效）」，占格仍是 **(48,48,36)**、Mesh 仍 `SM_RomanFountain_20`（面板缩略图不带水效） |
| 关卡 | `DayNight_Lighting`：旧的 `RomanFountain1`(StaticMeshActor) + `RomanFountainFX_Jet`(NiagaraActor) → 合成一个 `AColdSteelFountain`，位置沿用旧变换 (1350,−1550,−360)。**旧水柱在 z=720（比塔尖高 360），新类按包围盒放** |

## 3. 复现与证据

```text
# 1. 水材质 + 实例 + 水效网格 + 主网格水槽
UnrealEditor-Cmd.exe <uproject> -run=pythonscript \
  -Script=D:/FPS3D/FPSGAME/SourceAssets/RomanFountain20260917/build_fountain_water_20260918.py ...
# 2. 构建（Game + Editor，编辑器关闭时）
Tools/Build/Build-Editor.ps1
# 3. 调色板登记 + 关卡迁移（无头必须带 FOUNTAIN_HEADLESS=1，
#    否则 is_in_play_in_editor() 会 ACCESS_VIOLATION 崩进程）
$env:FOUNTAIN_HEADLESS='1'; UnrealEditor-Cmd.exe <uproject> -run=pythonscript \
  -Script=D:/FPS3D/FPSGAME/SourceAssets/RomanFountain20260917/register_fountain_prefab_20260918.py ...
```

| 证据 | 内容 |
| --- | --- |
| 水材质 | `M_FountainWaterFilm` 62 个表达式；Emissive ← LinearInterpolate、Opacity ← Clamp；`recompile_material` 返回**空错误表** |
| 实例参数读回 | `MIC_FountainWater` 11 scalar + 2 vector（Opacity/Roughness/Specular/SamplingScale/SpeedX/SpeedY/Wave Height/Wave Size/Wave Speed/Wave Normal Speed/Fresnel Power）；`MIC_FountainCaustics` Speed/SamplingScale/Colour；三个水膜实例 9 scalar + 1 vector + 2 texture |
| 水效网格 | `tris=13184 comps=20 open_edges=0 bbox 958×958×552`、四槽 = Foam/Wet/Cascade/Caustics |
| 主网格 | `bbox 960×960×720 tris=23808 slots=['M_RomanStone_V2','MIC_FountainWater']` |
| 调色板 | 读回 `roman_fountain cells=(48,48,36) actor=ColdSteelFountain`，落盘 FRESH |
| 关卡 | 迁移 11 项全 PASS，umap mtime 13:05:33 |
| 构建 | Game `Saved/BuildEditor/fountain-water-game-20260918.log`、Editor `Saved/BuildEditor/build-20260918-130435.log` 均 Succeeded |

发布记录：提交 `780c93a`（`origin/main`），发布目录 `D:/FPS3D/FPSGAME`，普通推送 `HEAD:main`。
内容依赖（本机 `Content/*`，按忽略规则不入库）：`SM_RomanFountain_20`、`SM_RomanFountain_WaterFX`、
`M_FountainWaterFilm` 与 5 个 `MIC_Fountain*` 实例。
**待办**：喷泉 v1–v4 的作者脚本（`build_fountain_20260917.py`、`scale_fountain_2x_20260918.py`、
`add_socle_20260918.py`、`place_fountain_2x_20260918.py`、`probe*/verify*`、`forensic_fountain.obj`）在本轮之前
就**未被跟踪**（不是本轮的改动），所以新克隆里只有本轮的 `build_fountain_water_20260918.py` 与
`register_fountain_prefab_20260918.py`；是否把它们一并入库需要用户确认。

## 4. 交给用户的实测清单（本轮未实测）

1. 进游戏看关卡喷泉：**水柱应贴在塔尖**（不再悬在塔尖上方）；三级盘沿应有向下流动的水帘，落点有泡沫环；水线处有泡沫与湿痕，水面半透明能看到盆底焦散。
2. 走近听：每 1–3 秒一次水花（占位音）——若嫌吵，关 actor 的 `bEnableAudio` 或调 `AudioMinInterval/AudioMaxInterval/AudioVolume`。
3. 建造面板（大理石 → 其他构造）放一座喷泉：**应和关卡里一样有水效**，且大理石跟随材质行、水仍是水。
4. 控制台 `fps.Fountain.Quality 0/1` 切换：0 应只剩水面材质（无泡沫/水帘/水柱/水声）。
5. 观感调参（都在 `Props/RomanFountain20260917/Materials` 的实例上，即时可见）：水太透 → `MIC_FountainWater.Opacity`↑；泡沫太密/太淡 → `MIC_FountainFoam.FoamSize/FoamIntensity`；水帘太亮/太急 → `MIC_FountainCascade.OpacityBase/FoamSpeed`；湿痕太重 → `MIC_FountainWet.OpacityBase`。

## 5. 本轮边界与未做

- **水柱仍是引擎模板** `FountainLightweight`（只调了位置与 scale 1.2）：没有"落回水面"的粒子、没有水雾；要做第二个 Niagara 才算完整。
- **没有粒子层**：落点水花/水雾/飞沫这轮用泡沫环代替；水包里的 `P_Water_Splashes`/`P_Waterfall_Foam` 是 Cascade 时代资产，5.8 可用性未验证。
- **水声是占位**（脚步水花随机播），不是水流循环声；要正式水声需要从 Fab 取一个 water loop 包并记录许可。
- 水面的波浪**尺度与方向受网格 XAtlas UV 影响**（三个碗是各自 UV 岛），只能用 `SamplingScale/SpeedX/SpeedY` 调；如果观感不对，下一轮把三个水面也搬进 WaterFX 网格（那里 UV 可控）。
- 焦散用包内 `M_Caustics`，其混合方式/亮度未目视确认。
- 水效网格 +13,184 tri、7 个半透明网格部件：**未做性能实测**；`fps.Fountain.Quality` 是预留的开关。
- 迁移脚本按"旧 actor 的变换"放置新 actor，没有重新贴地（无头 commandlet 不能用射线问地形）；如果喷泉整体看着埋进地面或浮空，那是 actor z=−360 的历史占位问题，要不要一起改请你定。

---

# 六次迭代：水体 v6（更像水 + 落水驱动，2026-09-18 晚）

用户回执（附 PIE 截图）："也还是很假，水体一点流动感都没有，完全是像个固体一样，你看一下 GitHub 有没有水体优化项目，
我们现有的资产能否做到，向我汇报。"→ 先做调研，再按用户选定的 **A+B** 落地（"剩下按你建议做，注意性能开销"）。
**按 AGENTS.md 全局规则：本批未实机验收，进游戏测试由用户执行。**

## 6.1 调研结论（GitHub 与"现有资产能不能做到"）

GitHub 上没有 UE5.8 可即插即用的"水体美化"项目，开源的几家都是**模拟实验**：
`mushe/NiagaraFluid`（MIT，143★，SPH + 屏幕空间水面渲染，自述 O(N²)、2024-03 停更）、
`AlfonsoPrograms/FluidForge`（MIT，v0.4 早期）、`The-Mooncake/ComputeFluidSim`（MIT）、
`W298/gvdb-fluid-unreal`（MIT，FLIP + NVIDIA GVDB）、`levvs-one/undine`（MIT，液体光学/射线焦散，含 Unreal HLSL）。
**结论：不需要引入第三方**——真正相关的两套系统**已经装在本机引擎里**：
Water / **WaterAdvanced**（245+72+147 资产，含 `NDC_ShallowWater`、`Grid2D_SW_River_Emitter`、`ShallowWaterRiverEmitter`、
`Water_Material_Simple`、`GenerateCausticsTextures`）与 **NiagaraFluids**（530 资产，含 `BP_WaterRenderer` 屏幕空间水面渲染）；
内容包 `/Game/WaterMaterials` 里还有**径向专用**的泡沫/波函数（`MF_Foam_Motion_Radial`、`MF_OceanWave_Motion_Radial`）、
成套的 `SM_Waterfall_Arc`+`MIC_Waterfall_Arc`、溅水材质/贴图/粒子、法线图与立方图。

## 6.2 v6 改了什么

| 项 | v5（用户判"固体"） | v6 |
| --- | --- | --- |
| 水面材质 | 包内 `M_Water_Clean` 实例：深色 + 在 XAtlas UV 上滚法线 + 无反射 | **工程自制 `M_FountainWater`**（58 表达式，编译 0 错误）：极坐标双层滚动法线（世界尺寸可控）、**落水驱动的解析涟漪**（在两个落点半径 r=92/137（1×）上生成向外扩散、按距离衰减的波列）、**场景深度浅→深配色与透明度**、**菲涅尔天空反射（`T_Cubemap`）**、波峰白沫 |
| 溢流水帘 | 白但看不见 | `MIC_FountainCascade` 提亮（FilmColor 0.94/0.97/0.99、OpacityBase 0.78）、泡沫滚动加快到 0.42/0.68、`FoamSize` 减到 34（更细的条纹） |
| 落点 | 只有泡沫环 | 逻辑构件新增 **4 个落点水花**（引擎 `FountainLightweight` 缩到 0.42 放在两级水帘的落水点，±对称） |
| 性能 | 无分级 | 距离分级：**近（≤26 m）全开 / 中（≤62 m）关水花 / 远（>62 m）只留水面材质**；`fps.Fountain.Quality` 0 仍可一键全关；**水效网格排除出 RT 几何与距离场**（`bVisibleInRayTracing=false`、`bAffectDistanceFieldLighting=false`） |

## 6.3 与"真模拟"（B 档）的取舍（需要你知情）

B 档原始定义是"用 WaterAdvanced 的浅水 SWE Niagara 驱动水面"。实现时我改了做法，理由如下：

1. Water 插件的 WaterZone/WaterInfo 是**景观级**水体（构建自己的水体网格与 RT），项目里目前没有任何 Water Body；
   给"玩家可反复放置的喷泉"每座挂一套 SWE 网格 + RT + 水体信息，与"注意性能开销"直接冲突；
2. 无头 commandlet 里不能做视觉验证（也不能按你们规则自渲染），把这种高耦合集成交付出去风险很高；
3. **同样的观感可以用解析涟漪做到**：本工程雨系统的"水面雨点/涟漪"就是解析计算（`Docs/RAIN_UPGRADE_20260910.md`），
   喷泉这轮照这个路子做——落点的扩散波列、按距离衰减、与法线/泡沫联动，成本几乎为零。

如果实机看过 v6 后你觉得"还是想要真的模拟"，可选的下一步是：
① **单座展示用**接 `Grid2D_SW_River_Emitter`/`NDC_ShallowWater`（限定 1 座、非建造物）；
② 用 NiagaraFluids 的 2D 流体 + `BP_WaterRenderer` 生成一张共享涟漪 RT 给若干喷泉采样（需要 1 张 RT + 距离限流）。

## 6.4 证据

- 水面材质：`water recompile -> []`（无错误）、58 个表达式、`BaseColor←LinearInterpolate`、`Opacity←Clamp`、
  `Normal←Custom`、`Emissive←Add`；`MIC_FountainWater` 读回 **23 scalar + 2 vector + 3 texture** 覆盖项（全部可调）。
- 水效网格与主网格：`tris=13184 comps=20 open_edges=0`、`slots=['MIC_FountainFoam','MIC_FountainWet','MIC_FountainCascade','MIC_FountainCaustics']`；
  主网格 `960×960×720 / 23808 tri / slots=['M_RomanStone_V2','MIC_FountainWater']`；脚本 `checks=30 failed=0 / RESULT: PASS`。
- 构建：Game `Saved/BuildEditor/fountain-water2-game-20260918.log`、Editor `build-20260918-142444.log` 均 Succeeded；
  两个二进制里都能搜到 `FountainSplash`（新增的落点水花组件）。
- **踩坑**：v6 第一版给水帘加了 WPO，随后又给水面材质重建表达式表，两次都在无头 MaterialEditor 里
  触发 `Assertion failed: !IsRooted()` 崩进程——**根因是"材质已被已保存的网格/实例引用时，重建它的表达式表"**。
  现在的做法：材质已存在且有表达式就**只改实例参数**，不再重建图；真要改图先删掉引用它的实例（v6 就是这么换掉
  水面实例父级的），或者换一个新的资产名。

## 6.5 交给用户的实测清单（v6 未实测）

1. 水面：应为**亮青、能看到天空反射与连续涟漪**，落点附近波纹最密、向外衰减；不应再是深色镜面板。
2. 水帘：三级+台阶水帘应有明显的**向下快速流动的白色条纹**，亮度和透明度比 v5 高。
3. 落点：两级水帘砸下的位置应有**向上溅起的水花**（4 个 Niagara 组件，缩放 0.42）。
4. 性能：走近时全开、走到 ~26 m 外水花停、~62 m 外只剩水面材质；`fps.Fountain.Quality 0` 全部关掉。
   RT 几何常驻内存告警（截图里的 85.662 MiB）应因水效网格退出 RT 几何而略有下降——请留意是否仍在报。
5. 编辑器里调参（都是实例，即时可见）：`MIC_FountainWater` 的 `WaterColorShallow/Deep`、`OpacityBase`、
   `ReflectionStrength`、`WaveScale/WaveSpeed`、`RippleStrength/RippleFreq/RippleLambda`、
   `MIC_FountainCascade` 的 `OpacityBase/FoamSpeed`。

## 6.6 仍未做（如实记录）

- **没有水雾/飞沫**：引擎模板里没有可直接复用的雾系统，自建 Niagara 在无头环境里做不出来（也无法目视验证）。
- 水帘没有 WPO 摆动（被上面那个断言挡下）；要摆动得在编辑器里手工加 WPO，或改用 Niagara ribbon。
- 水声仍是占位（脚步水花随机播）。
- 焦散仍用包内 `M_Caustics`，未目视确认。
- 性能只有"分级与开关"，**没有实测帧时间**（按规则不做主动性能测试）。

发布记录：提交 `8c283c1`（`origin/main`），发布目录 `D:/FPS3D/FPSGAME`，普通推送 `HEAD:main`。
内容依赖：`M_FountainWater` + `MIC_FountainWater/Foam/Wet/Cascade/Caustics`、`SM_RomanFountain_20`、
`SM_RomanFountain_WaterFX`（均在本机 `Content/*`，按忽略规则不入库）。
关卡里那座喷泉的**新增落点水花组件需要编辑器重载关卡后才会出现在已有实例上**（C++ 新增默认子组件）。

---

# 七次迭代：三条确认的根因（2026-09-18 深夜，只读排查）

用户回执："还是不对，喷泉跟固体差不多，而且喷水的位置也不对。"
这轮**先不盲调**：用两个只读探针把事实钉下来（`probe_water_state_20260918.py`、`probe_level_ground_20260918.py`，
日志 `probe_water.log` / `probe_level.log`）。编辑器开着也能跑、不写任何资产。

## 7.1 根因一：喷泉整座沉进地面 3.6 m（最大的"看起来不对"）

| 探针读数 | 值 |
| --- | --- |
| `Floor`（500 m 地面）包围盒 | z=[**−40..0**] → 地面顶面 z=0 |
| `MarbleFloor_Colonnade` / `RomanPavilion2_Base` / 10 根柱 | z=[0..20] / z=0 / z=20（都在地面上） |
| **`RomanFountain1`（ColdSteelFountain）** | loc z=**−360**、包围盒 z=[**−361..360**] |

`place_fountain_2x_20260918.py` 当初按"pivot 在包围盒中心"用 `-bb.origin.z` 贴地；但喷泉网格 pivot 在**底面**
（探针读回 `origin_z=360`＝高度一半，本地包围盒 z=[0..720]）。于是整座喷泉沉到地面以下 3.6 m：
**大盆与它的水面全埋在地下**，画面里只剩上半截"蛋糕塔"——这同时解释了"跟固体差不多"
（可见水面是被截断的中/顶盘）与"喷水位置不对"（水柱在本地 z=720＝真正塔尖，但相对**可见**的塔顶高了 3.6 m）。

**修法**：`reground_fountain_20260918.py` —— 从名字含 `Floor` 的静态网格 actor 取地面顶面 z，把 Actor 的 z 设成它
（`AlignGeometry()` 会把网格包围盒底面放到 Actor 原点，所以 Actor z = 地面 z），做一次包围盒相交检查后保存关卡。

## 7.2 根因二：水面材质光照模式还是默认值（收不到直射光）

探针读回：`blend=BLEND_TRANSLUCENT`、`shading=MSM_DEFAULT_LIT`、`tlm=TLM_VOLUMETRIC_NON_DIRECTIONAL`。
**半透明 Default Lit 的默认光照模式只吃间接光**，直射阳光几乎不参与 → 水面读成"没有光的暗板"。
上一版脚本按 `TLM_SurfacePerPixelLighting` 找枚举（**本版不存在**）→ 静默留在默认值。
正确名是 **`TLM_SURFACE_PER_PIXEL_LIGHTING`**（探针读出），已写进脚本。

## 7.3 根因三：SceneDepth 节点实际取的是 SceneColor

探针读回：`SceneTexture id = PPI_SCENE_COLOR` —— 上版写的 `PPI_SceneDepth` 也不存在（真实名 **`PPI_SCENE_DEPTH`**），
节点静默退回 SceneColor → "场景深度→浅深配色与透明度"整条链失效（`fade` 恒 0）：水面既无深度感，
透明度只由菲涅尔决定 → 掠射角更实、更像一块板。两处枚举名已改正，并加了"找不到就报 WARN"的护栏。

## 7.4 同时去掉的：四根乱喷的水柱

v6 我拿引擎"向上喷"的 `FountainLightweight` 缩到 0.42 当**落点水花**放在两个落水点周围 —— 实际观感是
**盆里多了四根小喷泉**（"喷水位置不对"的另一半）。已从 `AColdSteelFountain` 移除；要落点水花得专门做 Niagara，
不再复用向上喷模板。

## 7.5 待配合的一步（这轮没能烘到磁盘）

你现在开着编辑器（`UnrealEditor.exe`，16:12 启动），它持有 `.uasset`/`.umap` 的共享锁 → 材质与关卡的写入会
**静默失败**（前几轮踩过 `Error Code 32`）。所以上述修复目前只在脚本/源码里：

1. 你关掉编辑器后回我一声；
2. 我按顺序跑：① `build_fountain_water_20260918.py`（重烘水面材质：光照模式 + SceneDepth + 亮度/透明度/涟漪）
   → ② `reground_fountain_20260918.py`（喷泉贴地）→ ③ `Tools/Build/Build-Editor.ps1`（落点水花移除的 C++ 改动）；
3. 你重启编辑器进 PIE：喷泉应整座立在地面上、水柱在塔尖、水面亮且有涟漪。

## 7.6 执行结果（2026-09-18 16:34–16:39，已落盘并复核）

| 步骤 | 结果 | 证据 |
| --- | --- | --- |
| ① 水面材质属性修复 | `water tlm = TLM_SURFACE_PER_PIXEL_LIGHTING: 5`、`SceneTexture id = PPI_SCENE_DEPTH: 1`、`opacity clamp max = 0.62 (mode CMODE_CLAMP_MAX: 2)`、`water recompile -> []`、**32/32 PASS**、`M_FountainWater.uasset` 16:37:45 落盘（无 `Error saving`） | `SourceAssets/RomanFountain20260917/build_water.log` |
| ② 喷泉贴地 | 地面候选只认"XY 包含喷泉"的面 → `[('Floor', 0.0)]`；`move RomanFountain1: z 20.0 -> 0.0` → **世界包围盒 z=[−1.2..720.0]**；`save=True`，`DayNight_Lighting.umap` 16:38:47 落盘 | `reground.log` |
| ③ 编辑器模块 | Editor 构建 Succeeded（`Saved/BuildEditor/build-20260918-163851.log`）；**编辑器 DLL 与 Game EXE 里都已搜不到 `FountainSplash`**（四根乱喷水柱已从构件里彻底移除） | `binaries` 字符串复核 |
| ④ 只读复核 | `RomanFountain1` = `(1350,−1550,0)`，包围盒 `z=[−1..720]`，与 `Floor`（top 0）/ 凉亭台基（0..20）同一地面 | `probe_level.log` |

踩坑补充（都已进 skill）：

- `delete_all_material_expressions` 即便先删掉引用它的材质实例也会断言崩溃——被删对象在 GC 前仍持有引用。
  本轮改成**只改属性**（光照模式 / SceneTexture 节点 id / Opacity 上的 Clamp 参数），不再重建图。
- 本版枚举全部是**大写 + 下划线**：`TLM_SURFACE_PER_PIXEL_LIGHTING`、`PPI_SCENE_DEPTH`、`CMODE_CLAMP_MAX`
  （`ClampMode` 没有 MinMax）。写错时全部静默退回默认值，必须"设完立刻读回"。
- 贴地脚本第一版取"最高的 Floor 面"，结果选到 2100 cm 外抬高的凉亭台基（top=20）→ 改成
  **只吃 XY 范围包含目标的那个面**。
- 并行会话的 Unreal 进程会随时抢锁：一次 84 s 的运行里材质保存就全失败了（`LogSavePackage: Error: Error saving`），
  所以脚本改成"重跑幂等 + 每次核对 mtime"。

发布记录：提交 `62b4a7b`（`origin/main`），发布目录 `D:/FPS3D/FPSGAME`，普通推送 `HEAD:main`，
`git ls-remote` 回读一致（推送期间 GitHub 连接抖动，多次重试后成功，未强推）。
内容依赖：`M_FountainWater`、5 个 `MIC_Fountain*`、`SM_RomanFountain_20`、`SM_RomanFountain_WaterFX`、
`RomanFountain1` 的关卡变换（`DayNight_Lighting.umap` 16:38:47）。

---

# 八次迭代：让"水在动"变成确定可见（2026-09-18 晚）

用户回执："主要是水体，很僵硬，像固体。" 这轮不调"漂不漂亮"，只解决**为什么看不出水在动**，
并把关键手法改成不依赖网格 UV/切线的确定性做法。

## 8.1 两个结构性原因

1. **法线扰动原本可能完全不起作用**：本工程网格走 **XAtlas**，圆盘/锥面的 UV 岛方向随机、局部可能退化，
   而法线贴图是**切线空间**的 → 算好的涟漪法线被乱掉的切线基转掉，观感就是"一块没起伏的平板"。
   修法：水面都是水平盘面 → `M_FountainWater` 设 **`tangent_space_normal = False`**，材质里的 `(x,y,1)`
   直接当**世界空间**法线用（纯属性改动，不碰图）。读回 `tangent_space_normal = False` ✓。
2. **水帘流动只靠泡沫贴图对比度**：贴图偏平（低频灰度）时滚动几乎不可见 → 读成"静止玻璃片"。
   修法：新建 **`M_FountainCascadeFlow`**（新资产名，避免重建被引用的旧材质触发 `!IsRooted` 断言），
   用 **程序化 sin 竖条纹 + 泡沫贴图** 叠加、沿柱面 v 快速滚动 —— 条纹**确定可见**，贴图只做细节叠加。

## 8.2 参数强化（都在实例上，可继续调）

| 参数 | 之前 | 现在 | 作用 |
| --- | --- | --- | --- |
| `MIC_FountainWater.OpacityBase / FresnelOpacity` | 0.34 / 0.30 | **0.28 / 0.22**（Opacity 上限 **0.5**） | 更透，减少"实心板"读感 |
| `NormalStrength / NormalStrength2` | 0.9 / 0.6 | **1.3 / 0.9** | 双层波浪起伏更明显 |
| `RippleStrength / RippleFoam / RippleFoamOpacity` | 0.85 / 0.7 / 0.4 | **1.1 / 1.0 / 0.55** | 落水涟漪与**波峰白沫环**（不依赖切线，一定看得见向外跑） |
| `RippleFreq / RippleWidth` | 0.45 / 210 | **0.6 / 260** | 涟漪更快、扩散更远 |
| 水帘 | `MIC_FountainCascade`（贴图驱动） | **`MIC_FountainCascadeFlow`**（程序化条纹；`FlowSpeed 1.1`、`BandCount 9`、`OpacityBase 0.45`） | 向下流动确定可见 |

## 8.3 证据（已落盘）

`build_water.log`：`water_world_space_normal OK / tangent_space_normal = False`、
`opacity clamp max = 0.5 (CMODE_CLAMP_MAX)`、`cascade recompile -> []`；
水效网格读回 `slots=['MIC_FountainFoam','MIC_FountainWet','MIC_FountainCascadeFlow','MIC_FountainCaustics']`、
主网格 `slots=['M_RomanStone_V2','MIC_FountainWater']`、**33/33 PASS**，全部资产 18:13:13 落盘且无 `Error saving`。

**仍未实机判读**（按约定）：请重启编辑器后进 PIE 看三件事——① 水面涟漪/反射是否在动；
② 落水点是否有向外扩散的白沫环；③ 三级水帘是否有明显向下的流动条纹。若还有不对，给我
"贴水面的低角度"和"3/4 中景"两张图，我按图定位（数据侧我已经查完了）。
