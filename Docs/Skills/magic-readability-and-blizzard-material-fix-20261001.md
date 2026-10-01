# 电矛可读性与暴风雪凝聚材质修复

用户要求加粗、增强电矛光柱，将充能准星改为枪械十字线，改善看不到的杖前魔法阵，并排查凝聚暴风雪云团的棋盘格。只调整这两项技能的表现与对应说明，沿用伤害、贯穿、击退、充能时间、随机散射和释放交互。

电矛保留三层柱体／四个加速环、共七个无碰撞组件。光柱直径从 96／45.6／21.6 cm 加倍为 192／91.2／43.2 cm；外辉光／中层／白热芯的发光倍率为 9／14／24，透明覆盖为 .22／.62／1。生成后在原 Hold 时段保持亮度，再在原 Fade 时段线性淡出，不再从第一帧平方衰减。加速环同步扩大、提亮；加法材质只在 Opacity 应用形状和消散，避免重复削薄覆盖与亮度。表现尺寸不改变伤害判定半宽。

充能准星使用与枪械相同的四向直线结构，内端对应 `LanceCrosshairExtent` 的实际散射投影半径，长度随充能收短；100%只显示中心点。沿用充能颜色及现有“已充能完毕”提示，细暗描边帮助在明亮场景辨认。不再绘制圆周，未满充仍均匀随机取圆盘方向。

魔法阵由 54 cm 扩到 64 cm，杖尖前移距离从 12 cm 调到 24 cm，加粗双环／符文，发光倍率从 2.4 改到 14，起始覆盖由 .36 改到 .8。形状仅应用一次，避免加法混合的二次削弱。组件加入角色实例列表并挂在相机上；每帧仍使用同帧法杖起点更新世界变换，以相机右方向固定平面朝向。原版为细弱线条；本轮未运行画面复现，不能将这些可读性调整当成可见性验收。

乌云棋盘格有明确日志原因：`Saved/Logs/FPSGAME.log` 的 2026-10-01 11:55:52 UTC 记录 `M_BlizzardGatherCloud` 和实例在 PCD3D_SM6 编译失败，DepthFade 读深度与 Output Velocity 写深度互斥，随后使用 Default Material。关闭这份专用凝聚材质的 `output_translucent_velocity`，保留 DepthFade、软边遮罩、Responsive AA、原生云纹理与已有局部空间／自然翻卷。区域风暴材质及 Niagara 不重建。

定向保存入口 `Tools/Skills/refine_magic_readability_20261001.py` 只保存 Column／Coil／Circle 和凝聚乌云母材质／实例这五份资产。全量与局部恢复作者同步修改，避免下次制作恢复冲突设置。日志与保存回执位于 `Saved/MagicReadability20261001`。没有启动游戏、PIE、截图、渲染或进行运行验收，观感由用户测试。

五份正式材质已经通过现有编辑器的互斥桥实际保存，执行结果 `asset-bridge-01.txt` 为 success=True，`asset-authoring.json` 记录乌云 Output Velocity=False／Responsive AA=True。原生 Game 构建 `build-game-01.log` 和普通 Editor 构建 `build-editor-01.log` 均为 Result: Succeeded、退出码0。用户保存并关闭编辑器后完成普通 DLL 落盘；没有重新打开编辑器。源码、五份材质、Game 程序和普通 Editor DLL 均已落盘，未实机测试。
