# 温带丘陵入场天气组件空引用修复

2026-11-06。入口为 `/Game/GameMaps/L_TemperateHills_Initial`。用户从主场景进入丘陵时，预期完成场景加载，实际在天气管理器 BeginPlay 阶段崩溃。

## 原因与证据

- 用户崩溃栈：`UWeatherViewEffectsComponent::Initialize()` 第 52 行，由 `AFPSWeatherManager::BeginPlay()` 第 47 行调用；读取地址 `0x1c0`。
- 本机对应记录：`Saved/Crashes/UECC-Windows-3E6B7D174B60D70FFB442BAD67B04E21_0000/`，11:42:56 已开始加载丘陵并创建 UDS/UDW，尚未打印天气管理器 ready。
- 只读解析该 minidump 的异常上下文：`EXCEPTION_ACCESS_VIOLATION`、`RCX=0`、访问地址 `0x1c0`。结合函数入口的 `bInitialized` 读取，直接故障是空 ViewEffects 实例进入非静态成员函数，不是湿润材质异步加载失败。
- 当前天气迁移源码把默认子对象名称由已提交版本的 `WeatherViewEffects` 改成了 `WeaponWetEffects`。旧地图/蓝图的序列化引用与默认子对象名称不再兼容，是空引用的来源候选；本轮没有启动引擎重现反序列化过程。

## 修改

仅修改 `Source/FPSGAME/FPSWeatherManager.cpp`：

1. 默认子对象恢复原有稳定名称 `WeatherViewEffects`，功能仍是现有武器湿润表现。
2. BeginPlay 在调用组件前恢复无效引用：优先查找当前 Actor 已有的有效同类组件，确实缺失才创建瞬态组件、加入 Actor 并注册。
3. 保留客户端初始化与专服禁用表现 Tick 的原有分支。没有用直接跳过初始化的方式永久关闭武器湿润。

当前 UDS/UDW、服务端天气与时钟、逐武器湿度、地图和材质资产保持现有实现。修改前文件保存在 `Saved/WeatherInitCrash20261106/FPSWeatherManager.cpp.before`；没有回滚工作区已有天气迁移或其他开发内容。

## 交付边界

后台构建已完成：

- `FPSGAME Win64 Development`：Succeeded，540.64 秒；本任务执行，629 项动作完成，包含天气管理器编译及 `FPSGAME.exe` 链接。日志：`Saved/WeatherInitCrash20261106/build-game.log`。
- `FPSGAMEEditor Win64 Development`：Succeeded，23.69 秒；复用紧接 Game 构建完成的共享 Editor 构建，其动作包含本次修改后的天气管理器编译及 `UnrealEditor-FPSGAME.dll` 链接。本任务发现已有该构建后未另起竞争构建。原始日志：`Saved/BuildEditor/build-20261106-115151.log`；完成后副本：`Saved/WeatherInitCrash20261106/build-editor-shared.log`。

本任务没有启动 UE 编辑器、游戏、PIE 或联机测试，没有修改/重存地图。构建成功不等于运行验收；用户后续自行进入温带丘陵测试。若触发兼容恢复，日志会出现 `FPSWeatherManager repaired missing ViewEffects`。
