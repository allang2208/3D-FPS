# 玩家方向闪避

用户指定左 Shift 点按触发，最新参数为持续 0.3 秒、水平移动 3 米，并在闪避过程中无敌。经用户选择，按住左 Shift 仍然奔跑；短按不超过 0.2 秒后松开触发闪避。原按住奔跑的按下响应保留，长按后松开不触发闪避；动作期间的额外点按不排队、不延长无敌。

## 行为

- 触发瞬间读取当前移动输入，按镜头水平朝向换算 WASD／组合方向；没有移动输入时沿镜头水平朝向。方向归一化，因此斜向仍为 300 cm。方向在本次闪避期间锁定，允许自由观察。
- 位移进度为 `p(t) = 2t - t²`，前快后慢。0.3 秒内计划水平位移 300 cm，起步速度 2000 cm/s，平均 1000 cm/s；结束时清除闪避的水平余速，由普通输入重新接管。
- Root Motion Source 将每个时间区间的曲线位移换成速度，交由原 CharacterMovement 执行胶囊 Sweep、墙面滑动、斜坡和 40 cm 跨阶。遇阻后不瞬移到目标，也不追赶丢失的路程。3 米是无阻挡情况下的计划水平距离。
- 地面与空中均可水平闪避，保留原重力和竖直速度。动作中不启动跳跃、滑铲或攀爬；闪避不打断独立的武器换弹。后续已接入体力消耗与闪避技能成长，见 [体力与闪避技能](UI/stamina-dodge-plan-20260913.md)。3 米为成长前基础距离，持续时间保持 0.3 秒，无额外冷却。
- 第一人称加入轻微下沉、横向侧倾和持枪回收，沿现有镜头／持枪计算叠加，不替换手臂骨骼动画或枪械姿势资产。

## 无敌与生命周期

`AFPSGAMECharacter::TakeDamage` 在原点伤害／范围伤害／通用伤害事件前拒绝闪避中的伤害；健康组件提供同一闪避状态的 `IsInvulnerable` 查询，防止扣血和受伤反馈。新增中毒、恐惧也在各自施加入口遵循这一状态。已有中毒和恐惧不清除，状态时钟照常运行；已有毒伤恰好落在闪避窗口时不扣血。

闪避状态归移动组件所有，源位移完成后回收。传送、销毁、禁用移动或控制器禁止移动时撤销闪避，并恢复正常可受伤状态；无敌查询同时限制在动作的截止时间内。未启用玩家多人网络输入预测，入口沿用本项目单机范围。

## 接入和调节

- 玩家默认值：`DodgeDuration = 0.3`、`DodgeDistance = 300`（UE 厘米）、`DodgeTapMaximumHold = 0.2`，位于玩家蓝图默认值的 `FPS Movement | Dodge`。
- 角色接口：`TryDodge()`、`IsDodging()`；血量组件接口：`IsInvulnerable()`。
- 位移实现：`Movement/FPSDodgeRootMotionSource.*`、`Movement/FPSDodgeMovement.cpp`。
- 输入及表现：角色的 Sprint 按下／松开、镜头和视模更新，以及 `Movement/FPSPlayerDodge.cpp`。

## GitHub 参考

- [delgoodie/Zippy 移动组件](https://github.com/delgoodie/Zippy/blob/main/Source/Zippy/Private/ZippyCharacterMovementComponent.cpp)：参考闪避输入意图进入角色移动流程、与其他移动状态协调的组织方式。其 PerformDash 使用 Flying 和 Montage，本项目自行实现精确区间位移并保留原 Walking／Falling、重力和台阶，不复制其整套移动组件。
- [zSelimReborn/MovementExhibition](https://github.com/zSelimReborn/MovementExhibition)：作者展示按速度区分翻滚／后闪，以及空中 dash 的动作分支。仅作行为经验参考，本项目按用户指定的输入方向／无输入朝向规则实现。
- 实际位移接口依据本机 UE 5.8 的 `RootMotionSource.h/.cpp`，使用 Override、IgnoreZAccumulate 和部分末帧时间处理；未复制外部源码或导入外部模型、动作素材。

本次未运行测试、lint、回归、截图或实机验收。效果与参数交由用户测试；构建结果单独记录，不能替代实机确认。

必要的 FPSGAMEEditor Win64 Development 构建已完成（退出码 0，Result: Succeeded），使用模块后缀 `9132240`，日志为 `Saved/PlayerDodge-Build-20260913.log`。未关闭或重启已打开的编辑器；用户保存并重启编辑器后再测试新代码。

后续按用户要求将距离调整为 3 米、持续时间调整为 0.3 秒。此次必要构建使用模块后缀 `9132241`，因 `Weapons/M1911DevelopmentAudit.cpp` 访问私有 `GunsmithPanel`、`TObjectPtr` 类型推导等错误失败（退出码 1，OtherCompilationError），未生成本次参数调整的新模块。日志：`Saved/PlayerDodge-3m-Build-20260913.log`。未改动这些其他任务的文件，未运行测试。

用户关闭编辑器并要求检查、继续后，确认编辑器进程已退出，源码默认值为 300 cm、0.3 秒；上述 M1911 错误对应的代码已有后续修复。本轮使用 `Tools/Build/Build-Editor.ps1` 完成正常名称的完整 Editor 构建，成功生成 `Binaries/Win64/UnrealEditor-FPSGAME.dll`（退出码 0，Result: Succeeded）。日志：`Saved/BuildEditor/build-20260913-222810.log`。本轮未额外修改玩法源码，未启动编辑器或进行实机玩法测试；下次打开编辑器可加载本次构建。
