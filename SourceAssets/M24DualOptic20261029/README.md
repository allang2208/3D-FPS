# M24 原装双瞄具切换

原装 `m24_custom_scope_6x` 在 ADS 时使用滚轮向上选择主体 6 倍镜，向下选择上方 1 倍辅助镜。端点仍消费滚轮，避免同时切枪；退出再进入 ADS 保留本次装备的选择，重新装备默认 6 倍。

倍率、ADS 高度、灵敏度和光学遮罩使用同一个显示倍率。采用帧率无关的指数插值，响应系数 16/s，约 0.19 秒完成 95% 的变化，约 0.29 秒完成 99%。反向滚动从当前显示状态继续过渡。1 倍模式使用实体上方镜和中心红点，6 倍模式沿用 M24 密位分划；两者使用同一相机射线。

`measure_top.py` 从现有 Blender 源文件提取镜片边界，未渲染。`install.py` 按上方镜片边界中心添加 TopSightRear / TopSightFront / TopSightUp，保留主镜瞄点、模型、材质。枪身高度偏移按两个镜片瞄线差计算，包含骨架根节点单位换算，保持已接受的前后距离。未修改动作、握姿、换弹时间或近战动作。

资产路径：`/Game/Weapons/M24/Surface20261027/SM_M24_m24_custom_scope_6x`。

## 落盘入口

- `run_assets.ps1 -Stage install`：通过已有编辑器桥或后台 nullRHI commandlet 保存目标资产，持有现有批次互斥。PIE 会阻止引擎资产保存。
- `build_incremental.ps1 -StageOnly`：利用当前 UE 生成的编译响应文件，编译五个受影响源文件并链接到本目录 Staging，不替换运行中的 DLL。
- `build_incremental.ps1`：编辑器关闭后重新编译、链接并发布 DLL，保留旧 DLL 备份。用于现有 FabToolset 模块规则阻止标准 UBT 的环境，不修改引擎插件。

完成状态以 `install-receipt.json` 的保存结果和 `build-receipt.json` 的 `published` 为准。未启动游戏、运行测试或视觉验收，交由用户试玩。

## 1 倍红点加粗

上方镜红点直径由 1080 高度参考下的 2.5 增至 5，最低直径由 2 增至 4；加深色细描边并提高红色填充亮度，描边与红点共用原有淡入淡出。仅影响 M24 上方 1 倍镜。编译入口可用 `build_incremental.ps1 -CompileUnits ColdSteelCrosshair.cpp` 仅重编本次受影响源文件并链接发布。
