# M870 第三人称瞄准与联机表现发布 · 2026-10-18

本轮发布 M870 抵肩／瞄线标定、射后泵动支撑手和激光归零，以及复查发现的持续泵动同步、装备快照乱序和服务端静止瞄准修复。双手锤、其他枪型接入、施法、天气、死亡动作等并行修改保留在工作区。

## 公开源码与恢复

生产修复直接进入八个原路径：`FPSBodyRifleStockContacts.h`、`FPSBodyRifleHold.cpp`、`FPSPlayerBodyComponent.h`、`FPSPlayerBodyMotion.cpp`、`FPSPlayerBodyNetwork.cpp`、`FPSPlayerBodyEquipment.cpp`、`FPSPlayerBodyActions.cpp` 和 `TacticalDeviceComponent.cpp`。共享文件从发布前 HEAD 构造，只重放本轮修改；工作区其他改动保持原样。

枪托生成器 `SourceAssets/ThirdPersonRifleShoulder20261006/read_stock_contacts.py` 同步支持本枪。`SourceAssets/M870ThirdPersonAim20261018/` 发布只读几何采样工具、初轮构建回执记录器、隔离检查与本地 UDP 检查入口；它们仅在用户明确要求相应操作时运行。`record_build.py` 只记录最初四个表现文件的构建覆盖，最终联机修复证据以本轮汇总为准。

完整 M870 模型、动画、第一人称手臂、身体骨架与配件依赖沿用 [2026-10-17 恢复说明](../M87020261017/README.md)。原素材、UE 包、密集姿态采样、网格数据、完整日志与构建产物留本机；当前发布没有新制或改写 UE 资产。UC 动作的再分发许可仍未确认，公开原创脚本不授予其原始或派生动画的再分发权。

### 检查夹具的接入边界

本轮两个新增检查实现和四个共享夹具接线差分保存在 [presentation-audits.patch](Integration/presentation-audits.patch)。目标是 `Source/FPSGAME/Weapons/` 下的 `M870ThirdPersonAudit.cpp`、`M870PresentationWireAudit.cpp`、`ShotgunAttachmentAuditCommandlet.h/.cpp` 和 `ShotgunWireAudit.h/.cpp`。

共享 Shotgun 夹具及 `SkillNetworkAuditCommandlet` 尚未作为完整框架公开，因此本补丁不直接加入主模块，也不能对干净检出盲套。先恢复已有合法本机框架、审计档案隔离和 friend 接口，再按 [前置散列](audit-prerequisites.json) 核对基线并应用；散列统一按 UTF-8 无 BOM、LF 行尾计算。前次 M870 快速近战夹具的恢复边界仍有效。补丁已在临时文本基线重放并逐文件核对目标散列，该操作不是 UE 编译或玩法测试。

## 本机归档

128 份文件，共 4,287,544 字节，已移动到 `trash/m870-third-person-retired-20261018/`，移动后逐文件 SHA-256 一致。其中 108 份是失败／中断输出和重复日志，20 份是完成发布检查后的临时源码基线、暂存候选和一次性准备工具；没有留下常驻源码副本。一个无输出的中断队列目录一并移动。原路径、归档路径、大小、原因和保留替代物见 [清单](retired-files.json)。

包括编辑器占用 DLL 的失败构建、首次枪托测试路径错误、六个失败／中断的联机尝试以及重复日志。失败证据仍可从 trash 取回。有效采样、当前作者工具、最终 `AfterWire/` 与 `Wire/20261018-094854/` 通过记录、Editor/Game 构建回执保留原位，没有移动生产 Content。

## 已有结果与本次发布检查

- 完整本机宿主的 Editor 和 Game Development 构建曾成功。
- 最后一次隔离回归为 29 项、0 失败；真实本地 UDP 首次连接与新客机接入共 12 个场景通过，两端实际设置各 60 ms 延迟、5% 丢包。
- 双端夹具使用固定源帧和受控瞄准输入。没有完成鼠标／CMC 压缩输入端到端、互联网、同一玩家的持久档案恢复或有画面的连续动作验收。
- 本次仅归档读回、SKILL 同步和 Git 发布检查，没有启动 UE、重跑构建、游戏或联机用例。历史完整宿主的构建不能作为本次精确发布子集的独立编译证据。

详细修复和结果见 [瞄准与激光](../../Weapons/m870-third-person-aim-laser-20261018.md)、[联机复查](../../Weapons/m870-third-person-network-review-20261018.md)；公开证据摘要见 [历史结果索引](evidence-summary.json)。完整回执仍在 `SourceAssets/M870ThirdPersonAim20261018/NetworkReview/`。

## 技能沉淀

个人技能与工程参考同步更新 [M870 泵动枪接入](../../../skills/ue5-weapon-workflow/references/m870-pump-integration.md) 和 [全身表现](../../../skills/ue5-cpp-gameplay/references/player-world-body.md)，复制技能增加对应入口。内容覆盖原生枪轴／单位、同帧支撑手、泵动 ADS 门控、服务端相机缓存陷阱、实例／布局匹配和真实联机证据边界。个人与工程入口保留各自既有版式，只同步新增路由段落。
