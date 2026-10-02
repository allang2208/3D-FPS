# 手臂动作与撞门整理发布（2026-10-02）

按本对话授权整理和发布原创源码、作者配方及经验。撞门当前 V10 revision `2026100212` 保留 0.25 秒护拳，整臂摆动后直接恢复，总长 0.507 秒；ASH-12 使用完整作者链消除原厂持握偏置，弓的入场与实时恢复移除重复参考旋转补偿。法杖、空手与现有枪械动作的具体合同以各专项文档及运行源码为准。后续检视、空手挥拳和材质等增量见 [本轮整理发布](weapon-arms-publication-20261003.md)。

## 归档与保留

已否定的初版推搡、旧拳形、0.5 秒护拳后前推、旧外网音效移入 `trash/fps-arms-door-20261002/`。逐文件原路径、目标、大小和 SHA-256 见 [归档清单](../../SourceAssets/FPSArmsPublication20261002/archive-manifest.json)。`trash` 留在本机，不进入公开仓库。

现版仍读取的 V8 `authored-guard.json`、其 `BeforeAuthored/full-pose.json` 上游输入、腕掌权重制作源、V9 材质配方、当前用户 MP3 和各修复回退快照继续保留。不能按版本号或“Before”目录名清空重制作输入。归档脚本只作历史恢复，不直接执行。

## 完整工程恢复

1. 先恢复合法的 BarePalmV7 原生网格、Skeleton、动画和服饰 profile，以及 M4、M16、ASH-12、HK416、201、法杖与弓的既有生产资产。实际路径由正式运行资产头及各专项文档定义。
2. 法杖制作保留 `StaffQuickCombat20261001`、`StaffQuickCombatFix20261001` 与 `ApprenticeStaff20260927` 中当前积蓄／释放作者输入；空手依赖 `UnarmedIdle20261001` 与 `UnarmedLocomotion20261001` 的合法 native/pose 数据。公开脚本不会替代这些本机依赖。
3. 恢复 `HK416ReloadGrip20261001` 的实际动画与握把差量、201 原生托握修订、`M16SprintDoorWrist20261002` 的当前网格与奔跑资产；之后恢复撞门 V8 的腕掌权重改动及 V9 的 M16 材质派生。保留当前原生绑定、UV 和装备身份。
4. 还原 `DoorPush20261002/GuardWristThumbV8_20261002/authored-guard.json` 后，以当前 `author_motion.py` 生成公共动作与本机 `DoorPushAuthored20261002.h`；`save_editable.py` 依赖本机 `ModularOutfit20260925/BarePalmV7/Editable/M4_BareArmsV7.blend`。同样用本轮法杖和空手作者入口恢复它们的生成头；既有 Staff LeftGaitV16／PrimaryV28 继续按已公开配方恢复。密集姿态表保留本机，不作为公开 C++ 数据发布，不需要新 AnimSequence。
5. 从用户合法本地源 `D:/FPS3D/资产/音效/撞门.mp3` 运行 `UserAudio20261002/prepare_audio.ps1`，保留完整 0.672 秒、48 kHz、16-bit 双声道，再导入保存同一路径 SoundWave。没有公开原始音频，不能套用已归档候选的 CC0 声明。资源在 BeginPlay 预加载，0.31 秒成功开门时播放。

公开清单见 [发布文件](../../SourceAssets/FPSArmsPublication20261002/published-files.json)，交付边界见 [运行接入说明](../../SourceAssets/FPSArmsPublication20261002/runtime-handoff.json)。完整原生 JSON、密集骨架姿态头、网格、皮肤贴图、Blend、音频、UE 包、DLL、日志和运输回执留在本机；公开源码需要先恢复生成表及内容依赖，不能直接视为完整可开箱运行的工程备份。

## Git 与状态边界

遵循根 `WORKFLOW.md` 第 4、5、7、8 节：fetch 及核对授权远端，审查全部待推提交和精确发布清单，检查暂存差异、大小、敏感信息及资源许可，再普通推送 `HEAD:main`。共享文件仅取本对话语义片段，保留其他任务的未提交修改和原暂存内容。

Game／Editor 构建与资产保存是此前制作的结果；本次只做用户要求的仓库整理和推送检查，没有追加构建、游戏测试、试听、渲染或 UE 启动。发布审查与用户实机验收分别记录，视觉和手感由用户测试。
