# 木工工作台入口与实景交互调整

日期：2026-10-09。代码实现、资产保存、离线验证、原生构建和实际体验分别记录。

## 现在的入口

`E 交互木工台 → 项目选择面板 → 明确确认项目 → 异步准备台面资源 → 实景准备 → 启动加工 → 结果`

- 选择阶段保持原相机，显示现有项目、轮廓预览、规则和练习说明；不创建加工 Actor，不启动锯片/倒计时，不进行物品交易。
- 确认有效选项后才创建实景 Actor；重复确认被状态门控拒绝。资源准备可取消；相机只在资源就绪和工作台仍有效时进入。
- 保留木工原有的单独“启动加工”：进入实景仍是 Preview，点击后才调用原 `WoodworkingSystem::Start`。没有把耗时或收费提前到选择阶段。
- “返回项目”回到选择面板；“退出工作台”恢复普通交互。加工中或有未领取的正式结果时，离开需确认放弃，确认期间原计时继续。完成/失败后可返回项目重新选择。
- 不增加正式弓杖配方或产出；目录仍来自现有配置。练习无消耗、无产出，正式领取仍由现有事务执行。

## 对照的成熟流程

- `FPSGAMEPlayerController.cpp:491` → `ColdSteelForgingHUD.cpp::OpenForging` → `ColdSteelForgingWidget` 确认 → `StartWorldForging` → `ForgeInteraction::Enter`。结束回调可重新打开项目面板。
- `FPSGAMEPlayerController.cpp:499` → `ColdSteelWorkbenchHUD.cpp::OpenWorkbench` → `ColdSteelGunAssemblyWidget::HandleAction` → `StartGunAssembly` → `GunAssemblyInteraction::Enter`。结束回调可重新打开项目面板。
- 复用冷钢玻璃、卡片、字体和按钮。木工选择面板右侧停靠，滚动内容保留固定确认/退出区；实景中仅显示上下 HUD 条。

## 实景及生命周期

- `Building/WoodworkingWorldView.cpp`：相机跟随已放置 V4 台面；真实动态网格木板厚 1.2 cm，顶/底面和切口侧壁来自权威遮罩。轮廓与损伤标记使用同一目标数据。
- `Building/WoodworkingStockGeometry.cpp`：合并占用格为矩形，生成含孔洞/分离区的外向边壁。总显示预算 65,536 个四边形；一个异步作业，网格更新最多按 15 Hz 调度，刚体位姿每帧更新，无碰撞烹饪。
- `UI/WoodworkingEntryFlow.h`：独立的选择、准备、加工、关闭门控；不持有计时/经济逻辑。
- `UI/ColdSteelWoodworkingWidget.cpp:347` 为选择界面，`:612` 为确认入口，`:630` 为同步幂等结束会话，`:643` 为返回选择。`Configure` 与 `NativeConstruct` 已移除创建/切换实景相机的行为。
- `UI/ColdSteelWoodworkingController.cpp` 在移除 Widget 前清空当前面板归属并调用 `EndSession`；旧 Widget 延迟析构不会再关闭新开的共享子系统。相机恢复立即完成，避免快速重开遗留混合目标。
- 退出/返回释放鼠标捕获、木板 Actor、锯片电机和本轮声音。倒塌、工作台移除、距离超限及角色更换走同一退出路径。控制器仍只持有一对移动/视角输入锁。

## 资产与保护范围

新增 `/Game/Building/WoodworkingWorld20261009/M_WoodworkingStock` 与 `M_WoodworkingMarks`。先在隔离工程制作，确认项目路径不存在后安装；在已有项目编辑器经互斥桥从磁盘读取并核对材质图，不保存或修改既有包。

40 项受保护文件的 SHA-256 未变化，包含全部 29 份 V4 资产、原切割/计时/评分/经济代码、配置、面板数组别名修复及建造注册资产。修改前备份保留在本任务 `Before`，原实景改造前的备份仍在上一轮任务目录。

## 验证结果

- 状态门控 C++ 离线探针：重复确认、准备取消后的迟到回调、关闭后的迟到回调、返回选择、幂等关闭、旧新会话隔离、10,000 次重新打开循环通过。
- 53 项静态/保护检查通过，包括选择阶段不创建相机/不调用 Start/Claim、确认门控先于创建、资源就绪后切相机、同步关闭顺序。
- 最新木工界面再跑原数组别名回归：14 项全部通过；包括最初触发崩溃的 Num34/Max35、剩余容量和闭合轮廓情况。
- 几何探针已通过 65,536 种遮罩及 292 组旋转映射；本轮几何规划源文件与该通过版本哈希一致。
- 材质在独立于制作进程的现有项目编辑器读回通过；此操作没有启动游戏/PIE，没有保存地图。

- `FPSGAME`：Succeeded，UTC `2026-10-09T04:12:14.818522+00:00`，二进制 `357927936` 字节，SHA-256 `c53fcc787cb97981d11a5b751852e0712e328d53884288d824664c752c45dfa7`。日志 `C:\Users\allan\Documents\Codex\2026-10-04\task-2\woodworking_entry_20261009\FPSGAME-20261009-120321.log`。
  - 共享工作区此后更新了该二进制：当前 UTC `2026-10-09T04:19:29.846956+00:00`，`357934592` 字节，SHA-256 `9942b6896974ae46647c82c8ef6038b33f90adf44c3d3dd9a5167da7bb958f69`。保留历史构建凭据并单独记录当前版本，未重复发起构建。当前版本包含本轮全部三条入口标记，任务源码哈希未改变。
- `FPSGAMEEditor`：Succeeded，UTC `2026-10-09T04:14:54.0209721Z`，二进制 `25041920` 字节，SHA-256 `197d463c2aeb47e3bf433ffa7f236b5b69c0dff2fcf14c74b82fc23e66b21b87`。日志 `C:\Users\allan\Documents\Codex\2026-10-04\task-2\woodworking_entry_20261009\FPSGAMEEditor-20261009-122235.log`。

Game 的成功凭据来自 UBT 的 `Result: Succeeded` 和构建后新二进制时间/哈希。后处理记录曾因 `Get-FileHash` 不可用中止，现已使用独立读取补存；未持久化的原始退出码与构建前时间保留为 null，没有推测填值。记录驱动已改用 .NET 流式 SHA-256。

最终 Editor 复核构建退出码为 0、`Result: Succeeded`，报告 `Target is up to date`（0 个 action）。本任务排队期间已有新的 Editor DLL 落盘；最后一次无需再链接。额外确认当前两份二进制均比本任务全部源码新，记录其当前哈希，并以严格 UTF-16 字节匹配确认三条新的选择/取消准备/返回项目文案。Game 的构建后共享更新单独记载，不将旧哈希冒充当前版本。字符串核对只证明新代码已进入产物，不证明运行行为或视觉效果。

## 尚未进行的运行验收与限制

未启动游戏/PIE、未截取运行截图、未写真实存档、未关闭现有编辑器，未提交或推送 Git。离线状态/静态检查不等同于 UE 中鼠标、焦点与窗口切换实测。

实际相机取景、不同分辨率的 HUD 遮挡、台面道具间隙、拖动手感及关闭/重入仍待用户体验。切面是像素遮罩离散几何；脱落废料没有独立刚体物理。损伤红色区域是半透明位置标记，不是剩余木料。网格视觉会有异步生成延迟，计时与评分始终由原子系统判定。本轮不含正式打包/cook 验证。

证据目录：`Saved/WoodworkingEntry20261009`。制作、备份与构建工作目录：`C:/Users/allan/Documents/Codex/2026-10-04/task-2/woodworking_entry_20261009`。
