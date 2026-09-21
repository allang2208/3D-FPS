# 环绕飞剑：连发与命中

针对 `RuneOrbBladesComponent` / `RuneOrbBladeProjectile`，案例见项目 `Docs/Weapons/rune-orbit-blade-burst-20260921.md`。

- 短时间多发请求用受剩余弹数约束的计数队列；布尔排队会吞输入。首次接触帧发射后，调用共享手势的 `ContinueSpellRelease` 延长停留，只叠加回震，不重置起势时钟。
- 自然发完和强制取消分开：前者保留最后一发后的停留与 recover，切武器、死亡、超时等才取消。每把投射物保存召唤时的属性，避免新一轮召唤改写已经飞出的剑。
- 回震叠加已有衰减脉冲，不把正在回震的位移突然归零。按当前 V9 姿态驱动完整左臂，不扭腕、不拉长小臂。腕臂原理见 [施法与完整骨段](../../ue5-fps-arms-animation/references/casting-arm-volume.md)。
- 弱点必须读完整命中信息；`bBlockingHit` 只说明发生阻挡，不代表命中要害。裁剪到剩余射程再扫碰撞，避免低帧率多飞一帧。
- 命中隐藏完整剑体并生成蓝色碎片。沿用冰锥的碎片运动时只换网格/材质；不要在 Tick 提前 return 后仍依赖该 Tick 执行消隐。
- 当前网格作者 `SourceAssets/RuneOrbBlade20260921/build_blade.py`，导入 `Tools/AssetPipeline/import_rune_orb_blade_v2.py`，运行路径 `/Game/Weapons/RuneOrbBlade20260921`。旧粗模源已归档；旧目录中的图标作者仍有效。造型和碎片未记为用户已验收。
