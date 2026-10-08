# 缚群 V8：衣物表面、挥鞭节奏与触手接地

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

用户反馈：衣物材质与细节不足，挥鞭停顿偏长，平时触手僵直且会进入地面。

## 本次制作

- 保留 V7 修正后的衣物权重、4 mm 非等厚补偿壳层和隐藏布料代理。长衣上部仅沿平滑法线向外填补凹陷，最大 6.5 cm；不重新收紧到身体鼓包，也不移动袖口或改绑供体骨骼。
- ClothTravel 的 R 保留物理移动范围；G 记录距真实边界的距离，B 记录下摆污损范围。新材料使用旧织物纹理，以低对比度、弱织纹法线和高粗糙度表现旧布；增加边缘磨损、断续缝线、下摆污色。两侧袖料、衬里和束带使用不同旧布色。
- 原生与蓝图同时设置：蓄力 0.62 s、释放 0.135 s、收势 0.48 s。取消蓄力末尾原有 22% 保持段与收势开头 6% 等待段，保留物理解算的后拉—前甩动作和非线性释放曲线。2 s CD 仍从起手计算；缠住目标时依旧完成拖拽再进入下一次攻击。
- 被动触手加入步态相位驱动的传递波，行走幅度按速度渐变；保留加减速与转向惯性，低速时衰减为轻微摆动。使用现有动画代理，没有新增 Actor Tick。
- 游戏线程采样触手下方及攻击目标附近的可行走地面；普通移动 15 Hz、攻击 30 Hz。工作线程只消费接触面缓存。接触抬升沿相邻骨段分散，保持段长，应用于被动姿态和最终攻击姿态；攻击缓存保存修正后的姿态，收势不会跳回穿地位置。

## 文件与接入

- 源：`SourceAssets/BoundCongregateMeshy20261006/ClothMotionV8/BoundCongregate_ClothV8.blend`。
- FBX：同目录 `SK_BoundCongregate_ClothV8.fbx`。
- 制作脚本：`Tools/BoundCongregate/author_cloth_motion_v8.py`、`materials_cloth_v8.py`。
- 后台构建与落盘：`Tools/BoundCongregate/finish_cloth_motion_v8.ps1`。
- 导入脚本：`Tools/BoundCongregate/import_cloth_motion_v8.py`；保存 V8 活体、布料、材料、匹配软体尸体，最后更新原有 `BP_BoundCongregate`。
- Editor/Game Development 已完成必要构建；后台导入完成并保存活体、材料、布料、尸体及原有蓝图，`delivery.json` 的 `saved` 为 `true`。未启动 UE 界面、游戏、测试或验收渲染；材质、布料接触和触手实际表现交用户测试。

地面避让针对采样到的可行走表面，不等同于完整触手墙面碰撞或自碰撞模拟。
