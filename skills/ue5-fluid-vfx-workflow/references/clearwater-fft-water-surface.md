# Clearwater FFT 水体：移植与诊断参考（2026-09-26）

本文件是 [Aureliengmz/clearwater](https://github.com/Aureliengmz/clearwater)（WebGL2 单文件实时浅水渲染器，MIT，© 2026 Lumaris）移植到 UE 5.8.2 后的可复用技法。
任务过程、实测数据与未解决的观感缺陷以正本为准：`Docs/Fluids/clearwater-water-migration-20260926.md`。
本文件只留**换个水体还要再遇到**的部分。

> 上游那份实现约 740 行 JS + 180 行 GLSL，全部在网页里做完了整套海洋：频谱 → GPU FFT → 位移／法线 → 光学着色 → 屏幕空间焦散 → 帧间镜头衍射眩光。
> 移植价值不在代码，在**这套分工**。UE 侧不要照抄它的渲染路径，照抄它的分层。

## 1. 上游做了什么，各自对应 UE 的哪一层

| 上游技法 | 上游做法 | UE 侧落点 |
| --- | --- | --- |
| Phillips 型波谱 | `buildH0()` 生成 256×256 复数频谱，随风向与截断波数成型 | **离线**烘焙成 48 条解析波，`SourceAssets/ClearwaterWater20260926/waves.json` |
| 16-pass FFT butterfly | GPU 上每帧做完整 FFT | **不做**。48 条解析波直接在 Custom 节点里求和，省掉整条 FFT 链 |
| 色散量化 | `w = floor(w/w0)*w0`，`w0 = 2π/60` → 60 s 无缝循环 | 每条波给离散周期（0.42–5.46 s），保证时间上可循环 |
| `C1 = H − i·kx·H`、`C2 = i·kz·H` | 同一频谱同时产出**梯度**与**水平／choppy 位移** | 位移与法线出自同一次求和，不额外采样法线贴图 |
| 精确介质 Fresnel | `fresnel()` 解电介质方程，不是 Schlick 近似 | 宏 `CW_FRESNEL`，掠射角行为正确 |
| `SIG_A` / `SIG_S` / `SIG_T` 吸收散射 | 逐通道吸收与散射系数 | 宏库 + 材质标量参数 |
| Henyey-Greenstein 内散射 | 解析相函数 | 宏，控制水体通透感 |
| Beckmann NDF glint（LEAN 加宽） | 用斜率方差加宽高光瓣，得到"闪烁带"而不是死高光 | 宏，法线驱动 |
| `texBS()` 4-tap 三次 B 样条 | 采样重建 | 纹理采样**必须留在材质图里**（见 §3.3） |
| 折射网格焦散 + 逐通道 IOR | `IORS=[1.3315,1.3335,1.3365]`，屏幕空间 Jacobian | **离线**烘焙 32 帧环形序列，见 §7 |
| 帧间镜头衍射眩光 | FFT 卷积 `buildPSF()`（六边形光圈、划痕、灰尘、8 个波段） | **离线**烘焙成核 + 权重，`glare/` |
| `sky()` 天空 | 山脊／松树／空气透视的程序化天空 | **换成本工程 `SkyAtmosphere`**，只保留它的天顶／地平线色常数 |
| 自适应分辨率 | 质量 0.42–1.0，>21 ms 降 ×0.87，<14.5 ms 升 ×1.06，DPR 上限 2 | UE 侧走 TSR／动态分辨率，**不要**移植这套手写缩放 |

**一句话**：上游把"频谱→FFT→位移→光学→焦散→眩光"全塞进一帧；UE 里正确的切法是
**位移／法线／光学留在实时材质**（48 条解析波够了），**焦散与眩光退到离线烘焙**，
**天空换成引擎大气**。照搬它的 FFT 只会把 GPU 预算花在 UE 用不上的环节上。

## 2. 移植后的五段式结构（可重建源全在 `SourceAssets/ClearwaterWater20260926/`）

```
clearwater_spectrum.py   → spectrum.json + waves.json   48 条波的振幅/波数/周期/相位
clearwater_meshes.py     → meshes/*.obj                 水面 + 海床盆地
clearwater_caustics.py   → caustics/caustics_00..31.png 32 帧环形焦散
clearwater_ripples.py    → ripples/T_*_N.png            法线
clearwater_glare.py      → glare/glare_kernel.png       衍射核
        ↓
clearwater_generate_nodes.py → Shaders/ClearwaterWaves.ush（宏库）+ nodes.json（5 个节点体）
        ↓
clearwater_embed_check.py    → 按 UE 的包裹方式离线编译校验（假绿灯防线，见 §3.4）
        ↓
author_clearwater_water.py   → 编辑器侧建 3 个材质 + 关卡 + 灯光
```

**顺序不能反**：改数学必须先跑 `clearwater_generate_nodes.py` 再跑 `clearwater_embed_check.py`，
通过后才动编辑器资产。跳过校验直接授权资产，等于把编译错误写进已保存的材质。

`nodes.json` 是**生成物，不要手改**——它是生成器与作者脚本之间的合同（含每个节点的引脚清单）。

### 关键参数与上游默认值的偏差

| 参数 | 上游 | 本工程 | 原因 |
| --- | --- | --- | --- |
| 波谱 patch `L` | 4.6 m | **46 m** | **最长波 = patch 尺寸**。4.6 m 只给出 1.2 s 的池塘碎浪，不是开阔水面 |
| 波数上限 `kcut` | `2π/0.045` | 同 | 最小波长 ~0.045 m 由网格与法线精度决定 |
| 目标 RMS 斜率 | — | **0.078**（`match_target_slope()` 归一到该值） | 斜率而非波高才决定观感；归一后波长 0.27–46 m、周期 0.42–5.46 s |

## 3. UE 侧四个硬约束（这一节是移植的真正成本）

### 3.1 Custom 节点体是**函数体**，不能含函数定义

UE 把 `code` 字段原样塞进：

```hlsl
float3 CustomExpression0(FMaterialPixelParameters Parameters, float2 P, ...)
{
    <code 字段，原样>
}
```

因此 223 行函数库（`CWFrac`、`CWFresnel`、`CWDisplace`…）进去就报
`error: function definition is not allowed here`，材质编译失败，UE **静默换成 Default Material**，
日志只有一行 `LogMaterial: Warning`——极易被误判成"没打光/全黑"。

**修法**：库改成**宏**（宏不创建作用域，函数体内合法），48 波循环由生成器**展开**成直线代码。
`#include` 救不了：它也原地展开，函数照样落在函数体内。

### 3.2 `/Project` 的映射是引擎给的，别再自己加

引擎已经把虚拟目录 `/Project` 映射到 **`<ProjectDir>/Shaders`**（`LaunchEngineLoop.cpp:2553`），
且 `AddShaderSourceDirectoryMapping` **不覆盖已有条目**。自己写一条
`AddShaderSourceDirectoryMapping("/Project", "Source/Shaders")` 会静默失效，
表现为 `File '/Project/ClearwaterWaves.ush' not found`。

**修法**：头文件放**工程根**的 `Shaders/`，删掉自己的映射代码。

### 3.3 Custom 节点收不到 `Texture2D` 输入

引脚到 Python／HLSL 侧是 `float4`，`CausticMap.SampleLevel(...)` 报
`invalid format for vector swizzle 'SampleLevel'`；
且 `MaterialExpressionTextureSampleParameter2D` 的**可连引脚列表为空**——UV 无法从 Python 连线。

**修法**：**纹理在材质图里采样，只把标量结果传进 Custom 节点**（`caustic_value()` 就是这么做的）。

### 3.4 离线校验必须复刻宿主的包裹方式

第一版 `clearwater_embed_check.py` 把节点体拼在**文件作用域**编译，全绿 —— 但完全没测到真实结构。
现在它：把代码放进函数体、按 `/I` 原地展开 `#include`、静态拒绝节点体里的函数定义。

**没有复刻宿主结构的校验，比没有校验更糟**：它买走了你的怀疑。

## 4. 与水交互系统的对接

本工程已有全水体注册表，**不要**为 Clearwater 另建一套查询：

- `RiverPilotFXSubsystem::IsWaterSurfaceRegistered(const UStaticMeshComponent*)` —— 水面是否已注册。
- `WaterImpactFootprints.cpp` 的回落表 —— 加 `FindComplementaryWaterFootprint` 兜底分支即可。
- `ClearwaterWaterFootprint.cpp` 从**网格包围盒**推平面方形轮廓（`GetBoundingBox()`／`GetExtent()`／`GetCenter()`），
  不手写尺寸常量：网格改了，轮廓自动跟上。

**水面网格必须清掉碰撞**（`convex_count = 0`）。留在里面会挡住回程传送门的落地线迹——
一个跟水本身毫无关系的症状，却花了很久才定位。

## 5. 两个传送门共存

`SceneTestPortal` 里两个安装器都写过 `Facing.Vector() * -350`，于是**后装的门叠在先前那扇上**。
正确做法：新门用**玩家朝向的侧向**偏移，并显式隔开间距：

```cpp
const float LeftYaw = PawnYaw - 90.f;
const FVector Position = PawnLoc + FRotationMatrix(FRotator(0, LeftYaw, 0)).GetUnitAxis(EAxis::X)
                       * -ScenePortalMaps::PortalSpacing;   // 350 cm，命名常量
```

命名常量（`PortalSpacing`）而不是散落的字面量，是这次能快速确认间距的原因。
水关卡里要放一扇回程门，否则测试者进得去出不来。

## 6. 视距、雾与天空装置

- 视距 `VIEW_DISTANCE_CM = 9600`，视高 `VIEW_HEIGHT_CM = 230`，相机 FOV `64°`——按岸线站位量出来的，不是默认值。
- **可用的天空必须四件套**：`DirectionalLight`(atmosphere_sun_light、投影) + `SkyAtmosphere`
  + `SkyLight`(`SLS_CAPTURED_SCENE`、`real_time_capture`、`lower_hemisphere_is_black=False`)
  + `ExponentialHeightFog`(**非黑 inscattering**)。**单独一个 `SkyAtmosphere` 不产生任何组件**，所以没有天空。
  创建顺序也要紧：`SkyAtmosphere` 必须**先于** `SkyLight`。
- 雾密度从 0.012 降到 **0.004**：0.012 在 ~100 m 视距下光学厚度 ≈1.2，约 30% 像素是雾的散射。
  雾是"画面发白"的常见嫌疑人，但**要用 `r.VolumetricFog 0` 前后对比来判定，不要靠推理**（见 §9）。
- 太阳：仰角 +31.0°、方位 +6.0°（从 +X 起算）；`sun_direction()` 返回
  `(cos(el)cos(az), cos(el)sin(az), sin(el))`。

## 7. 焦散的正确烘焙方式

用**反投影 + 逐通道 IOR** 烘离线序列，强度取 `1/|det J|`：
本次峰值聚光 **140×**。若改成"每 texel 数光线"只能得到 ~1.9×，**完全不是焦散该有的样子**。

平铺无缝性是**可证的**：场周期性误差 3.5e−14，不靠肉眼验收。

## 8. 无头截图：先证明"能看见"，再谈观感

```powershell
& "E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" `
  "D:\FPS3D\FPSGAME\FPSGAME.uproject" /Game/Clearwater/L_ClearwaterWater `
  -game -RenderOffscreen -unattended -nosplash -nosound -ResX=1280 -ResY=720 `
  -ClearwaterNoMenu -ExecCmds="Shot showui"
```

三条本环境实测的死路，别重走：

1. `-ExecCmds="HighResShot"` 在**第 0 帧**触发，地图还在流送 → 纯黑（max pixel 0.00000），
   看起来跟"没打光"一模一样。
2. `-ExecCmds="quit"` 在引擎启动队列里执行，**早于 gameplay**，会在流送中途杀掉进程。
3. 自定义的 `-ClearwaterShot=N` 定时器钩子在本环境**从未触发**。

`-ClearwaterNoMenu` 是必需的：不加的话启动模式菜单盖住视口，每张截图都是菜单的照片。
**拍完先确认不是纯黑**再下任何结论。

## 9. 诊断法：逐行扫描判别"平滑渐变 vs 真水面"

水面渲染坏掉时，症状往往不是"颜色不对"，而是**退化成解析竖直渐变**。
判别法是逐行统计（左半屏避开 HUD）：

| 行 | 均值 RGB | 行内亮度 std |
| --- | --- | --- |
| 184 | (0.249,0.314,0.382) | **0.0024** |
| 264 | (0.352,0.431,0.509) | **0.0031** |
| 344 | (0.725,0.787,0.836) | 0.0052 |
| 424 | (0.858,0.896,0.925) | 0.0112 |

**行内 std 只有 0.003** —— 带 48 条波、焦散和 glint 的水面不可能这么均匀。
这比"看着不对"强得多：它把"观感问题"变成了"结构缺失"。

配套两条：

- **关掉体积雾（`r.VolumetricFog 0`）再拍一张**。本次渐变几乎不变（0.235→0.868），
  于是排除了雾，锁定是水面自身输出。
- **把中间量接 Emissive 做临时材质变体**，比反复改数值重跑 60 s 截图快得多。
  优先验证：WPO 是否真的生效（`WaveHeightScale=0` 与 `=5` 是否不同）、`nrm_norm` 是否真的到了
  `MP_NORMAL`、Translucent 域下 `SceneColor` 是否为空（**这一条是待验证的假设，不是已证结论**）。

### 本次仍未解决（不要当成已通过）

材质**编译通过**不等于**渲染正确**。本次三个材质零错误编译、天空正常、几何就位，
但水面仍然是那个平滑渐变，`F·Refl + Spec` 恰好就是这个形状。
**未验收项**：水面观感、涟漪未接弹道命中、水下后处理次序未验证。
后续接着查时，从上面那三条"中间量接 Emissive"入手。

## 10. 交付与验收边界

- 按用户规则：不主动测试、预览、截图或采集性能。本文件里的数据来自用户明确要求的排查轮次。
- 交付时如实区分**已构建／已编译**与**已运行验收**：C++ 构建成功、材质编译零错误是前者；
  水好不好看只有用户能拍板。
- 2 m 内按 **E** 进传送门，**必须先收起启动菜单**——`UsePortal()` 会因为
  `PC->bShowMouseCursor` 为真而拒绝响应，这不是 bug。
