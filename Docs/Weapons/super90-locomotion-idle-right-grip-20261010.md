# Super90 移动右手统一到待机握姿

用户明确认可待机右手持枪，要求移动状态统一到待机。当前运行加载普通 `A_Super90_walk` / `A_Super90_run`，在独立移动通道中与 idle 混合；战术冲刺另有进入、循环与返回的动作所有权。

读取当前安装源后，walk / run 首帧右手相对枪身的旋转与 idle 相差约 10.25°，握点位移不足 0.2 mm，主要差异在握持朝向而非枪身位置。本次以实际安装 idle 第 0 帧为认可参考，将完整右侧锁骨、上臂、前臂、辅助骨、手掌和手指（26 条轨道）按枪身空间迁入 walk / run。这样保留原移动枪身起伏，又不单独掰腕或重新拟合手指。四种前握把分别使用自己的 idle 参考，重新制作移动右侧差量。

只修改两条基础移动序列的右链和四份 Profile 的 walk / run 右链条目。idle 资产及其差量不改；左手、武器和机械轨道、时长、移动混合、战术冲刺、R9 快速近战与 R24 快速拉栓保持。无 C++ 或网格改动。

制作源：`SourceAssets/Super90LocomotionIdleGrip20261010/`。`read_inputs.py` 读取当前资产，`author_motion.py` 生成右链补丁，`save_assets.py` 合并并保存实际运行资产；`inputs.json`、`animation_patch.json` 与 `Before/Content/` 保留来源及恢复资料。默认和四种握把的 walk / run 共十套可编辑动作位于 `Super90_Locomotion_IdleGrip_Editable.blend`。

六份游戏资产已通过现有编辑器桥保存，`save_receipt.json` 为 completed=true；日志 `import-bridge-f1ec541cd1b240289dfd289174a6d318.txt` 返回 `SUPER90_LOCOMOTION_IDLE_GRIP_SAVED 6`。没有运行游戏、截图、渲染或追加测试，统一握姿后的实际效果由用户体验。
