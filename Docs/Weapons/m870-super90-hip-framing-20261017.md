# M870 待机位置统一到 SUPER90

用户要求：M870 待机持枪过低，以 SUPER90 为位置标准。

原先两枪在 `RifleHipFraming::PresentationOffset()` 都使用 `(6, 0, 0)` cm，且共用 M4 的枪轴与右手腕目标。M870 原生待机中机匣与右手腕的相对位置不同，因此只统一腕位仍会把枪体放得更低。

制作使用当前已保存的压缩待机动画 0 秒、组件缩放 1：

- M4 标尺：`/Game/Weapons/M4ContactImpactFinal/A_AKM_idle`
- SUPER90 参考：`/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_idle`
- M870：`/Game/Weapons/M870/Tactical20261015/Animations/A_M870_idle`

按现有枪轴解算，把 M870 的后照门位置对齐到 SUPER90。相机空间 X 向前、Y 向右、Z 向上，单位厘米：

| 项目 | X | Y | Z |
| --- | ---: | ---: | ---: |
| SUPER90 后照门目标 | 19.859521 | 11.182938 | -6.721911 |
| M870 原后照门位置 | 27.760031 | 9.502520 | -16.219920 |
| M870 整体位置增量 | -7.900510 | 1.680418 | 9.498009 |
| M870 新展示偏移（含原 X=6） | -1.900510 | 1.680418 | 9.498009 |

新偏移只在已有初始化解算中应用一次，握把切换继续按原有 profile 重算，未增加逐帧骨骼采样。枪体、双臂与附属件整体移动，骨骼、手指接触、动画资产保持现状。ADS 目标仍由独立瞄点标定，沿现有权重从新腰射位置过渡；后坐力、散布与联机数值未修改。SUPER90 的偏移保持 `(6, 0, 0)`。

制作输入、计算脚本、计算记录和原源码备份在 `SourceAssets/M870HipFraming20261017/`。构建状态另见该目录交付记录。此处数值为制作计算，未启动游戏、截图或进行视觉验收，由用户测试最终构图。

常规编译时遇到既有服装模块的 C2039：UE 5.8 的 JSON 对象键是 `TSharedString<TCHAR>`，没有 `IsNumeric()`。在 `FPSModularOutfitComponent.cpp` 中将该次调用改为 `FString(*Entry.Key).IsNumeric()`，保留原有槽号判断及材质读取行为，用于解除本轮构建阻塞。修改前文件与首轮失败日志已保存在同一制作目录。

2026-10-17 15:25 的共享常规 `FPSGAMEEditor Win64 Development` 构建已覆盖上述源码；15:25:55 的构建回执为 `Target is up to date`、`Result: Succeeded`，基础 `UnrealEditor-FPSGAME.dll` 已更新。保留该次成功日志和源码／对象文件／DLL 信息到 `editor_build_success.log` 与 `build_receipt.json`，并结束本任务尚未启动编译的重复等待进程。没有依赖热编译补丁，没有启动游戏或进行视觉测试。
