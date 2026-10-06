# M4 快速近战节奏调整 · 2026-10-06

用户反馈 M4 快速近战过慢，本次仅调整 M4 枪托砸击的播放和事件计时。

## 排查结论

- 当前 Base、Drum、Angled、Vertical、Canted、Prism 六份实际动画长度均为 0.9 秒，RateScale 均为 1；未发现这六份动画被意外设置低速。
- 读取时 `/Game/Weapons/AnimationProfiles20261001/ue_m4a1/DA_*` 六个配置均不存在，当前走 `M4QuickMeleeReplica20260919` 的原分支；运行入口仍支持已有的共用姿态配置。
- 原入口使用 1 倍速，以完整 0.9 秒作为近战动作占用时间。接触在 5/27 处，即约 0.167 秒，其后跟随与回收约 0.733 秒。
- 此结论来自当前资产元数据与运行加载/计时代码，未启动游戏测量实际手感。

## 改动

在 `AFPSGAMECharacter::TriggerRifleStockMelee` 中按 `A_M4_QuickCombat_` 动作家族选择 1.5 倍速，避免用其他枪械也共用的 `bUsingM4Infima` 标志扩大调整范围。

| 时间 | 原设置 | 新设置 |
| --- | ---: | ---: |
| 动作及占用总长 | 0.900 秒 | 0.600 秒 |
| 接触 | 0.167 秒 | 0.111 秒 |
| 跟随段结束 | 0.267 秒 | 0.178 秒 |
| 展示位置开始回归 | 0.540 秒 | 0.360 秒 |
| 动作权重开始交接 | 0.702 秒 | 0.468 秒 |

动画采样保留原时间轴；近战组件接收 `源长度 / 播放倍率`，武器状态和动作混合使用同一播放时长。技能占用条、接触音效和下次动作解锁由原组件沿缩短后的计时驱动。保留六种作者握姿、原伤害/距离/消耗与命中反馈参数。原序列和姿态差量资产未改动，无需重制 Profile。

## 制作记录

- 源码：`Source/FPSGAME/FPSGAMECharacter.cpp`。
- 只读排查与原始回执：`Tools/Weapons/M4QuickMeleeTiming20261006/read_timing.py`、`timing_before.json`。
- 必要后台构建入口：同目录 `build_native.ps1`；构建成功与否以 `native-build-receipt.json` 及对应日志为准。
- 用户保存并关闭编辑器后，后台 `FPSGAMEEditor Win64 Development` 与 `FPSGAME Win64 Development` 均构建成功（退出码 0）。基础 Editor DLL 和 `Binaries/Win64/FPSGAME.exe` 已落盘；未重新启动编辑器。
- 首次构建由 `BoundCongregate.h` 的三处 UFUNCTION 参数 `Mesh` 遮蔽 `ACharacter::Mesh` 而中断；仅将这三处声明的参数名改为 `SourceMesh`，继续构建。
- 后续必要构建修正：`BoundCongregate.cpp` 复制宏要求参数名 `OutLifetimeProps`，伤害参数改名 `EventInstigator` 避免成员遮蔽；`BoundCongregateAuthoring.cpp` 的 `TObjectPtr` 数组循环改用 `const auto&`；`ColdSteelIconResources.cpp` 的 Super90 头文件使用正确的上级相对路径。均为编译兼容修正。
- 同次日志里的 `RuneSwordAzureDragon.cpp` 接口不一致来自其他在途修改；其文件随后已更新，本任务未覆盖该实现。
- 未启动游戏或执行回归测试，动作手感由用户测试。
