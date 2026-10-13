# 镭射落点同步（2026-10-13）

用户要求本机与其他玩家看到同一镭射落点。此前拥有者按准心／瞄具归零，世界副本沿枪轴另做描线，且远端光效创建只处理 Super90 的战术件，其他枪仅复制配件网格。

## 落点与装备

- 拥有者保留现有手枪 ADS 平滑衔接、步枪到位归零、每手独立换弹／冲刺规则和近墙遮挡，输出最终射线终点、表面法线及光点显隐。
- `FFPSBodyLaserSample` 随已有身体表现状态复制，以装备索引、配件索引和机构布局签名绑定实际配件；每份样本最多四束，不写入存档。
- 原生配件组件向装备清单提供普通／赐福镭射类型和出光轴规则。所有枪型的世界副本从这份清单创建效果，覆盖单持、双持、法杖副手与双战术槽；不再按 Super90 路径猜测或替换网格。
- 世界光束从可见枪上实际发光口发出，光点使用拥有者传来的同一个终点。世界枪与第一人称枪位置不同，必要时只截短世界光束，不另生成一个落点。
- F6 切换只改变可见发光口；射线继续取第一人称实际武器和游戏相机，观察镜头不会改动共享落点。

## 网络与生命周期

- 沿用原有 `ServerBodySnapshot`／`ServerBodyTransition` 和 `ReplicatedState`。有镭射时采用现有 25 Hz 活动表现频率；启停／装备绑定变化走可靠边沿，位置更新不增加逐帧可靠 RPC。主机也按 25 Hz 请求更新。
- 服务器核对本机装备清单、武器实例、配件身份、布局签名、有限坐标、法线及射程；只接受外观信息，不影响命中、弹药、伤害或改造属性。
- 换枪、配件卸除、隐藏、翻越、死亡及表现样本过期时取消旧光束；使用原有 0.6 秒网络表现租约，正常启停随可靠状态边沿更新。迟到的旧装备样本不能驱动新枪。
- 远端不重新推算瞄准方向，不对落点做跨表面的插值，避免插值把光点拉进墙里。网络传输仍有延迟；同一份样本的落点是一致的，不代表不同机器能零延迟同时呈现。

源码入口：`Characters/FPSPlayerBodyLaser.cpp`、`FPSPlayerBodyTypes.h`、`FPSPlayerBodyNetwork.cpp`、`FPSPlayerBodyActions.cpp`、`FPSPlayerBodyEquipment.cpp` 与 `Weapons/TacticalDeviceComponent.*`。

## 交付

本轮持续 ADS 自动架枪已按用户后续要求撤回，保留退出并重新进入 ADS 的确认交互；最终只保留镭射同步代码修改。构建回执在 `Saved/BipodLaserSync20261013/change-receipt.json`。网络结构有新增字段，双方使用同一新版程序。仅进行制作和正式后台构建，不打开编辑器、不运行游戏或测试，实际联机观感由用户确认。

正式构建已完成：`FPSGAMEEditor Win64 Development` 日志 `Saved/BuildEditor/build-20261013-225920.log`，`FPSGAME Win64 Development` 日志 `Saved/BipodLaserSync20261013/game-build-r2.log`，均为 `Result: Succeeded`。基础 Editor DLL 与 Game EXE 已落盘；未执行实机或双客户端测试。
