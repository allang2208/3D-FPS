# 大羊排收枪时的手电补查与修复

用户追问枪械手电是否同步排查。本轮沿实际设备创建、进食状态、照明与恢复路径读取源码，发现本地已有覆盖，远端手电尚有遗漏。

| 路径 | 排查结果与处理 |
| --- | --- |
| 本地主手：M870、Super90、RSH12、HK416、PitViper2011、G18、LMG201、SVD、PKM、A762、M16、ASH12、DanWesson715、M1911、QBZ191、AKM、M4 | `SetGunsmithTactical` 共用 `UTacticalDeviceComponent`；已有双手进食提前返回，`HideEffects()` 同时隐藏镭射与手电。 |
| 本地支持的第二战术槽 | 同一 `ConfigureSlot` 创建的设备，走相同隐藏路径。 |
| 本地副手手枪 | `PistolDualWieldComponent` 创建同类设备，双手进食时也受组件入口判断控制。 |
| 本地 F6 第三人称 | 原设备切换世界装备发射位置，仍先经过本地双手进食判断。 |
| 远端 M870、Super90 手电 | `ConfigureWorld` 创建照明组件；手电在 `ResolveLaserSample` 前返回，远端也没有执行本地 `PotionUse`，因此收枪、抬枪阶段可能漏出照明。本轮补齐。 |
| 远端其他枪械 | 当前装备重建只为普通／祝福镭射创建世界设备；远端手电创建限定 M870、Super90，本轮未扩展装备功能。 |

修复在 `FPSPlayerBodyComponent` 提供只读布尔接口 `ConsumableStowsTacticalEffects()`，复用原有“大羊排 Consume 状态”判断。世界设备在进入手电发光分支前调用该接口，原远端镭射采样也复用它，避免两个分支遗漏或复制整个身体状态。

此处理覆盖已同步的大羊排收枪、进食、抬回过程；只暂时隐藏照明，不改装配配置或开关。结束／取消后，随着同步 Consume 状态退出，仍由原设备可见性与启用状态决定是否恢复。

修改文件：

- `Source/FPSGAME/Weapons/TacticalDeviceComponent.cpp`
- `Source/FPSGAME/Characters/FPSPlayerBodyComponent.h`
- `Source/FPSGAME/Characters/FPSPlayerBodyLaser.cpp`

原文件快照与构建记录保存到 `SourceAssets/ConsumableFlashlightStow20261017/`。没有资产修改、导入或存档迁移；未启动 UE、游戏、PIE 或执行测试，由用户实机确认。

正式构建已完成：Game `Build-20261017-194827-Game` 成功，114 个构建步骤，331.85 秒；等待已有后台任务释放模块后，Editor `Build-20261017-195523-Editor` 返回 `Target is up to date`、`Succeeded`，7.88 秒，当前源码已在共享工程的正式 Editor 产物中。汇总回执为同目录 `delivery.json`。
