# 枪械镭射拖影与残影调整

应用到 `TacticalDeviceComponent` 共用的激光束、命中光点，以及当前实际加载的两份 `ScopeOptics20260927/M_ScopeAwareLaser*` 材质。保留已有枪型挂点、光束方向、80 m 射线、ADS 完全到位后 0.08 秒汇聚、高倍镜内衰减与光点尺寸限制。

## 第二轮：命中圆点仍有残影

用户反馈第一轮后命中圆点仍有残影。本轮只修改实际加载的 `M_ScopeAwareLaserDot` 材质，光束材质与运行时源码未改。

- 圆点由不透明改为半透明，使用 `AfterMotionBlur` 通道。本机 UE 渲染流程会在 TSR/TAA 与运动模糊之后合成该通道；关闭运动模糊时也单独合成，不写回时域历史。圆点不再写入接收表面的不透明历史，撤掉其第一轮 `TemporalResponsiveness` 节点与速度输出。光束仍保留第一轮设置。
- 该通道禁用硬件深度测试，因此在材质中明确比较 `SceneDepth` 与 `PixelDepth`，裁掉被前方物体挡住的像素。使用光点自身的一像素深度斜率容差，处理未抖动圆点与抖动场景深度在斜面上的差异；不使用前景深度跳变扩大容差。现有相机至命中点的遮挡射线仍保留。
- 沿用原扁球、真实命中点与表面法线，以局部 XY 半径及屏幕导数软化圆点最外圈，不依靠多帧累积来平滑边缘。保留原始发光输入、`ScopeAlpha` 衰减与镜内尺寸上限；仍在 Bloom、Tonemap 和镜片后处理之前合成。
- 制作入口 `create_laser_materials.py` 同步保留新设置；新增 `laser_dot_coverage.hlsl` 与仅处理圆点的 `update_laser_dot.py`，本轮不重编译或保存光束。版本为 `laser-dot-post-temporal-v2`。

实际圆点材质已由无界面 commandlet 编译并保存，退出码 0；回执为 `Saved/LaserDotNoHistory20260927/material-save.json`，制作日志为同目录 `material-commandlet02.log`。回执仅含圆点，`saved=true`、`beam_modified=false`；旧圆点备份位于同目录 `Before/`。本轮没有原生源码修改，不需要 C++ 构建。未打开交互式编辑器，未运行游戏、截图或视觉验收；残影改善交由用户实机测试。

## 第一轮：源码原因与修改（历史）

- 原 Tick 开头无条件隐藏所有效果，随后把有效光束/光点重新显示。`SetVisibility` 的真实状态变化会使 UE 渲染状态失效，不利于保留上一帧变换和正确的运动向量，也带来重复更新。改为每帧计算最终可见性，只在可见性确实变化时更新；所有提前退出、遮挡、未命中及完整高倍镜的隐藏路径仍即时处理。
- 激光束与光点显式使用 Movable 组件，位置、朝向、缩放合为一次 `SetWorldTransform` 更新；关闭这两件极小自发光效果参与动态间接光与距离场照明，保留表面发光外观。
- 命中光点会跨表面跳跃，光束遇到遮挡时还会改变长度，单纯刚体运动向量无法完整表达。两份材质添加 `TemporalResponsiveness=1`，按引擎合同拒绝旧时域历史；复用工程已有的 `r.Velocity.TemporalResponsiveness.Supported=1`，未修改全局画质设置。
- 半透明光束启用深度/速度输出与 TAA Responsive AA，禁用只依赖相机深度的速度模式；速度写入透明度门槛设为 0.01，使镜内淡出过程仍可写入响应。光点保持原不透明材质和亮度，光束保留原半透明颜色、透明度与镜内衰减。
- 保留 Before DOF 合成和深度检测。UE 5.8 的 After Motion Blur 通道会关闭深度测试，因此本次未使用该通道绕开历史，避免激光束显示到墙前。现有第一人称相机已设置 `MotionBlurAmount=0`。

这些是源码与本机引擎实现支持的原因分析，没有进行运行时归因采样。没有新增粒子、光源、Tick、SceneCapture、射线或每帧材质加载。

## 第一轮：制作入口与状态（历史）

- 运行时源码：`Source/FPSGAME/Weapons/TacticalDeviceComponent.cpp`。
- 同步更新材质制作入口：`Tools/Weapons/ScopeOptics20260927/create_laser_materials.py`，重跑保留同一套时域设置，避免后续制作回退。Scope 包装版本不变，时域节点使用独立版本标记，不重复叠加镜内衰减。
- 材质保存回执：`Saved/LaserTemporal20260927/material-save.json`；修改前的两份材质备份放在同目录 `Before/`。

源码和制作脚本已落盘。无界面 Python commandlet 已成功编译并保存两份实际运行材质，退出码 0；材质回执为 `Saved/LaserTemporal20260927/material-save.json`，制作日志为 `material-commandlet.log`。本任务未打开交互式编辑器。

原生构建首次提交前因已有进程占用而未启动；占用结束后执行常规 `FPSGAMEEditor Win64 Development` 构建，返回 `Result: Succeeded`、`Target is up to date`（0 actions），当前基础目标已经包含落盘源码。记录为 `Saved/LaserTemporal20260927/build-editor.log`，未使用热补丁替代基础目标。

未启动游戏、截图或进行实机测试，最终拖影改善和手感交由用户确认。
