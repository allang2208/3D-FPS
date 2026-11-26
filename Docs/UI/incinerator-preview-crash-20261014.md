# 打开焚化炉面板时的图标预览崩溃

2026-10-14。已完成源码修复、普通 Editor DLL 构建及本次断言路径的无界面定向诊断；未运行实际面板交互、截图或联机测试。

## 崩溃依据

- 用户提供的堆栈从 `UColdSteelWeaponIcons::Tick → Prepare → FColdSteelPreviewScene` 进入引擎并断言 `Ret->IsA(T::StaticClass())`。
- 对应本机崩溃目录为 `Saved/Crashes/UECC-Windows-3BDF7B3B494F33D1CF6315910588C7B2_0000`。报告中的引擎版本为 5.8.3-58210709。
- 用当前引擎 DLL 导出表还原未符号化帧：`Engine+0x2292b85` 是 `FSubsystemCollectionBase::AddAndInitializeSubsystems+0x135`，随后依次为集合 Initialize、UWorld::InitWorld、InitializeNewWorld 和 FPreviewScene 构造。
- 该引擎函数在调用 `ShouldCreateSubsystem` 前先执行 `Class->GetDefaultObject<USubsystem>()`。默认对象类型不匹配会直接断言，单靠子系统拒绝预览世界无法拦截。
- 同一日志在 14:32:11～14:32:15 记录 Live Coding 重建 `DungeonSharedProgress`、`AuthoredDungeonGenerator`、`DungeonRunSubsystem`、`FacilityHallEncounter`，14:33:35 发生断言。此顺序符合热更新后反射类型/默认对象不一致的故障路径；现有小转储未确定具体失配类，不能仅凭重建列表断言某一个类就是故障对象。

## 修复

- `FColdSteelPreviewScene::TryCreate` 在调用引擎基类构造前，沿引擎同样的派生类范围和 Abstract/AuthoritativeClass 筛选规则检查世界子系统默认对象。先使用无模板接口取得对象，再校验它既属于 UWorldSubsystem，也属于声明的具体类。
- 异常时不创建预览世界，不修改类注册表或玩家世界；返回含子系统类、默认对象及其实际类型的原因。
- `UColdSteelWeaponIcons::Prepare` 使用该入口。失败进入既有 `FinishJob(false)`：保留目录图回退、移除当前队列任务、广播就绪通知。焚化炉与使用同一图标服务的背包/仓库等面板保留原有物品、库存和交互规则。
- 检查仅发生在新建图标摄影场景时；不新增每帧全局类扫描，也不关闭动态图标、渲染特性或全局引擎断言。
- 完成常规 DLL 构建，后续冷启动使用磁盘模块；本次未触发 Live Coding，也未启动交互编辑器。

## 构建阻塞的最小修订

首轮构建被 `Production/WarhammerShockwave.cpp` 的 `DOREPLIFETIME` 宏阻塞。该宏要求输出参数名 `OutLifetimeProps`，原函数使用 `Out`。仅修改函数定义中的参数名及 Super 调用，不调整战锤数值或行为。

## 定向诊断与产物

新增显式调用的 `ColdSteelPreviewSceneDiagnosis` commandlet。在独立 NullRHI 进程中临时以非子系统对象替换一个世界子系统的 CDO，确认创建入口拦截；随后立即恢复原 CDO，并创建/销毁正常预览世界。没有创建 GameInstance、玩家档案或加载游戏地图，所有临时类型状态随该进程结束丢弃。

- 首次诊断夹具使用抽象 UObject 触发额外 ensure，进程非零退出；该轮不视为成功。夹具改用具体 USceneComponent 后重编译并重跑。
- 最终构建：`Saved/BuildEditor/build-20261014-145045.log`，`Result: Succeeded`，已链接 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。
- 最终诊断：`Saved/PreviewSceneDiagnosis20261014/run-145148/commandlet.log`，进程退出码 0，`checks=7 failures=0`。
- 覆盖错误类型被拒绝、错误详情、拒绝时不分配世界、原 CDO 恢复、正常预览世界创建、成功时清理错误以及世界上下文释放。

以上结果证明本次默认对象类型断言路径被拦截、正常创建路径仍成立。实际焚化炉面板操作和热更新完整复现仍由用户在重新打开 UE 后体验，未将无界面诊断当作画面或联机验收。
