# 感染矿工：矿镐从身体外侧回转

2026-09-13。用户指出上一版的问题实际是矿镐穿过身体后才完成转向。本次替换攻击路径，待机、移动、人物模型、手指抓握、材质与放大 25% 的矿镐沿用现有资产。

## 修改原因与动作

`NaturalWrist` 从 `DragGround` 保留了错误的工具方向变化：起势第 3–7 帧把镐头从身后翻到身前再翻回，收势约第 43 帧又指向身体内侧。单独约束手腕折角无法修复这条运动路径。

本次以完整矿镐的连续回转为制作依据：侧后方拖镐 → 外侧抬臂及前臂翻转 → 上方前挥砸地 → 抬起镐头并沿外侧下弧收回。工具俯仰采用连续展开角度及三次曲线，不直接对远隔的起止方向做最短弧插值。前臂翻转单独编排在镐头处于身体外侧/后方的阶段，镐柄朝向不会随之横扫躯干。

左臂按该路径和既有骨长重建，举镐时保持握持点的外侧余量，为镐柄尾端避开头肩；手腕沿用现有放松抓握。上臂从当前锁骨参考姿态求方向，避免继承旧错误动作的轴向翻转。起止姿态回到现有拖镐 Idle。

保留原躯干、腿部、前倾及放松右臂，攻击时长仍为 54/30 秒；伤害窗口 22/30–25/30 秒、原生状态混合 0.16 秒不变。此版本包含本地重制的持镐手臂与工具轨迹，不称为未修改的现成动捕。

## 交付与接入

- 本机可编辑源、攻击 FBX、制作参数：`SourceAssets/InfectedMiner20260913/OuterSwing/Delivery/`。
- UE 攻击：`/Game/Monsters/InfectedMiner/OuterSwing20260913/A_Miner_OuterSwing_Attack`。
- 原 `BP_InfectedMiner` 仅替换 Attack；Idle/Walk 继续使用 `NaturalWrist20260913`，模型继续使用 `DragGround20260913`。
- Blender 制作入口 `Tools/InfectedMiner/author_outer_swing.py`；UE 导入入口 `Tools/InfectedMiner/import_outer_swing.py`。不需要修改或构建原生代码。
- 延续用户的预览请求：`render_default_preview.py -- --outer-swing` 与 `package_default_preview.py --outer-swing` 输出双视角 GIF/MP4，位于 `OuterSwing/Previews/`。

导入完成日志 `Saved/InfectedMiner/import-outer-swing-final.log`。首次启动遇到 AutoFootstep 热重载模块冲突；并行构建更新模块后，使用正常插件配置完成导入。预览是离线 Blender 模型画面；本次没有运行游戏、战斗或回归测试，也未添加运行时地形/障碍物 IK。由用户在原村庄刷怪点测试。原始商店资源及派生二进制只保留本机，Git 发布制作脚本、说明与参数。
