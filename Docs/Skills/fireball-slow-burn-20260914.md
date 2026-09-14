# 火球缓慢燃烧版本（2026-09-14）

用户要求减少火球的轮廓感和细线感，采用已讨论的柔和亮核与慢速翻滚火焰方案。

后续已在该运行主体中追加 [Free Spline VFX FireFlame 外焰](fireball-outer-flame-20260914.md)。本文记录基础两层结构，新增外焰的参数和来源见后续说明。

## 资产与视觉组织

- 运行主体引用改为 `/Game/Skills/Fireball/NS_FireballSlowBurnCore`。
- `FireballCore` 使用已有 Epic FireBall 8×8 循环贴图，生成率 3/s、寿命 1.5–2 s，出生位置分散在球心附近 1–4 cm，尺寸约 22–28 cm。取消同尺寸粒子完全重叠在原点的做法。
- `FireballSlowRoil` 使用本地 `MI_FireRoil_8x8` 对应的 FireRoil 循环素材，生成率 10/s、寿命 1.2–1.8 s，出生位置覆盖内部 2–8 cm，宽短火焰片约 17–27 cm。悬浮时以 3 cm/s 缓慢上移，并有小幅不同步横向摆动。
- 两层均独立随机起始帧，以 10–13 帧/s 播放 64 帧循环，保留帧间混合。取消速度拉伸、统一绕轴旋转及不断扩张的球壳。不同粒子的尺寸、位置和播放相位错开。
- 新建专用材质 `M_FireballSoftSprites`，从 Epic 原始父材质复制。移除该副本的低透明度直接裁切，增加轻微变化的柔和边缘衰减，接入原父材质的深度淡化和预乘透明输出之前。没有修改库中原始材质。
- `MI_FireballSoftInner` 与 `MI_FireballSlowRoil` 分别调整发光、透明度与温度范围；不再让粒子透明度驱动硬阈值裁切。首版没有烟雾、表面火星与细长外火舌。
- 点光源强度由 1400 调整为 1250，快速单频闪烁改为两个小幅、慢速周期叠加。

## 发射与玩法

- 保持凝聚、脱手悬浮、左手恢复、发射、碰撞、爆炸、伤害、耗魔及经验规则。
- 新增私有 `FlightAge` 计时及 Niagara `User.FlightAge` 输入。发射后前 60 ms 将外焰平滑收至后方，随后不再有悬浮状态的向上位移。
- 后方外焰被限制在约 22 cm 的包络中，不直接拿较长的悬浮粒子年龄乘飞行速度，避免老粒子在发射瞬间跳到远处。
- `NS_FireballVelocityTrail` 继续沿真实飞行线段在世界空间生成，保留之前的向后速度规则。主体局部 +X 继续由实际弹道速度确定。
- 仍沿用现有单机组件和 Actor 生命周期，新增计时不是网络同步接口。

## 可编辑源与交付

- 作者脚本：`Tools/Skills/build_fireball_slow_burn.py`；完整重建入口 `build_fireball_assets.py` 已追加调用。
- 来源图结构：`SourceAssets/FireballSlowBurn20260914/material-source.json`。它是制作所需的源材质读取记录，不是实机验收。
- 制作参数及本地素材来源：`SourceAssets/FireballSlowBurn20260914/authoring.json`。
- 沿用本地已取得的 Epic Niagara Examples 素材及其依赖、许可；不新增原始素材再分发授权。
- 原生构建日志：`Saved/Fireball-Slow-Burn-Build-20260914.log`，模块后缀 `914113500`，构建成功。
- 资产制作日志：`Saved/Fireball-Slow-Burn-Assets-20260914.log`。
- 三个材质资产及 Niagara 系统已保存，系统编译 `valid=1`，Python 制作脚本执行成功。命令行退出码 1 来自工程原有 `GameFeatureData` 资产管理器配置错误；日志还记录了并行怪物工作中的 Pus 材质缺失。本次未改动这些无关内容。
- 作者脚本使用引擎返回的材质输入名称，适配本机中文输入端口；Niagara CPU 平滑插值使用展开的三次多项式，避免 VectorVM 不支持 `smoothstep` 内置调用。材质像素着色器仍可使用该内置函数。

按用户规则，未运行游戏、自动测试、截图或渲染。实际轮廓、亮度和动态观感交由用户测试。
