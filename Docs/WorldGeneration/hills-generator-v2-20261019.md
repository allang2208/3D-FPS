# 丘陵生成 V2：版本化高度场优化（2026-10-19）

## 1. 这次改了什么

给丘陵高度场加了 **V2**，通过 `GeneratorVersion` 按世界选择；V1 公式保持逐字不变，旧存档继续走 V1。

| | V1 | V2 |
|---|---|---|
| 噪声 | 3 层 value noise + 1 层细节 | 大陆度 C、侵蚀度 E、域扭曲、4 层 ridged 山脊、2 层细节 |
| 插值 | 三次 smoothstep | 五次 quintic，并旋转 36.87° 打破轴向晶格 |
| 起伏 | 固定 3.2 km / 1.8 km / 2.8 km 波长 | C/E/R 多层，波长约 1.4 km / 0.9 km / 0.52 km，按种子变化 |
| 坡度 | 最大约 24–29°，坡度掩码基本空转 | 最大约 55–60°，岩石/陡坡规则开始生效 |
| 1 km 起伏（seed 122） | 58.4 m | 84.2 m |
| 4 km 起伏（seed 122） | 约 98.5 m | 147.1 m |

V2 的公式在 [TemperateHillsSurface.h](FPSGAME/Source/FPSGAME/WorldGeneration/TemperateHillsSurface.h) 的 `HeightV2`：

```text
C = Fbm(x/1400m, y/1400m, 4 oct)          // 大陆度
E = Fbm(x/900m,  y/900m,  4 oct)          // 侵蚀度
W = Fbm(x/2200m, y/2200m, 2 oct) * 120m   // 域扭曲
R = Ridged((x+Wx)/520m, (y+Wy)/520m, 4)   // 山脊
D = Fbm(x/65m, 3 oct)*3.5m + Fbm(x/24m,2)*0.9m
Base = 70m + 35m*C
Amp  = clamp(140m + 140m*C, 50m, 280m) * lerp(1, 0.3, smoothstep(0.2,0.8,E))
H    = max(1.5m, Base + Amp*(R-0.35) + D - 15m*exp(-((y-ValleyY)/90m)^2))
```

单位是厘米；`Fbm`/`Ridged` 内部用项目原有的 32 位哈希，没有引入第三方噪声库。

## 2. 版本与存档

- `ATemperateHillsWorld::GeneratorVersion`：0 表示未解析，1=V1，2=V2；参与复制，客户端按服务端版本重建。
- `UTemperateHillsSave::GeneratorVersion`：旧存档没有该字段，反序列化后为默认 1；新存档显式写入。
- 新世界默认 **2**；读旧存档保持 **1**。
- 命令行：
  - `-HillsNewWorld -HillsGen=2`：新建 V2 世界。
  - `-HillsNewWorld -HillsGen=1`：新建 V1 世界（回滚/对照）。
  - `-HillsSeed=122 -HillsGen=2`：指定种子新建 V2。
  - 已有存档不会因为 `-HillsGen` 自动换版本；要继续同一个世界，必须用原版本。
  - 新世界/新审计槽默认就是 V2；要对照旧行为，必须显式 `-HillsNewWorld -HillsGen=1`。
- 交互测试脚本（项目根）：
  - `& ./Tools/WorldGeneration/Open-TemperateHills.ps1 -Seed 122`：新建 seed 122 的 V2 世界。
  - `& ./Tools/WorldGeneration/Open-TemperateHills.ps1 -Seed 122 -Gen 1`：新建同种子的 V1 对照世界。
  - `& ./Tools/WorldGeneration/Open-TemperateHills.ps1 -Continue`：续玩本样地上次的世界（版本按存档）。

日志：

```text
HILLS_SESSION seed=122 generator=2 world=...
HILLS_GEN generator=2 seed=122 size=1024m
```

## 3. 离线测量（不是运行时验收）

用 [audit_hills_v2.py](../../Tools/WorldGeneration/audit_hills_v2.py) 的 Python 哈希/噪声镜像采样，2 m 网格（1 km）和 4 m 网格（4 km），seed 122，未叠加河流雕刻与实际网格 LOD：

| 指标 | V1 1 km | V2 1 km | V2 4 km |
|---|---:|---:|---:|
| 最低/最高 | 20.4 / 78.8 m | 53.8 / 138.0 m | 25.9 / 173.0 m |
| 起伏 | 58.4 m | 84.2 m | 147.1 m |
| 平均坡度 | 7.1° | 14.9° | 15.5° |
| 坡度 p95 | 14.6° | 31.8° | 34.1° |
| 最大坡度 | 23.9° | 55.1° | 60.3° |
| 大于 30° 面积 | 0% | 6.74% | 9.18% |
| 大于 45° 面积 | 0% | 0.20% | 0.46% |

其他种子（1 km，同一采样）：

| seed | 起伏 | 坡度 p95 | 最大坡度 | 大于 45° |
|---:|---:|---:|---:|---:|
| 122 | 84.2 m | 31.8° | 55.1° | 0.20% |
| 123 | 74.5 m | 24.5° | 42.5° | 0% |
| 7 | 133.7 m | 35.8° | 56.4° | 0.65% |
| 12345 | 149.5 m | 43.2° | 63.7° | 3.53% |

V2 的种子差异明显大于 V1：同一位置 seed 122 与 123 的高度相关系数约 0.48（V1 约 -0.27），说明布局确实换了，而不是只改细节。

## 4. 对现有系统的影响

- **河流**：`Generate` 和 `FPlan::Height` 接收版本；V2 世界用 V2 高度做优先洪泛和河床雕刻，仍是单干流，不是河网。
- **网格/LOD**：`MakeMesh` 接收版本；V2 的坡度更大，8 m 远景 LOD 的轮廓差异会比 V1 明显，裙边仍按同一高度函数封边。
- **PCG**：`GetPlacements` 走 `Height`/`SurfaceNormal`，自动使用当前版本；树 29.5°、石 44°、草 33.9° 的坡度阈值在 V2 下开始真正筛掉陡坡。
- **远景**：`TemperateBackdrop` 用 V2 高度；固定 5.12 km 环、内环 1.536 km 不变。
- **出生点**：V2 沿谷地向东最多搜索 128 m，取第一个坡度不超过 8° 的点；V1 保持原来的固定出生点。
- **存档/联机**：版本随存档和复制保存；旧存档继续 V1，不会因为升级改变地形。

## 5. 未做与已知限制

- 世界尺寸仍夹在 1024 m（`SizeMeters` 的 UPROPERTY ClampMax 和 `StartWorldPipeline` 的运行时夹取），这次没有放开 2 km。
- 河流仍是全图单干流；4 km 时优先洪泛节点数约为 1 km 的 16 倍。
- 没有生物群系/气候输出；C/E 目前只影响高度，不驱动植被或材质。
- PCG 的 `CanExecuteOnlyOnMainThread=true` 未改；2 km/625 格时仍需观察主线程开销。
- V2 每个高度采样约 84 次哈希（V1 约 20 次），`Normal` 每顶点 4 次高度；网格生成成本约 4–5 倍。离线没有测真实帧时间。
- 出生点搜索最多 128 m；如果整条采样带都超过 8°，回退到最平点，不保证一定 ≤8°。离线 seed 12345 的回退点约 10.2°。
- 远景 Blend 以 `Half` 到 150000 cm 过渡；1 km/2 km 的 `Half` 不超过 150000，核心 proxy 不受影响。放开 4 km 时 `Half=204800 > 150000`，`SmoothStep` 会在可玩区内变成 1，核心 proxy 会叠加远景噪声，必须先改过渡起点。
- `TemperateHills::ValleyY` 与 `TemperateHillsSurface::ValleyY` 目前是两份相同公式；V2 高度和出生点搜索分别用这两份，改其中一处必须同步另一处。
- 没有运行游戏、PIE、编辑器或自动验收；以上坡度/起伏均为离线数值，实际画面、碰撞、河流和 PCG 需用户测试。

## 6. 回滚

- 旧存档：不动，继续 V1。
- 新世界要回 V1：`-HillsNewWorld -HillsGen=1`。
- 代码回滚只需把新世界默认值改回 1；`HeightV1` 和 V1 的调用路径没有改。

## 7. 下一步建议

1. 先跑一次 `-HillsNewWorld -HillsGen=2` 看 seed 122 的画面和碰撞；重点看 45° 以上岩坡、树根悬空、出生点。
2. 如果 V2 方向认可，再把 `SizeMeters` 上限和流送环改成 2 km/4 km。
3. 河流从“全图单干流”升级为粗流向图 + 按块采样，避免 4 km 全图洪泛。
4. PCG 元素移到 worker，保持 `CandidateKey` 稳定。

## 8. 编译状态

2026-10-19 23:09，`FPSGAMEEditor Win64 Development` 编译并链接成功（UHT + 142 个 action，`Result: Succeeded`）。没有启动游戏、PIE 或编辑器，也没有跑自动验收；实际地形、碰撞、河流、PCG 和帧时间由用户测试。

## 9. 改动文件

- `Source/FPSGAME/WorldGeneration/TemperateHillsSurface.h`
- `Source/FPSGAME/WorldGeneration/TemperateHillsWorld.h`
- `Source/FPSGAME/WorldGeneration/TemperateHillsWorld.cpp`
- `Source/FPSGAME/WorldGeneration/TemperateHillsRiver.h`
- `Source/FPSGAME/WorldGeneration/TemperateHillsRiver.cpp`
- `Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp`
- `Source/FPSGAME/WorldGeneration/TemperateHillsBackdrop.h`
- `Source/FPSGAME/WorldGeneration/TemperateHillsBackdrop.cpp`
- `Tools/WorldGeneration/audit_hills_v2.py`
- `Docs/WorldGeneration/hills-generator-v2-20261019.md`