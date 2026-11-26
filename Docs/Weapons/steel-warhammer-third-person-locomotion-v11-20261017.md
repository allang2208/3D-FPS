# 双手锤第三人称走跑 V11

2026-10-17。用户反馈 V10 持锤走路、跑步依然僵硬、机械。

## 原因与修正

V10 将站立持握循环作为持续上身覆盖，按独立的世界时间采样；`BlendSword` 又用该站立素材的胸部姿态覆盖移动中的胸部。腿部虽然在走跑，上身的重心传递、胸部反向转动和肩肘时序却被覆盖。同时普通持握还经过固定手部锚点、固定肘极的通用 IK，进一步消除了源动作的动态。这是上一版接入方案的不足。

V11 使用工程中现成的 Jason/Manny 双手持械移动素材，制作独立的战锤全身移动家族：普通站立 1 套、八方向走路 8 套、八方向跑步 8 套。保留源动作的根、骨盆、脊柱、腿部轨道及左右脚落地标记；按战锤实际双手握距适配手臂，并保留源动作中与步伐同步的肩肘变化。握持适配更强调保留肘部弯曲，并继续约束肩胸、柄尾、锤头空间。

新家族直接进入现有方向混合、走跑混合、速度和步频系统。完整家族加载后，普通持锤不再叠加独立站立上身循环，也不再被固定锚点的通用手臂 IK 覆盖。左右脚标记、源根位移用于现有步频匹配，实际位移继续由角色胶囊控制。

第一人称动作仍独立。第三人称不恢复转锤待机或检视；攻击、风车反向旋转和头部稳定逻辑保留。V10 的 Carry / SprintCarry 保留为缺少新家族时的回退，旧资产不覆盖、不删除。

## 路径与范围

- 配置：`Warhammer.Idle`、`Warhammer.Walk.{Fwd,Fwd_Right,Right,Bwd_Right,Bwd,Bwd_Left,Left,Fwd_Left}`、`Warhammer.Jog.{同八方向}`。
- 源码：`Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp`。
- 作者数据：`SourceAssets/WarhammerThirdPersonSevarog20261016/LocomotionV11/`。
- 制作入口：`prepare_locomotion_v11.py`、`LocomotionV11/author_locomotion.py`、`save_locomotion_v11.py`。
- 保存的新包：`/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/LocomotionV11/Animations/`。

17 个动画包已在后台保存，`LocomotionV11/assets-saved.json` 的 `complete=true`；保存 commandlet 于 10:29 完成、退出码 0。

首轮正式构建被运行中的 UE 占用阻止。编辑器退出后等待已有构建结束，再正式构建；`Saved/BuildEditor/build-20261017-103543.log` 返回退出码 6、`OtherCompilationError`。错误位于当前天气改造：`FPSWeatherManager.h` 内联访问未完整定义的 `UFPSUDSBridgeComponent`；`FPSUDSBridgeComponent.h/.cpp` 中的弱字段指针条件、类变量作用域和属性查询函数；`SurvivalClockAuditCommandlet.cpp` 对已删除时钟接口的调用。本轮没有改动这些并行文件。

新走跑配置尚未发布，当前游戏仍使用 V10 持握接入。编译阻塞解除后，重新执行正式 Editor 构建并将成功输出保存到 `LocomotionV11/build-editor.log`，随后运行 `LocomotionV11/publish.py` 即可切换；17 个动画包无需重做或重新导入。

未启动游戏、姿态渲染或运行测试，最终观感与穿模情况由用户体验。

## 14:52 后续状态

后续工程的正式 Editor 构建已包含 V11 播放逻辑，原构建阻塞已解除。用户继续指出待机侧倾后，V12 改用自然站立与徒手走跑源，重新居中躯干和肩线，并保存、发布完整家族。当前使用 `CenteredCarryV12` 的 18 个新资产及 19 项配置角色；V11 持械源资产未发布，不再按上面的待办执行 `LocomotionV11/publish.py`。实现与交付记录见 [居中持握 V12](steel-warhammer-third-person-centered-carry-v12-20261017.md)。
