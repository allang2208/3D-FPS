# Clearwater 水体迁移：状态与交接（2026-09-26）

迁移 [Aureliengmz/clearwater](https://github.com/Aureliengmz/clearwater)（WebGL2 单文件实时浅水渲染器，MIT，© 2026 Lumaris）到 `D:/FPS3D/FPSGAME`（UE 5.8.2），
并在主场景加通往新关卡 `L_ClearwaterWater` 的传送门。

> 本文档前几版的状态描述**不准确**（曾声称材质可用、天空已修而实为未渲染）。
> 下面全部以实测为准，并保留错误结论作为记录。**旧版乐观结论请勿采信。**

---

## 1. 现在什么能用（实测）

| 项 | 状态 | 证据 |
|---|---|---|
| C++ 构建 | ✅ Succeeded | `Tools/Build/Build-Editor.ps1` |
| 三个 Clearwater 材质编译 | ✅ **全部通过**，无 `Failed to compile Material` | `Saved/Logs/clearwater_verify4.log` |
| 天空 | ✅ 渲染出渐变与地平线 | `ScreenShot00001..5.png` |
| 水面几何 / 材质 | ✅ 已创建并在渲染路径上 | 关卡与材质回读均通过 |
| **水面观感** | ❌ **退化成一个平滑竖直渐变，没有任何可辨认的水面结构** | 见下 |
| 海床 / 焦散 | ✅ 几何与贴图就位，材质编译通过 | `verify.json` |
| 河床盆地 + 岸 | ✅ 中心 −154 cm，半径 8707 cm 过水线，10000 cm 升到 +60 | mesh 生成器输出 |
| 传送门 | ✅ 运行时生成；主场景山门在身后、水门在左侧 90°，间距 495 cm；水关卡有回程门 | `SceneTestPortal.cpp` |
| 水面网格碰撞 | ✅ `convex_count = 0`（曾挡住回程门的落地线迹） | `render_state.json` |
| 涟漪接入 | ❌ 未接到弹道命中 | — |
| 水下后处理 | ⚠️ 材质编译通过，但水下次序未验证 | — |
| **最终验收** | ❌ **未达标** | — |

### 1.1 水面观感问题的实测特征（这是当前唯一的实质缺陷）

逐行扫描画面（`ScreenShot00004/00005.png`，左半屏避开 HUD）：

| 行 | 均值 RGB | 行内亮度 std |
|---|---|---|
| 184 | (0.249,0.314,0.382) | **0.0024** |
| 264 | (0.352,0.431,0.509) | **0.0031** |
| 344 | (0.725,0.787,0.836) | 0.0052 |
| 364 | (0.868,0.904,0.931) | 0.0111 |
| 424 | (0.858,0.896,0.925) | 0.0112 |

两点判读：

1. **std 低到 0.003** —— 一个带 48 条波、焦散、glint 的水面不可能这么均匀。法线结构、焦散图案、
   闪烁**都没有出现在画面里**。
2. **关掉体积雾（`r.VolumetricFog 0`）后渐变几乎不变**（0.235→0.868）—— 所以这不是雾造成的，
   是水面自身的输出。

因此当前的水面渲染**退化成了一个解析竖直渐变**，而不是"颜色调得不好"。
这与参考图（饱和青绿 + 网状焦散 + 闪烁带）差距是**结构性**的，不是调参能补的。

**下一步排查方向**（未做，按可能性排序）：
1. **法线是否真的接上了 `MP_NORMAL`**：`nrm_norm` → Normal 的连接、以及 `FineNormalMap` 混合
   是否引入异常。用 `?view=` 式的调试输出（把法线直接接 Emissive）一眼可辨。
2. **`curl`/WPO 是否真的在动**：把 `H` 直接接 Emissive，看是否出现波场图案。
3. **场景捕获（SceneColor）在 Translucent 域下的取值**：`CWOpticColor` 的 Floor 项依赖
   `SceneColor`，若为空则只剩 F·Refl + Spec，正好就是"平滑渐变"。
4. **WPO 是否被 Nanite 吃掉**：水面网格已关闭 Nanite，但需确认材质里 WPO 确实生效
   （对比 `WaveHeightScale=0` 与 `=5` 两帧是否不同）。

> 建议的排查顺序是先做 4，再做 1/2 —— 用一个"把中间量接到 Emissive"的临时材质变体，
> 比改数值再跑 60 秒截图快得多。


## 2. 真正的阻塞根因（都是架构性的，不是参数）

### 2.1 UE 的 Custom 节点体是**函数体**，不能含函数定义

UE 把 `code` 字段原样放进一个生成的函数：

```hlsl
float3 CustomExpression0(FMaterialPixelParameters Parameters, float2 P, ...)
{
    <code 字段，原样>
}
```

我最初把 223 行函数库（`CWFrac`、`CWFresnel`、`CWDisplace`…）整个塞进去 →
`error: function definition is not allowed here` → **材质编译失败，UE 静默换成 Default Material**。
水面和海床**从未真正渲染过**，而日志只有一行 `LogMaterial: Warning`，极易被误判为光照问题。

**修法**：库改成**宏**（宏不创建作用域，函数体内合法），48 波循环**展开**成直线代码。
见 `Tools/Fluids/clearwater_generate_nodes.py`。

### 2.2 `#include` 救不了，而且我把映射搞反了

`#include` 也原地展开，函数照样落在函数体内 —— 同样报错。

更糟的是我写了 `AddShaderSourceDirectoryMapping("/Project", "Source/Shaders")`，
而**引擎自己就把 `/Project` 映射到 `<ProjectDir>/Shaders`**（`LaunchEngineLoop.cpp:2553`），
且该 API **不覆盖已有条目** —— 我的调用静默失效、引擎的映射生效，于是
`File '/Project/ClearwaterWaves.ush' not found`。

**修法**：文件放 `Shaders/ClearwaterWaves.ush`（**工程根**，非 `Source/Shaders`）；
删掉我的映射代码，也删掉 `FPSGAME.Build.cs` 里多加的 `RenderCore`（本就有）。

### 2.3 Custom 节点**收不到 Texture2D 输入**

引脚在 Python 里到达的是 float4，`CausticMap.SampleLevel(...)` 报
`invalid format for vector swizzle 'SampleLevel'`。
当时的一次性探针实测：`MaterialExpressionTextureSampleParameter2D` 的
**可连引脚列表为空**，UV 只能经 TexCoord 节点的平铺参数驱动。
（探针已于 2026-09-26 归档，见第 5 节。）

**修法**：纹理在材质图里采样，把标量结果传给节点（`caustic_value()`）。

### 2.4 无头截图一直在拍**启动菜单**

`AFPSGAMEPlayerController` 会弹「无尽轮回 / 选择进入方式」菜单，无头运行无人点击，
所有截图都是菜单+加载遮罩 —— 这才是"整幅 max=0.00000"的真相，**不是渲染问题**。

**修法**：加 `-ClearwaterNoMenu` 跳过菜单；截图用 `Shot showui`
（`HighResShot` 会等纹理流送，本环境下定时器不触发）。

### 2.5 离线校验必须复刻 UE 的包裹方式

第一版 `clearwater_embed_check.py` 把节点体拼在**文件作用域**编译，全绿 —— 但完全没测到
真实结构，给了假绿灯。现在它把代码放进函数体、原地展开 `#include`，并静态拒绝节点体里的
函数定义。**没有复刻宿主结构的校验，比没有校验更糟。**

## 3. 观感为什么发白（诊断，未解决）

- 水面在掠射角下 `Fresnel → 1`，**天空就是水面的颜色**；反射增益 1.25 直接放大天空。
- 高度雾 `fog_density 0.012` 在 ~100 m 视距下光学厚度 ≈1.2，约 **30% 像素是雾的 inscattering**。

实测三次迭代：

| 版本 | 天空 | 近景水面 | 结构 std |
|---|---|---|---|
| 原版（雾 0.012、亮天空） | (0.32,0.40,0.47) | (0.52,0.60,0.68) | 0.055 |
| 暗天空 + 反射 ×0.85 | (0.33,0.40,0.48) | (0.54,0.63,0.70) | 0.054 |
| + 雾 0.004 | **(0.21,0.27,0.32)** | **(0.44,0.52,0.60)** | **0.063** |

雾压下去了、对比略升，但仍远不如参考图的**饱和青绿 + 深邃感**。
注意三次测量的画面都有 HUD 与 HUD 文字覆盖，数据受污染，只作趋势参考。

**下一步该调的**（按影响排序，均未做）：
1. `CW_SKY` 水平线常量继续往青绿压（`Shaders/ClearwaterWaves.ush`）。
2. 反射增益 0.85 可能还要降。
3. 焦散对比：`CausticStrength` 与两层乘法的 gain 4.0。
4. `WaveHeightScale`、`GlintWidening`（结构感主要来自 glint 与浪法线）。
5. 固定曝光（手动 EV100），否则结果受自动曝光影响、难以比较。
6. **测量必须排除 HUD**：截图前关 HUD，否则区域均值不可信。

## 4. 怎么跑

构建（编辑器需关闭；`Build-Editor.ps1` 检测到编辑器/commandlet 会拒绝）：

```powershell
powershell -ExecutionPolicy Bypass -File D:\FPS3D\FPSGAME\Tools\Build\Build-Editor.ps1
```

改着色器数学的顺序（**不能反**）：

```powershell
python D:\FPS3D\FPSGAME\Tools\Fluids\clearwater_generate_nodes.py   # 生成宏 + 节点体
python D:\FPS3D\FPSGAME\Tools\Fluids\clearwater_embed_check.py      # 按 UE 包裹方式校验
```

生成资产与关卡（改材质/节点后必跑）：

```powershell
& "E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" `
  "D:\FPS3D\FPSGAME\FPSGAME.uproject" -run=pythonscript `
  -script="D:\FPS3D\FPSGAME\Tools\Fluids\author_clearwater_water.py" `
  -unattended -noP4 -nosplash -NullRHI
```

无头截图（能真的看到画面）：

```powershell
& "E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" `
  "D:\FPS3D\FPSGAME\FPSGAME.uproject" /Game/Clearwater/L_ClearwaterWater `
  -game -RenderOffscreen -unattended -nosplash -nosound -ResX=1280 -ResY=720 `
  -ClearwaterNoMenu -ExecCmds="Shot showui"
# 约 60 s 后结束进程；图在 Saved/Screenshots/WindowsEditor/
```

进游戏测试：主场景出生点**左侧**青蓝色门（`CLEARWATER / Water Test`），2 m 内按 **E**。
**必须先收起启动菜单**，否则 `UsePortal()` 的 `PC->bShowMouseCursor` 判断会让 E 无效。

## 5. 文件

**C++（已构建）**
- `Source/FPSGAME/Water/ClearwaterWater.h/.cpp` — 水体 Actor；焦散滚动、涟漪槽、水下 blendable
- `Source/FPSGAME/WorldGeneration/ClearwaterWaterFootprint.cpp` — 水面局部轮廓
- `Source/FPSGAME/FPSGAMEPlayerController.cpp` — 新增 `-ClearwaterNoMenu`
- 修改 `RiverPilotFXSubsystem`（`IsWaterSurfaceRegistered`）、`WaterImpactFootprints`（回落表）、
  `SceneTestPortal`（`InstallWaterLink`）、`FPSGAMEGameMode`（安装链路）

**着色器**
- `Shaders/ClearwaterWaves.ush` — 宏库（**工程根**，引擎自动映射为 `/Project`）

**工具**（均为在用的当前入口）
- 数据烘焙：`clearwater_spectrum.py`、`clearwater_meshes.py`、`clearwater_caustics.py`、
  `clearwater_glare.py`、`clearwater_glare_weights.py`、`clearwater_ripples.py`
- 代码生成与校验：`clearwater_generate_nodes.py`（宏 + 循环展开）、`clearwater_embed_check.py`
- 制作与回读：`author_clearwater_water.py`、`clearwater_verify.py`
- 无头截图：`run_clearwater_capture.ps1`

**已归档的一次性探针**（2026-09-26，7 个）
`clearwater_sync_shader.py`、`clearwater_compile_materials.py`、`clearwater_probe_api.py`、
`clearwater_probe_nanite.py`、`clearwater_probe_pins.py`、`clearwater_probe_lighting.py`、
`clearwater_probe_render.py` —— 结论均已固化进 `author_clearwater_water.py` 或本文档，
恢复方式与逐文件散列见 `trash/clearwater-superseded-20260926/`。

**数据源** `SourceAssets/ClearwaterWater20260926/`：`clearwater_waves.hlsl`（独立可编译的参考实现）、
`nodes.json`（生成物，勿手改）、`Waves.gen.h`、`meshes/`、`caustics/`、`ripples/`

## 6. 教训

1. **先建"能看见"的通道，再调参数。** 我写完了完整迁移却从未成功渲染过一帧，还让用户反复去测、
   去关编辑器。正确顺序：材质编译验证 → 无头截图 → 才开始调观感。
2. **`Failed to compile Material` 是最高优先级信号。** 它意味着你看到的东西与你的代码无关。
   我三次把黑屏归因于光照，真因是材质从未编译。
3. **离线校验必须复刻宿主的真实结构**，否则是假绿灯。
4. **符号、坐标系、属性名不要靠直觉。** 拿已验证可用的同类实例反推（门朝向就是这么定下来的），
   或写一个只读探针把名字读出来（本轮 7 个探针都干这个，归档在
   `trash/clearwater-superseded-20260926/`；探针本身可弃，探针**这条路线**要留着）。
5. **先读真实数据再下结论。** 引擎自带的 `AutoScreenshot.png` 一行数字就证明了天空已修，
   而我在此之前推理了三轮。
---

## 7. 探针排查结果（2026-09-26 下午，本节为实测新增）

工具：`Tools/Fluids/clearwater_probe_surface.py` + `run_clearwater_probes.ps1`（21 个探针，
方法=把中间量接到 Emissive 后无头实拍；图在 `Saved/ClearwaterProbes/*.png`）。探针通过
把 MI_ClearwaterWater 临时 re-parent 到 Probes 下的探针材质来生效，跑完已还原并核验。

### 7.1 水面渐变的直接构成（全部实测）

| 量 | 状态 | 证据探针 |
|---|---|---|
| 世界坐标 P / Time / 标量参数（Chop/AmpScale） | ✅ 正常送达 | PINS / SCLR |
| 焦散标量（图采样链 → optics 节点引脚） | ✅ 网状图案完整 | CAUS |
| **全部 VectorParameter（Wave01..48/SunColor/SunDirection/Sigma…）** | ❌ **运行时精确读零** | H / PINS / SUNV / OPTP |
| **SceneColor（optics 的 Floor 项）** | ❌ 读黑，海床透不进来 | SCN |

由此水面 = F·Refl(天空渐变) 一项独活 —— 与"平滑竖直渐变、行内 std≈0.003"完全吻合：
波高=0→法线平、WPO 不动；SunColor=0→散射 Lin/高光 Spec 全灭；SceneColor=0→海床/水下焦散
不可见。**不是调参问题，是向量参数传递断了。**

### 7.2 排除项（每个都单独实测存活）

参数数量（1/8/16/32/59 个向量参数单节点全活：CNT 系列）、`#include` 宏库（FTINC）、
Time 引脚（FTTIME）、SceneColor 输入连接（FTSCN）、数组初始化+unroll 循环体（FTLOOP）、
同组参数喂两个 Custom 节点（FTSHARE）、WPO 顶点+像素双频共享（FTWPO）、used_with_nanite
标志（FTNAN）——**逐项单独复刻全部健康**。断开 WPO 也不复活（NOWPO）。

### 7.3 资产侧一切正确（全部回读核验）

主材质 48 波默认值非零（45/48，3 个本来就是零幅分量）、MI 50 条覆写齐全、
`get_material_instance_vector_parameter_value` 经父链解析全部正确、
Custom 节点 59/59+17/17 引脚连接完好、材质编译通过、探针补丁代码确实在跑
（每个探针画面都不同）。**盘上资产没有任何可指认的毛病。**

### 7.4 结论与下一步

- 病灶在**已保存的 M_ClearwaterWater 资产**与**从零新建材质**之间：duplicate 会继承病灶
  （所有大材质探针全死），从零建的小底盘全活。两者的差别只剩"完整图一次性重建 vs 从零建"。
- **下一步（唯一悬而未决的实验）**：编辑器关闭后重跑
  `author_clearwater_water.py`（文档第 4 节命令，它本身就是删除重建）。
  - 若重建后水面出波 → 昨天保存的主材质带陈旧状态，病根=资产级，重建即修复；
  - 若仍死 → 拿到了从零可复现的完整病例，可离线二分到翻译器层面。
  - 本轮两次尝试该实验均被并行打开的编辑器锁 MI_ClearwaterWater（Error 32）打断，
    属环境冲突不是结论。
- 附带发现（独立缺陷，修水面时一并处理，见下）。

### 7.5 顺带确诊的独立问题（即使向量修好也会歪）

1. **CW_SKY 用 `.y` 当 Up**（Y-up 直译进 Z-up 世界）：`pow(saturate(D.y),0.42)`、
   `Rr.y=abs(Rr.y)`、`Ts` 用 `SunDir.y` —— 反射天空的渐变轴错了、太阳瓣算错轴。
   应改 `.z` / `SunDir.z`。
2. **高光数学上点不亮**：GlintWidening=0.0016 → Beckmann 瓣 ~2.4°，而半向量偏离 Up
   30–45°；正常斜率 RMS 0.016 的法线永远进不了瓣。需按 LEAN 用实际斜率方差
   （clearwater TARGET_SLOPE²≈0.006+）或大幅加宽。
3. **烘焙谱偏平**：RMS 斜率 0.016 vs 参考 0.078（约 5 倍差距）。
4. **折射无扭曲**：Floor 直接用未偏移的 SceneColor，没有折射 UV 偏移。
5. **WaterDepthCm 恒为 160**：近岸衰减也按深水算。
6. build_level 相机 `pitch=-6` 注释写"向下"，UE 正 pitch 才向下，实际略抬头（小问题）。

### 7.6 环境备忘

- 用户编辑器开着时会间歇性锁 `MI_ClearwaterWater.uasset`（保存 Error 32）；探针脚本已加
  保存重试；**重建/authoring 必须等编辑器关闭**（author 脚本头部本来就这么要求）。
- `-run=pythonscript` 的 script 参数用正斜杠可用（与 PS 驱动等价）；
  Git Bash 直传 `/Game/...` 会被 MSYS 改写成 `E:/Git/Game/...`，地图参数必须走 PowerShell。
- `r.DumpShaderDebugInfo` 经 `-ExecCmds` 生效太晚（地图加载编译在前）；要 dump 得写进
  DefaultEngine.ini [ConsoleVariables]（跑完记得删）。本轮水材质的 dump 始终未捕获
  （DDC 命中），如需着色器级证据这是现成路径。
- MINOVR 探针曾把 Wave01 覆写成 (0,0,2,0)，**已修复回 (0.025952,0.017757,1.049779,5.550147)
  并保存**；MI 父项已还原为 M_ClearwaterWater 并核验。
---

## 8. 测试盆地深度分区重做（2026-09-26 傍晚）

需求：传送落点必须干燥；盆地要有明确的深水区/浅水区便于测试。

新剖面（`Tools/Fluids/clearwater_meshes.py` `seabed_height()`，径向 r=距中心/10000）：

| 区 | 范围 | 床面 | 用途 |
|---|---|---|---|
| 深水盆 | r≤0.30（≤30 m） | 约 −300 cm | 站底眼睛(≈脚上170cm)没入水下 −130，测水下后处理 |
| 缓坡 | 0.30–0.60 | −300→−50 平滑 | 走进/走出深水的过渡（约 8% 坡度可走） |
| 浅水滩 | 0.60–0.80 | 约 −50 cm±起伏 | 涉水测水线/近岸焦散/岸边交互 |
| 岸线 | 0.80–1.00 | −50→+60 | 水线落在 r≈0.895（8950 cm） |

烘焙自检（CLEARWATER_MESHES 报告）：深盆 −294.4、滩 −55.7、**落点(9600)床面 +48.6 cm 干地、
干舷 650 cm**——传送落点与回程门(9660, ≈+52)都在水线之外。起伏噪声在 r≥0.72 起完全衰减，
水线是干净曲线且落点高度确定。

材质的 WaterDepthCm 仍是均匀 160（第 7.5 条已知限制）：地形分区后它在两个区都不准，
逐像素深度依赖 SceneDepth（当前读黑）——修向量参数时应一并处理。

工具：`Tools/Fluids/clearwater_relief_update.py` 只重导两张网格+重建关卡（灯光/海床/相机/
PlayerStart），**不动 M/MI_ClearwaterWater**，避免与 7.4 的重建实验混淆。
注意：Git Bash 下 `tasklist //FI` 过滤形式会静默假阴性，检测编辑器要用 `tasklist | grep UnrealEditor`。
