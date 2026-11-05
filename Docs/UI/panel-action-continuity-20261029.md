# 打开栏位时保留正在进行的动作

日期：2026-10-29。用户要求进食、喝药及其他动作期间打开状态、背包等栏位，不因打开栏位而打断动作。

## 改动

普通栏位切换继续接管鼠标、移动和视角输入，但不再调用整套 `SuspendWeaponForMenu`。新的 `PrepareForPanelInput` 只清理连续开火、自动拳击等重复输入及选弹界面，保留已经开始的动画、换弹时钟、消耗品接触点和效果结算。

控制器增加 `IsActionPreservingPanelOpen` 与 `BlocksActionContinuation`。原 `BlocksOngoingActions` 保留现有新动作输入门禁语义；持续播放、接触回调和动作位移使用新的继续判定。不能仅因为显示光标或面板设置了 IgnoreMoveInput／IgnoreLookInput 就撤销已经开始的动作。

共用规则覆盖状态、背包、装备、弹药袋、技能、图鉴以及通过同一背包入口打开的仓库／商店／制作管理栏；枪匠、强化、出征和开发面板也使用保留动作的打开入口。

具体接入包括：

- 进食、喝药和饮水的持续时间轴与接触结算。
- 主副手换弹交接、武器检视、徒手和快速近战。
- 剑、弯刀、生产工具、双手锤、法杖和弓的现有动作时间轴，以及已开始蓄力后的释放阶段。
- 电系施法、冰墙和暴风雪已发起的施法手势及接触释放；元素箭、照明箭、魔法箭雨的准备状态。
- 已开始的闪避和近战动作位移、双手锤上挑／旋风斩及其权威命中回调、架枪维持。

新操作仍使用原输入门禁。物品数量和效果仍在原动作接触点提交；面板打开不会提前结算，也不会启动第二次使用。真实换装、死亡、控制异常、场景离开和工作台实际操作的专用互斥继续由各玩法处理。暂停菜单仍使用原暂停入口；打开生产管理栏与真正进入手工生产不是同一种动作。

## 文件入口

- `Source/FPSGAME/FPSGAMEPlayerController.h/.cpp`：栏位状态与继续判定。
- `Source/FPSGAME/FPSGAMECharacter.h/.cpp`：面板接管重复输入。
- `Source/FPSGAME/UI/ColdSteelHUDWidget.cpp` 及枪匠、强化、出征、开发面板：打开入口。
- `Source/FPSGAME/Items/FPSPotionUseComponent.cpp`：食物／药水／饮水。
- `Source/FPSGAME/Weapons/`、`Production/`、`Skills/`、`Movement/` 的对应动作消费者：区分开始与继续。

本次用户要求覆盖历史文档中“打开面板取消活动动作、退回 Idle”的旧约定。本轮没有改动画资产、食物数值、原技能费用或计分公式。

## 交付状态

源码已落盘；必要的常规 Editor/Game 后台构建记录位于 `Saved/PanelActionContinuity20261029/`。首轮编译期间 `LPVOScopeWidget.h` 更新，旧 UHT 生成行号与当前头文件不一致而失败；没有覆盖该并行改动。首轮日志已保留为 `FPSGAMEEditor-attempt1-console.log`。

用户保存并关闭编辑器后，后台重建已完成：`FPSGAMEEditor Win64 Development` 于 2026-10-29 18:07（北京时间）成功，`FPSGAME Win64 Development` 于 18:13 成功，两者退出码均为 0。更新后的 `UnrealEditor-FPSGAME.dll` 和 `FPSGAME.exe` 已生成；`queue.json` 为 `complete`，各目标结果保存在 `FPSGAMEEditor-result.json` 与 `FPSGAME-result.json`。构建后没有自动打开编辑器。

没有启动图形编辑器或游戏，未运行测试、截图或验收；实际表现由用户测试。
