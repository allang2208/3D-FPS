# 高草踩踏形态修正（2026-09-27，mf-v11 / pass-v5）

用户实机反馈：走过的草变为大块慢速流动的马赛克，倒伏痕迹不清晰。上一轮 24 项 RT／运行状态断言通过，但画面仍不合格，不能把该计数当作视觉完成。

## 原因和本次实现

- v10 按每个顶点的世界 XY 选择方向及强度，再按整丛的最低 Z 推算高度。相邻顶点方向可能相反，只挪动高度向量又不旋转草片横向分量，叠加逐顶点 100 cm 限幅，会把三角形拉宽、折叠。
- v11 从现有 PivotPainter 的 UV1 和 `Position and Index Texture` 读取每片草的根部，以 INSTANCE→WORLD 转换。RT 和爆炸波前都在该根部采样；同片所有顶点做同一刚体旋转，恢复过程中仍保留形状。
- 最大角 78°；260 cm 位移预算通过整片统一角度上限约束，主材质 WPO 边界 300 cm。不会对同一三角形的不同顶点单独截断。
- 原风 WPO 作为函数输入组合到旋转中，压倒时降低至 5%，恢复时连续返回原风强度。原 Add A 仍保留，函数返回值扣除该原风以避免重复叠加。
- RT 的 GB 改为 `.5 + .5 * R * direction`，Fade 同步缩放；空白和相反方向的过滤不再放大为突变。窗口每次移动对齐整数像素（1024 下约 3.984375 m），避免旧版 4 m 对应 85.333 像素而不断重采样模糊。
- 角色仍在 10 Hz 着地投影入口发事件，每次一个 GPU pass 覆盖上次到本次的连续线段；半径至少 75 cm、核心 40% 保持强度，强度 .75–1，20 cm 起写。超过 300 cm 的跳变不连成草痕，空中仍不踩草。单点脚步和爆炸接口不变。

适用两个正式主材质：`MA_Grass` 和 `M_TemperateMeadow`，高草测试场以及继承它们的丘陵／草库实例一起使用。未修改网格、密度、LOD、草颜色或测试地图布局。

## 制作证据

- 作者：`Tools/GrassDeform/setup_assets_m1.py`。
- 已保存 9 个资产，3 个 pass 与 2 个主材质最终 SM6 编译错误列表均为空：`SourceAssets/GrassDeform20260927/authoring-20260927-102542.json`。
- 改前二进制备份：`SourceAssets/GrassDeform20260927/BeforeV11-20260927-102542/`。
- 两种测试草、全部 8 个 render LOD 的每三角形 UV1 差值均为 0：`Saved/GrassShape20260927/blade-uvs.json`。因此同片顶点确实使用同一 pivot，非仅假设素材适配。
- 已保留两个历史 WPO FunctionOutput 身份并全部连接新实现。图节点 `GrassV10.*` 是持续使用的节点身份，不代表仍在运行 v10 代码。

## 构建与运行状态

- 普通 Editor 目标构建成功：`Saved/BuildEditor/build-20260927-103037.log`；测试启动前 DLL 时间 10:30:50，晚于草子系统最后源码修改 10:30:29。运行日志的窗口中心 `(-1593.750,-796.875)` 也对应新版 398.4375 cm 网格。没有使用 Live Coding 或另起交互编辑器。
- 构建中遇到弓模块 `UPoseableMeshComponent` 不存在 `GetSkeletalMeshAsset` 和缺省参数不一致；必要修复仅把 `BowFlexMeshComponent.cpp`／`BowPartComponent.cpp` 的 4 个读取改为基类实际提供的 `GetSkinnedAsset`，并让 `BowPartComponent.h` 的 `RingDegrees` 默认值与底层一致为 0。没有修改弓动作逻辑。BowAssembly 同类错误在后续编译前已由并行修改消除，本轮未覆盖该文件。
- 沿用用户此前明确提出的检查授权，独立后台游戏 `-RenderOffscreen -GrassFunctionalAudit`，隔离存档 `GrassAudit-shape-v11-20260927`。24 项运行断言全部通过，进程已正常退出。
- 证据目录：`Saved/GrassDenseValidation20260926/shape-v11-20260927/`。`results.txt` 末尾 `COMPLETE checks=24 failed=0`；`runtime.log` 没有草材质编译失败。
- 实际步行约 6.55 m、保持着地，生成草痕及 3 个脚印／2 个扬尘；空中不踩踏、脚步池释放、禁用清空、18 秒恢复均通过。6.008 秒内强度从 .8896 降至 .5278；旧草可在新脚印不断产生时恢复至 0。
- 固定相机 `01_before.png`／`02_stamped.png` 与 v10 的 `functional-01/02_stamped.png` 对照，新版中心草片不再拉宽为大三角。`05_walk.png` 是真实角色行走后的回望画面，可见两侧倒伏和中间露出的通道。截图支持形态修正，但不把静帧当成用户对完整动态观感的确认。

传送门回程问题不在这次草片形态修正范围，不能据此宣称回程已修复。没有做性能、音频听感或打包版测试；未更改这些系统。
