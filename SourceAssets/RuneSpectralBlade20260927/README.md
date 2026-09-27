# 幽蓝灵体剑 · 2026-09-27

用户选择的 G 键环绕飞剑新外观。原创程序建模与解析材质，不含第三方模型或纹理。

## 作者与引擎资产

- Blender 源：SpectralRuneBlade.blend；作者脚本：build_spectral_blade.py。
- 全长 60 cm，剑尖 +X，剑身宽 3.36 cm、最厚 0.62 cm；保留原飞剑原点及朝向合同。
- 四个 FBX：SM_SpectralRuneBlade、SM_SpectralWake、SM_SpectralWisp（初版保留）、SM_SpectralImpactParticle（当前命中粒子）。
- 导入：import_spectral_blade.py；输出 /Game/Weapons/RuneSpectralBlade20260927。
- 剑身采用真实透射的 Substrate Unlit BSDF；细刃面和两面的几何符文分材质。半透明外壳不做厚重折射，符文及淡纹基于物体自身 UV 流动，不随飞行滑动贴图。
- 短拖尾由三条渐细带组成，仅发射后显示。命中立刻隐藏整剑和尾迹，使用一个 ISM 组件播放随机大小、旋转与扩张速度的亮蓝爆心、不规则冲击弧、蓝色光晕和 32～48 个飞散粒子，整体 0.85～1.15 秒消散；复用已有蓝光灯短暂照亮命中处。
- 超时、收起或射程到达后的剑体用真实透明度淡出，取消旧缩小成点的表现。
- 沿用原四剑、可追加剑数、伤害快照、扫掠半径、速度、射程、手势队列、命中与冷却规则。
- 新网格使用已有预加载目录；每次召唤建立动态材质，流光由 GPU 时钟驱动。无新增贴图与 Tick 加载；每次命中保留 3 层爆炸主体，总实例数上限 51。随机参数在命中时确定，随后连续演化。

## 接入状态

当前为 [随机蓝色爆炸 V4](BlueExplosionV4Random/README.md)：针对用户反馈 V3 形状固定，随机化主体、冲击弧和粒子喷散。本版构建与材质保存结果以该目录记录为准。没有启动游戏测试。此前加强可见性的版本保留在 [蓝色魔法爆炸 V3](BlueExplosionV3/README.md)。

前版加深蓝色与命中粒子记录保留在 [BlueImpactV2/README.md](BlueImpactV2/README.md)，剑体深蓝和不透明度继续沿用该版。

初版三个网格与四个材质已保存（import_receipt.json，saved=true），四个材质编译错误列表均为空。飞剑 4,988 三角面，短尾迹 192 三角面，单缕灵光 128 三角面。M_SpectralWake 的实例化网格用途已编译并保存（finalize_commandlet.log）。
FPSGAMEEditor Win64 Development 常规构建完成并链接 UnrealEditor-FPSGAME.dll，native-build.log 记录 Result: Succeeded。实际运行引用与生成的预加载目录均已切换至新资产。
未主动启动游戏、截图、渲染或执行测试，视觉效果由用户测试。

接入过程记录：桥接等待期间，编辑器执行 Live Coding 并重载尚在制作中的 RuneOrbBlade 类时崩溃；之后改用独立后台 commandlet，修正 Python 材质接口差异，完成新资产保存，再完成常规构建。没有自动重开编辑器。
