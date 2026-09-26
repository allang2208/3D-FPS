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
