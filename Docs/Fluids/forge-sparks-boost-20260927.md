# 锻造落锤火星增强

在原有锤面接触事件中增强火星，保留判定光圈、锻造评分、动作、淬火及蒸汽时序。

- 单个锻造交互沿用一个无碰撞、无阴影 ISM 组件，对象池由 44 改为 72；每锤复用原实例，不追加组件。12 个氧化皮、24 条长火丝、36 个短亮点。
- 短亮点持续 0.28–0.55 秒，长火丝 0.60–0.95 秒，氧化皮 0.50–0.85 秒；飞散速度按层区分。保留重力、阻力及砧面范围内的一次衰减反弹。
- 火丝按速度拉长，上限 4.5 厘米再乘实例尺寸；宽度适度增加。专用材质从白黄色亮芯衰减为橙红余辉，火星峰值发光系数从 32 调到 55，氧化皮从 6 调到 8。
- 复用现有 85 厘米范围、无阴影的局部灯；落锤脉冲从 65 调为 95 流明，保留原指数衰减，不增加灯光或后处理。

源文件：`ForgeInteraction.cpp`、`ForgeHeatPresentation.cpp`、`Tools/Forging/forge_materials.py`。`update_forge_materials.py -ForgeSparksOnly`（UE commandlet 参数）只重建并保存 `M_ForgeScaleSpark`，全套重建也使用同一作者函数。

后台 commandlet 已完成火星材质保存，日志为 `Saved/forge-sparks-boost-material-20260927.log`。其后已打开的编辑器在 Live Coding 应用补丁、重建 UObject 时崩溃（UObjectHash.cpp:650）；没有将该次热编译视为成功，也未重开编辑器。

编辑器退出后已完成 `FPSGAMEEditor Win64 Development` 常规编译，`Result: Succeeded`，日志为 `Saved/BuildEditor/forge-sparks-boost-20260927.log`。未启动游戏、截图、自动测试或性能采样，实际观感由用户测试。
