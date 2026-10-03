# 第三人称双手持剑与手部接触（2026-10-03）

## 复用样板

用户指出剑类第三人称看起来仍为单手持剑，要求查找双手样板并直接复用。本次读取本机素材库、项目动画和技能的双手近战／改造握把约定，使用现有已接入的双手剑样板：

- `/Game/Weapons/AzureRunesword20260913/A_RuneSword_*` 的 Idle、Walk、Slash1、Slash2、Thrust、Overhead、HeavyCharge、HeavyRelease、Guard。
- `/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_*` 对应长柄版本；运行时继续通过现有 `DA_Sword_LongGrip` 差量使用该握距。

只读采样包括手腕、前臂、手指和武器根骨，每段取 9 个时刻。标准待机双腕间距约 17.62 cm，长柄约 18.70 cm；它们的双手握距与动作配合确实已存在。Guard 源动作包含左手移到剑身的意图，不能一律锁在柄尾。

`/Game/Characters/JasonPlayer20261003/Grip/A_Jason_SwordGrip` 是手指握姿片段，手腕仍处于参考展开姿势；它不能单独当作整身双手持剑样板。完整手腕运动继续从上述双手剑源动作读取。

资料脚本：`Tools/PlayerBody/read_two_hand_sword.py`；采样文件：`SourceAssets/ThirdPersonTwoHandSword20261003/sources.json`。本轮读取时没有正在运行的游戏角色，因此没有用户现场逐帧运行数据，也没有为此启动游戏。

## 首轮握点可达性分析

第三人称已在读取双手运动和手指，但以前把右手重定位到 `(-18,43,111)*PoseScale` 的腰部偏远位置，随后分别对两只手做不伸长骨段的 IK。以 Jason 参考骨架及标准 Idle 样板计算，右手目标距肩约 53.4 cm、左手约 61.9 cm，而单臂总长约 51.4 cm。左手在进入挥砍之前已经不可达；解算器各自限制手腕位置后，持剑右手与左手接触会分离。

这说明只传入双手动画或把手指握紧，并不能保证最终双手落在同一把剑上。

## 修改

1. 剑类待机握持中心改为较高、较近的 `(-10,32,134-40*Crouch)*PoseScale`；实际源轨迹和备用第三人称姿态使用同一入口 `FPSBodyPoses::SwordReady`。工具保持原有持握位置。
2. 保留双手剑样板中的左右腕相对变换、长柄差量和手指姿态；仍从真实动作时钟读取挥砍、突刺与回位，没有重新制作另一套攻击时序。
3. 在两只手过渡完成后，以当前人物肩部和原生大小臂长度同时约束整组握持。求可达区域内距离目标最近的共同平移，双手与武器一起移动；不分别拉开双手，不缩放骨段或握距，保留肘部余量。
4. 左手继续由右手实际解算结果和源相对握姿导出，武器随右手移动，手指沿用原生掌面配准。施法、消耗品与翻越占手时不强制启用剑的双手耦合。

这是既有双手剑动作的第三人称接触适配，没有改变已采用的第一人称动作、伤害、攻击窗、移动或联网消息格式。远端第三人称同样使用现有源动作快照及这套接触求解。

## 唐刀现场追加排查

用户反馈前述适配后仍为单手持剑，因此前述构建成功不代表问题已解决。现场只读采样确认装备为 `ue_tang_dao`、`Family=Melee`、`Action=None`、`ActionVariant=Idle`，双持与副手枪均为关闭。第一人称唐刀复用的双手源姿态正常，但全身最终两腕间距约 50 cm，双臂下垂，说明还存在全身姿态应用问题。

临时在当前角色关闭后处理并恢复后，双手仍下垂（`postprocess-isolation.json`，原始与恢复后的 `disable_post_process_blueprint` 都是 false）。保留原有 MetaHuman 后处理。

### 已定位的根因与修复

用同一 `UFPSPlayerBodyAnimInstance`、唐刀的 Frost 手臂及 Idle 源姿态在无游戏的临时世界中复现。输入 `Melee`、左右腕掩码 3、双手耦合与骨骼有效性均正确，IK 也确实到达目标。问题发生在其后的胸部反应与最终输出：`LocalBlendCSBoneTransforms` 把已求解子骨转换回局部空间，而 UE 5.8 `BonePose.h` 中的 `ConvertComponentPosesToLocalPosesSafe` 只写仍标记为组件空间的骨骼，不复制那些已改为局部空间的结果。`Out.Pose` 因而保留了原始待机手臂，覆盖了刚求解的双手。

修复为安全转换前执行 `Out.Pose=Pose.GetPose()`，先保存完整混合空间缓冲，再转换剩余组件空间骨骼。原有双手源姿态、指节、握距、受击层、后处理与玩法时钟继续使用。临时日志已撤除：读取组件空间会改变缓存标记，曾让带日志的帧看似正确，因此修复复现使用不读取中间姿态的正式代码。

### 本轮定点复现结果

`fps.body.DiagnoseSwordPose` 是仅 Editor 构建提供、显式调用的诊断入口；在临时预览世界求值 20 帧，不启动玩法，不保存资产。调用脚本 `Tools/PlayerBody/run_sword_pose_diagnosis.py`。修复前 `baseline-headless-pose.json`：最终双腕间距 45.779 cm，右手落在 `(-21.837,-0.651,87.815)`、左手 `(20.133,17.627,88.224)`。修复后 `headless-pose.json`：最终右手 `(-9.066,30.400,128.479)`、左手 `(4.718,26.690,118.814)`，与输入握点一致；双腕间距 17.239 cm。

本轮按用户要求排查并复现了唐刀待机接触；没有进行截图、视觉验收或其他武器／动作的全套回归。关闭前的编辑器会话热更新成功（`livecoding-pose-fix-response.json`），`FPSGAME Win64 Development` 常规构建成功（`build-fix-game.txt`）。用户保存并关闭编辑器后，首次最终 `FPSGAMEEditor` 常规构建在 UHT 阶段被并行新增的怪物模块阻塞：`Source/FPSGAME/Monsters/HangingBellM09.h:77` 的反射函数 `BuildPhysics(USkeletalMesh* Mesh,...)` 参数 `Mesh` 与父类 `ACharacter` 成员重名，构建退出码 6（`build-fix-editor.txt`）。其实现文件在该次构建之后仍有新增写入，按并行文件冲突规则保留现场，没有修改该模块，也没有重开编辑器。该次未能更新基础 Editor DLL；后续常规构建完成情况见下节。

### 用户再次关闭 UE 后续接构建

再次继续时，前述 `HangingBellM09` 参数已改为 `InMesh`，原 UHT 参数重名阻塞已解除。前台编辑器已关闭，但仍有 `UnrealEditor-Cmd` 在后台导入资产，并出现其他 Game 构建；按构建串行与 DLL 占用规则等待其结束，没有停止这些进程，也没有联系其他任务。

占用释放后，`FPSGAMEEditor Win64 Development -NoHotReload -NoHotReloadFromIDE` 常规构建成功，17 个构建步骤完成，用时 17.84 秒，退出码 0。基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已链接落盘，本次唐刀修复不再依赖已关闭会话中的 Live Coding 补丁。完整日志为 `SourceAssets/ThirdPersonTwoHandSword20261003/build-fix-editor-resume.txt`。本次续接仅完成构建与记录，没有启动编辑器或游戏，没有追加运行测试或视觉验收，最终观感由用户测试。

## 原轮构建记录

源码、资料和说明已保存，`FPSGAME Win64 Development` 与 `FPSGAMEEditor Win64 Development` 均已常规构建成功，游戏程序和编辑器 DLL 已落盘。日志分别为 `SourceAssets/ThirdPersonTwoHandSword20261003/build-game.txt` 和 `build-editor.txt`。原有动画资产直接复用，无新增导入资产。没有启动编辑器、游戏、PIE、截图、渲染或运行验收，最终握持与动作观感由用户测试。
