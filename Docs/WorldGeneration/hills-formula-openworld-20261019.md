# 丘陵 PCG 公式排查与“每局随机种子”开放世界方案

日期：2026-10-19。对象：`D:/FPS3D/FPSGAME`（UE 5.8.2）。
范围：只读源码、离线数值复算与公开资料核对；未启动编辑器或游戏，未做画面、性能或打包验收。文中的高度/坡度/频谱数字来自 [`audit_hills_formula.py`](../../Tools/WorldGeneration/audit_hills_formula.py) 对基础高度公式的复算，不含河道、地形编辑与 PCG 实例。

## 0. 结论

1. **现在的地形不是开放世界，是 1.024 km 见方的单块样地。** 高度函数本身在整个平面上连续、可无限采样，但流送只接受 `[0, Count)` 的格子，PCG 候选被 `±Size/2` 裁掉，远景是固定的 5.12 km 环形背景片。离“每局随机种子的开放世界”还差一层世界管理，而不是一条噪声公式。
2. **地形高度不是 PCG Graph 算的。** 高度由 `TemperateHillsSurface::Height()` 这个纯 C++ 函数给出；PCG 只把 C++ 生成的候选点实例化成树/石/草。排查“PCG 公式”要同时看高度场和散布规则，两者是分开的。
3. **当前高度公式 = 4 项 value noise 叠加 + 固定东西向谷地 + 后置河道。** 没有 fBm/ridged 多层、没有气候/侵蚀参数、没有山脊/台地/海岸，所有种子都是同一统计模型的不同采样。
4. **量化结果：** 1 km 内高差 58.4 m、平均坡度 7.1°、最大 23.9°、>30° 占比 0%；4 km 内高差 98.5 m、最大 28.7°。75% 的高度方差在 400 m 以上波长，50 m 以下只占 0.016%。这套地形是“低缓起伏的牧草地”，不是设计文档里 0–250 m、局部 320 m、含 >45° 岩坡的丘陵。
5. **GitHub 有成熟件，但没有一块可以直接替换本项目的 UE5 成品。** 噪声有 FastNoiseLite/FastNoise2/OpenSimplex2；Minecraft 式群系有 Cubiomes（MIT，只做群系/结构，不做方块地形）；分块世界有 Craft（MIT，最小实现）和 Luanti（LGPL，完整体素地图生成）；UE 运行时网格有 RealtimeMeshComponent（MIT）；PCG 扩展有 PCGEx（MIT）。Minecraft 1.18 的多噪声 + 样条架构是公开可复现的，照它做比找“一键开放世界插件”靠谱。
6. **建议做 4 km × 4 km 的有限世界，不做无限。** 4 km 已经能放下 3–5 个生态区、出生地、6–10 个据点和道路网；无限世界会额外引入原点重定位、64 位坐标、跨平台浮点一致性、无边界存档和远景 HLOD，投入产出比很低。Minecraft 是体素游戏；本项目已退役体素地形，不要为了“像我的世界”重新引入第二套地形后端。
7. **“每局随机种子”的语义建议按 Minecraft 来：每个存档一个 64 位种子，可输入、可分享、可复现；不是每次进游戏重 roll。** 当前代码已经是“无存档时随机、有存档时继续”，方向对，缺 64 位种子、生成器版本号、世界列表和多世界槽位。

## 1. 代码地图

| 位置 | 作用 |
|---|---|
| [`TemperateHillsSurface.h`](../../Source/FPSGAME/WorldGeneration/TemperateHillsSurface.h#L19-L27) | 纯数值高度/法线，供后台网格任务复制使用，不碰 UObject |
| [`TemperateHillsWorld.cpp:250`](../../Source/FPSGAME/WorldGeneration/TemperateHillsWorld.cpp#L250-L253) | `Height = BaseHeight + TerrainOffset`；`BaseHeight` 在有河时走 `RiverPlan->Height` |
| [`TemperateHillsWorld.cpp:241`](../../Source/FPSGAME/WorldGeneration/TemperateHillsWorld.cpp#L241-L247) | 与 Surface.h 等价的成员版 value noise |
| [`TemperateHillsRiver.cpp:47`](../../Source/FPSGAME/WorldGeneration/TemperateHillsRiver.cpp#L47) | 全图 16 m 网格优先洪泛，选一条排水河道 |
| [`TemperateHillsRiver.cpp:251`](../../Source/FPSGAME/WorldGeneration/TemperateHillsRiver.cpp#L251-L282) | 河床/河岸混合，`lerp(Base, Bed, Bank)` |
| [`TemperateHillsStreaming.cpp:45`](../../Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp#L45) | 地形格 64 m；`Count = SizeMeters/64`，只接受非负格子 |
| [`TemperateHillsStreaming.cpp:415`](../../Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp#L415-L424) | `Wanted()`：范围裁剪、近/远 LOD 半径 |
| [`TemperateHillsWorld.cpp:546`](../../Source/FPSGAME/WorldGeneration/TemperateHillsWorld.cpp#L546-L646) | 树/石/灌木/草的候选规则与半开边界归属 |
| [`TemperateHillsPCG.cpp:21`](../../Source/FPSGAME/WorldGeneration/TemperateHillsPCG.cpp#L21) | 自定义 PCG 节点只能在主线程执行，且不缓存 |
| [`TemperateHillsBackdrop.h:10`](../../Source/FPSGAME/WorldGeneration/TemperateHillsBackdrop.h#L10) | 远景固定环外半径 5.12 km |
| [`TemperateHillsWorld.cpp:197`](../../Source/FPSGAME/WorldGeneration/TemperateHillsWorld.cpp#L197) | `SizeMeters` 被夹在 256–1024 m，按 128 对齐 |

关键点：`SizeMeters` 的 UPROPERTY 上限也是 1024（[`TemperateHillsWorld.h:169`](../../Source/FPSGAME/WorldGeneration/TemperateHillsWorld.h#L169)）。想上 4 km，先把这几个硬夹子去掉，否则改配置也不会生效。

## 2. 公式拆解

### 2.1 噪声原语

```cpp
Mix(v): 32-bit 整数哈希（xor-shift + 两次乘法）
Key(x,y,seed,salt) = Mix(Mix(x*0x9e3779b9) ^ Mix(y*0x85ebca6b+0x1b873593) ^ Mix(seed+salt))
Unit(key) = (Mix(key) & 0xFFFFFF) / 2^24          // [0,1)
Noise(x,y) = smoothstep 双线性插值的 value noise // [-1,1]
```

所有频率的单位是 **per centimetre**，`X/Y` 是世界厘米。`smoothstep` 在格点处一阶导为 0，所以 value noise 的格线附近会出现“压平”的十字带；这不是渲染问题，是公式本身。

### 2.2 基础高度

记 `N(x,y;salt)` 为上面的 `Noise`，`u = Unit(seed)`：

```text
w(x,y)  = 4200 * N(0.000024 x, 0.000024 y; 14)                 // ±42 m 域扭曲
Hill    = 2400 * N(0.000055 (x+w), 0.000055 (y-0.5w); 73)      // ±24 m, λ≈182 m
Large   = 3200 * N(0.000020 x + 1.31, 0.000020 y - 2.1; 91)    // ±32 m, λ=500 m
V(x)    = 1900 sin(0.000065 x + 3u) + 850 sin(0.00014 x)       // ±27.5 m 东西向摆动
Valley  = -1200 * exp(-((y - V(x)) / 9000)^2)                  // -12 m, σ=90 m
Detail  = 95 * N(0.00035 x, 0.00035 y; 26)                     // ±0.95 m, λ≈28.6 m
        + 14 * N(0.0011 x, 0.0011 y; 88)                       // ±0.14 m, λ≈9.1 m
H       = round(5400 + Large + Hill + Valley + Detail)          // cm
```

注意：公式里的 `3200/2400/1200/95/14` 都是**厘米**系数；后两项换算成米是 ±0.95 m 和 ±0.14 m，不是 ±9.5 m/±1.4 m。

逐项看：

| 项 | 振幅/范围 | 特征波长 | 作用 | 问题 |
|---|---:|---:|---|---|
| 域扭曲 `w` | ±42 m | 417 m | 让丘陵边界不规则 | 只作用于 `Hill`，`Large`/`Detail` 不扭曲 |
| `Large` | ±32 m | 500 m | 区域起伏 | 单个 octave，没有 fBm 的层间细节 |
| `Hill` | ±24 m | 182 m | 主要丘陵 | 单个 octave；与 `Large` 频率比约 1:2.7，缺少中间尺度 |
| `Valley` | -12 m | σ=90 m | 一条谷地 | 只随 `X` 变化，**永远东西向**；无分支、无盆地 |
| `Detail` | ±0.95 m / ±0.14 m | 28.6 m / 9.1 m | 地表细节 | 9.1 m 低于远 LOD 的 8 m 采样 Nyquist |
| 常数 5400 | 54 m | — | 基准高程 | 没有海平面/水位基准 |

`w` 的 4200 cm 是坐标偏移；乘上 `0.000055` 后只相当于 **0.23 个 Hill 格**（±42 m / 182 m），扭曲幅度不大。

### 2.3 河道与地形编辑

- 河道不是高度公式的一部分，而是启动时在 **全图 16 m 网格**上做优先洪泛（priority-flood），选一条满足长度/靠近出生点/切割量评分的排水路径，再按到河心的距离把基础高度 `lerp` 到河床/河岸高度（[`TemperateHillsRiver.cpp:251`](../../Source/FPSGAME/WorldGeneration/TemperateHillsRiver.cpp#L251-L282)）。
- 河宽半宽默认 450 cm（全宽约 9 m），河床深 65 cm，河岸影响约 32 m。它是一条**小溪**，不是把地形切成谷地的大河；真正 180 m 宽的“谷”来自上面的 `Valley` 项。
- 河道计算覆盖整张图：1 km 约 1.6 万节点，4 km 约 25 万，8 km 约 100 万，16 km 约 400 万。它不是按玩家位置流送的。
- 弹坑/铲子编辑是在此之上加的 `FTerrainEdit`，最大下挖 4 m、上填 1 m，按桶索引查询；与高度公式解耦，这部分设计是合理的。

### 2.4 PCG 散布

PCG 图里只有一个自定义节点类型（四层图各挂一个），它调用 `World->GetPlacements(Layer, Bounds, Out)`，把候选点写成带 `Mesh`/`CandidateKey` 属性的点，再交给 UE 原生 StaticMeshSpawner / SkinnedMeshSpawner。散布规则：

| 层 | 网格/间距 | 概率 | 主要拒绝条件 |
|---|---:|---|---|
| 树 | 12 m，抖动 ±0.28 格 | `0.045 + Forest*0.48` | 河岸 >0.02、离谷心 <11.5 m、离出生点 <22 m、法线 Z<0.87 |
| 石 | 24 m，抖动 ±0.4 格 | `0.12 + (1-Nz)*1.6` | 法线 Z<0.72、离谷心 <7 m、离出生点 <16 m |
| 灌木 | 6.5 m，抖动 ±0.4 格 | `0.05 + Forest*0.28` | 法线 Z<0.83、离谷心 <2.4 m |
| 草 | 6.5 m，抖动 ±0.4 格 | `0.77 - Forest*0.23` | 法线 Z<0.83、离谷心 <2.4 m |

`Forest = smooth((N(0.00014x,0.00014y;173)+0.45)/1.05)`，波长 = 1/0.00014 cm ≈ 71.4 m。候选键是 `Key(GX,GY,seed,salt)`，实例 ID 是 `CellId(GX,GY)`；位置按半开边界归属到唯一 PCG 格，所以跨格不会重复。这部分是当前系统里做得最稳的一块。

但：① 只查树干的跨层占用，石/灌木/草之间可以互相重叠；② 没有蓝噪声/Poisson，只有网格抖动；③ 没有道路/据点/群系掩码；④ 自定义节点 `CanExecuteOnlyOnMainThread=true` 且 `IsCacheable=false`，草层按 16 m × 2 m 条带切分也只是缓解主线程压力。

还有一个隐蔽问题：**坡度掩码在基础地形上几乎不触发。** 树的阈值 `Normal.Z<0.87` 对应 29.5°，石 `0.72` 对应 44°，灌木/草 `0.83` 对应 33.9°；而基础地形 1 km 最大 23.9°、4 km 最大 28.7°（见下一节）。所以树几乎不会因坡度被拒，石/灌木/草的阈值在未编辑地形上基本不触发。岩石不会真的长在陡坡上，坡度分层是“有代码、没地形”。

## 3. 数值体检

离线复算 seed 122，基础公式，不含河道和编辑：

| 指标 | 1 km | 4 km |
|---|---:|---:|
| 高程范围 | 20.35–78.76 m | 2.31–100.84 m |
| 相对高差 | 58.4 m | 98.5 m |
| 标准差 | 10.5 m | 16.8 m |
| 平均坡度 | 7.1° | — |
| 95% 坡度 | 14.6° | 15.8° |
| 最大坡度 | 23.9° | 28.7° |
| >30° 占比 | 0% | 0% |
| >45° 占比 | 0% | — |

**波长分布（1 km，2 m 采样）：**

| 波长 | 能量占比 |
|---|---:|
| >800 m | 37.8% |
| 400–800 m | 37.1% |
| 200–400 m | 10.0% |
| 100–200 m | 0.47% |
| 50–100 m | 0.05% |
| <50 m | 0.016% |

也就是说，**约 75% 的地形方差在 400 m 以上，人眼近处能看到的 50 m 以下细节只占约万分之一点六**。近处的“细节”主要来自草、石、地表材质，不是高度场。

**其他量化：**

- **格线压平：** 对未扭曲的 `Large` 项，格线附近平均 |∇H| 只有格中的 **10.8%**（X 方向）和 **47.5%**（Y 方向）。这是 value noise + smoothstep 的轴向伪影，表现为每隔 500 m 有一条隐约的平直带。
- **远 LOD 误差：** 8 m 网格对连续高度的双线性误差 RMS 5.3 cm、最大 23.5 cm；2 m 网格 RMS 0.4 cm、最大 2.5 cm。几何误差本身不大，但 LOD 切换时会有可见跳变。
- **9.1 m 细节欠采样：** 8 m 采样重建的 RMS 误差是该 octave 标准差的 28.5%，混叠到约 **66.7 m** 的假波长。绝对量只有 2 cm，但会在远处产生缓慢的“呼吸”纹理。
- **种子差异：** seed 122 与 123 的 1 km 高度场相关系数 -0.27（不同实现会略有差异），说明种子确实换了布局；但换的是同一统计模型的另一段采样，地貌类型不变。

图：4 km 种子 122 的离线山体阴影（不是游戏截图）——[`hills_seed122_4096m.png`](../../Saved/WorldGenerationAudit/formula-20261019/hills_seed122_4096m.png)；四个种子的 1 km 对比——[`seeds_contact_sheet.png`](../../Saved/WorldGenerationAudit/formula-20261019/seeds_contact_sheet.png)。完整数据在 [`report.json`](../../Saved/WorldGenerationAudit/formula-20261019/report.json)。

## 4. 与“每局随机种子开放世界”的差距

| 优先级 | 问题 | 现状 | 影响 |
|---|---|---|---|
| P0 | 世界只有 1.024 km | `SizeMeters` 夹 256–1024；`Wanted()` 只接受 `[0,Count)`；`GetPlacements` 按 `±Half` 裁 | 走不出样地，无法放 4 km 的路网/据点 |
| P0 | 只有一种地貌 | 4 项固定频率/振幅，无气候、侵蚀、山脊、台地、海岸 | 每个种子都是“同一片牧草地的另一段” |
| P0 | 谷地永远东西向 | `PathDistance = abs(Y - V(X))` | 所有世界的宏观骨架同向；不能形成分支谷/盆地 |
| P1 | 种子 32 位、无生成器版本 | `int32 Seed`，`Mix(GUID.A)` 取随机；存档 Version=3 只是存档结构版本 | 世界不可靠分享；改公式会静默改变旧世界 |
| P1 | 河道全图 O(N²) | 16 m 网格优先洪泛，启动时一次算完 | 4 km 25 万节点、8 km 100 万；不能随玩家流送 |
| P1 | PCG 节点主线程 | `CanExecuteOnlyOnMainThread=true`，不缓存 | 大世界多格并发生成时会卡主线程 |
| P1 | 远景固定环 | `OuterHalf = 5.12 km`，环半径写死 | 4 km 世界的内环/外环顺序会失效；远景不随玩家移动 |
| P1 | 单世界槽 | 固定 `TemperateHills_World` | 不能同时存在多个随机世界，不能做“新游戏/继续/删除”列表 |
| P2 | LOD 只有两档 | 2 m（160 m 内）/ 8 m（384 m 内），裙边 | 4 km 世界视距太短；LOD 切换有跳变 |
| P2 | 9.1 m octave 欠采样 | 远 LOD 8 m 采样 | 远处轻微呼吸/闪烁 |
| P2 | 散布无全局占用 | 只避树干 | 石/灌木/草可重叠；据点/道路净空无法保证 |
| P2 | 坡度掩码空转 | 树 29.5°、石 44°、草 33.9°，但基础地形最大 23.9°/28.7° | 岩石不会真的长在陡坡上，坡度分层名存实亡 |
| P2 | 浮点确定性 | `FMath::Sin/Exp` + 1 cm 取整 | 同平台稳定；跨平台分享种子需固定实现 |
| P2 | 内容预算 | 1 km 约 1,844 棵树，Nanite 骨骼树 | 4 km 同密度约 3 万棵；需要 HLOD/ impostor/ 群系密度 |

## 5. GitHub 上有什么

先说明：**没有一个 MIT 的 UE5 插件能直接给你“Minecraft 式随机种子开放世界”**。成熟件是分层的，需要拼。星数为 2026-10-19 约值。

| 需求 | 仓库 | 许可证 | 星数 | 能借什么 | 不能借什么 |
|---|---|---|---:|---|---|
| 噪声（首选，轻量） | [Auburn/FastNoiseLite](https://github.com/Auburn/FastNoiseLite) | MIT | 3.5k | 单头文件 C++98；OpenSimplex2/Perlin/Value/Cellular；fBm、ridged、domain warp 都是内置枚举 | 没有 SIMD；超大面积烘焙时性能一般 |
| 噪声（SIMD/节点图） | [Auburn/FastNoise2](https://github.com/Auburn/FastNoise2) | MIT | 1.4k | C++17 + SIMD，适合一次烘焙几百万点或高吞吐生成 | 集成比 Lite 重；运行时按点采样不一定划算 |
| 噪声算法参考 | [KdotJPG/OpenSimplex2](https://github.com/KdotJPG/OpenSimplex2) | CC0 | 0.7k | 无轴向偏置的 2D/3D 实现与论文式说明 | Java 参考实现，C++ 需移植或用 FastNoiseLite 的 C++ 版 |
| Minecraft 群系/结构 | [Cubitect/cubiomes](https://github.com/Cubitect/cubiomes) | MIT | 1.0k | 1.18 多噪声群系、64 位种子、结构位置；最好的“照抄参数语义”参考 | **只做群系/结构，不做方块地形**；C 库，不能直接塞进 UE |
| Minecraft 式分块世界（最小） | [fogleman/Craft](https://github.com/fogleman/Craft) | MIT | 11.1k | 无限区块、噪声地形、SQLite 持久化、玩家/方块交互的最小闭环 | 地形和群系很简化；C/OpenGL，不是 UE |
| 体素地图生成（完整） | [luanti-org/luanti](https://github.com/luanti-org/luanti) | LGPL-2.1+（代码） | 13.7k | mapgen v7 的群系/洞穴/装饰/分块调度，工程上很成熟 | 体素后端；LGPL 有源码/重链接义务；美术资源 CC BY-SA，不能直接搬 |
| UE 运行时网格 | [TriAxis-Games/RealtimeMeshComponent](https://github.com/TriAxis-Games/RealtimeMeshComponent) | MIT | 1.8k | 运行时 LOD、碰撞、分区更新、异步提交；比 DynamicMeshComponent 更适合大量地形块 | 需要改地形后端；不是“开箱即用的地形系统” |
| UE PCG 扩展 | [Nebukam/PCGExtendedToolkit](https://github.com/Nebukam/PCGExtendedToolkit) | MIT | — | 聚类、路径、空间过滤、样条、属性操作等生产级 PCG 节点 | 仍是 PCG 层，不生成高度场 |
| 体素/Transvoxel（仅参考） | [VoxelPlugin/VoxelPluginFreeLegacy](https://github.com/VoxelPlugin/VoxelPluginFreeLegacy) | 仓库未声明 SPDX | 1.8k | Transvoxel、体素 LOD、无限世界的工程参考 | 免费 legacy 版；当前 Voxel Plugin 2 是商业版；**许可证不明确，不能直接当 MIT 用** |

几条判断：

- **Cubiomes 是最值得读的“Minecraft 1.18 参数语义”参考，但它不是地形生成器。** 它把 temperature/humidity/continentalness/erosion/depth/weirdness 映射到群系；地形高度是另一套样条。你可以借它的参数命名、量纲、群系表结构，不要指望它给你高度。
- **Craft 适合看“最小分块世界怎么闭环”，不适合看地貌质量。** 它的地形只有几层噪声，群系也很粗；但区块加载/卸载、玩家周围生成、SQLite 存档的代码很短，适合对照。
- **Luanti 是完整答案，但许可证是 LGPL。** LGPL 允许与闭源程序链接，但有提供 LGPL 部分源码、允许用户替换/重链接等义务；静态链接进 UE 模块时要在发布前让法务确认。更稳的做法是只读它的 mapgen 设计，自己实现。
- **VoxelPlugin 不要因为“像我的世界”就引入。** 本项目已经在 2026-09-16 退役体素地形；再引入第二套地形后端，流送、LOD、碰撞、存档、植被、导航全部要重做。高度场 + 独立洞穴入口网格是更便宜的路线。

### 算法清单（不依赖某个仓库）

| 问题 | 成熟算法 | 备注 |
|---|---|---|
| 连续噪声 | OpenSimplex2 / Perlin / Value + fBm、ridged、billow | FastNoiseLite 已封装；关键是每层用不同 seed 和频率 |
| 域扭曲 | Inigo Quilez 的 domain warping | 当前只扭曲了 Hill；应扭曲山脊和细节 |
| 山脉/山脊 | ridged multifractal（Musgrave） | `1 - abs(noise)` 叠加，配合侵蚀权重 |
| 气候/群系 | Minecraft 1.18 多噪声：地形用 continentalness、erosion、peaks&valleys、weirdness；群系用 temperature、humidity、continentalness、erosion、depth、weirdness；高度再走样条 | 公开资料可查；Cubiomes 是可运行的语义参考 |
| 河流/湖泊 | priority-flood 填洼 + flow accumulation；或 Voronoi 河网 | 当前已用 priority-flood，但只选一条河、全图计算 |
| 地形 LOD | CDLOD / geometry clipmap；相邻级用裙边或 stitched 边界 | 当前是两档 + 裙边，可先扩到 3–4 档 |
| 植被散布 | Poisson-disk / blue noise；分层占用掩码 | 网格抖动够用，但大世界需要跨格去重和净空 |
| 据点/村庄 | WFC、图语法、模板拼接 | 先用 6–10 套手工模板 + 随机组合，不要一上来做语法 |
| 侵蚀 | droplet erosion / thermal erosion，离线烘焙 | 运行时逐块算太贵；每个种子在世界创建时烘焙一张粗侵蚀图，或直接用“侵蚀”噪声参数近似 |

## 6. 推荐架构

### 6.1 分层

```text
WorldSeed (64-bit) + GeneratorVersion + RulesetHash
        │
        ├─ MacroRecipe（每局一次，存档）
        │    ├─ 大陆度 / 侵蚀度 / 气候（温度、湿度）
        │    ├─ 出生地、据点候选、主路连通图
        │    └─ 河流/湖泊的粗流向图
        │
        ├─ Height(x,y)（纯函数，任何线程可算）
        │    ├─ base = Spline(continentalness)
        │    ├─ relief = f(erosion)
        │    ├─ ridge = ridged fBm(peaks&valleys)
        │    ├─ detail = fBm，按距离衰减
        │    └─ river/lake carve（从 MacroRecipe 采样）
        │
        ├─ BiomeWeights(x,y)（温度 × 湿度 × 海拔 × 坡度 × 河流距离）
        │
        ├─ Chunk(128 m) → LOD 网格 + 碰撞 + 水体
        │
        ├─ PCG 层（树/石/灌木/草/据点），每格 + 1 格 halo
        │
        └─ WorldDelta（地形编辑、采伐、建筑、容器）→ 存档
```

### 6.2 硬规则

1. **种子 64 位。** `WorldSeed` 用 `int64`/`uint64`；`ChunkSeed = SplitMix64(WorldSeed ^ Hash(CellX,CellY))`；每层再派生独立 salt。不要用 `rand()`、`std::hash` 或时间。
2. **生成器版本化。** 存档写 `GeneratorVersion` 与 `RulesetHash`；旧世界继续用旧版本公式，不能静默升级。当前 `Version=3` 只是存档结构，不是公式版本。
3. **先做有限世界。** 4 km × 4 km（半宽 2 km），世界边界用山脊/海/峭壁+雾收口，不做隐形墙。坐标仍在 ±2 km 内，float 精度足够，不需要原点重定位。
4. **宏观与微观分开。** 宏观（大陆度、侵蚀、气候、河流、据点）每局算一次并写进 `WorldRecipe`；微观（高度细节、草、石）按块实时算。不要让每个块重新决定河流走向。
5. **PCG 只做“点 + 属性”。** 高度、坡度、群系权重、河流距离、道路距离、据点净空都由 C++ 提供；PCG Graph 负责实例化和资产选择。自定义节点把纯数学放 worker，主线程只创建组件。
6. **稳定 ID。** `EntityId = StableHash(WorldId, CellX, CellY, LayerId, CandidateKey)`；CandidateKey 来自候选格坐标，不用过滤后的数组下标。
7. **存档只存差量。** `WorldHeader`（seed/version/bounds）+ `WorldRecipe`（宏观结果）+ `ChunkDelta`（编辑/采伐/建筑/容器）。不存地形顶点。
8. **水体单独一层。** 河/湖的水面是独立网格和材质，不要用地形高度“假装水”；水深、流向、岸边湿度都可从同一张粗流向图采样。

### 6.3 分块与 LOD

| 层 | 建议 | 说明 |
|---|---|---|
| 逻辑块 | 128 m | 比现在的 64 m 少一半格数；PCG 格可继续 64/32/16 m |
| 地形 LOD | 2 / 4 / 8 / 16 / 32 m，4–5 圈 | 近处 2 m，1–2 km 视距；用 CDLOD 或 clipmap，裙边只遮缝 |
| 碰撞 | 仅近圈（约 128–192 m） | 远处不烹碰撞；传送/落地前等待目标格 |
| 远景 | 真实低模地形或天空盒山脊 | 不要再用固定 5.12 km 环；远景要随玩家移动或做成无限地平线 |
| 植被 | 树 300–500 m、石 200 m、草 60 m | 远处用 impostor/HLOD；按群系调密度 |

### 6.4 世界管理

- `WorldSlot`：一个 `WorldId` + `WorldSeed` + `GeneratorVersion` + 创建时间 + 玩家档引用。
- 新游戏：输入种子（可空 → 随机 64 位）→ 生成 `WorldRecipe` → 验证（出生点可走、河流到边界、据点连通）→ 写头 → 加载出生块。
- 继续：读头 → 版本检查 → 重建 Recipe → 按块重建 → 应用 Delta → 过滤已采伐实体 → 放玩家。
- 删除/复制世界：只动槽位和 Delta，不动物理地图。

## 7. 参考公式 v2

下面是一个可落地的起点，不是最终数值。单位仍是 cm，噪声用 FastNoiseLite 的 OpenSimplex2 + fBm/ridged。

### 7.1 宏观参数

| 参数 | 频率/波长 | 类型 | 用途 |
|---|---|---|---|
| `C` 大陆度 | 1/6000 m，4 oct | fBm [-1,1] | 决定基准海拔：低地/丘陵/山地 |
| `E` 侵蚀度 | 1/2200 m，4 oct | fBm 重映射 [0,1] | 高=平缓，低=崎岖 |
| `PV` 峰谷 | 1/850 m，4 oct | ridged [0,1] | 山脊/谷地 |
| `T` 温度 | 1/4000 m，3 oct | fBm [-1,1] | 群系 |
| `M` 湿度 | 1/3200 m，3 oct | fBm [-1,1] | 群系 |
| `D` 细节 | 1/55 m，3 oct | fBm [-1,1] | 近处起伏，按距离衰减 |

### 7.2 高度

```text
base  = Spline(C, { -1: 8, -0.35: 22, 0: 45, 0.35: 85, 0.75: 170, 1: 300 })   // m
amp   = lerp(210, 18, smoothstep(0.15, 0.85, E))                               // m
H     = base + amp * PV + (2 + 6*(1-E)) * D                                     // m
```

- `C` 低 → 8–45 m 的湿地/平原；`C` 高 → 170–300 m 的山地。
- `E` 高 → 起伏只有 18 m；`E` 低 → 起伏 210 m，配合 ridged 的 `PV` 可以出现 >45° 的岩坡。
- `D` 的振幅 2–8 m、波长 55 m，在 2 m 网格上可表达；超过 300 m 视距后淡出，避免远 LOD 欠采样。

### 7.3 群系

用 `T/M/C/E` 查表 + 软权重，不要用 if-else 硬切：

| 条件 | 群系 | 植被/地表 |
|---|---|---|
| `T` 低、`M` 高 | 湿冷针叶/湿地 | 密针叶、芦苇、泥炭 |
| `T` 中、`M` 中 | 草甸/疏林 | 当前 Black Poplar + 草花 |
| `T` 高、`M` 低 | 干草原/岩坡 | 稀疏草、碎石、露岩 |
| `E` 高、`C` 中 | 台地/平原 | 深土、农田/废墟 |
| `C` 高、`E` 低 | 山地 | 岩坡、悬崖、雪线（可选） |

群系权重用于：地表材质混合、树/草密度、岩石族、环境音、怪物表。权重在块边界要连续，不能按格硬切。

### 7.4 河流/湖泊

- 在 32 m 或 16 m 粗网格上算 `flow accumulation`；对每个盆地做 priority-flood 填洼；河宽随流量 `sqrt(flow)` 增长。
- 只在世界创建时算一次，存成 `RiverPlan`（点列 + 半宽 + 水位）；块生成时按距离采样，`lerp` 到河床。
- 湖泊 = 填洼后仍低于出水口的洼地；水面高度取溢出高程。
- 河岸带用湿度/材质/植被权重表达，不要只挖一条沟。

### 7.5 分块

- 块 128 m；高度采样 2 m（近）/4/8/16/32 m（远）。
- 相邻 LOD 共享边界顶点；不能共享时用裙边遮缝，碰撞仍按各自网格。
- 每块生成完写 `ChunkState`：`HeightReady/CollisionReady/NavReady/PCGReady`；传送/落地只等目标块。
- PCG 每层带 1 格 halo 计算候选，只输出归属本块的点；跨块占用用稳定优先级解决。

## 8. 迁移路线

| 阶段 | 内容 | 关键文件 | 风险/备注 |
|---|---|---|---|
| P0 快修（1–2 天） | ① `Seed` 改 64 位并派生 salt；② 加 `GeneratorVersion`；③ 谷地方向按种子旋转；④ 9.1 m octave 按距离淡出；⑤ 去掉 `SizeMeters` 1024 上限，先允许 2048 | `TemperateHillsWorld.h/.cpp`、`TemperateHillsSurface.h` | 旧存档必须继续走 V1 公式；不要直接覆盖 |
| P1 扩到 4 km（1–2 周） | ① `Wanted()` 改成以玩家为中心的环形格索引；② `GetPlacements` 去掉 `±Half` 硬裁；③ 远景环改为跟随玩家/真实 LOD；④ 世界槽位 | `TemperateHillsStreaming.cpp`、`TemperateHillsBackdrop.*`、存档 | 先测 2 km 再上 4 km；注意 `Count` 与 `CellOrigin` 的负索引 |
| P2 宏观地貌（2–4 周） | ① 多噪声 `C/E/PV/T/M`；② 高度样条；③ 群系权重与材质/植被；④ 河道改为粗流向图 | 新 `WorldRecipe`/`HeightV2`；PCG 掩码 | 会改变所有新世界；旧世界锁 V1 |
| P3 世界内容（3–6 周） | 据点模板、道路连通、出生地选择、POI、导航 | 新子系统；PCG 图 | 先做 6–10 套模板，不要先做语法 |
| P4 性能/远景（持续） | 3–4 档 LOD、HLOD/impostor、PCG worker、异步碰撞 | Streaming/PCG | 以 60 FPS、生成 1–2 ms/帧为预算 |

建议顺序：**P0 → P1（2 km 验证）→ P2 → P1（4 km）→ P3**。不要先做 8 km/无限；先把 2 km 的边界、河流、远景、存档跑通。

## 9. 验收指标

纯算法（不依赖渲染）：

1. 同 seed + 同 `GeneratorVersion`，在 100 个固定点的高度哈希一致；改变线程顺序/块生成顺序结果不变。
2. 相邻块边界高度差 = 0（共享函数）；法线夹角 < 0.1°；LOD 接缝无可见裂缝。
3. 100 个种子：高程范围、坡度分布、群系覆盖率在目标区间；无 NaN/Inf；出生点坡度 < 8°、离水 > 20 m、在边界内。
4. 河流：从源头到边界/湖泊全程下降（允许局部回水），不穿山脊；河口与水面高度一致。
5. 据点：每个主据点至少一条纵坡 ≤15° 的连通路径；门口净空 ≥ 4 m。
6. PCG：候选 ID 唯一；跨块无重复；树不在河里/出生圈/道路上；石/灌木/草不插进树干；物体接地误差 < 5 cm。
7. 存档：重载后高度哈希、据点、采伐/编辑状态一致；旧版本世界不被静默改写。

运行时（需要真实打包）：

8. 60 FPS 基线，生成提交 1–2 ms/帧；碰撞/导航/资源首次加载单独计时。
9. 长距离奔跑/传送无缺地、无掉出世界；LOD 切换无 >1 帧的可见跳变。
10. 4 km 世界内存/显存峰值在预算内；树/草实例数不超过上限。

## 10. 参考

- [FastNoiseLite](https://github.com/Auburn/FastNoiseLite)（MIT）与 [FastNoise2](https://github.com/Auburn/FastNoise2)（MIT）
- [OpenSimplex2](https://github.com/KdotJPG/OpenSimplex2)（CC0）
- [Cubiomes](https://github.com/Cubitect/cubiomes)（MIT，Minecraft 1.18 群系/结构）
- [Craft](https://github.com/fogleman/Craft)（MIT，最小分块世界）
- [Luanti](https://github.com/luanti-org/luanti)（LGPL-2.1+，体素地图生成）
- [RealtimeMeshComponent](https://github.com/TriAxis-Games/RealtimeMeshComponent)（MIT，UE 运行时网格）
- [PCG Extended Toolkit](https://github.com/Nebukam/PCGExtendedToolkit)（MIT，UE PCG 扩展）
- [Voxel Plugin Free Legacy](https://github.com/VoxelPlugin/VoxelPluginFreeLegacy)（许可证未声明，仅参考）
- [Minecraft Wiki: World generation](https://minecraft.wiki/w/World_generation)（1.18 多噪声/样条/群系的公开说明）
- [Minecraft Wiki: Custom world generation](https://minecraft.wiki/w/Custom_world_generation)（noise settings 参数名与结构）
- Priority-Flood：Barnes, Lehman, Mulla, *Priority-Flood: An optimal depression-filling and watershed-labeling algorithm for digital elevation models*, Computers & Geosciences, 2014.
- CDLOD：Strugar, *Continuous Distance-Dependent Level of Detail for Rendering Heightmaps*, Journal of Graphics, GPU, and Game Tools, 2010.
- Poisson disk：Bridson, *Fast Poisson Disk Sampling in Arbitrary Dimensions*, SIGGRAPH 2007.

## 11. 复算方法

[`audit_hills_formula.py`](../../Tools/WorldGeneration/audit_hills_formula.py) 逐行复刻 `TemperateHillsSurface.h` 的 32 位哈希、24 位 unit、smoothstep 双线性噪声和 4 项高度，采样后输出：

- `report.json`：高程/坡度/频谱/格线偏差/LOD 误差/种子对比/河流节点数。
- `hills_seed122_4096m.png`：4 km 离线山体阴影。
- `seeds_contact_sheet.png`：四个种子的 1 km 对比。

```powershell
python Tools/WorldGeneration/audit_hills_formula.py --seed 122
python Tools/WorldGeneration/audit_hills_formula.py --seed 122 --half-m 2048 --step-m 4 --out D:/tmp/hills
```

它只是数值复算，不替代游戏内画面、碰撞、流送和性能验收。