# 当前枪械抛壳口校准配方

本目录为 2026-10-09 用户要求的逐枪检查和修正。运行实现见 [CasingPortCalibration.h](../../../Source/FPSGAME/Weapons/CasingPortCalibration.h) 与 [逐枪记录](../../../Docs/Weapons/casing-port-calibration-20261009.md)。

公开脚本与稀疏位置配方；`Meshes/`、`Geometry/`、`Views/`、`AfterViews/`、骨骼/动画采样和构建回执留在本机。复做需要已授权的完整 UE Content，单独克隆 Git 不包含这些模型与动画。默认宿主是 `D:/FPS3D/FPSGAME`，Blender 5.1 和 UE 5.8；独立计算脚本使用 Python 3.11、NumPy 和 SciPy。脚本中的宿主断言及工具路径在换机前按实际环境调整。

## 制作输入与顺序

1. 先用相邻 `RifleAxialRecoil20261008/read_motion.py` 和 `read_remaining_motion.py` 读取当前长枪引用。它们通过现有 UE Python 批次桥或后台 commandlet 执行，生成本地 `motion_before.json`、`remaining_motion.json`。
2. `read_ports.py` 读取 16 款单枪和 10 套双持网格，并导出单枪当前 FBX。FBX 网格导出需要 RHI；无编辑器时使用现有 `SourceAssets/WeaponSurface20260930/run_ue.ps1 -WithRHI` 后台入口，不另起可见编辑器。重读前保留旧捕获；脚本默认复用已存在的 FBX，不能把旧 FBX 与新引用数据混配。
3. `read_mesh_reference.py` 只读当前网格的绑定姿态；不提交 `SkeletonModifier`。这一步不能用共享 Skeleton 的参考姿态或未注册组件的全零 socket 代替。
4. 用 Blender 后台执行 `inspect_geometry.py`，得到本地 NPZ 几何、`geometry_report.json` 与参考姿态视图。`view_geometry.py` 用于指定位置的局部观察。此类几何检查/渲染只在用户要求对应工作时执行。
5. `calibrate_ports.py` 使用本轮人工选定的窗口像素、外侧平面、网格基准和实际开火样本生成 `calibration.json`。这些像素与本轮镜头/网格一一对应；模型升级后要重新定位窗口，不能盲目沿用。HK416、A762、AKM 采用已有正确开火位置，PKM 只向外让开盖板并修正方向。
6. `write_calibration_header.py` 只需公开的 `calibration.json` 即可重制运行表；不依赖 UE 资产或图像。运行时按枪型查表后缓存到机匣/套筒坐标，发射时取一次世界变换。

`review_pose_mapping.py` 与 `render_calibrated.py` 是本轮用户要求的检查配方，不是每次开发自动执行的验收步骤。侧视红点为实际 fire 首帧挂点，绿点为新位置；重合代表保留原位。两款左轮检查现有退壳路径，不在此表内新增逐发抛壳。

## 构建与状态

`build_backend.ps1` 顺序构建指定 Editor/Game 目标；已有构建或 commandlet 时等待，不关闭或启动编辑器。2026-10-09 两项目标已构建成功，没有运行游戏。最终运行效果由用户实机体验。

失败探测与前版本备份已带散列移入本机 `trash/weapon-gunplay-retired-20261009/`，清单见 [归档记录](../../../Docs/AssetArchives/weapon-gunplay-20261009.json)。公共仓库不含这些恢复副本或第三方资源派生几何。
