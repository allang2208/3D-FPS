# PKM / SVD 换弹后的 recover 衔接

用户要求优化两枪换弹回待机的僵硬感，参考现有枪械及沉淀的 SKILL。本轮处理运行时收势与待机交接，不重制已接受的接触手型。

## 依据与原因

- `ue5-fps-arms-animation/references/reload-handoff.md`：沿用已接受的 M16 做法，将视模展示偏移的回收安排在动画收尾内部；与 `ReloadSourceTime` 同步，动作完成时清除残余状态。
- `Weapons/QuickCombatRecovery.h`：已有 recover 使用五次曲线，使开始和结束的速度、加速度归零。本轮复用这一曲线形式，并按两枪各自接触时序设置源时间窗口。
- SVD 的普通换弹枪体运动继承 `AKMReloadPolish20260911`；当前空仓正式源是本任务上一轮保存的 `SVDChargeGrasp20260924`。原运行时仅在最后 0.45 秒线性回收组件位置，晚于手部收势且起止突变。
- PKM 当前普通换弹源为 `Reload16`，空仓为 `Charge34`。运行时没有换弹内的展示位置回收，退出状态后才开始指数回位；换弹结束也没有像 M16/SVD 那样同时清除活动动作与展示权重。
- 通过原本运行的编辑器读取了两枪五种握持的 idle / reload / reload_empty 共 30 个资产的实际来源与时长，记录在 `recovery_inputs.json`。这是制作所需输入读取，不是动作验收。

## 已实现

| 枪械 | 普通换弹收势窗口（源秒） | 空仓换弹收势窗口（源秒） |
| --- | --- | --- |
| SVD | 2.4833–3.3333 | 3.2667–4.2917 |
| PKM | 5.76–6.50 | 5.88–6.60 |

- 在现有手部回握过程中，以五次曲线回收整套视模位置，使枪体和双臂一起落回当前腰射锚点；不对尾部再加滞后滤波。
- SVD 最后 0.10 源秒的动画到 idle 混合也使用同样的平滑端点，避免末段权重线性切换。
- PKM 继续保留完整动画权重到末尾，避免新旧弹箱、弹链停放骨在混合中穿过枪身；结束时同时清除活动动作、动作权重与展示偏移，直接交给现有 idle / ADS / 移动逻辑。
- 普通、空仓以及原厂 / vertical / canted / prism / angled 均通过同一运行时入口生效。
- 仍使用 `ReloadSourceTime`，随敏捷、快手和配件倍率走同一时钟。未改变换弹总长、补弹提交、拉柄接触、声音事件、抓握、模型、蒙皮或快速近战。
- 未改动 M16 已接受的线性回位参数，以及其它枪械原有回位方式。

修改文件：

- `Source/FPSGAME/Weapons/RifleReloadRecovery.h`：两枪收势窗口及平滑权重函数。
- `Source/FPSGAME/FPSGAMECharacter.cpp`：展示位置、SVD 末段权重、PKM 动作完成交接。
- `Before/FPSGAMECharacter.cpp`：本轮修改前快照，包含当时已有的共享改动；仅供定位本轮差异，不应整文件覆盖正在开发的源码。

## 构建与测试

原编辑器进程在输入读取后、热编译脚本执行前退出。本轮没有关闭或重开编辑器，转用 `build_editor.ps1` 经共享批次互斥调用工程常规 `Tools/Build/Build-Editor.ps1`。

2026-09-24 12:29：常规 `FPSGAMEEditor Win64 Development` 构建成功，退出码 0。重新编译 `FPSGAMECharacter.cpp`，链接基础 `UnrealEditor-FPSGAME.dll`，总耗时 15.90 秒。日志为 `build_console.log` 及 `Saved/BuildEditor/build-20260924-122937.log`；这次产物是下次启动使用的基础 Editor DLL，并非仅当前进程的 Live Coding 补丁。

没有追加测试、PIE、截图或预览渲染，也没有自动启动编辑器；最终回位观感和游戏操作由用户测试。
