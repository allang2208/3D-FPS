# 垂直握把：左侧支撑修正

用户指出前臂几乎与枪械平行，并指定参考棱镜阻手器。本次核对 `M4PrismGrip` 的实际源姿态：肘部应在手腕左侧。此前垂直握把肘部位于手腕内侧，虽然腕轴折角较小，整臂方向仍不符合目标。

新方案按棱镜的外侧支撑方向设置肩肘链，前臂在枪身水平面上斜向握把。仅把肘部移左且固定掌面会产生约 35° 的腕轴折角，因此整只手沿圆柱握把轴转向 25°，保持原逐指弯曲和对握意图，使腕轴折角约为 17°。未镜像或缩放手臂，未修改骨长、蒙皮、手指局部平移。配件模型、安装位置和材质沿用紧凑版。

复现：`orient_grasp.py` 从 WristNatural 原参数生成方向修正；`fit_support.py` 读取棱镜实测肩肘方向并生成作者脚本；`build_animation.py` 输出九条动作。再执行 `validate_source.py`、`validate_arm.py`、`check_geometry.py -- --full`、`import_assets.py`、`run_validation.ps1`、`assemble_editable.py`、`make_delivery.py <run>`。

`reference_positions.json` 和 `support_parameters.json` 是实际坐标证据。`before_top.png`、`after_top.png`、`prism_top.png` 使用相同视角。`ReferenceWorkflow` 为仍被作者入口使用的冻结依赖。

运行目录 `/Game/Weapons/M4VerticalLeftSupport`；静态模型仍为 `/Game/Weapons/M4VerticalGripCompact75/SM_VerticalForegrip`。原取弹、插入、压实、拍击区间和右手/武器机械轨道及弹药结算保持。

验收状态以 `acceptance.json` 为准。未进行打包运行和音频验证；本次未更改声音、UI 或物品数据。旧测试报告不作为本次动画通过证据。

本次运行 `vertical-left-support-v1`：348 项运行检查通过，446 个手指/配件采样无相交，九条动画源与导入读回通过。稳定握姿相对原版为整手绕握把轴转向；逐指局部姿态保持。图像与动作源已实际查看。

导入 commandlet 退出码 1，来自既有 GameFeatureData 配置错误；资源读回与新游戏进程均通过，未进行打包验收。完整可编辑源为 `M4_VerticalForegrip_Integrated_Editable.blend`，视频为 `M4_VerticalForegrip_Gameplay.mp4`。
