# 龙息首次释放无火焰：表现准备闭环

## 当前覆盖：真实绘制材质也要在后台准备（2026-10-15 实测）

用户随后明确要求重新进入游戏、检查自动准备和首次火焰。本次独立游戏进程、真实 DX12/SM6 画面发现：原逻辑能结束“火焰准备中”，GPU 实例处于活动状态并正常扣蓝，但第一轮首次施法的四张截图没有火焰。另一个新进程在缓存已有的情况下显示了火焰。仅有 Niagara 实例／PSO 就绪不足以证明实际体积材质已可绘制。

修正保持 R6 资产和玩法不变：预热期间组件允许参与渲染，`User.Strength=0` 同时把发光、密度和温度消光归零，画面仍不可见；10% 燃料脉冲与清空阶段继续分帧执行。随后读取 **实际动态材质的静态排列资源**，非阻塞等待 ShaderMap 可用于渲染、编译结束、组件 PSO 结束且渲染代理已建立，才暂停并隐藏保留实例。不要读未使用的基材资源代替实际 MI/MID。尾焰清空后的再次准备也遵循此流程。没有全局着色器等待、同步 GPU 读回或新增进场门槛。

修正后两组完整 25 项已学技能测试已通过：普通首放（1 级）与提前输入（20 级）均在第一次实际释放中显示火焰，两轮输入锁定计数均为 0。龙息排到第 21 项，分别于测试启动后 79.691/80.262 秒自动就绪，输入早在 0.224/0.247 秒已放行；提前输入经过 0.957 秒准备后，原请求自动释放，未提前扣蓝。其余技能的模型准备在无界面独立进程中出现逐项超时，队列继续前进；上述约 80 秒是整条后台队列等待时间，不是加载遮罩时间。完整证据和最终构建结果见专项记录。

证据与限制：`Docs/Skills/dragon-first-cast-regression-20261015.md`。测试使用独立档案、实际正常游戏世界和屏幕外渲染，不是原来不推进完整世界的 DragonBreathReadinessAuditCommandlet；没有修改原玩家档案。

## 2026-10-15 修复“火焰准备中”持续不结束

R6 恢复厚实外观后，用户在正常游戏中反馈龙息一直显示“火焰准备中”。原日志 12:40:50（北京时间）记录后台龙息实例等待超过 10 秒，随后放行其他技能，但龙息没有进入隐藏模拟。

本地 UE 5.8 实现中，`HasOutstandingCompilationRequests(true)` 同时包含 `NeedsRequestCompile()`：资源只标记了待编译、尚未真正提交时也返回 true。原加载分支因此跳过 `RequestCompile(false)`，后续 `PollForCompilationComplete(false)` 又明确不提交待处理请求，形成一直等待未启动任务的循环。通用技能渲染准备也使用了同样写法。

- `FPSDragonBreath.cpp` 和 `PlayerSkillRenderPreparation.cpp` 改用 `PollForCompilationComplete(true)`：只在引擎仍有待提交请求时发起非强制编译，随后非阻塞轮询结果。这里的 true 是“提交待处理请求”，不是等待编译完成。
- 保留已学技能按序异步准备、进场不等待、超时继续后续技能；不增加同步加载、运行时等待或强制反复重编译。
- 当前编辑器中对已加载龙息补交一次非强制编译。日志 12:46:43 记录 `deferred_before=1 pending_before=1 pending_after=0 valid=1`，编译约 0.891 秒；随后隐藏模拟自动启动，12:46:44 记录 `background simulation ready ... age=0.255`。这是本次卡点和恢复准备链的直接证据。
- R6 的热源、厚度、颜色及 Niagara/M/MI 资产不修改；施法资源、动作和伤害不修改。
- 当前会话接入与构建记录位于 `Saved/DragonPreparationStall20261015`。没有启动游戏、执行施法测试或额外验收；上述状态来自用户已运行的会话和必要修复操作，不代表画面验收。

接入结果：首次接入的 Live Coding 返回 `Result: Success / Live coding succeeded`；独立 Game 目标后台构建退出码 0。随后用户关闭编辑器并明确要求完成正式构建，`FPSGAMEEditor Win64 Development` 常规构建成功（退出码 0，96.24 秒），日志包含 `FPSDragonBreath.cpp`、`PlayerSkillRenderPreparation.cpp` 编译和 `UnrealEditor-FPSGAME.dll` 链接。主 Editor DLL 已更新，下次启动会使用包含此修复的正式模块，无需依赖上一会话的热补丁。日志 `Saved/DragonPreparationStall20261015/editor-formal-after-close.log`，文件时间与 SHA-256 回执 `editor-formal-delivery.json`。没有重新打开编辑器或启动游戏，冷启动后的自动准备及实际释放仍由用户试玩确认。

## 当前覆盖：实际分帧初始化并暂停驻留（2026-10-15，用户再次反馈后）

用户反馈进入游戏后仍将加载留到首次使用。既有 `Saved/Logs/FPSGAME.log` 在 03:30:32.918 UTC 记录 Niagara 编译，03:30:32.970 记录旧的 `visuals prepared in background`，证明后台资源入口已经执行，但旧日志不能证明 GPU 模拟准备完成。

进一步读取 UE 5.8 本地引擎实现：`UNiagaraComponent::DeactivateImmediate` 进入系统 Complete；`FNiagaraSystemInstance::Complete` 会调用 `DestroyDataInterfaceInstanceData` 并移除 GPU compute proxy，组件 OnSystemComplete 还销毁 render state。上一版激活后在首次模拟 Tick 前立即停用，把刚准备的内容又释放了。

本次实现覆盖下面的旧“立即停用并保留休眠实例”方案：

- 已学龙息的本地玩家进场/复活后自动准备，不依赖装备法杖、轮盘选中或按施法键。远端角色仅有真实施法状态时准备其表现，专用服务器继续跳过。
- 只对尚未就绪且没有现存编译任务的 Niagara 资源提交编译，避免每次重生/远端角色出现都重新请求共享系统编译。
- 创建组件后以玩家当前技能参数设置实际流体网格；显示强度为零、组件隐藏且暂时关闭可见性裁剪。先用 10% 源发射量分帧推进至少 0.25 秒，覆盖 GPU 燃料注入的首次 shader/PSO 路径；随后关闭源、ResetSystem 清空旧粒子和网格，再以零燃料推进至少 0.25 秒。不使用同步 AdvanceSimulation、等待线程或加载遮罩门槛。
- 仅在系统已出 PendingSpawn、数据接口初始化且模拟时间达标后 `SetPaused(true)`。保留 GPU 网格、数据接口和渲染代理，空闲时停止模拟。就绪判定同时要求真实活动实例/接口和已暂停的预备态，不能只看组件指针或资产句柄。
- 首次施法发布真实喷口和方向后解除暂停，不再 Reset/Activate 销毁或重置已准备的空网格；正常施法恢复原可见性裁剪。正在播放但意外失活时保留恢复激活逻辑。
- 尾焰结束以 `ResetSystem` 清空旧模拟，再通过同一后台阶段暂停保留；连续快速重放保留数据接口。死亡/EndPlay 仍销毁实例并清理句柄。
- 新日志区分 `background simulation started` 与 `background simulation ready ... age=... (paused, GPU resources retained)`；尚未运行本轮游戏验证，这些新日志为后续用户体验定位入口。

本次只修改现有 C++ 函数及 include，不新增反射字段、改变资产、龙息 R5 外观或伤害/消耗/动作规则。构建及当前编辑器接入结果见下方追加记录。

### 本轮最终构建与交付

- `FPSGAMEEditor Win64 Development`：Succeeded，13.67 秒，正式 `UnrealEditor-FPSGAME.dll` 已更新。记录 `Saved/DragonBackgroundSimulation20261015/editor-final-build.log`。
- `FPSGAME Win64 Development`：Succeeded，19.53 秒，正式 `FPSGAME.exe` 已更新。记录 `Saved/DragonBackgroundSimulation20261015/game-final-build.log`。
- 最终版本包含远端尾焰清空后完成后台暂停的路径，避免远端空网格一直模拟。所有角色的死亡/离场仍使用原销毁流程。
- 本任务没有打开/关闭编辑器或启动游戏；在编辑器退出、共享构建及资产进程结束后完成后台正式构建，未使用 Live Coding。没有运行本轮游戏、性能采样或测试，首次施法观感由用户确认。

## 上一轮方案（已被当前覆盖）

用户反馈每次进入后第一次释放没有火焰。读取本次既有游戏日志：02:31:33.627 后台队列已记录 `completed 12/16 dragonBreath`，02:32:53.662 才记录 `NS_DragonVolume` 编译完成（0.208690 秒）。包加载完成并不等于 Niagara 编译、渲染管线和首次实例初始化已经完成。

## 本次实现

- `LoadDragonBreath()` 仍为异步资源请求；专用服务器跳过表现加载。编辑器收到资源后主动请求 Niagara 非强制编译，交由已有组件 Tick 非阻塞轮询。
- `PrepareDragonBreathVisuals()` 创建一个隐藏、发射量为零的 Niagara 组件，预缓存渲染管线；可激活后在首个模拟 Tick 之前立即停用，保留同一休眠实例。`DragonLoad` 在此准备阶段完成后释放，system/component 由原有 UPROPERTY 持有。
- 初始休眠实例以 `DragonVisualCastId=0` 表示尚未进入真实施法，不创建尾焰、伤害或播放声音。使用与实际喷吐相同的网格尺寸、画质和坐标参数配置函数。
- 早到的本地输入进入已有动作队列，显示“火焰准备中”；表现准备完成才启动手势、扣蓝和冷却。开菜单、切出法杖、死亡等继续按原队列取消规则处理。
- 实际施法复用预建组件。尾焰结束后停用并隐藏，保留一个休眠实例；死亡、EndPlay 的 ClearEffects 销毁它。复活/清理后缺组件时重新走准备路径。
- 正在喷吐时，如果组件因编译/重新初始化而失去激活状态，在就绪后重新激活；不再用“组件指针存在”代替“正在播放”。异步完成只重放最新复制状态，不保存旧施法快照到回调。
- 服务端非本地玩家的权威释放不依赖宿主视觉准备；专用服务器无须 Niagara 即可结算。没有新增 RPC 或复制字段，也未改龙息玩法公式、射程与喷口限幅。
- 全局进入/背景队列保持用户要求：世界准备好即可进入，不等待本技能的表现编译。

## 制作与构建

本次同时完成用户追加的 R5 颜色/喷流形态制作。Niagara 与 M/MI 三个资产已后台保存，见 `SourceAssets/DragonBreath20261013/VolumeV8R5_20261015/delivery.json`。

- Editor：`Saved/DragonBreathVolumeV8R5_20261015/editor-build.log`，`Result: Succeeded`，28.62 秒，正式 DLL 已落盘。
- Game：`Saved/DragonBreathVolumeV8R5_20261015/game-build.log`，`Result: Succeeded`，5.61 秒，当前源码目标已最新（前一轮正式构建已编译相关 cpp）。
- 未主动开启/关闭编辑器，未启动游戏、模拟、视觉渲染、冷启动回归或联机测试。日志是修复前问题定位证据；编译成功不代表本轮画面与首次施法已通过实机验收。
