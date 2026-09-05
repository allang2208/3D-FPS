# 溪谷预览场景（2026-09-05）

原入口仍是 `scenes/demo_terrain.tscn`，场景脚本改为 `scenes/scenic_valley.gd`。
新脚本继承旧 `demo_terrain.gd` 的玩家、HUD、NPC 和双向传送接口，仅重做环境构造。
`scenes/scenic_valley.tscn` 是可直接运行的同版入口。旧脚本和原 `assets/terrain_data/demo` 区域文件保留。

## 本次构造

- 出生点移至溪谷左侧观景坡，面向西侧湖盆与远山；返回门与鼠王位于身后附近。
- 高度、地表控制图、湿润度、水面、植被共用河岸边界；水面宽窄变化，水平横断面向西下降，湖面保持同一高度。
- 草、泥、碎石、岩面、林下土五个真实材质分区；降低地表法线强度并提高干地粗糙度。
- 分块 MultiMesh 装饰，近景蕨类、灌木与短草，中景露岩、混交林，独立远山网格。
- 细草 180625 个实例，约 40 米范围，按材质控制图排除水边、岩面；原配置 561001 个实例。
- 树干具有碰撞与 `impact_surface=wood`；草、灌木、露岩仍是装饰，与旧场景一致。
- 现有 fir_sapling 资源实际包含三棵并排变体，新场景每处只保留一种；为导入时丢失贴图绑定的材质设置场景局部覆盖。

## 资产来源

复用仓库内 Poly Haven 模型（CC0）和 AmbientCG 地表纹理，没有引入新外部模型。
`assets/textures/scenic_valley/fir_twigs.jpg` 是已有 `fir_sapling_twigs_diff_2k.jpg` 的原样副本，
用于绕过该原文件 `.import` 的既存 `valid=false` 状态，未修改原图、原导入记录或插件源码。

## 缓存与重建

新区域缓存位于 `user://terrain_cache/valley_02`。修改高度/控制/颜色配方后更新
`CACHE_REVISION`，或者启动时追加 `-- --rebuild-valley`。首次构建需要生成地图，后续读取缓存。
本机真实路径：`%APPDATA%/Godot/app_userdata/无尽轮回 3D FPS/terrain_cache/valley_02`。

## 验证与预览

```powershell
$engine = 'E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64_console.exe'
& $engine --headless --path 'E:\3d\3-dfps' res://tests/test_scenic_valley.tscn
& $engine --path 'E:\3d\3-dfps' --script res://tests/render_valley.gd --resolution 1280x720
```

回归检查实际入口、玩家落地、地形碰撞、树木贴地/贴图/碰撞、河床与岸高、NPC、
返回门目标及真实 Area3D 触发、草实例预算。返回主场景的异步加载不在此结构测试内。
渲染脚本隔离鼠标输入，保留实际出生相机，再检查河岸和高处总览。

`docs/preview/valley_before.png` 是本次实际运行的旧入口截图；
`valley_after_0.png` / `_1.png` / `_2.png` 分别为新出生点、河岸与总览（隐藏 HUD/枪械以看清环境）。
所有截图使用项目默认 D3D12 / Forward+，1280×720。

当前资产的树冠密度、细草形态、山体细节仍与用户的写实参考有距离；本次建立可继续调整的构图和材质分区，不能视为一比一复刻。
