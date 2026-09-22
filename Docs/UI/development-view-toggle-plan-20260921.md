# F6 玩家视角切换

2026-09-21。用户授权直接开发与接入；默认不运行测试或预览。

- 入口：F6 → 基本调参 → 会话开关首行“玩家视角”。按钮显示当前“第一人称”或“第三人称”，点击切换。
- 结构与布局：沿用现有 UMG `FTuningRow`，相邻开关共用卡片、字体、按钮高度和宽度。窄内容区按原 360px 断点把按钮移到说明下方；内容继续由现有 ScrollBox 滚动，页签和返回按钮固定。
- 数据：`UDevelopmentTuningSubsystem` 新增 `ThirdPersonView` 会话选项。默认第一人称；关闭 F6 保持，全部关闭恢复第一人称，退出本次游戏重置；无存档字段迁移。
- 输入与状态：沿用当前单机开发调参的可用条件；无本地受控角色时禁用。点击调用子系统并通过现有 OnChanged 刷新，不新增 UI 定时器或委托。F6/Esc 的焦点与输入归还保持现有入口。
- 镜头：`AFPSGAMECharacter::CalcCamera` 先计算原镜头，再由身体组件沿瞄准轴向后移 300cm。12cm 球形 Camera 通道扫掠处理墙壁遮挡，推近 60cm 内暂时隐藏拥有者身体，保留影子。切换不移动第一人称相机组件，不改变手臂动画、射击起点或翻越相机回正。
- 模型：第三人称对拥有者显示全身、世界武器、配件及衣物，隐藏相机子树中的第一人称网格；切回恢复原拥有者可见性规则。更换装备时新建世界网格读取当前视角选项。
- 操作范围：门窗等通用交互和建造使用 `ColdSteelWorldInteraction::GetReachViewPoint`，第三人称仍取角色眼部起点，保留原交互距离与建造 600cm 射线；第一人称继续使用原控制器视点。枪械本来就从第一人称相机组件取眼部射线，本次不移动该组件。
- 范围：开发面板、开发调参子系统、玩家身体显示及角色相机入口；不新增素材、自由环绕操作或存档设置。当前第三人称动作仍沿用既有简化动画。
- 交付：完成必要原生构建；实际显示、移动、换装、开火及贴墙效果由用户测试。

## 构建状态

用户关闭 UE 后，常规 `FPSGAMEEditor Win64 Development` 构建已完成，包含门窗／建造交互距离补充。`UnrealEditor-FPSGAME.dll` 链接成功，结果 `Succeeded`，不再有待完成链接。日志：`Saved/Logs/PlayerViewToggleBuild20260921-after-close.log`。未启动编辑器、PIE、截图、游戏测试或验收，由用户打开工程测试。

视角开关、镜头和拥有者可见性已完成首次常规 Editor 构建（`Saved/Logs/PlayerViewToggleBuild20260921.log`，`Result: Succeeded`）。随后补齐门窗／建造的眼部交互起点；其源码编译已完成，但最终链接被重新打开的 UE 进程 `21464` 占用 `UnrealEditor-FPSGAME.dll` 阻止（`Saved/Logs/PlayerViewToggleBuild20260921-ready.log`，LNK1104）。

此前曾通过桥调用 `LiveCoding.CompileSync`：第一次返回 no code changes detected；为实际编译补充源码再次调用后，未收到热更新完成结果，当时未计为已生效。已停止本任务等待中的 Python 客户端，未终止 UE 编辑器；该中间状态现已由上面的成功常规构建取代。
