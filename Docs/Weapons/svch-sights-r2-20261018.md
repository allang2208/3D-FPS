# SVCH 精细机械瞄具与拉栓避让

2026-10-19：最终 ElbowFit 版本已保存、接入并完成本次定向实机复查。用户明确同意微调拉栓阶段肘部避让，同时保留抓握、手指姿态、动作时序及 V9 网格。

## 最终改动

- 复用项目已有 HK416 精细圆鼓照门与弧形前准星，保留真实开孔、滚花、刻度、调节螺钉、夹轨槽和圆顺边缘。两件瞄具共 65,840 三角面，整份含备用手臂的骨骼模型共 147,201 三角面。
- 使用独立深色涂层金属材质，复用原 4K 颜色、法线、粗糙度、金属度及 AO。瞄线离导轨 3.1 cm。
- 导轨中段的悬空薄片实际来自枪机分件：旧绑定令它在待机时偏离制作位置约 7.278 cm。对该分件的 857 个导出顶点加入绑定补偿，保留原形状、UV、法线和枪机动作轨道；待机时回到源模型正确位置。没有用隐藏部件掩盖问题。
- 为给原有抓握留出空间，后照门相对首版精细样件后移 6.5 cm，重新测量保存网格的瞄点。光学配件沿轨偏移同步补偿为 14.5 cm，保持其原绝对安装位置。
- 空仓换弹用独立姿态差量配置进行右臂避让：沿用原肩部轨迹，以完整上臂、前臂、辅助骨和手腕链解算；接近及脱离段分别增加最大 6 cm、3 cm 的外绕，接触段保持手掌位置与方向。肘部相对原源姿态最大偏移约 11.83 cm，最大极向角约 35.76°，只出现在拉栓局部段。
- 共享 SVD 动画资产、V9 网格、手指局部曲线、普通换弹配置、弹匣/扳机绑定、机械事件时钟、回位逻辑和弹道未改。目录图标与服装适配已同步。

## 当前资产

- 网格：`/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/SK_SVCH_SightsR2_ElbowFit`
- 接触配置：`/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/DA_SVCH_ElbowFitGrip`
- 瞄具材质：`/Game/Weapons/SVCH/Replacement20261018/SightsR2/Materials/M_SVCH_DetailedSights`
- 可编辑源：`SourceAssets/SVCHReplacement20261018/SightsR2/SVCH_SightsR2_ElbowFit_Editable.blend`
- 导出：同目录 `SK_SVCH_SightsR2_ElbowFit.fbx`；枪机绑定补偿在导出副本中烘焙，编辑母版保持正确装配外形。
- 制作入口：`export_elbow_fit.py`、`bake_elbow_clearance.py`、`install_elbow_fit.py`、`activate_elbow_fit.py`。
- 标定：`elbow_calibration.json`；构建：`run_build.ps1`；定向运行：`run_elbow_review.ps1`（再次运行须使用新标签）。

## 本次证据与范围

`build_receipt.json`、`build-console.log` 记录 FPSGAMEEditor Win64 Development 构建成功。`elbow_install_receipt.json` 记录实际保存网格与配置；不是仅准备导入脚本。

最终实机目录：`Saved/SVCHPoseAudit/svch-sights-r2-20261019-a4`。独立档案、离屏 1600×900，86 帧，6 个稳定 ADS 样本及 30 个原生 V9 空仓动作样本。开镜最大滚转约 0.000000575°，前后瞄点投影误差 0 px；空仓换弹完成并返回待机。

已查看腰射、ADS、拉栓接近/接触/释放及回位关键帧：导轨悬空片消失，之前照门切入右腕的现象未在这些帧中再出现。视觉判读与自动完成状态分别记录在 `delivery_receipt.json`，不扩大为全动作或所有角度验收。

实际引擎接触对比 `runtime_contact_comparison.json`：A3 到 A4 在源帧 304–344 匹配 19 个样本，手掌相对枪机的位置最大差异约 0.0237 mm，旋转最大差异约 0.00507°。手指曲线和时间数组保留原值。离线封闭体积筛选的最小间隙约 2.24 mm；未封口的手臂网格不使用射线符号距离作为“内部/外部”验收依据。

本轮未重跑普通换弹、弹道、全部配件、检视或联机；未构建打包目标。最终手感与审美由用户体验确认。

## 对比图

源模型近景：`before_rear.png` / `final_rear.png`、`before_front.png` / `after_front.png`。这些是 Blender 渲染，非游戏截图；最终装配为 `final_assembly.png`。

实机修正前：`Saved/SVCHPoseAudit/svch-sights-r2-20261019-a3/Frames/reload_empty_00035.png`。

实机修正后：`Saved/SVCHPoseAudit/svch-sights-r2-20261019-a4/Frames/reload_empty_00035.png`；同目录 `hip_00004.png`、`ads_00013.png` 和 `hip_return_00085.png` 分别为腰射、开镜及回位。