# 破势印头顶古印

按用户要求复用已有古印网格，新增金色头顶悬浮表现，保留命中位置的暖铜印纹。

- 运行逻辑：`Source/FPSGAME/Combat/AncientBreakingSealComponent.h/.cpp`。
- 复用网格：`/Game/Weapons/CommonHammerSeats20261024/AncientSealV1/SM_AncientSeal_TargetMark`。
- 材质：同目录 `M_AncientSeal_TargetMark`，新增 `MarkColor` 向量参数；头顶实例为线性 HDR 金色 `(4.0, 2.4, 0.42)`。
- 尺寸：按身体碰撞高度取 26–44 cm，底缘高于身体顶端约 15 cm，轻浮幅度 3 cm；单个目标仅保留一个头顶印。
- 生命周期：现有服务端到期时间和刷新序号控制；刷新短暂变亮，最后 0.7 秒淡出，清除、死亡、销毁时移除。

`build.ps1` 完成 Editor/Game 必要构建；`update_material.py` 仅更新并保存古印材质；`save_material.ps1` 使用现有资产批次互斥执行后台材质制作。原始 `import_assets.py` 已同步同一参数，重导不会移除金色能力。

本轮不启动编辑器或游戏，不进行截图、运行测试或联机验收。构建和保存结果以本目录回执为准。

接入完成：Editor 与 Game 构建退出码均为 0；共用古印材质已完成 GPU 编译并保存。未运行游戏、联机或视觉验收。
