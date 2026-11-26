# 双手锤第三人称持握与冲刺就绪奔跑 V10

2026-10-17，用户要求第三人称不播放待机转锤和检视，并优化冲刺攻击触发后的奔跑姿势、注意穿模。

## 表现调整

普通状态原先通过 `CaptureMotion` 的 `NativeMelee` 路径读取第一人称实时手腕、武器骨骼和配件变换。第三人称因此也跟随转锤、检视及第一人称的冲刺持锤。现在普通持握和检视使用独立的第三人称 Carry；手指、锤柄骨骼与配件统一读取静态装备握持，停止第一人称展示动作向世界模型传递。

冲刺攻击就绪后，通过已有复制字段 `ActionVariant=WarhammerSprintReady` 选择 SprintCarry。源为现有 Kwang 全身 Idle，按照 Jason 原骨长和战锤的静态双手握距适配。新姿势稍向前倾，双手相对普通持握向前、向上支撑；拟合时约束两肘位于胸廓外侧、肩线前方，并为前臂到肩关节、锤柄及锤头到胸部保留空间。制作没有采样第一人称的拖锤或跑步轨迹。

持握切换使用 0.30 秒过渡；启动攻击后的短举锤过渡为 0.12 秒。Carry、SprintCarry 与 SprintLift 的腿部继续使用移动步态，避免提前套用原地过顶重击的腿部。实际释放仍使用现有动作和命中时间。

保留 V8 的普通攻击、重击、上挑、快速近战，以及 V9 的第三人称风车反向旋转。头部稳定逻辑保留。第一人称的待机、检视、冲刺、伤害、体力和移动规则维持当前实现。

## 文件与资产

- `Source/FPSGAME/Characters/FPSBodyWarhammerMotion.h`：独立持握状态与素材选择。
- `FPSPlayerBodyActions.cpp`：发布冲刺攻击就绪的表现标识。
- `FPSPlayerBodyMotion.cpp`：隔离第一人称待机、检视和冲刺的手腕、机械骨骼与配件运动。
- `FPSPlayerBodyAnimInstance.cpp`：持握循环、过渡和腿部步态所有权。
- `SourceAssets/WarhammerThirdPersonSevarog20261016/CarrySprintV10/author_carry.py`：第三人称姿态作者数据。
- 新资产目标为 `CarrySprintV10/Animations/J_Hammer_Carry` 与 `J_Hammer_SprintCarry`，配置角色为 `Warhammer.FullBody.Carry`、`Warhammer.FullBody.SprintCarry`。

## 当前交付状态

源码和作者数据已落盘，正式 Editor 构建成功：`Saved/BuildEditor/build-20261017-091327.log`，结果 `Succeeded`。本批构建输出为 `CarrySprintV10/build-editor.log`。等待期间的共享构建曾报告冰甲模块错误；当前工作区对应代码已更新，本轮未修改冰甲源码，随后正常完成链接。

两个动画包已于 09:22 在后台成功保存，commandlet 退出码 0，`CarrySprintV10/assets-saved.json` 中 `complete=true`。已将两个新动作角色加入 `Content/ColdSteelData/player_body.json`，发布回执为 `CarrySprintV10/assets-published.json`。源码、正式构建、动画包和配置切换均已落盘。

此前初始化退出及桥接无可连接节点的尝试未写入资产；最终通过后台 commandlet 完成保存。未运行游戏、姿态渲染或自动测试，最终衣物间隙与奔跑观感由用户体验。
