# 左拳冲刺撞门接入（2026-10-02）

持续按住 Shift 向前冲刺、正对需要交互打开的关闭门时，左手从当前握姿释放，握拳举起护在身前，完整保持 0.25 秒，然后直接回到当前装备或空手的实时动作。保持结束时打开门，同时播放单次撞门声和短促镜头抖动。沿用原有门的开启方向、碰撞和自动关闭逻辑。

## 当前保持时长调整

按用户要求，revision `2026100212` 将护拳停顿由 0.30 秒缩短为 0.25 秒。起势仍为 0.06 秒，开门／音效／抖动共用时点改为 0.31 秒；恢复仍为 0.197 秒，总长为 0.507 秒。保持段轻摆关键帧按比例压缩，拳形、手臂轨迹及轻摆振幅沿用现有版本。作者脚本、姿态 JSON、运行头和可编辑 Blend 同步；无需重新导入音效或 AnimSequence。构建状态见 `SourceAssets/DoorPush20261002/integration-completion.json`，未运行游戏测试。

本轮正式 Editor 和 Game 后台链接已完成，日志分别为 `Saved/BuildEditor/build-20261002-234440.log` 与 `Saved/DoorPushHold250ms20261002/FPSGAME-20261002-234533.log`。未启动 UE 或进行游戏测试。

下方版本记录保留各轮原始时长，本轮覆盖其中 0.30 秒保持的设置。

## V10 全武器接入（保持时长修订前记录）

V10 初次交付反馈：屏幕抖动各轴幅度提高 60%，左臂护拳晃动幅度翻倍，保持当前完整拳形与 0.30 秒护拳停留。枪械、双持、剑、法杖、斧镐和空手继续共用同一动作层；补齐弓的同帧收放／恢复及无手臂工具的 V7 备用左臂。详见 [当前反馈与武器接入](door-push-feedback-all-weapons-v10-20261002.md)，实际制作与构建状态以本轮 completion 回执为准，未实机测试。

## M16 自然腕部修订（原始制作记录）

M16 腕部已改用共同 M4 V7 的自然 mesh-local 绑定，受影响表面重新制作，并同步导入完整 M4 奔跑左链与握把差量。上一版分数 twist 特例已撤掉；拳形、整臂轻摆与 0.30 秒保持时钟沿用。详见 [M16 奔跑左臂与撞门腕部修订](../Weapons/m16-sprint-door-wrist-20261002.md)。已保存资产与正常构建记录位于 `SourceAssets/M16SprintDoorWrist20261002/integration-completion.json`。

## GuardWristSwayV6：M16 腕部绑定与护拳轻摆（上一版，部分旋转补偿被否定）

用户确认腕部变细与拉伸发生在 M16 撞门动作。源 M4 护拳的手腕与四根辅助骨局部旋转保持原值，scale 为 1，骨长未变；M16 原生手腕的绑定局部旋转与该母版相差约 80.162°，四根辅助骨的局部绑定则基本相同。直接复用整链姿态会让相邻腕部皮肤受到不同的旋转形变。

本轮保留作者手腕、19 根掌骨／指骨、完整拳形与主臂轨迹。在 Capture 缓存时，为 M16 两根前臂辅助骨按其自身原生参考框架处理手腕相对前臂的轴向绑定差：先求 `ForearmDeform^-1 * HandDeform`，投影到原生前臂轴，只分配该相对扭转。随后统一回到目标参考框架，按父骨重建局部旋转。没有在已完整转向的前臂上再次叠加作者的累计 roll，不复制 donor 骨长或缩放，不改皮肤资产或持枪、换弹动作。

用户要求的排查记录位于 `GuardWristSwayV6_20261002`：`native-guard-source-diagnosis.json`、`m16-bind-diagnosis.json` 与 `m16-cuff-skin-diagnosis.json`。对保存的 M16 绑定及腕部 241 个混合权重样本作离线旋转分析，近腕辅助骨与手部的蒙皮旋转差由约 80.162° 降为 38.635°；混合旋转的最小奇异值由约 0.886 提高到 0.961。这是定位和制作依据，不是实机视觉验收。

护拳保持期间加入整条左链刚性轻摆，只有锁骨根平移；手腕、掌骨、指骨与其余子骨的局部姿态不单独抖动。

| 时间 | 侧向 Y 偏移 | 垂直 Z 偏移 |
| --- | --- | --- |
| 0.06 s | 0 cm | 0 cm |
| 0.135 s | +0.28 cm | +0.10 cm |
| 0.21 s | +0.04 cm | +0.20 cm |
| 0.285 s | −0.16 cm | +0.08 cm |
| 0.36 s | 0 cm | 0 cm |

轻摆两端归零，沿用举拳 0.06 s、保持 0.30 s、0.36 s 开门／声音／抖动、0.197 s 直接恢复，总长 0.557 s，无前推。源 revision 为 `2026100207`，7×27 姿态表及 1000 Hz、558 帧 Blend 已实际保存，take 为 `A_DoorPush_LeftFist_V7_20261002_GuardV6RigidSway300msRecover`。作者与运行备份位于 `GuardWristSwayV6_20261002/BeforeAuthored` 和 `BeforeRuntime`。

## GuardOnlyV5：护拳保持后直接恢复（上一版）

用户要求保留当前护拳的完整手型与腕臂关系，取消向前推出。本版复用 GuardPoseV4 的 Prepare 完整 27 骨姿态，保持期间拳、肩肘腕位置不变；没有前送、前压制动或短回弹。动作位置固定在作者相机坐标，删除随门距平移手臂的接触适配。

| 阶段 | 时间 | 动作 |
| --- | --- | --- |
| 实时进入 | 0.00 s | 捕获当前装备或空手的完整左链 |
| 护拳完成 | 0.06 s | 使用现有护拳姿态 |
| 保持结束／撞门事件 | 0.36 s | 完整保持 0.30 s，成功打开原目标门时播放声音与抖动 |
| 实时回接完成 | 0.557 s | 0.197 s 直接回接当帧持握／空手走跑动作 |

该版动作源 revision 为 `2026100206`，take 为 `A_DoorPush_LeftFist_V7_20261002_GuardV5Hold300msRecover`，1000 Hz、558 帧。作者备份位于 `GuardOnlyV5_20261002/BeforeAuthored`，运行源备份位于该目录的 `BeforeRuntime`。本节与下方 GuardPoseV4、FixV3 保留原始制作时长；当前采用文首 revision 2026100212 的 0.25 秒保持时序。

## 触发和门行为

接入对象是原生 `AColdSteelDoor`、继承它的病区玻璃门 `AWardGlassDoor`，以及 `AColdSteelDoubleDoor`。普通窗户、Fab 钥匙门和战斗封门 `DungeonRoomGate/EncounterGate` 不进入此动作。

本地单机第一人称角色在地面持续按住 Shift 并向前输入至少 0.21 秒，且正对关闭的门面时触发。沿用 E 交互的视点和第一处可见阻挡，保留可回收箭矢的交互优先级。最大视线探测距离为 210 cm，没有最小距离或接近速度要求；抵住门叶、实际速度为零时也能触发。

0.31 秒保持结束时仍保持 Shift 前进冲刺、门仍关闭、视线仍命中原目标，才执行一次 `OpenDoor()` 或双扇门的 `OpenWindow()`，不调用 Toggle 或造成伤害。保持阶段是拳姿停留，角色运动仍沿用既有逻辑；即使被关闭门叶挡停，只要仍持续按住 Shift 前进，此时仍可开门。短按 Shift 的闪避、原有动作占用与取消规则保持既有接入。

## GuardPoseV4：参考护拳与 0.50 秒停留（上一版）

本轮参考用户手部照片：前臂上举、肘部下沉、拳护在身前，掌侧及卷指面朝向玩家，四指收拢、拇指外扣，手腕自然衔接前臂。沿用项目现有 V7 握拳内在骨骼形态，只改护拳的锁骨、上臂及下臂局部姿态，保留 19 根指骨／掌骨、手腕及四根 twist 的 24 根原有局部变换；后续 Contact、ShortRebound 仍完整复用原 27 骨动作。作者肩点为 `(-9,-20.8,-23)`、肘点 `(17.581,-20.064,-31.009)`、腕点 `(23,-14,-5)` cm；腕在肘上方，护拳到 Contact 的前向行程为 22 cm。

| 阶段 | 时间 | 动作 |
| --- | --- | --- |
| 实时进入 | 0.00 s | 捕获当前装备或空手左链 |
| 护拳完成 | 0.06 s | 左拳举起护在身前 |
| 停留结束 | 0.56 s | 完整护拳保持 0.50 s |
| 门接触 | 0.62 s | 独立 0.06 s 加速强推，成功开门时触发镜头抖动 |
| 接触制动 | 0.638 s | 完整 Contact 左链继续前压 1 cm |
| 短回弹 | 0.663 s | 衔接现有回收 |
| 实时回接 | 0.86 s | 0.197 s 回接当帧持握／空手步频动作 |

该版运行备份位于 `SourceAssets/DoorPush20261002/GuardPoseV4_20261002/BeforeRuntime`，作者备份已归档到 `trash/fps-arms-door-20261002/SourceAssets/DoorPush20261002/GuardPoseV4_20261002/BeforeAuthored`。参考照片存于同目录的 `Reference/user-left-fist-guard.jpg`。历史 revision 为 `2026100205`，可编辑 take 为 `A_DoorPush_LeftFist_V7_20261002_GuardV4PhotoHold500ms`，保存 1000 Hz、861 帧 Blend 与生成的 C++ 作者表。M16 本地轴适配、整臂插值及回接保留，无需额外手型运行层或 AnimSequence 导入。本节与下节 FixV3 仅保留原始制作记录；当前采用文首 revision 2026100212 时序。

## FixV3：完整动作复用与冲击（上一版）

FixV2 只取了现有拳形的 19 根指骨／掌骨，肩肘腕仍在运行中重新 IK。完整作者表与腕朝向没有直接播放；所有区间使用五次 Ease，接触前速度降为零。接近门时单独移动接触腕点也会压缩前伸行程。入场和回收的肘插值只保留 flex/roll，会丢失当前握枪旋转的剩余分量。

本版直接复用 `SourceAssets/StaffQuickCombat20261001/full-pose.json` 中 Ready、Contact、ShortRebound 的完整 27 骨左链：锁骨、上臂、下臂、腕、掌骨、五指和 twist 辅助骨。手型与腕臂关系整体复用，包括 V7 拇指外扣姿态；不重新拟合卷指，不每帧按目标点解算左臂。

| 阶段 | 时间 | 动作 |
| --- | --- | --- |
| 实时进入 | 0.00 s | 捕获当前装备或空手左链 |
| Ready | 0.06 s | 现有完整蓄拳姿态，腕 X=1.5 cm |
| 停顿结束 | 0.26 s | Ready 完整保持 0.20 s |
| Contact | 0.32 s | 0.06 s 加速前送，腕 X=45 cm，处理开门 |
| 接触制动 | 0.338 s | 整条 Contact 左链继续前压 1 cm |
| ShortRebound | 0.363 s | 复用现有短回弹，接入回收 |
| 实时回接 | 0.56 s | 0.197 s 回接当帧持握／空手步频动作 |

前送使用 t³ 加速，制动和回弹使用接触后的独立曲线。表中位置是作者相机厘米；运行会整体平移整个动作以适配预计接触点，最大 10 cm，Ready、Contact、Brake、Rebound 使用同一偏移，保留 43.5 cm 作者前送行程。偏移只在动作开始计算，不随逐帧墙距挤压接触腕点。

M4/V7 原生手模直接读取完整作者 local 变换。用户确认失败测试武器是 M16：当前武器资产为 `/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny`，另有同源 V7/M16 资产。M16 与 M4 的本地骨轴和关节位移兼容，但参考旋转分别记录各自的持枪姿态；该历史版本 M16 直接复用完整作者局部旋转与相机锁骨方向，保留 M16 本地骨骼位移、尺度和长度，不迁移原持枪参考旋转。当前 V6 额外修正 M16 原生腕部绑定差对应的两根前臂辅助骨，见文首。其他原生绑定在 Capture 时将完整作者姿态的参考形变适配到当前绑定；手指形变以掌面参考方向适配，再按完整目标父骨求 local，保留当前骨长、平移和缩放。运行只进行局部插值及一次 FK。肘部与原动作一样使用完整局部四元数插值，不再将现有入场姿态投影为只有 flex/roll 的旋转；完整捕获和当前目标得以保留。

入场和末帧的空手姿态只是编辑源例子。游戏从实际左链进入，回到当前实时持枪、持杖或空手动作，右手和主武器继续原层。双持副手隐藏／恢复、弓的既有收起和 V7 左臂 fallback 沿用原接入。

## 接触镜头反馈（2026-10-02）

成功执行原目标门的 OpenDoor/OpenWindow、确认门已进入打开状态时，触发一次 0.18 秒的相机局部抖动。0.018 秒达到主冲击峰值：向后 1.28 cm、向下 0.40 cm、俯仰 1.12°、侧倾 0.32°；随后两次较小回弹并回到零偏移。当前 0.30 秒护拳停顿及取消／未接触／门未打开的情况不触发抖动，沿用 `fps.Camera.Shake` 的全局开关与强度。

实现为 `DoorPushCameraShake.h/.cpp` 的短时 CameraShakePattern，由现有接触分支启动；不新增组件 Tick，不修改 ControlRotation 或 FOV。M16 完整局部骨轴适配沿用当前版本，时钟改为护拳保持结束后直接恢复。此前声音仅完成搜索、导入又受编辑器占用阻断；本轮已在后台实际导入保存。

## 接触声音反馈（2026-10-02）

声音资产为 `/Game/Audio/Interactions/DoorPush20261002/S_DoorPushImpact`，已实际导入并保存。BeginPlay 将音效与手模合并异步预载，现有 `Load` 句柄持有资源至 EndPlay 取消并释放。0.36 s 保持结束、成功打开原目标门后播放一次 `PlaySound2D`，音量倍率 0.85、原音高、从零播放，作为游戏声音而非 UI 声音。声音分支独立于镜头抖动开关。

无额外 Tick、逐帧音效查找或接触帧同步加载；`Config/DefaultGame.ini` 已加入该音效目录的打包清单。旧版 Kodack 的 CC0 拳击木门预览已被用户指定的 `D:/FPS3D/资产/音效/撞门.mp3` 替换，完整录音转换为 0.672 s、48 kHz、16-bit PCM 双声道 WAV。SoundWave 保留音量 1、原音高、非循环、压缩质量 90、FORCE_INLINE 和默认 SoundClass。当前保存回执位于 `SourceAssets/DoorPush20261002/UserAudio20261002/import-receipt.json`，导入输出位于 `Saved/DoorPushUserAudio20261002/import-live-editor-02.txt`。旧版制作记录已归档到 `trash/fps-arms-door-20261002/SourceAssets/DoorPush20261002/Audio20261002/`。未作试听或游戏运行测试。

## 源资产与接入

- 可编辑源：`SourceAssets/DoorPush20261002/DoorPush_LeftFist_V7_20261002.blend`。
- 完整作者表：`Source/FPSGAME/Movement/DoorPushAuthored20261002.h`。
- 运行姿态：`Source/FPSGAME/Movement/DoorPushPoseLayer.cpp`。
- 触发及开门：`Source/FPSGAME/Movement/FPSDoorPushComponent.cpp`。
- FixV2 运行备份：`SourceAssets/DoorPush20261002/FixV3/BeforeRuntime`。
- FixV2 作者备份：`trash/fps-arms-door-20261002/SourceAssets/DoorPush20261002/FixV3/BeforeAuthored`。
- 本次初稿作者备份：`trash/fps-arms-door-20261002/SourceAssets/DoorPush20261002/FixV3/BeforeFullActionReuse`。
- 作者输出与保存回执见作者目录；运行直接消费 C++ 作者表，不需额外导入 AnimSequence。

用户给定参考视频及已有观察资料保留在 `References`，本次修订采用项目现有法杖 F 动作完整姿态作为实际复用来源。没有改写 Staff 源动作。

## 历史制作与构建状态（V4–V6）

GuardOnlyV5 的作者源、声音资产及正常 Game／Editor 构建已完成，日志位于 `Saved/DoorPushGuardOnlyV5_20261002`。本轮 GuardWristSwayV6 的轻摆作者源、Blend 和 M16 腕部适配代码已保存，Game 与 Editor 正常后台构建均已完成，Editor DLL 已更新。当前日志位于 `Saved/DoorPushGuardWristSwayV6_20261002`。未自动打开或重启编辑器，也未运行游戏测试。

本次续建先遇到并行练习靶源码的编译错误：`AActor` 私有伤害标记和 `FVector_NetQuantize` 三元类型问题在读取时已有并行修正，保留其现状；随后将可选资源查找器对私有 `Object` 的访问改为公开 `Get()`，仅作必要编译解阻。修改前快照位于 `GuardWristSwayV6_20261002/BuildUnblock/FPSPracticeTarget-before-optional-finder-fix.cpp`，失败日志分别保存为 `FPSGAMEEditor-practice-target-failure.log` 和 `FPSGAMEEditor-optional-finder-failure.log`。最后正常 Editor 构建成功生成 `UnrealEditor-FPSGAME.dll`。

必要构建中遇到现有火球模块编译错误，已先备份原文件，再作最小修正：补 `FFireballCast` 前置声明和原表达式缺失的 `P=Model()`；`TObjectPtr` 使用 `IsValid(Shooter.Get())`；用 `::Cast` 消除快照成员同名遮蔽；允许其所属 `UFPSFireballComponent` 调用表现资产私有设置函数。保留现有业务与并行改动，未作火球玩法调整。原文件保存在 `GuardPoseV4_20261002/BuildUnblock/BeforeFireballRuntime`，两轮失败日志已单独保留。

GuardPoseV4 构建日志位于 `Saved/DoorPushGuardV4_20261002`。前一轮音频制作期间编辑器重新运行，占用基础 DLL，音效仍未实际导入，Game 音频构建已成功但 Editor 更新未完成；该轮日志位于 `Saved/DoorPushAudio20261002`。本轮使用编辑器已退出的后台窗口完成导入与必要构建。状态记录见 `SourceAssets/DoorPush20261002/integration-completion.json`。本任务未启动、关闭或重开交互编辑器，也未启动游戏、截图、渲染或动作测试；未试听，交由用户自行测试。

### 前两版构建记录

本版动作作者、可编辑 Blend、C++ 接入已后台制作落盘。M16 动作修正的上一轮 FPSGAME 与 FPSGAMEEditor 正常后台构建均成功，历史日志位于 `Saved/DoorPush20261002FixV3`。

本次镜头反馈源码已保存，FPSGAME 正常后台构建成功。现有正常 Editor 后台构建同样编译了当前 `DoorPushCameraShake.cpp` 与 `FPSDoorPushComponent.cpp`，成功生成 `UnrealEditor-FPSGAME.dll`（2026-10-02 13:53:07）；未在已有编辑器运行时另行构建、关闭或重启编辑器。该 Editor 日志来源为 `Saved/BuildEditor/build-20261002-135053.log`，副本与 Game 日志一起保存在 `Saved/DoorPushImpact20261002`。

首次 Game 链接遇到 `ColdSteelInventory::ColdSteelCompartment::Transfer` 未解析引用；该源文件在对应对象文件编译后已有更新，未改动该并行模块，重新进行正常构建后成功。首轮失败日志保存在 `FPSGAME-first-link-failure.log`。最终状态见 `SourceAssets/DoorPush20261002/integration-completion.json`。本任务未启动 UE、游戏、截图、渲染或追加动作测试，交由用户自行测试。

## 用户指定音效替换（当前，2026-10-02）

撞门声音已替换为用户提供的 `D:/FPS3D/资产/音效/撞门.mp3`。完整转换为 0.672000 s、48 kHz、16-bit PCM、2 声道 WAV，保留录音长度和原声道，不裁剪、不归一化。来源按用户提供记录，不继承旧候选的 CC0 声明。

同一个 SoundWave `/Game/Audio/Interactions/DoorPush20261002/S_DoorPushImpact` 已通过现有编辑器 Python 连接导入并保存；保留原音量、音高、加载方式及音频分类。当前运行逻辑为 0.31 s 成功开门事件播放一次，音量倍率 0.85，独立于镜头抖动设置。制作源、旧资产备份和本次回执位于 `SourceAssets/DoorPush20261002/UserAudio20261002/`；导入输出为 `Saved/DoorPushUserAudio20261002/import-live-editor-02.txt`。本次只替换资产，不需要原生编译；未试听、未运行游戏测试。

## 护拳腕掌与拇指 V8（原始制作记录，2026-10-02）

保留现有完整腕臂和中立腕骨，只调整护拳三根拇指局部旋转：减小根部过量轴向拧转，沿原生关节屈曲使指腹贴靠食指／中指外侧。M16 的 9 个网格同步收回腕侧过量拇指权重，平滑过渡到真实拇指根部；不改几何、UV、材质、骨长、缩放、公共 Skeleton 或其他动作。保留 0.30 s 停顿、轻摆、0.36 s 开门反馈和本轮用户 MP3。

腕掌权重资产已通过后台 commandlet 实际保存，完整动作表、Blend 源及正常 Game／Editor 构建已落盘。制作与接入记录位于 `SourceAssets/DoorPush20261002/GuardWristThumbV8_20261002/`。未运行游戏或验收渲染，手型由用户测试。
