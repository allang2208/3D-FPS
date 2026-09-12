# 翻越与攀爬审计修复（2026-09-11）

接续 [审计记录](traversal-system-audit-20260911.md) 的五项问题。当前直接修改 UE5 宿主源码；点按空格、空中保持/重新按键接墙、按镜头选墙及两倍翻越速度保留。没有修改动画源文件、模型或地图资产。

## 修复后的行为

1. 支撑组件被关闭查询碰撞、改为不阻挡 Pawn、注销或销毁时，立即取消动作并恢复下落。原有静止、非物理模拟、组件变换检查继续有效。完成时重新检查可行走地面、双向阻挡、地面间隙和实际胶囊净空；无支撑不能记录成功。
2. 恐惧效果的 `Apply` 显式取消攀爬，由恐惧组件接管逃跑。普通菜单输入锁允许当前动作完成；不会只因菜单打开强制摔落。两者的输入锁归属保持独立。
3. 中断立即恢复胶囊物理运动，镜头单独回归。真实身体位移随角色携带，恢复偏移使用 1800 cm/s² 加速及 450 cm/s 限速，期间持续避碰；恢复旋转也有速度限制。
4. 动作镜头和取消镜头共用胶囊碰撞 Profile 的 5 cm 球体扫掠。阻挡 Pawn、忽略 Visibility 的实体能挡住镜头，反向组合不会错误阻挡。
5. 探测器将左右墙沿接触点和法线直接传给手臂。移除手部层独立的法线 Z>0.65 条件；保留墙沿 Z>0.2、独立左右采样、落脚可行走及完整胶囊路线检查。手掌、手指和前臂的体积避碰与骨长约束保留。

同时移除一次重复的抬升路径 Sweep。没有降低空中检测频率或扩大距离、高度与净空门槛。

## 实现与测试入口

- `Source/FPSGAME/Movement/FPSTraversalComponent.*`：支撑有效性、共享双手接触数据。
- `FPSTraversalExecution.cpp`、`FPSTraversalCamera.cpp`：运行支撑复核、实际成功条件、取消镜头回归。
- `FPSTraversalArmsComponent.*`：复用探测器接触点，移除第二套门槛。
- `Source/FPSGAME/FPSGAMECharacter.cpp`：提供正常镜头目标和 DeltaSeconds。
- `Source/FPSGAME/Monsters/HandBrainFearComponent.cpp`：恐惧控制交接。
- `FPSTraversalBoundaryAudit.cpp`：真实组件/碰撞故障和恐惧 Apply 测试。
- Air/Surface/Village 测试的成功断言同时要求 `bLastTraversalSucceeded`、Walking 和落点；Surface 还要求双手建立锚点。地面及村庄夹具改为设置实际 Controller 视角。
- `Tools/SceneTests/run_traversal_acceptance.ps1`：新增 Boundary 模式、30/60/120 Hz 参数，以及明确的成功退出码。

## 已取得的验证证据

- Editor Development 构建成功：`Saved/TraversalFix20260911/Build5.log`，当前模块 `UnrealEditor-FPSGAME-9119105.dll`。此前 9119104 已验证全部玩法修复；9119105 追加真正旋转的斜台夹具与检查。
- `FixRules1.log/.json`：47 项规则、80 项真实碰撞世界断言通过，含可翻越陡楔形墙沿及其两只手的法线 Z≈0.5 接触数据。命令进程退出 1，来自已有 GameFeatureData 配置错误；不记作干净启动。
- `FixBoundary60_2`、`FixBoundary30_1`、`FixBoundary120_1`：每次 7 组边界全部通过，退出 0。覆盖关闭碰撞、忽略 Pawn、注销组件、真实恐惧 Apply、菜单输入锁、销毁支撑及即将完成时撤掉落地地面。镜头通道的两个方向另有明确断言。
- 中断首帧的回归位移：30 Hz 为 2.000 cm，60 Hz 为 0.500 cm，120 Hz 为 0.125 cm。各次扣除身体位移后的回归速度上限实测 450 cm/s，并能结束回归；这组数据来自相同地面高墙夹具。
- `FixAir1`：11 组空中实际输入用例通过，退出 0，包含侧向起跳转镜头、离墙运动、下降接墙、释放/重按空格、上方阻挡及支撑销毁。
- `FixSurface2`：6 组地面动作通过，退出 0。真实 ±6° 斜台的双手接触高度相差大于 5 cm，骨长误差小于 0.05 cm；0.4 s 翻越、1.4/2.55 s 攀爬、武器和弹药、恢复移动均通过。旧夹具先设为 Static 再旋转，在运行时被 UE 拒绝；现改为允许旋转的静止 Movable 并断言真实角度。`FixSurface1` 仅作为此前平面回归保留，不能作为斜台证据。
- `FixVillage1`：在真实 Normandy 村庄地图中找到并执行两处现有合格石墙，点按进入、完成后的有效支撑、弹药及移动恢复全部通过，退出 0；不是遍历整张地图所有模型的保证。

已查看真实渲染帧：村庄 `FixVillage1/case_1_frame_0004.png`（双手接触破损墙沿）和 `0006`（翻过墙后）；斜台 `FixSurface2/case_2_frame_0039.png`（左右抓点）；恐惧取消 `FixBoundary60_2/case_3_frame_0000.png` 和 `0008`（恢复持枪/下落）。文件夹名称实际带上述统一 Profile 前缀。

## 与修复前同一故障序列的直接比较

复用原审计观察脚本，仅更换输出目录与独立存档。当前证据是 `Saved/TraversalFix20260911/boundary_observer.py`、`boundary_observer.json`、`BoundaryObserverFix1.log`；原证据保留于 `Saved/TraversalReview20260911/`。

- 关闭支撑碰撞：仍在 t=6.466667 s 注入，修复后 t=6.483334 s 即取消、恢复 Falling、日志 success=0；修复前继续到 t=7.7333 s 并误报 success=1。
- 仅禁用菜单移动输入：继续完成且以 Walking 结束，符合本次明确的菜单策略；真实恐惧打断另由 Boundary 的实际 Apply 用例验证。
- 空中下降抓墙后销毁支撑：取消前角色仍为 `(60054, 10000, 10277.620)`，镜头仍为 `(60129.4318, 9996.9753, 10237.5180)`，与旧复现一致。16.67 ms 后角色位置不变，镜头位移从原 **35.46 cm** 降为 **0.50000006 cm**，恢复 Falling。

这段观察会故意破坏 AirAudit 的正常完成预期，不计入普通运行全通过统计；它用于同条件的修复前后对比。持续回归是否收敛、速度和多帧率边界由正常 Boundary 模式验证。

运行日志和 JSON 均在 `Saved/TraversalTapVillage20260911/`。渲染帧位于 `Saved/TraversalRuntimeAudit/ColdSteel_TraversalRuntimeAudit_<RunId>/`。

首轮 `FixBoundary60_1` 的末帧地面夹具过早将角色直接瞬移到墙后，额外制造了穿过墙体的镜头路径。后续将注入时机改为实际执行末段，并保留原失败日志；其他六组在首轮已通过。

本轮独立存档/临时世界验证不修改用户存档或地图。共享源码构建、Standalone/PIE 验证不等同于独立发布快照、打包或联网验收。已经打开且加载旧 DLL 的编辑器需要重启后才能使用新版原生逻辑。
