# 环绕飞剑：连发与命中

针对 `RuneOrbBladesComponent` / `RuneOrbBladeProjectile`，案例见项目 `Docs/Weapons/rune-orbit-blade-burst-20260921.md`。

- 短时间多发请求用受剩余弹数约束的计数队列；布尔排队会吞输入。首次接触帧发射后，调用共享手势的 `ContinueSpellRelease` 延长停留，只叠加回震，不重置起势时钟。
- 自然发完和强制取消分开：前者保留最后一发后的停留与 recover，切武器、死亡、超时等才取消。每把投射物保存召唤时的属性，避免新一轮召唤改写已经飞出的剑。
- 回震叠加已有衰减脉冲，不把正在回震的位移突然归零。按当前 V9 姿态驱动完整左臂，不扭腕、不拉长小臂。腕臂原理见 [施法与完整骨段](../../ue5-fps-arms-animation/references/casting-arm-volume.md)。
- 弱点必须读完整命中信息；`bBlockingHit` 只说明发生阻挡，不代表命中要害。裁剪到剩余射程再扫碰撞，避免低帧率多飞一帧。
- 命中帧隐藏完整剑体和飞行尾迹，再执行对应风格的消散。当前灵体剑使用随机蓝色爆炸 V4：爆心、不规则断续冲击弧、光晕三层主体，加 32～48 个粒子，共用一个 ISM、总实例数上限 51，持续 0.85～1.15 秒。每次命中一次性抽取尺寸、形状、旋转、扩张、喷散与消散参数，Tick 连续推进；不要每帧重新随机或恢复固定圆环。已有飞行点光源短暂闪亮。`bFinished` 分支须推进残留特效，不可提前停止更新。来源与落盘记录见 SourceAssets/RuneSpectralBlade20260927/BlueExplosionV4Random，伤害与判定范围未改；材质 Kind、Seed 经 VertexInterpolator 进入像素阶段。
- 2026-09-27 用户选择「幽蓝灵体剑」方向，当前作者 `SourceAssets/RuneSpectralBlade20260927/build_spectral_blade.py`，导入同目录 `import_spectral_blade.py`，运行路径 `/Game/Weapons/RuneSpectralBlade20260927`。使用 Substrate Unlit 真实透明度、局部 UV 流光符文、发射时短尾迹和蓝色命中粒子；后续反馈已加深剑体蓝色并提高不透明度。源与导入/构建状态见该目录 README 和 BlueImpactV2 回执；造型尚未由用户游戏验收。新增粒子网格须在退出 Play 后导入，空网格不能作为接入完成；资产保存和原生 DLL 编译分别记录。
- 快捷栏图标作者位于 `SourceAssets/RuneOrbBladePolish20260927`，运行图源为 `Skills/rune_orb_blades_cold_steel.png`。G 槽及分隔线与施放共用 `SwordEquipped()`，只看当前主手符文长剑，并排除生产工具；不要改回所有双手剑共用的 `URuneSwordComponent::IsEquipped()`。
- ISM 的形状类型与随机种子经 `PerInstanceCustomData → VertexInterpolator` 传入像素材质，兼容非 Nanite 栅格路径；只在命中时选种子，材质用连续时间推进，避免每帧跳变。先限制实例数和持续时间，再随机外形，保留可辨的蓝色爆心。
- 已加载且 rooted 的材质表达式优先原位更新，避免清空后重建触发编辑器断言。材质输出必须接 Substrate `FrontMaterial`；导入脚本成功保存与 DLL 已包含命中分支是两项独立交付状态。
