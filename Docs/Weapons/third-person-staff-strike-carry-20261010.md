# 第三人称法杖攻击接续当前持杖手臂

用户要求普通攻击和快速近战沿用已调整的持杖手臂，避免动作开始后回到旧的贴身姿态。

## 普通攻击

- 基底为 `ThirdPersonStaffCarryClearance20261010` 当前原生持杖姿态；不再使用旧 KayKit 攻击的腕点和手掌补偿。
- 保留当前手腕局部姿态、指部抓握、骨长和辅助骨关系。以现有肘弯曲平面制作屈伸，由整个上臂调整杖轴方向；下段杖柄继续向身体右外侧展开。
- 起势、蓄势、接触、下压、回弹、收回使用连续非匀速曲线，首尾回到持杖基底。接触与释放标记分别为归一化时间 `0.60`、`0.70`，运行时仍读原攻击执行器的时钟、攻速与命中停顿。
- `NativeStaffArm` 标记启用完整右臂播放分支，沿用持杖的肩部/躯干朝向处理；左手和移动下肢保留各自所有权，后续旧腕部拟合不再覆盖攻击。

## 快速近战

左手出拳、持书推击和副手枪近战期间，第一人称法杖骨架仍可能发布右腕轨迹。第三人称现在忽略这一右腕动作覆盖，继续使用当前持杖整臂。对于使用全身动作库的左拳，在躯干混合后重新应用右侧支撑，避免再次通过保留腕点的 IK 把肘部和杖体拉回身体。

左手快速动作、既有持书姿态、第一人称动作、伤害及体力消耗逻辑未在本轮改写。

## 制作与接入

- 作者入口：`Tools/PlayerBody/author_staff_strike_carry20261010.py`
- 保存入口：`Tools/PlayerBody/save_staff_strike_carry20261010.py`
- 参数和完整骨架帧：`SourceAssets/ThirdPersonStaffStrikeCarry20261010/authored.json`
- 动画：`/Game/Characters/JasonPlayer20261003/StaffStrikeCarry20261010/Animations/J_StaffStrike_FromCarry`
- 配置：`Content/ColdSteelData/player_body.json` 的 `Staff.FullBody.Strike`。
- 播放分支：`FPSBodyStaffStrikePose.inl`、`FPSBodyStaffCarryPose.inl`、`FPSBodySwordPose.inl` 与 `FPSPlayerBodyAnimInstance.cpp`。

资产保存回执和构建日志放在上述制作目录。遵循用户规则，没有启动游戏、运行测试或渲染；后台保存/构建不代表视觉验收。
