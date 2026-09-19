# M4 弹鼓：斜甩、身后取鼓，保留 R5 装鼓姿态

最终回放：`drum_throw_r6f_normal.gif`、`drum_throw_r6f_empty.gif`。
最终运行记录：`runtime-drum_throw_r6f.log`。
`drum_throw_r6` 至 `drum_throw_r6e` 为调试候选，不作为交付回放。

## 用户纠正与最终边界

用户确认 R5 的装鼓方式正确。本次初稿错误地重算了装鼓阶段的肩、肘及蒙皮辅助骨，引入手臂扭曲，已撤销该做法。
最终版本从源动画正常换弹第 50 帧、空仓换弹第 43 帧起，直接保留 R5 左臂、手腕、手指和辅助骨在武器空间内的完整姿态；右臂全程复用 R5。整把枪的朝向/构图可以变化，装入时手、弹鼓、武器之间的动作关系保持原样。

参考已实际查看的普通弹匣游戏视频：`../Revision6/standard_reload_reference.jpg`，源视频在 `../../M4ContactImpact20260910/Delivery/M4_换弹与开火_实际录音_silent.mp4`。标准弹匣资产未修改。

## 最终动作

- 旧鼓先退出弹槽 6 cm，源帧 18/14 释放为独立物理物体；左向初速 180 cm/s、向前 65 cm/s、向下 110 cm/s，随后受重力影响。
- 左手保持护木抓握至源帧 20/16，然后沿身侧下摆、后探。源帧 36/31 在左后方取新鼓，新鼓此后与手掌共同移动。
- 取鼓时使用原有手臂姿态并整体绕肩摆动；仅在空手段连续展开腕部轴向角，消除原先跨过 ±180 度边界时辅助骨突然翻转的问题。
- 正常第 50 帧、空仓第 43 帧起，装入、松手、复位及空仓操作保留 R5。
- 大弹鼓持枪采用固定的额外 6 cm 镜头距离，持枪和换弹共用；换弹构图只向左 3 cm、向上 7 cm 调整。删除原先只在换弹期间增加约 14 cm 深度的做法。ADS、普通弹匣动画与弹药规则未改。

## 资产和源文件

- `M4_DrumThrow_Editable.blend`：可编辑源，保留 `BeforeThrow_reload` / `BeforeThrow_reload_empty` 原动作。
- `build_drop_reload.py`：从 `../Revision5/M4_DrumFlow_Editable.blend` 生成最终动作。
- `A_M4_DrumThrow_reload.fbx` / `A_M4_DrumThrow_reload_empty.fbx`：120 Hz 动画。
- 游戏资产：`/Game/Weapons/M4DrumDrop/Throw/A_M4_DrumThrow_reload` 及 `_reload_empty`。
- C++ 默认加载路径已改为上述资产。最终编译模块为 `UnrealEditor-FPSGAME-2026091097.dll`；已打开的编辑器需要重启才能加载新原生代码。
- `*.rejected_ik.py`、`configure_throw.py`、`restore_accepted_arm.py`、`finalize_builder.py` 等为过程记录，不应作为最终生成入口重新执行。

## 验证与限制

`throw_validation.json` 对装鼓阶段每半帧、每个左侧骨骼进行武器空间比较：旋转误差为 0 度，最大位置误差低于 0.0002 cm。并检查持枪接触、身后取鼓位置、携带新鼓的手掌关系与固定握把深度。

`check_twists.py` 检查全部手臂骨骼及辅助骨的 120 Hz 旋转步长，拒绝 45 度以上的单步跳变。`validation.json` 检查肘关节轴、骨长及手部与弹鼓体积交叠。这些数值不能替代动作观感验收。

`import_report.json` 确认正常/空仓源动画仍为 2.1/2.7 秒及 UE 压缩误差。导入 commandlet 存在项目既有的 GameFeatureData 设置错误，故总退出码为 1；本次两资产导入脚本标记 `DRUM_WRIST_IMPORT_PASS`，随后用真实渲染进程验证。

最终独立游戏进程 `drum_throw_r6f` 使用隔离存档、实际按 R 输入换弹，共捕获 184 帧；报告 `COMPLETE failures=0`。两次握把相对摄像机深度范围分别为 1.1990 cm / 1.6547 cm，保留轻微摆动，无原先的大幅前后平移。测试确认 50 发容量、备弹记账、每次仅一个旧鼓、独立落地和侧向甩出。

已查看正常/空仓实际画面和侧面模型渲染。旧鼓主要从画面下缘甩离；身后拿取发生在镜头外，没有新增第三人称弹鼓袋。HUD 会遮住部分低处的手部画面。最终动作观感仍以用户实机确认意见为准。
