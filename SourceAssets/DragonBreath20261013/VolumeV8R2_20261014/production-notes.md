# 龙息 V8 R2：主体暖色与高光控制

2026-10-14。用户反馈火焰主体过白，并授权执行已讨论的优化方案。

## 制作范围

沿当前三维体积火焰修改颜色与发光，不重做流体，不改源粒子、方向、遮挡、技能成长、伤害、耗蓝、修炼或网络逻辑。原火球、篝火与 Epic 母版保持原样。

R1 的温度显示范围为 0.35–5.3，而上一轮独立诊断记录的模拟热值最高约 145.875。这些是模拟标量，不是摄氏温度。本轮不重跑模拟，使用已有数据制定颜色映射。

## 颜色与厚度分离

- 专用材质以 VolumeTex 的 G 通道读取温度，颜色范围独立设为 0.35–160。
- 原有透明度温度范围 0.35–5.3、温度透明度增益 1.25、烟密度增益 0.18 保持，避免压低高光时把整个火柱变稀。
- 颜色使用平滑的暗红、橙红、橙黄、金黄、暖浅黄五段曲线，最高段仅在归一化热值 0.90–1.00 过渡，曲线没有中性纯白端点。实际高光屏幕占比尚未测量。
- Temperature Color Gain 从 0.8 调整为 0.4，仍乘 User.Strength，停火淡出沿用原实现。
- 复制 R1 材质中的单次曝光补偿，不额外叠加。颜色选择的两个静态分支都使用专用曲线，避免继承的黑体开关重新选回白热曲线。
- 复用同一 VolumeTex 采样结果，只新增颜色计算，不增加流体网格、可见粒子或体积纹理采样。

HLSL 源：本目录 `DragonFlameColor.hlsl`。
增量入口：`Tools/Skills/build_dragon_volume_color.py`。
完整重建入口：`Tools/Skills/build_dragon_breath.py` → `build_dragon_breath_volume.py`，已同步 R2 材质及增益。

运行系统继续使用 `/Game/Skills/DragonBreath20261013/VolumeV8/NS_DragonVolume`，绑定同目录的 `MI_DragonVolumeFlame_R2` / `M_DragonVolumeFlame_R2`。
恢复副本：`trash/DragonBreathVolumeV8R2_20261014`，包含修改前系统、两份 R1 材质和完整作者脚本。

保存结果以 `delivery.json` 和 `Saved/DragonBreathVolumeV8R2_20261014/author-warm-body.log` 为准。仅制作、必要编译和保存；没有自动启动 GUI 编辑器、游戏、PIE、截图、GPU 回读或视觉／性能验收，最终观感由用户试玩确认。

实际落盘：2026-10-14 16:18:42，制作进程退出码 0，材质编译完成，Niagara `valid=1, pending_after=0`。系统与两份 R2 材质均已保存；无需为本次资产改动重编游戏模块。
