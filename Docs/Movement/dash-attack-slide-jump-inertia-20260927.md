# 冲刺攻击：滑铲跳后保留惯性

2026-09-27，按用户要求修改释放时的水平运动交接。

## 行为

- 空中释放冲刺攻击时，继承当时的水平速度与方向；同一帧刚触发滑铲跳、
  `LaunchCharacter` 尚未进入物理更新时，继承已排队的起跳速度。
- 沿用角色移动组件的胶囊碰撞、下落和落地。空中水平减速度为
  300 cm/s²，落地后为 1800 cm/s²，速度越高，停止所需的时间与距离越长。
- 惯性分支取消额外的一米前摇位移，避免继承速度与固定突进叠加。
  普通地面释放仍采用原一米前冲。
- 攻击原有移动输入锁定、动画、接触窗口、伤害、体力和修炼不变。
  接触期扇区跟随实际角色位置，防止人已向前而伤害区域留在原处。
- 攻击结束不会主动清零余速；无新移动输入时继续减速到停下。
  攻击结束后恢复的移动输入可接管运动。主动停止、传送、闪避、禁止
  移动的状态以及其他移动模式会退出惯性分支。
- 只接入现有单机动作合同，不新增复制状态、Tick、定时器或 Blueprint API。

## 实现

- `Weapons/RuneSwordDashAttack.cpp`：起跳速度捕获与交接、惯性分支禁止
  固定距离位移、接触扇区跟随实际位置。
- `Movement/FPSCharacterMovementComponent.h`、
  `Movement/FPSMeleeLungeMovement.cpp`：组件拥有瞬时惯性状态，物理更新
  内使用原生制动；不缓存并反复恢复碰撞前速度，不影响重力。
- `Movement/FPSCharacterMovementComponent.cpp`：传送清理状态。

## 构建与测试

三个修改的源文件已编译为隔离的对象文件，结果记录于
`Saved/DashAttackInertia20260927/compile-sources.json`，退出码均为 0。
用户关闭编辑器后，常规 `FPSGAMEEditor Win64 Development` 构建成功，
完成 32 项构建操作并链接正式 `UnrealEditor-FPSGAME.dll`，用时 28.53 秒。
日志：`Saved/DashAttackInertia20260927/build-editor.log`。
编辑器保持关闭；下次启动时加载新模块。
本次未启动游戏、预览、探针或回归测试，由用户测试运动手感。
