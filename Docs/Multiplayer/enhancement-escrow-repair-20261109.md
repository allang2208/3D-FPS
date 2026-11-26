# 工作台暂存联机修复与回归入口

## 本轮修复

- 网络物品消毒先把当前摆放尺寸转回未旋转坐标，再和目录及实例 JSON 比较，最后恢复摆放方向。旋转 M1911 的 2×3 不再被未旋转目录 3×2 扩成 3×3。保留斧、反曲刀的固定占格迁移。
- 联机 Confirm 只等待或使用 OnNetworkResult 的表现结果。监听主机同步回执已经播放后，不再重复刷新和启动仪式。此改动不涉及扣费逻辑。
- 旧强化验收已迁移到实际 EnhancementItem 暂存合同，不再把 Items 中直接加工或旧预览工作室当作当前行为。旧截图预览入口明确拒绝，不输出伪通过。

## 后台权威与持久化回归

入口：Tools/UI/run_enhancement_acceptance.ps1。

使用独立 EnhancementEscrowAudit 档案，两次进程分别写入与重载。覆盖旋转装备放入、替换、取回、陈旧请求、重复报价、保存失败回滚、满背包拒绝、网络序列化、初次主机消毒、已有影子防旧上传覆盖、客机操作不动主机，以及各方向消毒幂等。

此入口直接调用权威处理函数，不是 UDP、鼠标或视觉验收。JSON 中明确标注 udp_or_multiplayer_runtime=false、visuals_tested=false。

## 真实 UDP 回归

入口：Tools/UI/run_enhancement_escrow_wire.ps1。脚本不构建，必须先完成统一 Editor 构建。

在隔离 Entry 地图用实际登记的工作台 Actor、正式 StationReach 和共享事务处理，客户端走 RequestInventoryAction、正式档案分块上传和回执。阶段覆盖初次主机旋转暂存取回、放入、旧替换拒绝、有效替换、取回、再次放入、强化、旧强化重放拒绝、满包取回及替换拒绝、保存后退出与同一档案新进程重连。每阶段核对客户端状态、权威状态、持久化暂存身份与版本，检查主机档案未被修改。

满包场景是明确的双端测试种子，不是假装客户端物品修改已经获得服务端授权。再次恢复空间后保存、退出，然后才建立第二个客机进程。最多同时运行主机与一个客机。

同一连接另发送种植快照序号 1→2→1→3→2，调用正式 ApplyNetworkState，并检查 StateSerial 仅随更新快照推进。这只覆盖快照传输和接收顺序，不覆盖种植/收获事务 RPC、争抢或种植故障恢复。

输出包括主客各自日志与 JSON、启动参数和 PID、同档重连记录及退出码。所有运行使用 NullRHI；不证明 UI 拖放、仪式画面、其他玩家可见效果、互联网或打包专服。

## 当前状态

源码与脚本已落盘。PowerShell 语法检查与相关差异空白检查已通过。统一构建和运行回执尚待执行，不能把编写完成的用例称为已通过。最终结果以对应 Saved/EnhancementEscrowAudit 和 Saved/EnhancementEscrowWire 本轮报告为准。

## 2026-11-10 恢复执行记录

- 确认原 authority-run1 目录为空且无遗留测试进程，再执行隔离存档测试。
- authority-resume-20261110-095400 首轮因夹具清空 QuickBindings 但保留新 QuickBarVersion 被正式校验拒绝，后续失败为级联，不作为业务缺陷结论。
- authority-diagnostic-20261110-0958 明确诊断为“快捷栏绑定无效，保留原存档”。已修复 authority 和 UDP 两套夹具为当前版本、合法数量的空快捷栏；种子保存失败立即停止，避免级联误报。
- 修复夹具的两个 CPP 编译通过，但最终 DLL 链接被新开的项目编辑器及 LeapStrikeAudit 占用阻断。未关闭非本测试进程。尚未重新运行修正后的 authority 与 UDP，不宣称通过。
- 诊断编译成功日志：Saved/BuildEditor/escrow-regression-resume-20261110-095722.log；夹具修正后的链接阻断日志：Saved/BuildEditor/escrow-fixture-20261110.log。
- 下一步：项目编辑器及其他 commandlet 退出后完成链接，再运行两阶段 authority 和真实 UDP（包括种植快照乱序）脚本。NullRHI 不覆盖视觉、拖拽或金光效果；种植 UDP 只覆盖快照顺序，不覆盖种植/收获动作 RPC。
## 2026-11-10 第二次执行结果

- 用户关闭编辑器后核实无 UE/UBT 进程。构建检查成功，当前 DLL 已含合法快捷栏夹具。
- `Saved/EnhancementEscrowRepair20261109/authority-resume2`：write 33/33，reload 3/3，全通过；正式 Saved/SaveGames 前后散列差异 0。
- `Saved/EnhancementEscrowRepair20261109/wire-resume2`：真实 UDP 建连、角色上传成功，phase 0 取回请求返回通用失败，revision=0。未执行后续替换、强化、重连及种植快照顺序验证，不可宣称 UDP 通过。
- 在 WireAudit 的 ServerResult 增加测试诊断（shared 初始化、harvest model、runtime pawn、StationReach、escrow）。CPP 编译成功，DLL 链接再被 12:04:53 打开的项目编辑器占用；未关闭该编辑器。
- 需要保持项目编辑器关闭，链接后重跑测试，以诊断输出区分测试场景条件与真实业务缺陷。
## 最终结果：2026-11-10 12:41

### 修复与根因

- 真正的联机阻断位于 `Multiplayer/ColdSteelHarvestAuthority.cpp`：共享世界只保存采集字段，却把缺少角色属性和快捷栏的稀疏档案传入完整角色校验，`SharedHarvestModel` 创建失败，工作台共享事务入口直接拒绝。现为共享采集数据构造合法中性角色外壳，只复制采集字段，不拷贝房主物品，也不放宽访客校验。
- 测试夹具修正：合法空快捷栏；种子保存失败立即终止；保留角色初始化会自动补发的初始弓，避免重连额外本地弓占格而干扰工作台测试。此前重连失败时服务器已完成取回，客户端回执因本地新增弓与返回手枪重叠被安全拒绝；没有重复执行成功交易。
- 保留审计专用诊断以帮助后续定位回执校验失败。`LeapMovementWireAudit.inl` 的两处并行编译错误最终由其他任务修正，本轮未改该文件。

### 已通过

- 构建：`Saved/BuildEditor/escrow-final-relink-20261110.log`，153/153 actions，Result Succeeded。
- Authority：`Saved/EnhancementEscrowRepair20261109/authority-resume2`，write 33/33，独立进程 reload 3/3。
- 真实 UDP：`Saved/EnhancementEscrowRepair20261109/wire-final7`，host 13/13，guest-first 与 guest-reconnect 均 passed=true。
- 覆盖旋转手枪取回、放入、过期替换拒绝、有效替换、再次取回/放入、强化扣费、重复强化拒绝、满包取回与替换保护、退出后新进程重连取回；检查客机/服务器状态、正式交易持久化、主人暂存未串档。重连最终 revision=7。
- 同一 UDP 连接的5个种植快照按 1→2→1→3→2 传递，全部按新旧序列正确接受/忽略。
- Authority 执行前后正式目录散列差异0。最终 UDP 前后5199个原有文件均未改变；目录只新增其他 `BowSkillAudit` 与 `LeapStrikeAudit` 的8个审计文件，记录见 `wire-final7/save-differences.json`，未删除或还原它们。

### 验收边界

- NullRHI：未验证面板布局、鼠标悬停/拖拽卡片、武器完整外观、金/蓝粒子和魔法阵亮起。
- UDP 为本机 listen-host + 一名客机再重连，无专用服务器、延迟/丢包压力和多客机并发验证。
- 种植 UDP 只覆盖快照传输顺序，不覆盖种植/收获动作RPC或联机故障恢复。强化动作已测，附魔卷轴动作未单独加入此轮矩阵。
- 本轮测试进程已退出，已释放编辑器，不再启动构建或测试。