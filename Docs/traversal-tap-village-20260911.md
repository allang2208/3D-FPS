# 空格点按、翻越双倍速度与村庄适配（2026-09-11）

## 修改后的行为

- 玩家在地面且状态允许时，空格按下直接尝试翻越/攀爬；同帧松键也有效。合格动作只消费一次跳跃，松键不取消、不补跳。无合格目标/动画缺失则走原跳跃与滑铲跳跃缓冲。
- `VaultPlaybackRate=2`：翻越源动作仍为 0.8 s，执行为 0.4 s。Contact/Release 源时间 0.27/0.58 s 对应 0.135/0.29 s。位移、手臂、镜头和恢复共用加速后的源时间。低平台/高攀爬仍为 1.4/2.55 s；未改 Blend、FBX、网格、蒙皮或手型。
- 高度范围仍是大于 50 至 200 cm，翻越上限 120 cm，距离 20 cm、朝向偏角 40 度。全部地图复用角色组件，不需要给每个障碍额外挂脚本。

## 村庄失败原因与修正

用户实际日志已记录进入 `L_Normandy_FPS_Test`、使用 FPSGAMEGameMode，并输出 TRAVERSAL_INPUT_REJECT，因此系统已经接入。`Saved/TraversalTapVillage20260911/UserBefore.log` 保留了本轮修改前证据：多次正对墙面（FacingDot 0.939–1.000）仍被 MovingOrObliqueWall 拒绝。

真实游戏扫描确认村庄原有部分石墙运行时 Mobility=Movable；旧代码只接受 Static。现在允许当前静止、未模拟物理且阻挡人物的组件；人物不作为支撑。动作期间检测前墙及顶部/落点支撑的销毁、变换变化、速度和物理模拟状态。

仅放开 Mobility 仍不够：第一轮真实村庄扫描 0 个合格目标，主要因破损墙沿被 NarrowOrBrokenEdge 拒绝。修正为中心与左右手各自在前缘向内 2/8/16/24/32 cm 搜索墙沿，左右手约 ±28 cm，允许有限高差。翻越只需要可抓墙沿，不要求狭窄墙沿能站人；爬台顶部仍需可行走支撑。

正面、顶板和相邻支撑允许来自不同组件。站立检查使用实际胶囊半径 42/半高 96 cm，圆形九点支撑及完整体积 Overlap；不再要求单一组件至少厚 100 cm，也不使用膨胀后的方形足迹。落点脚底留 2 cm，越沿留 3 cm。顶部/侧面挡住胶囊、无安全落点、实际运动物体仍拒绝。

破损模型的背面射线只提供厚度初估；在允许的 120 cm 深度内逐步尝试落点，每个候选完整检查支撑、净空、抬升—跨过—下降 Sweep。有限抬升不越过翻越高度上限。高薄墙顶部不能站人时仍不支持悬挂或骑墙。

## 本轮证据

- `Build3.log`：Editor 模块 `UnrealEditor-FPSGAME-9112303.dll` 编译成功，下面的首轮运行使用此模块。
- `Rules2.log`：40 项规则 + 62 项真实碰撞场景，全部通过。包含静止 Movable、真实运动/物理物件拒绝、分离顶板、90 cm 平台、196 cm 净空通过、190 cm 净空拒绝、偏离中心的侧梁阻挡及旧斜向/凸面回归。Commandlet 本体返回 0；日志仍有项目既有 GameFeatureData 配置错误，不将该次进程标成干净退出。
- `VillageRuntime1.log`：只放开 Mobility 后仍找到 0 个候选（失败定位证据，不是通过记录）。
- `VillageRuntime2.log`：在用户历史位置扫描现有村庄模型，并对两处不同石墙执行真实 PlayerController 空格按下+同帧松开，2 组 0 失败。包含 Static 的 Mossy 石墙及运行时 Movable 的 PieceD 石墙；动作完成、可用落点、弹药与移动恢复均通过。未新增测试墙或更改地图资产。
- `SurfaceRuntime1.log`：6 组运行检查，0 失败；翻越、低台、1.8/2 m 高攀爬、障碍销毁、两武器恢复、镜头约束、骨长与表面修正和移动接续。已检查村庄双手抓墙及退出帧。
- `TapCourseFinal.json`：初始地图 4 种原有障碍真实空格点按，0 失败，进程退出 0。

预览：`Saved/TraversalRuntimeAudit/ColdSteel_TraversalRuntimeAudit_VillageTap2/village_tap.gif`，来自实际游戏帧，按 60 Hz 模拟采样间隔制作；不是性能测量。原始 PNG 与各动作旧作者文件均保留。

当前工具：`Tools/SceneTests/run_traversal_acceptance.ps1 -Mode Rules|Surface|Course|Village|Air|Boundary -RunId <唯一名称> -Hz 30|60|120`；用独立存档记录结果与进程退出码。早期 `inspect_village_traversal.py` 仅作编辑器初步诊断，已由真实 VillageAudit 替代并移入 `trash/traversal-publication-20260912/Tools/SceneTests/`。历史 Slide 检查依赖独立滑铲战斗任务，现由该任务的验收入口维护。

## 范围

这是通用碰撞判定修正，实机检查覆盖上述两处原有石墙；不宣称村庄全部模型或任意凹面都经过视觉验收。高薄墙无站立顶面、头顶不够高、动态平台、超过 2 m 的目标不在本轮支持范围。单机执行器不扩展联机。打开的旧编辑器需保存后重启加载新原生模块。

## 最终收尾验证

- `Build5.log`：当前完整宿主 Editor 模块 `UnrealEditor-FPSGAME-9112305.dll` 构建成功（包含最后的 UI 禁止移动入口检查）。中间 Build4 的错误来自并行怪物模块改动；没有回退或修补他人的代码，待其更新后重试通过。
- `TapSurfaceFinal.json`：最终模块运行 6 组检查，0 失败、进程退出 0，额外核对实际模拟耗时符合 0.4/1.4/2.55 s，并复核弹药、武器、镜头、骨长和移动接续。
- `TraversalSlideFinal.json`：滑铲中射击、ADS、换弹及滑铲跳跃回归通过，进程退出 0。
- 相关 diff 空白检查、作者诊断脚本语法、PowerShell 运行器语法及个人/工程攀爬技能镜像一致性检查通过。
