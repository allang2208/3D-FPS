# 龙息 V8 R1：方向与体积火焰显示

2026-10-14，针对用户反馈“喷射方向反了，看不到任何火焰”排查。

## 定位依据

- 读取实际运行引用 `/Game/Skills/DragonBreath20261013/VolumeV8/NS_DragonVolume`，运行代码仍以瞄准方向提供世界空间 Forward、Side、Up 和法杖喷口位置。
- 独立诊断 commandlet 在 0、90、180 度读取 GPU 源粒子与流体纹理。源粒子沿各自前方运动，三个角度均有温度数据；原始纹理为 G16R16F，981120 个有效体素，最高温度约 145.875。因此不直接反转玩法方向。
- 原生粒子注入的 streak 偏移将世界空间速度用于局部网格索引；随组件转动时空间不一致。本次将 Max Streak Samples 限制为 1，取消附加的位移样本。
- 通用气体材质含旧版坐标与采样分支。龙息专用材质明确指定局部网格坐标、R=密度/G=温度，避免落回旧版通道；按现用火焰材质的方式添加一次 EyeAdaptationInverse。没有取得旧运行实例的最终 MIC 分支，不能将旧分支一定启用写成已证实根因。
- 使用 5.8 的 InterpolatedSpawnMode=NoInterpolation，替代没有生效的旧 bInterpolatedSpawning 字段。

## 已交付内容

- 原运行路径的 NS_DragonVolume，以及同目录下 M_DragonVolumeFlame_R1、MI_DragonVolumeFlame_R1，2026-10-14 14:44 完成后台保存。
- `Saved/DragonBreathVolumeV8_20261014/install-r1-save.log`：退出码 0，Niagara `valid=1, pending_after=0`，两份材质编译与保存完成。
- 增量修复入口 `Tools/Skills/repair_dragon_volume_visibility.py`，完整作者 `build_dragon_breath_volume.py` 与源粒子作者 `dragon_fluid_source.py` 同步。默认入口仍为 `build_dragon_breath.py`。
- 保留 90 度、5–15 米、0.5 秒伤害节拍、法杖要求、耗蓝、修炼及网络玩法。本轮未修改游戏 C++，不要求重编游戏模块。
- 原资产与两份作者恢复副本在 `trash/DragonBreathVolumeV8R1_20261014`。厂商气体模板、现用火球与篝火未改动。

诊断工具位于 AuthorHost 的 DragonFluidInspectCommandlet，只用于本次明确要求的排查。它读取独立世界的方向、粒子和温度数据，不进入游戏或 PIE，不生成截图；这些数值不能代替玩家视角的视觉验收。实际画面仍由用户测试。

首轮修复后定向复读：`direction-repaired.log` 退出码 0；三个朝向仍有源粒子及温度。然而关闭 Use Streaking 后，原生模块把运行时 MaxStreakSamples 替换为 100、Streak Rate 保持 1，标量 splat 又不读取该静态开关。因此首轮不能算拖尾修复完成。最终作者保持 Use Streaking=true，并将生效的 Max Streak Samples 限制为 1。

最终版本于 14:48:54 保存，`install-r1-single-sample.log` 退出码 0、`valid=1, pending_after=0`。随后 `direction-single-sample.log` 退出码 0，三个朝向的运行时 MaxStreakSamples 均为 1，分别有 92848、92870、92997 个有温度的体素，源方向均朝前。最终结果已更新到 `diagnosis-after` 和 `delivery.json`，取代首轮诊断结论。未进行游戏或画面验收。
