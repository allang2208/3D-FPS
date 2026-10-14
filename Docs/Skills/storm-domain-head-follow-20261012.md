# 雷暴领域：头顶锚点与垂直跟随修订

用户上楼测试时进入云层。现行源码已有每帧 XYZ 更新，但顶部避障将云顶限制在世界天花板高度，云层下界又允许低于头顶，玩家向上移动时会追入云层。

本轮将云底改为当前胶囊头顶上方 24 cm；低净空时头顶间隙在 4～24 cm 内收紧，厚度在 6～110 cm 内压缩。云顶由当前头部锚点加厚度求得，不再独立缓动一个可降入身体的顶部高度。水平和 Z 位移逐帧同步，厚度恢复才使用平滑过渡。

环境探测保留实际顶部世界高度，Z 位移超过 8 cm 立即更新，常规最多每 0.12 秒更新。偏置采样不可跨墙，起点穿入结构或位于头顶以下的命中不作为屋顶，避免较低楼梯平台拉低整个云。Niagara 使用本组件更新后的参数再计算粒子。落雷起点沿用更新后的云层位置和原有室内短雷替代路径。

只修改 `FPSElectricMagicComponent.h/.cpp`；StormDomainV2 现有粒子每帧已经读取 CurrentPosition 与高度／厚度，无需重建材质或 Niagara。伤害、半径、持续时间、法杖条件保持原值。

源码已落盘，`FPSGAMEEditor Win64 Development` 与 `FPSGAME Win64 Development` 后台构建均为 `Succeeded`，已更新基础 Editor DLL 和游戏可执行文件。日志位于 `Saved/StormHeadFollow20261012/Editor-build.log`、`Game-build.log`。未打开编辑器、运行游戏或进行视觉测试。
