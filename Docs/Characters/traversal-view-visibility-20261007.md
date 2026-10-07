# 翻越／攀爬重复手臂与动作候选（2026-10-07）

## 定位与修正

复现范围：第三人称进入低墙翻越、低台攀上或高处攀上，或在动作中切换第一／第三人称。预期第三人称只显示 Jason 全身手臂。

源码确认 `FPSTraversalExecution.cpp` 创建的 `TraversalArms` 没有挂在相机下：它必须固定在世界中的墙沿位置。该组件设置 `OnlyOwnerSee=true`、`OwnerNoSee=false`，接触窗口内由 `SetVisibility(true)` 显示。原 `FPSPlayerBodyComponent::UpdateOwnerVisibility` 只遍历相机子组件，因此遗漏这套手臂；模块化衣袖和手套会继承它的可见性。普通持枪手臂的第三人称隐藏和这个漏项是两条不同路径。

修正纳入统一视角控制：

- 暴露翻越专用手臂只读访问入口，统一处理其 `OwnerNoSee` 及全部子组件。
- 第三人称隐藏，本机已有死亡视角隐藏条件继续保留；切回第一人称恢复 owner 可见资格。动作自身仍控制接触／收手显示窗口，结束或取消后不会被视角刷新重新显示。
- 开始动作时立即刷新视角规则，不等待 0.2 秒周期刷新；已有视角切换入口也会立即处理这套手臂。
- 保持翻越手臂的世界渲染空间；即便当前装备手枪，也不应用手枪专用的第一人称深度缩放。
- 普通武器临时隐藏、法杖独立组件隐藏及各自原状态恢复沿用既有逻辑。

本次检查范围为代码可见性路径和动作素材。未启动游戏、PIE、截图或进行视觉验收。

## 现成全身动作

优先来源：[Epic Game Animation Sample](https://www.fab.com/listings/880e319a-a59e-4ed2-b268-b32dac7fa016)。[官方说明](https://dev.epicgames.com/documentation/en-us/unreal-engine/game-animation-sample-project-in-unreal-engine)包含完整人形翻越／登上墙沿动作，并支持迁移动画及重定向角色。

当前文件读取确认：原工程 `D:/FPS3D/游戏动画示例` 中下列三个 `.uasset` 均在，项目 `SourceAssets/GASPTraversal20260910/Reference` 也已有对应完整人形 FBX。以下时长来自随本地导出保存的 `official_sample_inventory.json`，本轮未重新运行 UE 资产求值。

| 用途 | 原动画 | 原时长 | 适配注意 |
| --- | --- | --- | --- |
| 低墙翻越 | `M_Neutral_Traversal_Vault_1_0_stand_F_Lfoot` | 2.567 秒 | 撑手、身体前倾、收腿越墙；原片后段有下降，不能全段照搬到平地落脚。 |
| 低台攀上 | `M_Neutral_Traversal_Mantle_1_0_stand_F_Lfoot` | 2 秒 | 提腿、抬髋并站起；需要对应实际台高和手掌落点。 |
| 高处攀上 | `M_Neutral_Traversal_Climb_Start_2_5_stand_F_Lfoot` | 3.333 秒 | 抓沿、拉身、上台；源动作标称 2.5 米，不能据此改变游戏现有攀爬高度上限。 |

这些是 UEFN Mannequin 全身原动画。本轮读取已有 `Reference/official_motion_reference.jpg`，可见翻越的前倾收腿以及低台动作的提膝、起身；没有新增渲染，也不将源人形画面视为 Jason 验收。现有 `/Game/Movement/Traversal/Native` 资产是此前为第一人称手臂改制的版本，不能直接当作 Jason 第三人称成品。当前第三人称仍使用 `FPSPlayerBodyAnimInstance.cpp` 中的程序抬腿和手部接触解算，本次没有把发现的候选标为已接入。

建议制作路线：从完整源动作重定向到当前 Jason，保留躯干／髋部／腿部发力；只在支撑窗口将手掌适配到执行器已批准的墙沿点，松手后退出接触；原根运动转换为身体表现，避免和现有胶囊移动重复叠加。接触、松手、取消及落脚使用现有执行器时钟。

另有项目已导入的 CC0 `A_UAL2_Armature_ClimbUp_1m` 可作低台动作备选，但没有覆盖本任务全部三类动作，优先级低于已具备完整源文件的 Epic 方案。素材来源及复用边界沿用 `Docs/gasp-traversal-20260910.md`；不公开再分发 Epic 源素材。

## 交付状态

可见性修正源码已落盘。首次后台 Editor 构建受怪物模块编译错误阻塞，记录于 `Saved/BuildEditor/build-20261007-152415.log`；本次未改动该怪物模块。

用户关闭 UE 后，于 2026-10-07 16:13 再次执行 `Tools/Build/Build-Editor.ps1`，`FPSGAMEEditor Win64 Development` 构建成功，日志为 `Saved/BuildEditor/build-20261007-161310.log`（`Result: Succeeded`）。UBT 报告 `Target is up to date`，说明现有磁盘构建产物已包含当前源码，无需再次编译或链接。未启动或关闭任何编辑器，未发送跨任务消息，未运行游戏测试。

动作候选已找到并核对本地源文件，尚未制作新的 Jason 第三人称翻越／攀爬动画资产。实际画面效果由用户测试。

## 收尾复查与发布范围

用户明确要求复查、整理、沉淀技能并推送后，沿以下路径做源码复查，未发现本次隐藏修正的新遗漏：

- `TryStart` 在手臂进入显示窗口前调用 `RefreshViewMode`；失败入口不显示手臂。
- 开发面板的视角切换／关闭调参入口立即刷新，周期刷新继续兜住当前 owner 状态。
- `UpdateOwnerVisibility` 同时处理相机子树与独立世界手臂子树，不修改动作的可见窗口。
- `Finish`（含 `Cancel`）关闭专用手臂并恢复原武器隐藏状态；仅刷新视角不会重新开启已结束的手臂。
- 模块化衣物创建时继承源 owner 标志，每帧跟随时继续保留；世界手臂保持普通渲染空间，不受手枪深度压缩影响。
- 手臂骨骼求值继续服务现有攀爬镜头；本次未因隐藏而停止相机所依赖的姿态更新。

这次复查没有新增原生代码改动，不重新启动编辑器或游戏；16:13 的构建成功是此前本机完整工作区的结果，不作为公开源码快照或画面验收。

本轮无退役文件，归档数量为 0。有效 Epic 原动作、现有第一人称派生资产和构建失败证据继续保留；不按日期或“候选”字样将它们移入 trash。

仅发布三份源码中的本次可见性修改、本记录，以及 `ue5-fps-arms-animation` 的入口与 `references/traversal-contact.md` 更新。共享角色文件按语义片段暂存，死亡／进食等未发布改动保留在本机；公开快照沿用原先已有的隐藏条件。本轮不发布 Content、FBX、Blend、密集姿态数据、构建二进制、日志或 Epic 素材。个人技能与项目技能同步本次条目，保留双方其他差异。

按 `WORKFLOW.md` 第 8 节核对授权远端 `https://github.com/allang2208/3D-FPS.git` 与默认分支 `main`，发布前检查全部待推提交。六文件暂存范围、完整差异、空白错误、大小及新增文本敏感信息检查完成；两份手臂技能通过 `quick_validate.py`，本次新增条目同步一致。检查回执保存在本机 `Saved/TraversalVisibilityReview20261007`，不随源码发布。
