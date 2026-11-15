# 丘陵动物与联机补齐：整理和发布

本批保存 2026-11-15 两轮动物/丘陵联机工作的源码增量、诊断工具、最终回执和可复用技能；没有重新运行游戏或画面验收。

## 公开运行树与接入材料

- `FPSGAMEGameMode.h/.cpp` 的安全出生重试、`MonsterCorpseRagdollComponent.h/.cpp` 的客户端表现显式开关，已按干净公开基线定向接入；保留本机共享文件中的其它改动。
- `Integration/01-animal-audit`、`02-closure` 按顺序记录普通动物状态快照、尸体碰撞、休眠时钟、野狼死亡/连续受击、NullRHI 地图准备及地图标记编译修正。`integration-manifest.json` 列出目标和前后散列；不得对未知前置强行套用，也不要把整份本机宿主覆盖到公共源码。
- 动物基础实现及部分丘陵/库存/门/天气消费者尚未完整进入公开运行树。其增量依赖本机前置；这些补丁的发布不等于公共检出已完整集成或通过构建。
- `Sources/Source/FPSGAME/Development` 保存两套本轮新增的显式启用检查器。恢复相应本机前置后，复制到相同工程相对路径再构建；没有直接加入缺少动物前置的公开编译目标。
- 两个入口在 `Tools/Wildlife/run_wire_audit.ps1`、`run_hills_closure.ps1`。新的 `build_hills_audit.ps1` 保留构建入口，可重建已归档的测试输出目录。只在用户要求相应检查时执行；先完成源码接入与构建，不能复制旧 DLL 代替。

## 最终证据

- `Evidence/initial`：鹿、野猪和乌鸦，双方各 24 项，真实 UDP；该轮没有完整背包/重连/换图路径。
- `Evidence/closure`：42 个流程检查点，包含野狼、生产背包竞争拾取、强制结束客机后同档重连、8 个房间的逐视图计算、门 RPC/胶囊通行及丘陵—主神空间往返。主机和重连客机正常退出。
- 运行采用 NullRHI、60 ms 延迟和 2% 丢包；无最终渲染和音频验收。野狼使用服务端伤害刺激，不是玩家武器输入命中测试。该轮构建为完整本机源码构建，不是本次公开索引构建。
- 两份完整说明：[对话审查](../../WorldGeneration/conversation-audit-20261115.md)、[联机补齐](../../WorldGeneration/hills-multiplayer-closure-20261115.md)。

## 归档和保留

`cleanup-manifest.json` 逐文件记录原路径、trash 路径、大小、SHA-256、原因和保留替代物，`cleanup-receipt.json` 记录移动后的读回结果。

本轮两个 `Saved` 审查目录移入 `trash/HillsMultiplayer20261115/Saved/`：失败/中断尝试、重复隔离宿主与 DLL、临时 UBA 缓存、陈旧对象文件、原始日志及修改前快照均可按清单取回。它们不公开提交；最终小型 JSON 另保留于 `Evidence`。旧报告中的 `Saved/...` 是历史运行路径，当前原始材料位于上述 trash 映射。

首次 PowerShell 整目录移动意外沿测试宿主的 Content 联接移动了 360 个正式资产，命令报告首个错误后立即停止。全部 360 个资产已恢复到正式 Content，并逐文件核对 SHA-256 一致；没有覆盖不同版本的现存文件。恢复副本保留于 `trash/HillsMultiplayer20261115/RestoredAssetCopies`，详见 `asset-restore-receipt.json`。这是归档事故及恢复，不计为成功清理的 430 个文件。

后续按清单完成普通文件移动，再使用单路径文件系统重命名处理 18 个联接对象，并回读目标仍为原联接。正式资源已恢复；作者输入、项目当前 Binaries/Intermediate、玩家存档及其它任务材料未纳入归档。本轮没有新截图、GIF 或美术废案。

个人 SKILL 与工程镜像同步更新：动物动作快照、真实丘陵联机检查、流送出生和逐视图室内适应；并在现有存储联接参考中补充此类归档的具体方法和部分失败恢复规则。技能只记录可复用方法；历史通过记录不授权后续自动测试。
