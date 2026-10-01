# 汇聚弹 V2：真实尺寸螺旋与柔和余光

本轮按用户要求排查并调整现有汇聚表现。按后续指定，配色由纯白改为蓝色，并提高不透明度：加粗蓝色弹芯、蓝色螺旋环绕、整条蓝色拖尾，命中后停留 0.5 秒再渐隐。本文替代上一份案例中的几何、材质和拖尾时序结论；并非实机视觉验收。

## 源码排查得到的问题

- `FVector(ScaleXY,ScaleXY,Length)/100` 把已换算好的螺旋 XY 缩放再次除以 100：半径 12 cm 实际变成 0.12 cm，管粗 3 cm 变成 0.03 cm。不能仅用亮度参数补救。
- `SpiralTurns` 默认 20，但使用点限制最大 12，文档的 20 圈没有实际生效。
- 普通曳光 V13 将颜色混向 `(1,0.95,0.80)`；即使传入纯白，也不能保持中性白。
- 光柱复用短曳光的局部坐标与端盖判断。旧的 `[13,50]` 平台几何绕开了长轴渐暗，但仍继承硬管侧面及不合适的端部算法。
- 拖尾宽度取飞行弹芯的像素补偿值，弹头越远，枪口附近同一根光柱也越粗；此前 40 cm 只是上限，不能消除这种变化。
- `LingerSeconds=0.5` 实际是立刻开始淡出的总时长。瞬发分支又只增加 `FlashAge`、拖尾却读取 `LingerAge`，会维持亮度后突然回池。
- 旧 SKILL 所述“只能接受截面拉伸或逐帧重建”并不成立：固定世界尺寸网格配合材质显隐即可保留稳定组件与真实截面。

已有 22:56–22:57 日志中的 `CONVERGENCE_SHOT` 与 `TRACER_CONVERGED` 说明附魔标记和飞行路径已传到表现层；日志中的组件可见状态不等于玩家看见了理想画面。本轮没有启动游戏复现。

## 本轮实现

- 专用 `/Game/Weapons/GunplayFX/M_ConvergenceBeamV2`，从 V13 复制必要图结构，保留深度交界淡化及时域响应，替换颜色和形状函数。普通曳光继续使用原材质。
- 螺旋直接以厘米建模：半径 12、管粗 3、默认最大段长 1800 上 20 圈（固定螺距 90 cm）；常见 800 cm 可见窗口约 8.9 圈。几何位于 `z ∈ [-MaxLength,0]`，头端跟随弹头，实例缩放恒为 1。材质按实际段长隐藏尚未离开枪口的部分；不逐帧重建，不按段长拉伸截面。
- 螺旋每圈 24 段、截面 8 边，默认 7680 三角形；CVar 参数改变时才重建，段数上限 768。命中后停止自转并随弹芯淡出。
- 弹芯保留 ×2 宽度语义，额外限制默认直径最多 14 cm，并按螺旋内径留间隙；专属光晕亮度降至原值的 35%，使外侧环绕有辨识空间。
- 蓝色拖尾宽度独立于飞行弹芯的视深。默认 `1.6 × 2 × 2.8 = 8.96 cm`，世界宽度上限 24 cm；全路径仍保留，默认不限长。起点 65 cm 柔化、末端 24 cm 柔化均用世界尺度，不随千米路径放大。
- 后续配色调整使用 `Config/DefaultEngine.ini` 的 `[ConsoleVariables]`：线性蓝 `(0.08,0.35,1.0)`、拖尾 Emission `0.75`，覆盖 C++ 旧回退值。材质 Tint 默认值也改蓝色；空间 alpha 乘 1.35 后限幅，再乘时序 Opacity，保留尾段渐隐。弹芯／螺旋／拖尾的 facing 指数从 `1.35/0.8/1.6` 降至 `1.0/0.65/1.15`，让侧面轨迹更实。这次仅调配置和材质，不需要 C++ 构建。
- 命中后保持 0.5 秒，再用 0.35 秒曲线渐隐，总生命周期约 0.85 秒，按帧结束。瞬发与飞行两条路径使用各自正确的年龄；关闭拖尾时不额外保留池格。
- 不改变附魔扣弹、伤害类型与倍率、碰撞、弹速、射程、散布、后坐力。

## 新增或调整参数

| CVar | 默认 | 含义 |
| --- | --- | --- |
| `fps.Tracer.Converged.Tint` | `0.08,0.35,1.0` | 当前项目配置的蓝色，应用于弹芯、螺旋、拖尾、光晕及随弹灯 |
| `fps.Tracer.Converged.MaxWidthCM` | 14 | 弹芯直径上限，同时留出螺旋间隙 |
| `fps.Tracer.Converged.SpiralTurns` | 20 | 最大曳光窗口上的圈数，允许 0.25–32 |
| `fps.Tracer.Converged.HaloScale` | 1 | 汇聚额外光晕宽度倍率 |
| `fps.Tracer.Trail.LingerSeconds` | 0.5 | 命中后的保持阶段 |
| `fps.Tracer.Trail.FadeSeconds` | 0.35 | 保持结束后的渐隐阶段 |
| `fps.Tracer.Trail.NearFadeCM` | 65 | 枪口端自然出现的长度 |
| `fps.Tracer.Trail.Emission` | 0.75 | 当前项目配置的拖尾自发光 |
| `fps.Tracer.Trail.MaxWidthCM` | 24 | 独立世界直径上限 |

## 交付状态

以下构建记录属于 V2 几何与时序改动；蓝色与透明度调整单独记录材质保存结果，不把旧构建当成本次视觉验收。

- 2026-09-30 蓝色与不透明度调整已保存到配置和 `M_ConvergenceBeamV2.uasset`。后台命令返回 0，制作日志为 `Saved/Logs/ConvergenceBlue-Author-20260930.log`。本次未改变 C++，无需重编译原生模块。
- 本次编辑器接入未发现可连接节点，未执行在线脚本；编辑器已退出后使用 NullRHI commandlet 完成材质制作、编译和保存。未重新打开交互编辑器，也未启动游戏测试。

- 材质作者源：`SourceAssets/ConvergenceVFX20260929/ConvergenceBeamV2.hlsl`。
- 后台制作入口：`Tools/AssetPipeline/build_convergence_v2.py`。
- 资产已实际保存；后台制作日志 `Saved/Logs/ConvergenceV2-Author.log` 中有 `CONVERGENCE_V2_SAVED`，commandlet 返回 0。使用 NullRHI，不作为图形渲染验收。
- Editor 构建已成功：`Saved/BuildEditor/build-20260929-233520.log`，生成基础 `UnrealEditor-FPSGAME.dll`。
- Game 构建已成功：`Saved/BuildEditor/build-game-convergence-v2-20260929.log`，生成 `Binaries/Win64/FPSGAME.exe`。
- 未打开交互编辑器，未运行 PIE、游戏、截图或视觉测试；最终观感交由用户测试。
