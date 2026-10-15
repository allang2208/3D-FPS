# 战锤上挑 V3：待机握姿向右下退出与集中发力

用户要求蓄势退出镜头时保持待机持握方式，向右下退出，并进一步加快出手。V3 蓄势随后再次被否定，现按“左手高位柄尾留在画面内、右手下沉带锤头出镜”更新为 [V4](steel-warhammer-uppercut-rear-high-v4-20261015.md)。V3 的加速时钟继续保留；以下是本版历史制作记录。

## 动作与节奏

- 0–1.0 秒蓄势保留待机的锤柄朝向、双手握点和手指姿态，整体右移 21 cm、下移 27 cm。用缓入缓出的连续位移退出，不在蓄势中先翻柄。
- 肩带有限跟随，肘部采用原生骨长的两骨支撑，前臂沿既有蒙皮站点分配连续旋转；不缩放骨段或更换权重。
- 释放后用匹配端点速度、加速度的曲线接入原上挑正前方姿态。源时间 1.05 秒以后保留原向上带出、制动与回收；握姿在挥出中衔接原宽握，不在退出时先换握。
- 发力前半段从 75 ms 缩短到 55 ms，落脚后的后半段从 75 ms 缩短到 50 ms；实际出手起点由 1.205 秒变为 1.225 秒，挑击有效窗结束由 1.355 秒提前到 1.330 秒。
- 1.280 秒的正前方接触／落脚节点仍保留。时钟在各段边界连接速度，收势阶段接回原终点，不整段加速蓄力与恢复。
- 动画、服务端锤头扫掠和镜头继续共用 `WarhammerUppercutMotion::PoseTime`；上挑音效读取新的 `StrikeStart`。锤头轨迹从本版烘焙骨架重新生成。扫掠起点改为 `LoadedSource`，与实际 1.225 秒的发力／音效一致，避免右下蓄势期间提前判中侧前方目标；体力／冷却仍在原释放节点提交。

## 交付状态

- 工作目录：`SourceAssets/SteelWarhammer20261014/UppercutIdleExitV3/`，包含可编辑 Blend、FBX、制作脚本、配方及导入回执。
- 正式对象：`/Game/Weapons/SteelWarhammer20261014/UppercutV1/A_Warhammer_Uppercut`。
- 现有编辑器桥已完成导入、动画编译及保存，修订 `IdleGripLowerRightV3_20261015`，回执 `complete=true`。
- V1 的制作／导入入口已转到 V3，旧源 Blend 作为挥出与回收的制作输入保留；旧脚本和正式动画包在 V3 的 `Before/` 中备份。
- C++ 修改为 `WarhammerUppercutMotion.h` 的时钟、生成的 `WarhammerUppercutArc.h`，以及 `ProductionBluntUppercut.cpp` 的扫掠起点。本次热编译返回 `CompileNotStarted / Live coding canceled`，未应用补丁；随后编辑器退出，完成了正式构建收尾。
- 构建期间另修复两处阻塞编译的问题：`WardBedScatter.cpp` 将不存在的 `OverlapBlockingTestByObjectType` 改为引擎实际提供的 `OverlapAnyTestByObjectType`，查询对象／形状／参数保留；`FPSGpuTraceCapture.cpp` 将自行管理 Windows 包裹的 D3D12 头移出外层 Allow/Hide 区间。修改前文件均保存于 `Before/`，未改这些功能的业务逻辑。GPU 面板声明与 D3D12 模块依赖由并行修改补齐，本任务未覆盖。
- 最终 `FPSGAMEEditor Win64 Development` 返回 exit 0、`Result: Succeeded`，UBT 确认 `Target is up to date`（5.67 秒）。`build_receipt.json` 和 `delivery.json` 记录本轮正式构建与已保存资产；前两次失败日志分别保留为 `attempt1/attempt2`。未重新打开编辑器。
- 未运行游戏、预览渲染或额外测试。伤害与距离数值、前踏位移、体力／冷却规则保持原实现；动作效果由用户体验确认。
