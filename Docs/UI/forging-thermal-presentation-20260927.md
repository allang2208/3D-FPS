# 打铁炽热金属与接触特效

用户要求隐藏锻造中的铸造台 E 提示，改善截图中粉红色剑胚和大块暗斑，并增加落锤火星、薄烟及类似近战空间扰动的热感。本次只修改锻造局部表现及该交互提示的显示条件。

## 实现

- `UpdateInteractHint` 在 `IsWorldForging()` 时跳过世界交互查询并收起浮窗，准备、击打和淬火期间均覆盖；正常退出后回到原显示条件。
- 剑胚材质用模型局部厘米坐标生成细碎氧化皮、锻打凹凸、金属粗糙度变化及橙红温差，替换依赖不均匀 UV 的大块圆斑。薄边与柄部较暗；命中位置短暂变亮、氧化覆盖减弱；沿现有 Heat 参数淬火冷却。没有改变全局曝光或光照设置。
- `ForgeHeatPresentation.cpp` 由现有锻造 Tick 与接触时钟驱动，不新增第二条击打时钟。44 个固定实例包含亮火星与较宽、较暗的氧化碎片；按速度形成短拖尾，重力下落、在砧面范围内一次衰减弹跳，随后收缩消失。锤头实际接触剑胚才触发，包括敲到剑胚但未命中计分圈的情况。
- 18 个固定薄烟实例复用 `T_MuzzleSmokeMantaflowV14` 的 8×8 密度图集及现有 `RollingSmoke.hlsl` 双帧插值；每 0.16 秒最多发射一个，打击后短暂加浓，淬火约 1.08–1.8 秒使用 0.065 秒间隔的水汽。离开剑胚的烟保持铸造台空间运动，不随剑胚一起移入冷却桶。材质使用 R 密度、透明边界和深度淡化。
- 一个局部热浪面片复用近战折射法线 `T_NoiseNormal_A`，采用轻微 IOR 扰动与明确的零边界遮罩，不生成蓝色斩击轮廓或全屏滤镜。温度降低时停止显示。
- 一盏无阴影局部点光，85 cm 衰减半径，用于剑胚与击打闪光对手、砧面的暖色反馈。所有组件由本次锻造 Actor 持有和释放，资源在 Prepare 阶段异步预加载。装饰随机流独立，不消耗计分逻辑的随机序列。

## 文件与资产

- 运行：`Building/ForgeInteraction.h/.cpp`、`Building/ForgeHeatPresentation.cpp`、`UI/ColdSteelHUDWidget.cpp`。
- 重建入口：`Tools/Forging/forge_materials.py`、`update_forge_materials.py`；原始导入器 `import_forge.py` 同步创建热效材质。
- 原创 HLSL：`SourceAssets/ForgeHeat20260927/SteelSurface.hlsl`、`SteelIncandescence.hlsl`、`HeatVeil.hlsl`。
- 已保存材质：`/Game/Props/ForgeInteraction20260927/M_ForgeHotSteel`、`M_ForgeScaleSpark`、`M_ForgeFume`、`M_ForgeHeatVeil`。
- 材质保存回执：`Saved/forge-thermal-materials-20260927.txt` 和 `SourceAssets/ForgeHeat20260927/materials-*.json`。使用当前工程已有的烟雾图集、折射法线及 Engine Plane，不修改共享图集与近战武器。

后续光圈调整：每处仍随机持续 2.2–3.2 秒，剩余寿命同时控制显示半径与命中半径，从原始大小线性缩至零。出锤时锁定当时的大小直到接触判定，避免锤子飞行时间额外压缩操作窗口；接触后沿用原有随机间隔及回锤等待。实景光圈、面板光圈和操作提示已同步修改。

常规 `FPSGAMEEditor Win64 Development` 构建已成功，基础 DLL 已落盘；回执 `Saved/forge-shrinking-target-build-20260927.txt`。未启动游戏、截图、渲染、自动测试或性能采集；数量为实现预算，观感和实际开销由用户测试。
