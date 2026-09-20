# 斧头命中后的右肘与肩臂支撑

用户反馈：命中目标后，右小臂、上臂的肘关节衔接不自然，上臂方向有扭曲。

读取的正式动作源为 `SourceAssets/AxeHitPause20260919/Axe_HitPause_Editable.blend`，包含已修正拇指的 Swing 和命中后停住 0.20 秒的 HitRecover。没有重跑旧 V5 的整套动作生成，避免覆盖后续的停顿与手型修改。

## 调整

- 旧抽回阶段右肘曾抬到接近手腕高度，随后快速落下。改用肩—肘—腕弯曲平面定义肘关节方向，右肘优先向下、向身体右侧支撑，限制偏离此方向的角度。
- 肩带配合前送约 2.5 cm，向右约 0.5 cm，向下约 0.4 cm。两骨求解沿原骨长运行，不缩放上、下臂。
- 上臂围绕自身轴额外分担的旋转限制为 18°。前臂从肘的方向起步，剩余旋前按该 Manny 蒙皮的实际站点分布；不再靠大幅旋转上臂追随手腕。
- Swing 在运行时 0.34–0.46 秒平滑进入新右臂支撑，0.48 秒接触姿态与 HitRecover 首帧共用。命中后前 0.20 秒保持这个完整姿态，之后沿现有晃动、抽出节奏运行；回收末段交还当前待机。
- 固定工具、双手、手指和左臂的世界姿态，重建右手相对新父骨的局部变换。保持原握点、右拇指修正、斧刃轨迹、接触时刻和单次镜头重冲击。

## 文件与接入

- 作者脚本：`SourceAssets/AxeRightArm20260919/author_right_arm.py`。
- 可编辑源：同目录 `Axe_RightArm_Editable.blend`；300 Hz 的 Swing 和 HitRecover 在 `Export/`。
- 参数与制作记录：同目录 `authoring.json`；原动作输入记录在 `source_pose.json`。
- 正式导入仍使用 `Tools/Production/import_axe_two_hand_attack.py`。整套动作导入及单独回收导入入口同步指向新源，避免以后恢复旧右臂。
- 本轮只更新两个动画资产，不更换网格、材质、库存、伤害或采集判定。

Swing 与 HitRecover 已导入并保存到正式动画资产；记录在 `SourceAssets/AxeRightArm20260919/import_receipt.json` 和 `Saved/Logs/AxeRightArmImport20260919.log`。此次动画修改不需要新增 C++ 构建；同时完成了上一轮矿镐所需的正式构建与导入。

没有运行实机测试、截图或预览渲染；姿态效果由用户测试。
