# 垂直握把 75% 与导轨贴合修订

承接 TightGrip 的已接入紧握版。当前修改仅为游戏配件网格和左手动作；配件 ID、属性、M4 材质及换弹时序保持。

- 原包围尺寸 48 × 44 × 138 mm，新尺寸 36 × 33 × 103.5 mm，三个轴均乘 0.75；测量见 model_scale.json。
- 安装基准来自当前 M4 下导轨实际网格。缩放后槽底位于旧安装坐标 z=-7.5 mm，再沿安装上方向移 0.7 mm；导轨齿面约 -6.70 mm，槽底约 -6.80 mm，保留约 0.1 mm 的视觉接缝。导轨齿槽本身的周期空隙保留。
- 原生运行安装变换不改：0.7 mm 位移写入静态网格局部顶点，作者动画使用同量更新后的安装矩阵。手臂和骨架不跟随配件缩放。
- 根据细握把重新求解掌位、各指节及小幅掌骨收拢；重新生成连续拇指退握曲线及九条动作，保留原换弹业务时间和机械接触区间。
- prepare_compact.py → export_lbs.py → solve_compact.py → apply_fist.py → base_release.py → smooth_thumb_release.py → build_animation.py → validate_source.py / check_geometry.py → import_assets.py → run_validation.ps1 → make_delivery.py。
- Compact_Baseline.blend / fit_baseline.json 是本轮拟合输入；最终姿态为 M4_Vertical_Fitted.blend / fit_final.json。未采用的旧试验脚本来自上一版，不是当前复现入口。

完成验收后以 acceptance.json、import_report.json 和实机图片为准。

## 已完成：vertical-compact75-v1

正式资源目录为 `/Game/Weapons/M4VerticalGripCompact75`，运行 `M4VerticalForegrip.cpp` 的动画和网格路径已更新，并登记 AlwaysCook。旧静态网格被打开的编辑器锁定，初次覆盖失败日志保留为 import_locked_attempt.log；因此改用独立资源目录，旧版保留。安装变换数值未改。

UE 读回新网格尺寸为 3.6 × 3.3 × 10.35 cm，三轴比例 0.75。九条源动画合同通过；446 个真实手套/握把三角面姿态采样无相交；静态掌面及五指内部顶点均为零。九条 UE 动画导入及压缩读回通过。

本轮原生构建 suffix 2026095117 成功。共享工程随后存在其他构建更新模块清单，没有恢复或覆盖该清单。新游戏运行 vertical-compact75-v1：288 项通过，0 失败；UI 检查 24 项通过，0 失败。已查看实机第一人称、掌侧、正面、腕背以及枪匠侧视/全配件图。

最终导入命令返回 1，日志仅剩工程既有 GameFeatureData 配置及 8000 端口占用错误；独立目录的模型/动画保存与读回通过，没有旧资源文件锁错误。未做完整打包验收。

交付源 M4_VerticalForegrip_Integrated_Editable.blend、各动作 Blend/FBX、SM_VerticalForegrip.fbx、参数与日志。M4_VerticalForegrip_Gameplay.mp4 为 133 张实机画面组成的静音预览。已打开的用户编辑器未被强制关闭，需要重开工程加载新模块及资源引用。

后续腕部衔接优化已由 `../WristNatural/README.md` 接续：模型/材质/安装及抓握继续使用本版，当前九条动画运行目录改为 `/Game/Weapons/M4VerticalWristNatural`。本目录保留优化前的手臂姿态证据。
