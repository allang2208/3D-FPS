# 雷电迅捷：手脚电弧专项检查（2026-11-07）

用户要求检查环绕手部及脚步特效是否生效、是否符合雷系表现。使用隔离档案及后台 SceneCapture，不打开图形编辑器，不进入用户地图或用户角色存档。

## 发现的问题

1. **持续期间实际没有电弧。** 原资产从短促近战电弧复制，`Currency`、`MainPower` 均为 `Once + Infinite Loop Duration`，只在开始发射一批粒子；粒子寿命 0.24 秒且 `Kill Particles When Lifetime Has Elapsed=true`。组件之后仍是 Active，原运行代码不会再次激活。取样时四肢/两种视角均为 Active/Visible，但两个发射器粒子数均为 0，开启/关闭对照中没有电弧。
2. **第一人称脚部缺少最终姿态依赖。** `FirstPersonSharedBody` 是不执行 Tick 的姿态代理，真正的骨骼由 LeaderPose 的身体网格更新。增加实际姿态生产者的 Tick 前置依赖，并在切换/清理时移除。
3. **曲线只按 85ms 更新会偏离运动中的骨段。** 行走样本中，原设定 6cm 的脚部环绕半径出现约 3.40cm 和 8.97cm 的根部距离。现在每帧根据同帧骨骼重建曲线，只有随机种子保留 85ms 的跳变节奏。
4. **第一人称手模的导入缩放污染电弧。** `HandDiagnostic/result.json` 中 RuneSwordViewmodel 手骨世界缩放约为 `(100,100,100)`，被样条与 Niagara 继承，包围盒扩至数十米；两个手部发射器有粒子但正反面及仅电弧画面均不显示。第三人称和脚部骨架缩放为 1，能够显示。运行时改为只继承骨骼位置/旋转、单位缩放，样条点也使用此坐标系转换。

## 修正

- 专用 Niagara 资产继续只保留两组 CPU ribbon 发射器，禁用粒子寿命到期自动杀死；固定的一批粒子由迅捷组件统一控制亮度、淡出和销毁，不使用重复 burst 累积粒子。
- 继续使用四组独立样条（左右前臂、左右小腿/脚踝），现有雷系颜色、材质、脚后短尾迹和无动态灯设计。
- `Tools/Skills/build_lightning_haste_assets.py` 同步此配置，并在编译后重新绑定所有 `User.BladeSpline` 默认接口，实际保存原运行路径。
- 原资产备份：`SourceAssets/LightningHasteVFX20261107/Before/NS_LightningHasteArc.uasset`；保存回执：同目录上一级 `asset-receipt.json`。

## 证据与范围

- 运行检查入口：`SkillNetworkAudit -LightningHasteVisual -RenderOffscreen -AllowCommandletRendering -Out=<绝对路径>`。
- 检查源码：`Source/FPSGAME/Skills/LightningHasteVisualAudit.cpp`。
- 失败取样：`Saved/LightningHasteVFX20261107/Baseline`，16 个持续阶段样本均零粒子；资产输入：`asset-inputs.json`。
- 使用当前身体骨架、实际剑类手模、空手行走源动作和运行时附着函数；每组记录粒子数、曲线长度、根/末端距离及姿态生产者依赖，保存静止、行走、接近结束、结束后的画面与关闭特效的对照。
- 第一人称效果为真实分支生成；为 SceneCapture 显示，临时解除 OnlyOwnerSee 与第一人称投影标记。因此本轮不等同于实际玩家相机、服装全组合或真实网络传输验收。

## 持续粒子复查

- `Saved/LightningHasteVFX20261107/Persistent/result.json`：32 个四肢取样，粒子及附着断言为 0 失败；稳定阶段每肢两组各 25 个粒子，不随时间累积，到期清除全部组件。
- 此轮图片显示脚部及远端身体的电弧；第一人称手部虽有粒子但图片未显示，不能用这份计数结果判定手部画面通过。后续 `HandDiagnostic` 定位为骨骼导入缩放污染，最终结果见下节。
- 行走时四组曲线根部保持 4.5cm（手）/6cm（脚），第一人称腿部记录的姿态生产者依赖均存在。
- `FPSGAME Win64 Development` 后台构建成功，退出码 0，更新独立游戏 EXE；日志 `Saved/LightningHasteVFX20261107/build-game.log`，223.47 秒。未运行游戏。

## 最终结果（单位缩放修正后）

- `Saved/LightningHasteVFX20261107/UnitScale/result.json`：32 个四肢取样，0 失败，commandlet 退出码 0。第一人称与远端分支各包含左右手和左右脚；稳定阶段每肢 50 粒子，结束时四组组件全部清除。
- 已查看 `hands_030.png`、`hands_070.png`、`hands_fx_only.png`、`hands_reverse.png`、`feet_070.png`、`hands_118.png`。左右手电弧恢复可见，沿前臂环绕且按实际前后关系被手臂遮挡；脚部环绕与移动尾迹可见；结束画面无残留。
- 手模源骨骼仍保持约 100 倍导入缩放，电弧世界缩放改为 1。手部包围盒由数十米恢复至约 61×61×44cm（含保守边界），随机形状更新、细电丝亮芯及蓝紫色电光保留。
- Editor 最终常规构建成功：`Saved/BuildEditor/build-20261107-183029.log`，30.46 秒。
- Game 最终常规构建成功：`Saved/LightningHasteVFX20261107/build-game-final.log`，35.54 秒。两者均退出码 0，基础 Editor DLL 和独立游戏 EXE 已更新，专用 Niagara 包已保存。
- 本次没有打开图形 UE、进入用户存档或运行游戏；中途已有编辑器未被关闭或修改。隔离渲染只输出本任务图片与 JSON，未覆盖其关卡或资产。
- 检查覆盖当前手模与身体骨架的静止/行走/淡出/结束，不能替代实际玩家相机投影、全部服装武器组合和真实多人网络验收。
