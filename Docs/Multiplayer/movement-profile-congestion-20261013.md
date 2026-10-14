# 双人联机移动断流修复（2026-10-13）

用户现象：监听服主机看不到客机的移动，远端角色停在障碍物旁。场景为 `DayNight_Lighting` 双人 PIE。

## 排查证据

来自本次已有的 `Saved/Logs/FPSGAME.log`，时间为日志 UTC 时间：

- 2026-10-12 15:54:29.486：开始上传档案，532606 字节，521 个分片。
- 15:54:29.932：服务端移动看门狗报告 0.43 秒未收到移动。
- 15:54:32.252 起：客机反复报告 `CreateSavedMove: Hit limit of 96 saved moves`。
- 客机原本每帧发送两块 1 KB 的 reliable RPC，没有按照时间或连接带宽限制。UE `NetDriver.cpp::InternalProcessRemoteFunctionPrivate` 在连接拥塞时跳过非 reliable、非 multicast RPC；角色 `ServerMovePacked` 因而会受档案上传挤占。
- 服务端还限制 `TotalChunks <= 512`，因此日志中的 521 块档案全部被拒绝，客机却继续消耗带宽发送。
- 15:54:22.955：第二个玩家出生落脚对象是 `FPSGAMECharacter_0`，出生 Z=321.850；地面出生 Z=127.700。出生探测错误地接纳了另一名玩家头顶。

## 修改

- `ColdSteelProfileTransfer` 统一档案上行、私有镜像和篝火前置同步的 zlib 编解码；保留原档案字段、合并规则和磁盘 `.sav` 格式。网络信封携带版本标志与解压长度，压缩数据沿用 512 个 1 KB 分片上限，解压档案上限为 4 MB。
- 上传使用真实时间节流：连接带宽的 20%，且不超过 16 KB/s，按每片额外 256 字节预留协议开销；每次最多一片，拥塞时等待，不在卡顿恢复后追赶发送。
- 复用最后发送时间，无新增 Actor 成员布局；在途上传期间不再每两秒重复序列化同一份大档案。
- `FindSafeSpawn` 不接受 Pawn 作为落脚地面，继续尝试相邻候选位置；胶囊净空检测仍保留其他玩家的碰撞。

现有 `ColdSteelPlayer_A.sav` 的只读体积诊断：528747 字节，zlib 后 58539 字节。这是磁盘文件压缩体积，不是实测网络流量或运行验收。

## 生效边界

双方必须一起结束原联机会话并使用同一版代码后重进；新的压缩网络格式不与旧运行中实例混用。未更改存档结构、地图资产或障碍物碰撞。

已完成 Game 和 Editor 正式增量构建并链接落盘：

- Game：`Saved/MultiplayerMovementFix20261013/game-build-retry.log`，`Result: Succeeded`，输出 `Binaries/Win64/FPSGAME.exe`。
- Editor：`Saved/MultiplayerMovementFix20261013/editor-build.log`，`Result: Succeeded`，已链接 `UnrealEditor-FPSGAME.dll` 与 `UnrealEditor-ColdSteelNet.dll`。
- 首次 Game 构建遇到并行制作期间尚未出现的 `MagicOcclusion.h`；该文件随后落盘，增量重编译成功。本任务未修改那些技能文件。
- 运行中的 PIE 阻止了最初热补丁请求，未在联机途中改格式。用户结束会话、编辑器退出后，改为上述正式构建；没有启动或重启编辑器。

未进行双人运行复测或视觉验收，交由用户测试。

用户复测范围：重新开启相同双人 PIE，在客机行走、转向、跳跃并经过原障碍物，从主机观察位置更新；进入背包触发档案同步时也应继续正常移动。出生时第二人应在附近空地，而不是第一人头顶。
