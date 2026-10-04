# 上挑 V16：镜头拉扯扩大与双倍前踏

2026-10-04。按用户要求调整 `Source/FPSGAME/Weapons/RuneSwordUppercutMotion.h` 的现有表现参数：

- 镜头右下蓄势、左上甩动的主位移与旋转幅度均扩大为 V15 的 1.5 倍。短促制动振动、落脚反馈仍使用既有包络。
- 释放前踏由 75 cm 翻倍至 150 cm，推进窗口仍为 0.16 秒；沿用原有地面支持与扫掠碰撞约束，障碍物可能截短实际位移。
- 继续使用 V15 标准柄／长握柄动画、握点修正与 recover；本轮仅调整运行参数，无动画资产重导入。1 秒蓄势、0.075 秒主上挑和 2.05 秒动作总长维持。

构建记录位于 `SourceAssets/SwordUppercut20261004/FeelV16/`。`FPSGAME` 与 `FPSGAMEEditor` 的 Win64 Development 常规构建均已成功，退出码 0，正式 Game 可执行文件与基础 Editor 模块已落盘，详见 `build_receipt.json`。等待现有编译及资源导入结束后完成 Editor 构建，未使用 Live Coding。本轮未启动编辑器或游戏，未追加测试、截图或验收；手感由用户试玩。
