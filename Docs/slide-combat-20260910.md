# 滑铲战斗与角色 Tick 优化

滑铲中允许腰射、ADS、换弹。移动状态与武器动作分别维护；换弹仍禁止射击并退出 ADS，结束后恢复按住的瞄准输入。进入滑铲立即退出冲刺状态，沿用已有冲刺抬枪延迟；滑铲退出不再重置射击节拍。未改动画资产、换弹时长、弹药结算或存档结构。

原代码在 AimPressed、RefreshMovementState、FinishWeaponAction、ServiceHeldFire 和 FireShot 分别以 bIsSliding 屏蔽武器操作，StartSlide 还强制退出 ADS。ReloadPressed 原本允许滑铲中换弹。本次解除这些开火/瞄准屏蔽，同时保留武器忙碌状态与冲刺限制。

角色 Tick 原先每帧解析 InfiniteAmmoAudit、DrumGripAudit、AKMIntegrationAudit、WeaponHandlingAudit、MuzzleMigrationAudit 五个命令行开关；现在 BeginPlay 读取一次，实例成员保存到角色销毁。没有新增 Blueprint 接口或网络同步；沿用当前单人角色流程。此项为减少重复工作，未做 FPS 或 CPU 帧时前后基准。

## 验证

- Editor Development 编译成功，唯一模块后缀 6917。60 Hz 游戏日志确认加载 `UnrealEditor-FPSGAME-6917.dll`。
- 独立渲染游戏，通过 PlayerController 的模拟键盘/鼠标输入运行；使用独立 ColdSteelProfile，未操作玩家正式存档。
- 60 Hz：`Saved/GunplayUpgrade/slide-combat-60-v1/assertions.log`，14 PASS、0 FAIL、完成标记。截图同目录，已检查滑铲 ADS 与换弹画面。
- 30 Hz：`Saved/GunplayUpgrade/slide-combat-30-v1/result.json`，14 PASS、0 FAIL、完成标记、退出码 0。
- 检查腰射、ADS 射击、滑铲中发起换弹、换弹阻止按住的开火/瞄准、换弹完成恢复 ADS、换弹中进入滑铲不重置时钟、滑铲跳跃保留换弹，以及相机/网格变换有限。
- 这是固定模拟步长的行为验证，不是实际帧率基准。没有重新验证所有武器/配件、斜坡或低顶空间，也没有完整动态音画录制。
- 日志另有 GameFeatureData 配置和 StateTreeToolset Python 初始化错误；本次角色行为验收完成，不将其归为已修复。
- 用户原有编辑器未关闭或重启，新的独立测试进程已加载新模块；原有编辑器是否重新加载未验证。

复跑：在工程根目录运行 `Tools/AssetPipeline/run_slide_combat_acceptance.ps1 -Fps 60 -CaptureFrames`。脚本使用唯一输出目录/测试存档，超时只结束自己创建的测试进程。

共享角色源码改动前字节保存于 `Saved/SlideCombat20260910/Before`，用于区分并行编辑；该目录不作为待发布源文件。新增验收实现 `Source/FPSGAME/SlideCombatAudit.cpp` 仅在显式 `-SlideCombatAudit` 时运行。
