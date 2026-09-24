# 火球流体内核：首轮制作

用户选择先优化火球，待观感确认后再扩展到陨星和灼锋焰甲。2026-09-23 已完成原始模拟、贴图导出、UE 导入、当前材质修改与保存；没有运行游戏、截图、预览或视觉／性能验收。

## 本轮效果范围

保留现有 30×30 cm、持续存在的火球内核和原有凝聚缩放。用原创 Mantaflow 燃烧数据替代主要的内部热度变化来源，辅以原有火把噪声：橙红低温区、较热亮区和轻微烟密度暗部随流体动画变化。中心覆盖独立于烟密度，不用烟雾或 dissolve 把球核挖空。

沿用现有外焰、世界坐标飞行拖尾、命中爆燃和热浪。Niagara 发射器结构、粒子数量、额外灯光数、动作与输入、飞行轨迹、碰撞、伤害、技能成长及费用均没有修改。

## 制作产物

- 原始文件：`SourceAssets/FireballFluidCore20260923/FireballCombustion.blend`。
- 模拟缓存：同目录 `cache/data` 的 104 帧 OpenVDB，96³ 网格，24 fps、模拟时间倍率 0.8。
- 动画贴图：`T_FireballCombustionFields.png`，2048×2048，8×8 格，共 64 帧。跳过预热阶段，用额外的 8 帧平滑混合循环接缝；每格有 4 像素边缘留边。
- 通道：R 为沿视线积分的火焰强度，G 为火焰加权温度，B 为积分烟密度。全序列采用统一归一化参数，避免逐帧自动增益。
- UE 新资产：`/Game/Skills/Fireball/FluidCore20260923/T_FireballCombustionFields`。
- UE 当前修改材质：`/Game/Skills/Fireball/TorchBurn20260921/M_FireballCohesiveCore`，由现用 `/Game/Skills/Fireball/NS_FireballSlowBurnCore` 的持续球核使用。

材质以 18 fps 推进循环，混合相邻两帧，并按球体厚度弯曲采样坐标。保留现有曝光补偿、预乘透明、深度淡化与时域响应。纹理为线性 Masks 数据、双线性过滤、无 mipmap；2K 图集仅用于近景球核，不增加运行时体积求解、粒子或灯光。性能没有测量。

## 恢复与再制作

1. `Tools/Fluids/bake_fireball_core.py` 在 Blender 后台完成模拟及密度场投影；`--export-only` 复用已保存缓存。制作使用数值投影，不需要相机渲染。
2. `Tools/Fluids/apply_fireball_fluid_core.py` 导入贴图并增量修改当前球核材质。UE 已打开时通过 `Tools/AssetPipeline/mcp_call_codex.ps1` 批次互斥执行；不另起编辑器覆盖资产。
3. 原作者 `Tools/Skills/build_fireball_torch_burn.py` 的 `body_material()` 已接续流体内核安装函数，完整火球重建会保留本次升级。恢复时需保留本轮 HLSL、已导入贴图或原始 PNG。

修改前的材质位于源目录 `Before/M_FireballCohesiveCore.uasset`；`delivery.json` 记录路径和散列。`bake-manifest.json` 记录模拟和通道参数，`editor-authoring-output.txt` 记录两个资产保存成功与安装结束。

## 编译与验收边界

已有 UE 编辑器完成本次导入和材质保存，材质重编译 API 没有返回即时错误。着色器后台任务可能异步完成；没有运行额外的渲染或编译状态审计。不涉及 C++ 改动或原生 DLL 重建。实际观感与性能仍由用户测试。

新燃烧场为项目原创，原有火把材质依赖继续沿用原许可。[Blender FluidDomainSettings](https://docs.blender.org/api/main/bpy.types.FluidDomainSettings.html) 提供本次读取的火焰、密度和温度网格接口。
