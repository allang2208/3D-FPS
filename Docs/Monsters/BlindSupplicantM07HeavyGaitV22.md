# M-07 V22：沉重慢步与全身承重联动

日期：2026-10-03。工程：`D:/FPS3D/FPSGAME`。

后续用户反馈：腿脚动作基本没有问题，手部僵硬且掌心向外。[V23 内向掌心与随步摆臂](BlindSupplicantM07InwardArmSwingV23.md) 直接复制本版腿脚、骨盆、胸背及背膜曲线，只重制锁骨与臂掌，并已保存到现有 AI／F6 引用。本篇保留 V22 当时制作记录，用户的局部认可不覆盖本版手部。

用户表示此前动画仍不符合预期，要求重新开发，先从类似巨人／机器人缓慢移动、各关节协调和全身联动的移动动画开始。本轮完成两段新移动动画的 Blender 制作源、FBX 导出、UE 动画资产导入和现有 AI／F6 蓝图引用保存。未启动交互 UE、游戏、PIE、截图、验收渲染或测试；当前是待用户体验的制作候选，不宣称动作已达标。

## 动作编排

这次从原绑定重新编排沉重步态，不使用 V21 的慢跑运动曲线。慢走与追击都保留支撑时间和重量感，追击使用同一动作家族中更大的步幅与稍快的节奏。

| 项目 | 慢走 SlowWalk | 沉重追击 Chase |
| --- | --- | --- |
| 完整左右步周期 | 3.2 秒 | 2.4 秒 |
| 导出帧数／采样率 | 97 帧／30 fps | 73 帧／30 fps |
| 制作源／游戏速度 | 42／42 cm/s | 86／86 cm/s |
| 每步前进距离 | 67.2 cm | 103.2 cm |
| 每只脚支撑比例 | 68% | 68% |
| 全周期双脚支撑比例 | 36% | 36% |
| 摆脚基础抬升 | 11 cm | 15 cm |

这些数值是制作与接入参数，不是实机测量。使用原地动画，Actor 位移继续交由已有导航；满速预期播放倍率为 1。源速度保留超过 40 cm/s 的差距，与当前移动选择器的 ±20 cm/s 切换迟滞相容。

1. 左右脚分别在相位 0／0.5 脚跟接触，足底缓慢压实，再由脚跟抬起、前脚掌支撑和脚趾推离。支撑段向后的局部速度与导航前进速度配套，支撑脚保持固定横向通道。摆腿经过身下，下一次接触前减速下放，没有双脚同时腾空的制作相位。
2. 骨盆先向承重侧转移，落脚之后压低、缓慢恢复。脚仍在地面时由髋、膝、踝共同求解，使用 V17 实际解剖骨段与同一有符号膝铰链。够脚距离由平滑骨盆高度包络处理，容器根保持固定；不缩放腿骨、不移动容器根补偿接地。
3. 骨盆与胸廓反向转动，五段脊柱共同分担倾斜和扭转。胸肩响应比骨盆晚约 0.085–0.10 秒，头颈减小随身体的摆动，保持向行进方向的姿态。
4. 锁骨与肩胛先带动长臂，上臂相对腿部反向摆动；肘保留约 27–40° 屈曲，前臂和腕部再滞后。肩、肘、前臂、腕共同决定手掌姿态；前臂轴向旋转有界，不为局部掌面朝向拉直肘部。保留五指分别轻曲的结构。
5. 鳃膜真实连接根随胸背，自由骨段按同一次承重响应稍晚回落。当前近距布料与有限骨骼避让继续工作，本次没有增加运行时 IK、Tick、刚体、布料顶点或求解迭代。

这些是实际制作方法。未查看本轮运行画面，不能由方程、导出或保存成功推断所有关节在引擎中均自然、所有接触均无滑动／穿模。

## 原资产与接入范围

保留当前原 Meshy 几何、UV、材质、V11 的 83 骨参考、V16 手臂与 V17 腿部蒙皮、V18 显示模型及背膜代理。只新增并切换慢走与追击；其余待机、攻击、施法、死亡与技能时序保持当前引用，后续动作仍待用户指定开发。

新 UE 资产位于 `/Game/Monsters/BlindSupplicantM07/AnimationsHeavyGaitV22/`：

- `A_M07_SlowWalk`
- `A_M07_Chase`

现有 `/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07` 已保存：`slow_walk_clip` 指向新慢走，`chase_clip` 和兼容 `walk_clip` 指向新追击；`source_walk_speed`／`walk_speed` 同为 42，`source_chase_speed`／`chase_speed` 同为 86。F6 继续通过原「怪物生成 → 盲祷者 M-07」入口生成，无需另增菜单项。

未修改原生 C++，无需本轮原生模块构建。原生类的历史默认引用未改，本轮正式接入位于现有游戏／F6 使用的角色蓝图。V21 资产仍保留；修改前蓝图副本位于 `SourceAssets/BlindSupplicantM07Meshy20261001/HeavyGaitV22/Before/BP_BlindSupplicantM07.uasset`。

## 制作源与保存记录

- 动作制作：`Tools/BlindSupplicantM07/author_heavy_gait_v22.py`
- UE 导入及引用保存：`Tools/BlindSupplicantM07/import_heavy_gait_v22.py`
- 后台导入入口：`Tools/BlindSupplicantM07/run_import_background.ps1 -TaskScript D:/FPS3D/FPSGAME/Tools/BlindSupplicantM07/import_heavy_gait_v22.py`
- 可编辑源：`SourceAssets/BlindSupplicantM07Meshy20261001/HeavyGaitV22/Motion/M07_Original_HeavyGait_V22.blend`
- 同目录 FBX：`A_M07_SlowWalk.fbx`、`A_M07_Chase.fbx`
- 制作清单：同目录 `heavy_gait_manifest_v22.json`；逐帧制作参数在 `authored_*_production_record_v22.json`，不是测试报告。
- 实际保存回执：`SourceAssets/BlindSupplicantM07Meshy20261001/HeavyGaitV22/ue_heavy_gait_delivery_v22.json`，本次 `saved=true`，包含两段动画和原蓝图的保存路径、之前引用和新速度。
- Blender 制作日志：`Saved/Logs/M07-HeavyGaitV22-Author.log`
- UE 后台落盘日志：`Saved/Logs/M07Import-20261003-104907.log`

本次沿用后台方式。导入入口等待已有工程后台进程自然结束后执行，没有启动交互编辑器或跨对话发送协调消息。未测试，交由用户在 F6 重新生成盲祷者体验。
