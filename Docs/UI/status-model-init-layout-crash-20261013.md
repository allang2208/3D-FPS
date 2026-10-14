# 状态模型初始化访问异常：编译布局不一致

**最新状态（2026-10-13 11:10）：Editor 构建成功并落盘，原成员偏移不一致已消除。** FPSGAME 与 ColdSteelNet 两个 Editor DLL 均完成链接；原错误位置的两个目标文件偏移都为 0x5D68。下文失败记录为排障过程，不是当前交付状态。未打开 UE、未运行游戏或测试。

## 报告与范围

2026-10-13 10:36，进入 PIE 时在 UColdSteelStatusModel::LoadProductionDefinitions（ColdSteelProductionTools.cpp:25）发生 EXCEPTION_ACCESS_VIOLATION，读地址 0xffffffffffffffdc。调用来自 ColdSteelProfileRuntime.cpp:121 的 Initialize，尚未进入木工面板。

本次仅分析已有崩溃日志和目标文件，不启动编辑器、不运行游戏或测试。用户要求保留并行修改与存档。

## 已确认原因

用 MSVC dumpbin 读取现有 Editor 编译目标文件，发现同一个 Definitions 成员的访问偏移不一致：

| 编译单元 | 已有目标文件时间 | Definitions 偏移 |
| --- | --- | --- |
| ColdSteelProductionTools.cpp | 10:09:15 | this + 0x5CD0 |
| ColdSteelProfileRuntime.cpp | 10:26:01 | this + 0x5CE8 |

两者相差 24 字节。Initialize 加载基础物品表之后调用 LoadProductionDefinitions，后者对另一个内存位置执行 TMap::Add，触发容器访问异常。这不是通过空指针判断或跳过生产工具目录能够解决的问题。

证据位于 Saved/StatusModelInitCrash20261013：production-disasm.txt、profile-disasm.txt、before-evidence.json，以及 Before 下的两个原目标文件。崩溃目录为 Saved/Crashes/UECC-Windows-47AB169349869FCC7CFF15A1DADECEC0_0000。

## 归因边界

- 上一次木工卡片的 Lines.Add(Lines[0]) 是本对话引入的直接代码错误，已单独修复。
- 这次 LoadProductionDefinitions 的实现未在木工任务中修改。现场该文件相对 Git 基线只改过另一函数的按键提示，报错加载函数未变。
- 用户此次运行的 Editor DLL 生成于 10:33:46，晚于本对话上次交付记录中的 10:17:51；期间公共状态/档案结构有并行修改。
- 可以确认共享构建混入不同结构布局的目标文件，现有证据不能准确归到某一轮源码编辑或某一位修改者。链接成功本身不证明跨编译单元布局一致。

## 修复方式

使用项目已有 Tools/Build/Build-Editor.ps1 -RecompileGameplay：先备份旧 DLL/PDB，再使 FPSGAME 与 ColdSteelNet 的 Editor 生成目标文件失效，强制 UHT 并禁用 UBA 缓存，从当前源码完整重编两模块。不回滚源码、不修改玩法、不删除 Content 或存档。

重编完成后仅对报错的两个目标文件进行离线偏移比对，作为这次崩溃定位的收尾证据；不宣称实机测试通过。

## 重编证据与过程中阻塞

- 首轮使 711 个生成目标文件失效，原 DLL/PDB 备份在 Saved/BuildEditor/layout-recovery-20261013-103904；两模块实际构建动作使用 NoUba。
- 报错的两个目标文件重新生成后，Definitions 访问偏移均为 **0x5D68**，对应当前结构，已消除跨编译单元差异。反汇编记录：production-rebuilt-disasm.txt、profile-rebuilt-disasm.txt。
- 首轮构建期间新增了 Tasks/TaskTrackingSubsystem.h（10:40:39），部分文件因其 generated.h 尚未生成而编译失败。保留新增任务源码，后续以 NoUBTMakefiles、ForceHeaderGeneration、NoUBA 继续构建；没有为绕过错误删除该引用。
- 后续构建遇到的两个独立编译拼写问题已按最小范围修正并备份：ColdSteelDungeonTracker.cpp 的局部 Visibility 改为 ListVisibility，避免遮蔽 UWidget 成员；AuthoredDungeonGenerator.cpp 的复制属性输出参数改为 DOREPLIFETIME 宏要求的 OutLifetimeProps。玩法逻辑未改变。
- 同类复制宏参数名问题也出现在 SceneTestPortal.cpp 与 VoxelBuildPrefabActor.cpp，均只修正参数名并保留原逻辑。VoxelBuildNetwork.cpp 的不存在接口 FindMaterial 改为当前 UVoxelBuildPalette::Find。

## 本轮交付边界：未完成最终链接

已完成状态模型相关模块的源代码重编，原报错的两个编译单元访问偏移均为 0x5D68。最后一次 profile-final-disasm.txt 仍确认相同偏移。

**Editor-delivery.log 最终退出码 6，LNK2019/LNK1120。新的可运行 Editor DLL 尚未生成。** 现场并行联机改动已声明/调用但尚未实现三个函数：

- AColdSteelPlayerState::ExecuteWorldAction
- UDungeonRunSubsystem::FillNetworkState
- UDungeonRunSubsystem::ApplyNetworkState

这三个缺失实现与原始生产工具字典崩溃是不同问题；需要相应实现落盘后继续最后的构建。未增加空函数、未删除联机调用，也未恢复旧的已知存在布局错误的 DLL。原 DLL/PDB 仍在前述 layout-recovery 目录可恢复备查。

本轮没有打开 UE、没有运行测试；不能把目标文件偏移已一致描述为实机启动已通过。

## 用户要求继续后的接入

ExecuteWorldAction 已由现场并行实现补入 ColdSteelStationNetwork.cpp，复用该实现。新增 DungeonRunNetwork.cpp 补齐 FillNetworkState 与 ApplyNetworkState：服务端将当前 RunId、Cleared、Explored、bCompleted 填入既有快照；客户端只应用当前已绑定、RunId 一致的地牢状态，不经过有奖励/保存副作用的 MarkRoomCleared 或 CommitProfileRunState。未增加存档字段或另设客户端权威进度。

继续使用 NoUBTMakefiles、ForceHeaderGeneration、NoUBA 完成必要 Editor 构建，日志为 Editor-resume.log。

首次继续构建被 UHT 拒绝：ClientStationState 的两个 RPC 工件参数内含 PaidMaterials TMap。随后现场并行代码提供了不含物品/材料字典的 FColdSteelForgeNetState 与 FColdSteelAssemblyNetState，最终沿用这两个专用状态结构，接齐 RPC 声明、发送/接收和 ForgingSystem 的状态读取。只更新同一工件的命中、安装、校准和完成值；物品、实际支付材料、配方和分件配置仍由原库存回执维护。过程中的临时字节封装已移除，未另建传输方案，也未用空函数绕过错误。

## 最终落盘结果

- Editor-resume-03.log：FPSGAMEEditor Win64 Development，Result: Succeeded，退出码 0；本次构建禁用 UBA 缓存并强制生成反射代码。
- Binaries/Win64/UnrealEditor-FPSGAME.dll：2026-10-13 11:10:41；Plugins/ColdSteelNet/Binaries/Win64/UnrealEditor-ColdSteelNet.dll：11:10:40。
- 最终反汇编 production-delivered-disasm.txt 与 profile-delivered-disasm.txt：Definitions 均为 this + 0x5D68。对应目标文件生成于 11:07:00、11:07:04，均早于最终链接时间。
- 继续过程中另按编译器报错将 TemperateHillsStreaming.cpp 的 auto* Player 改为显式 APawn* Player，兼容 GetPawn 返回的 TObjectPtr。其余并行网络、任务、地牢与资源修改保留；DungeonRunNetwork.cpp 后续并行添加的 EnsurePlayerRun 也保留。
- 最新回执 Saved/StatusModelInitCrash20261013/delivery.json；前次未完成回执保留为 delivery-before-resume.json。
- 本轮交付为 Editor 模块和源码；没有重新构建 Game 目标，没有打开编辑器、运行游戏或自动测试。实际启动与交互仍由用户确认。
