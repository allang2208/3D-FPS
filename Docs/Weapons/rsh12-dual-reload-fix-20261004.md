# RSH 双持换弹反复起播

用户反馈：双持状态持续重播换弹，无法完成。

## 原因与修改

`UPistolDualWieldComponent::AdvanceReload` 在逐发空仓换弹和快速装填的退壳节点调用 `UColdSteelStatusModel::EjectDualPistolCases`。该事务只接受 `ue_dan_wesson715`，使 `ue_rsh12` 返回失败。控制器随后 `StopAction`，空仓且仍有备用弹药的自动换弹条件立即再次调用 `BeginReload`，形成重复播放。

在 `Source/FPSGAME/UI/ColdSteelDualPistolRuntime.cpp` 内统一 715/RSH 的左轮判断，用于退壳、逐发/快速装填后的弹壳数量和牛仔自动装填后的弹仓记录。保留每手实例匹配、主副手装备限制、已有事务提交、五发容量与共享弹药袋消耗。未改变动画、播放速度、阶段时点或自动换弹规则。

## 交付状态

源码已修复，并已进入 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。当前修复源码保存于本地时间 15:59:58，对应 Editor 对象文件编译于 16:07:28，基础 DLL 于 16:13:57 链接落盘。

本任务先前构建被工程内并行开发文件的错误阻塞；对 `HangingBellM09::BuildHitSurfacePhysics` 仅作参数 `Mesh` → `InMesh` 的改名，解决 UHT 与父类成员重名。其余并行源修改不由本任务回退或覆盖。后续共享 Editor 构建成功，直接复用其已包含本次修复的基础 DLL，未再重复全模块构建。

构建记录：`SourceAssets/RSH12DualReloadFix20261004/build_receipt.json`；成功链接日志：`SourceAssets/HangingBellM09Meshy20261003/HitSurfaceV23/Records/build_FPSGAMEEditor.log`。本任务未运行游戏测试、未主动打开编辑器。

上一轮两款紧凑瞄具的接入单独记录在 `SourceAssets/RSH12CompactOptics20261004/README.md`，与换弹循环原因无关。
