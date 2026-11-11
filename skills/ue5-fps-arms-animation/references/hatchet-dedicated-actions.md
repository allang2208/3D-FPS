# 单手斧（hatchet）：与原弯刀动作族共存的专属动作（2026-11-01～04）

来源：`ue_tactical_hatchet` 的专属动作（`SourceAssets/HatchetEquip20261101`、`HatchetChop20261102`、`HatchetSprint20261103`；记录 `Docs/Weapons/tactical-hatchet-20261101.md`）。任务形态是"武器外观换皮但共用弯刀骨架与运行时"，却在几处需要**只对斧头生效**的专属动作。按问题读取；历史验收不授权自动重测。

## 先说结论：只换表现，不换时钟

斧头的三处专属动作（装备抛接、三连击第三段劈砍、双持旋风副手避让）都遵循同一条：**服务端与命中判定沿用原弯刀表，只替换 clip 与呈现**。

- 单持劈砍写在弯刀**戳刺**的时钟上（`StabTempo`、命中窗 0.34–0.47、打击 0.367、缓冲 0.47、`KukriRhythm::Swings[2]` 的长度 38/30 s）。
- 双斧劈砍写在**双刺**的时钟上（`KukriRhythm::DualThrust*`：246/120 s、命中窗 0.54–0.72、打击 0.60、缓冲 0.84、前冲 100 cm、击退 150 cm）。
- 生成的头文件里用 `static_assert` 把长度、命中窗、打击时刻钉到原表上（`HatchetChopRhythm.h`、`HatchetDualChopRhythm.h`、`HatchetReadyRhythm.h`）。这样回执、权威窗口和连击规则都不用改。
- 接入点集中在 `KukriWeaponComponent` 的三个 profile 选择器：`SwingProfile()` / `StrikeProfile()` / `RiftProfile()` / `StageSwingCamera()`，各自在最前面判断"当前是斧头的第几段"。**不要**去改 `KukriRhythm.h` 的公共表。

## 斧头与弯刀的几何差别（姿态求解要点）

- 斧头共用弯刀的握点帧（原点在拳心、+Z 朝斧头、+X 朝刃口、0.01 缩放），所以 `kukri_frame`/`hand_rel` 直接适用；但**斧头 42 cm、重心在头**，同样拳位下斧头的扫掠半径比刀大得多。
- **锤握下斧头很难落到拳的正下方**：那需要前臂内旋 150–180°，超出手臂范围（`Work/probe_impact.py`）。所以下劈做成略斜的落点（从右肩上方到准星），斧柄在打击姿态约 40° 上左斜。不要为了"竖直下劈"去硬掰扭转。
- 斧头有两组典型姿态：**刃口朝前（`e≈+X`）** 是冲刺起手/举斧；**刃口朝下（`e.z<0`）** 是劈砍落点。姿态由 `author_hatchet_chop.KEYS` 的 `(fist, d, e, twist)` 驱动，`d` 是柄朝斧头的方向、`e` 是刃口方向，求解器自动把 `e` 投影到与 `d` 垂直。
- 摆锤式下落时斧头容易"翻背"——用 `HoldTrack` 的零速度保持键（`hold=True`）在顶点和停在目标里两处锁住，避免匀速感（符合工作流 §3 的动画节奏要求）。

## 双持：两只斧头同时劈

- 左手直接复用双持弯刀的镜像做法：左手 = 右手在**镜像空间**解出的虚拟右臂（`dual_rig.py`：`ROT_X180 @ qmat` 换旋转、`F @ (p - left_shift)` 换位置），左斧 = `D.left_kukri(Kv)`（绕刀面镜）。
- 两拳要**各向自己一侧外推 + 左拳略近略低**，否则两把斧头在空中相交（实测两斧头最近 2.8–3.5 cm；双持待机本身只有 3.5 cm，因为待机沿用弯刀的双持握姿，两个斧头在画面里是交叉的）。
- 交叉处在**离开待机**和**回到待机**这两段最容易穿模：在待机前一关键帧给出 `UNCROSS` 深度错开（右拳近、左拳远），而不是改待机本身（待机是弯刀族的共享资产）。
- 间隙用**斧头真实采样点**（头、刃、柄上段）算最近距离，不用胶囊：`HEAD_SAMPLE` 八点、逐帧取 `min`。写进 `clips.json` 的 `min_gap_cm` 做回归线。

## 双持斧头的 SPRINT-READY 跑姿（三段式）

- 形态抄双手剑的战术冲刺：**Enter / Loop / Exit** 三段，而不是一段带首尾的循环。
  - `Enter` 首帧 = 双持待机手势，尾帧 = 举斧姿势；`Loop` 是 80/120 s 循环（与 `A_Kukri_DualRun` 同长度，全速跑时手臂起伏与腿同相）；`Exit` 反向回到待机。
  - 运行时用 `ReadyRunPhase`（0 无 / 1 进入 / 2 循环 / 3 退出）在 `TickReadyRun()` 里驱动，`TickComponent` 在攻击分支之后调用；`IsRunClip()` 要认这三个 clip，进出才走跑步混合而不是 0.1 s 的通用混合。
- **举斧的手位**：头在准星右上方（约 NDC `0.34, −0.93`），斧柄朝上略后仰，刃口朝前。高过这个位置手臂就伸直到 0.67 以上、肘出画面。
- **左手**：这一项用户来回改过两次。当前定稿是**沿用 `A_Kukri_DualRun` 同相位的左臂**（即"弯刀冲刺跑姿"）。不要再自行改成待机手势——已明确要求撤回。
- **右手的摆动跟左手同频同幅**（11-04）：不要另写一条小幅起伏。取左拳在 `DualRun` 一个步幅的实测轨迹（握点屏幕偏移、深度、旋转），镜像到右侧、错开半步（`SWING_PHASE=0.5`：一次谐波反相＝两臂交替，二次谐波的步伐起伏仍同步），绕举斧握点走**同样的屏幕轨迹**。两拳深度不同（左 42 cm、右 30 cm），按厘米照搬时屏幕上竖直只有 74%（低处的左拳深度一变，屏幕位置也跟着变），所以按 NDC 匹配，深度起伏按深度比缩放。
- **就绪前的冲刺**（11-04）：双持斧头冲刺、尚未就绪时 `LocomotionClip()` 给 `DualWalk`（待机移动姿态），不给反握的 `DualRun`；"从奔跑到就绪的过程保持待机移动姿态"指的是这一整段，不只是 Enter 的首帧。
- **退出**要从当前姿态混入（0.18 s）：循环可以停在步幅任意位置，零混合会跳一下。
- **从就绪跑姿进冲刺攻击**用 0.26 s 混合（普通冲刺 0.18 s），并在起手时 `ReadyRunPhase=0` 复位状态机。

## 踩过的坑（都是真实发生、可复现的）

1. **`assemble()` 重建姿态时用了 `R.base_local`**：解完右臂后又用基础局部重建整副骨骼，右臂被打回站姿，手与举起的斧头错开 17 cm（表现为"手和斧头穿模"）。修法：在解出的姿态上 `R.rig.localize(world)` 起算，只覆盖左链。
2. **接触检查必须用真实网格**：`HatchetEquip20261101/check_contact.py`（V7 手模 vs `SM_TacticalHatchet` 的 BVH 内外判定）；`Work/check_ready_contact.py` 是同一套的多姿态批量版。**判据**：握持压入 0.65–0.77 cm 是已验收量级；超过 1 cm 或对另一侧手臂/头/前臂有穿插就是错的。
3. **副手斧在预览里是"固定摆位"**：渲染脚本把 `kukri_left` 当静态姿态摆，不跟手走，所以早期预览看不出穿模（11-04 冲刺就绪预览已改为 `virtual_hand` 跟手；组合与副手单持预览走 `HatchetPairs20261104/render_pair_preview.py`，每只手按自己的武器网格）。做接触检查时要按运行时的挂法（`KukriOffhandDraw::Grip()` 在 `hand_l` 下，单位 cm/100、缩放 0.01）自己算，不能直接用作者脚本给的左手斧变换。
4. **双持旋风的转身方向**：`GetWhirlwindFirstPersonYawOffset()` 里原本有 `IsDual()` 提前返回 0，导致双持第一人称看到的是世界转身（与单持相反）。去掉该例外后第一人称统一 `-2θ`；第三人称仍返回 0。**只改第一人称**是这类"观感方向"问题的通用边界。
5. **双持旋风时把手抬进视野**：旋风 clip 的左臂是护手拳，副手斧跟着进画面左上。试过绕锁骨转 45°（观感仍怪），最终改为 `SetLeftArmRest()` + `KukriLeftRest.h`（单持 Idle 第 0 帧的左臂局部旋转）做**自然垂放**，`FinishWhirlwind` 释放、下一段 locomotion 自然回待机。注意权重要在 `SamplePose` **之前**设置——`FinalizeBoneTransform` 在采样里执行。

## 斧头组合与副手单持（11-04，`SourceAssets/HatchetPairs20261104`）

- **混搭 = 各手按自己的武器**：两只手臂是独立骨链，混搭 clip 逐帧取各自来源的手臂（右臂和武器链取 A，左链和 `ik_hand_l` 取 B）。来源必须在同一时钟上；装备两边都在双持待机结束，短的那边停在末帧。不要为混搭另解姿势。
- **左手抛接的飞行表按左手武器选**：弯刀用 `KukriDualEquipBlade`，斧头用 `HatchetPairRhythm::LeftHatchet`。声音时刻也按左手武器，延迟 0.067 s。
- **双斧装备的间距**：单持抛接会把斧头带到画面中央，镜像后两把会撞。两拳全程各向外 8 cm，接住前后左拳近 6 cm、右拳远 3 cm。斧头头部宽，外推比弯刀的 6 cm 多。
- **主手空、副手单持（lone off-hand blade）**：
  - 身份统一用 `ActiveKukriWeapon()`（主手有物品时就是 `Equipped()`），只有主手空置时才不同；
  - 视模用 `bMirrorRightToLeft` + `bLeftHandOnly` 采样单持 clip，武器挂在 hand_l 上，变换 = 右手武器的镜像（`MirroredWeaponToHandL`）。
- **运行时镜像武器的公式**：旋转 = 镜像四元数 `(x,-y,-z,w)` × 绕握持 Z 转 180°（等于 `dual_rig.left_kukri` 的 `F·R·FY`）；位置 = 左手位置 + 右手到武器偏移的 X 取反。镜像修正必须用骨架绑定姿态（`ref_world`），用站姿基准会差 22°（`Work/probe_lone_mirror.py`）。
- **镜像招式的观感项也要镜像**：镜头偏航/滚转；`JumpRoot` 整体按镜头竖直面镜像（冲击、压入、跳跃摆动都在上面，不要逐项取反）；三连击和冲刺攻击的剑气 ribbon；旋风反向转（法杖配副手刀已有先例）。
- **镜像武器关系必须在入场淡化之前算**（11-04 用户实测“衔接错位”的原因）：`bLeftHandOnly` 把右臂收成零缩放，`CaptureEntry` 记下的就是收拢姿态。用淡化后的右臂去镜像，每次切 clip 刀都会缩进掌心、转错。正确做法：从 clip 本身的右手-武器关系（套同样的握持锁）乘 hand_l 的绑定修正得到左手关系，并让右臂和武器链跳过淡化。复核用 `-run=LoneOffhandBladeAudit`。
- **联机身份**：主手空时 `ActiveInventoryWeaponDefinition` 为空，身体状态的武器名必须改用 `ActiveKukriWeapon`，否则服务端的 SameWeapon 检查会丢掉全部动作。

## 双持冲刺攻击（11-04，`SourceAssets/DualSprintAttack20261104`）

- 单持冲刺攻击是**双手合握一把刀**的跳劈，双持时这个合握不存在。做法是"右手原样 + 左手同时刻镜像 + 两拳外推"，和双斧第三段一样，不重新求解关键帧：逐帧取单持的右臂，`shift_arm` 外推，`mirrored()` 给左链。
- 间距要按"画面里看得到的帧"算：跳劈过顶那段两臂都在画外，最紧的地方其实在**回到交叉握姿**的途中。回位顺序沿用双斧劈：右手在前，左手在后且低一些。
- 时长在头文件里写成和单持一样的 `40.f/30.f`。写成小数 `1.333333f` 的话，`static_assert` 的浮点相等比较会失败。

## 第三人称副手单持与混搭第三击（2026-11-10）

- **第三人称的"镜像单持"必须是整段上半身镜像，不是把左臂当成右手再套一份姿势**。单持库是右手的动作，直接拿它驱动左臂，右臂会跟着一起挥（等于双臂同时出手）。正确做法：在身体动画管线里、所有混合完成之后、手指抓握之前，按骨架绑定位姿把肩/臂/手/胸/头整段镜像到另一侧（`FControls::MirrorLoneBladeUpperBody`，与已认可的单持左手手枪 `FSinglePistolMirrorLayer` 同一构造）。腿部保留原步态，只把胸的朝向重新锚回未镜像的骨盆。
- **镜像要点**：`FAnimationRuntime::MirrorPose(pose, EAxis::X, mirrorBones, refRotations)` 操作的是**局部**变换；先把 component-space 姿态写回 local（`ConvertComponentPosesToLocalPosesSafe`），镜像后再 `InitPose` 回 component space 供后续层使用。参考旋转必须逐骨累乘参考骨架（父到子），不是只取本骨 ref。
- **三态同判**：`FFPSBodyState::bLoneBlade` 必须由本地采样、服务端影子档案（`ActiveKukriWeapon` 且主手空）和 observer 同时给出，否则远端看到的仍是右手持刀。身体装备项的 body identity 用主手实例（`S.WeaponInstance`），但挂点走 `hand_l`（`FFPSBodyWeapon::bLoneBlade`），`AttachHand` 仍为 1 —— 这两个"身份/挂点"要分开记。
- **不要让 `bOffhandKukriEquipment` 为 lone 置位**：那个标志会切到双持 clip 族（`DualClip`），而 lone 要走的是镜像后的单持库。
- **装备动作期间不能把 lonely 刀当"该藏的副手"**：`IsWorldWeaponStowed` 里 `Action==Equip` 的隐藏分支对 lone 要放行，否则拔刀全程刀不可见。
- **一次性姿势叠加层**：混搭第三击"各手各的"用第二条姿势输入（`SwordAlt` 在 `FProxy` + `FControls` 里各一份 `FPoseLink`），主取给右手整链、备取只覆盖左臂链（`LeftArmBones = LibraryArmBones & 2`）。两条 clip 必须同长同钟（本例都由 `KukriRhythm::DualThrustSeconds` 钉住），否则手腕会互相拉扯。`Update_AnyThread` 里只在 `SwordWeight > 0` 且 `bMixedPairAlt` 时更新备取，避免空转。
- **`PreserveHands` 与剑气窗口要同步放开**：混搭变体（`HatchetPairAttack3HK/KH`）在 `PreserveHands` 里要与 `HatchetDualAttack3` 同等处理，observer 剑气也要按"哪只手拿斧头"选斧刃采样，否则两道剑气共用同一把武器的几何。

## 资产与检查清单

- 三个作者目录各自独立：`HatchetEquip20261101`（装备抛接，V2.1 0.90 s）、`HatchetChop20261102`（单持劈砍 38/30 s、双斧劈砍 246/120 s）、`HatchetSprint20261103`（双持就绪跑姿三段）。
- 每个目录都有：`author_*.py`（生成 clip JSON + 头文件 + 预览）、`import_*.py`（commandlet 导入，写 `import_receipt.json`）、`README.md`（重建命令）、`Previews*/`（Blender 手模渲染，镜头曲线已叠加）。
- 交付时如实写：`FPSGAMEEditor` 构建结果、Game 目标是否构建、**未运行游戏/未测试**。第三人称通常沿用既有全身动作，除非用户明确要求。

## 第三人称下劈与回拉的手臂修正（2026-11-06）

- 先锁定视角与资产族：第三人称 `Kukri.Hatchet.DualChop`、`Kukri.Falcon.*` 指向 Jason/Kaitlin 全身资源。不要顺带替换第一人称 Arms 的连击、相机或刀光表。用户撤回第一人称候选后，保留原包散列与恢复备份，退役候选及其生成入口一起处理。
- 手掌仍握住斧头不代表肘部正确。固定手掌世界变换，沿肩到腕的圆弧调整肘部弯曲面；主链旋转、前臂扭转骨和肘部蒙皮辅助骨需要一致。不要通过改主骨长度消除表面塌陷。每种身体单独处理，Kaitlin 的 `upperarm_twistCor02_l` 等辅助骨还涉及平移重定向，不能照搬 Jason 的局部修正。
- 回拉单独保留已认可的下劈和低位停顿，再修拉回与收势；不能把整个动作重新线性混合。本例保持约 0.35 s 的低位停顿、手掌轨迹和两段接触时间不变。双手由作者动作控制时，清除额外腕部覆盖并核对 `PreserveHands`，防止通用副手保留或支撑 IK 再扭一次手臂。
- 用户要求检查时，读回已保存并压缩的资源，绑定实际身体表面看正背面与连续帧。作者 JSON、骨架线框、编译成功分别不能替代实际蒙皮结果。联机状态/时钟检查与实时画面验收分开记录。

当前作者入口为 `SourceAssets/HatchetDualChopRepair20261106/author.py`、`elbow_skin.py`、`pull_arm.py` 和 `PullAnatomy/save_pull.py`。发布与检查边界见工程 `Docs/Publication/HatchetThirdPerson20261106/README.md`；历史检查不授权自动重跑。
