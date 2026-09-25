---
name: ue5-fps-arms-animation
description: 制作、迁移和修正 UE5 第一人称手臂动画及手部装备外观（皮肤、衣袖、手套材质与袖口），包括自然手指抓握、双手近战挥砍/重击/突刺/格挡、单手工具挥击、甩弹匣、取弹插入、普通与空仓换弹、拉栓、装备、检视、换握和奔跑；用 MAT、Control Rig、Blender 及实际音画检查修复扭曲、穿模、抖动与接触不同步。
---

## UE5 默认开发方式（用户确定，2026-09-23）

后台优先：不主动启动 UE 编辑器；不主动检查、测试、启动 PIE、截图或验收渲染；不向其他对话/任务发协调消息。完整规则与「按改动选执行方式」表见仓库根 `AGENTS.md` 和 [后台开发与编辑器使用条件](../ue5-auto-assistant/references/editor-open-development.md)。

# UE5 第一人称手臂与换弹动画

用于游戏视模动画。FPSGAME 默认工作区为 `D:/FPS3D/FPSGAME`，旧 Godot HK416 仅作用户指定的动作/音频参考。当前用户选择保留 M4，按 HK416 动作意图适配；不能为追求“100%”复刻而替换枪型或宣称不同枪体接触位置完全一致。

## 开始每个动作

先实际查看已有视频、动作表或源模型渲染，读取 FPS、帧范围、时长、循环、接触帧及运行状态。记录左右手职责、起势—接触—收势和机械行程，再制作；不能只读取 clip 名称。缺少背面/深度时说明是三维适配。

排查顺序：实际加载资产/弹匣分支 → 源姿态与 rest/权重 → 部件坐标与接触 → 导入压缩 → 运行时姿态层和事件时钟。先定位首次出现差异的层，不用全局缩放、长混合或大幅转指掩盖问题。

## 当前动作合同

- **项目统一手模（用户于 2026-09-25 更新）**：以后新增、迁移和修改第一人称动画，统一以用户认可的当前 V7 裸手、裸臂为开发基准，游戏基础视模默认也使用这套裸手。覆盖枪械、近战、工具、技能与攀爬。保留该手型、腕臂线条、皮肤材质及各武器原生绑定；手套和衣袖作为装备外观匹配此基准，复用动作。此规则替代 2026-09-10 的默认原版手套条款。作者源、资产路径和接入约定见 [认可的裸手基准](references/accepted-bare-hands.md)。

- 普通弯弹匣：普通和空仓都先甩出旧弹匣；左手退到镜头外取新弹匣，完整抓握插入、压实。第一人称取弹不等于已制作背部实体弹匣袋接触。
- 非空仓装好后直接恢复腰射待机；空仓保留最后拍击/枪机释放。装备与切枪在该枪的腰射位置播放拉栓，避免先摆到画面中心。
- 右手食指保持自然弯曲；左手包握弹匣，不以指尖捏持。保留已确认的手型、甩匣和握持；弹鼓是独立动作分支。
- 当前空仓末次挥手比旧版快 50%，接触后有短促轻震；这是 M4 当前基线，不是其他动作的全局播放倍率。

## 按问题读取

- 旋转技能手/肩/武器错帧、蓄势分段顿挫或入场跳姿态：[旋转技能与连续蓄势](references/spin-windup-continuity.md)。先处理相机缓存时序，再用连续曲线与实际姿态衔接；区分背景模糊和前景时域残影。

- 枪械快速近战、跨枪握点、自然腕臂与结束后二次回正：[快速近战接触与收势](references/quick-melee-contact-recovery.md)。固定本枪握点，联动整枪与双手，在 recover 内完成姿态和视模锚点交接。
- 双持 F 偶发失效、改造枪转枪恢复与枪身形变排查：[双持快速近战](references/dual-pistol-quick-melee.md)。区分动作所有权、配件转轴、腕臂支撑和运行时形变证据。
- 第三段突刺肘部拧细、伸展露出袖口，或修肘后再露口：[突刺肘部与开口保护](references/thrust-elbow-clearance.md)。分开骨骼轴向差、相机缓存顺序和开口权重，锁住握点并按真实蒙皮分配旋转。

- 双手过顶下砍中段屈肘、保留原腕部观感：[过顶下砍伸展](references/overhead-reach-wrist.md)。约束全段肩腕距离，整体前送剑与双手，保留握点和骨长。
- 换弹结束瞬移、展示偏移滞后或复用已认可的插匣/拉柄动作：[换弹收尾与待机衔接](references/reload-handoff.md)。先区分动画末帧与运行时锚点，保持机械接触时钟。

- 同一把近战武器更换长柄、双手握距与配重锤联动：[改造握把的手部适配](references/modular-melee-grips.md)。保留原动作家族、接触状态和骨段长度，按实际握柄阶段调整左臂。

- 双手剑、双手近战挥砍/重击/突刺和格挡，或手腕扭转、左右臂交叉：[双手近战动作](references/two-handed-melee.md)。固定双手握点、分离剑身展示角与攻击刃向；符文剑 V21 格挡与 V22 蓄力左臂已获用户接受，转剑检视单独暂停。

- 手枪握把砸击类的双手+武器组程序化动作，或武器组搬运变换：[手枪握把砸击尝试](references/pistol-grip-bash-attempt.md)。含武器不挂手链时的刚体搬运变换教训（乘序/空间转换错一次枪就飞）与挂起状态。

- 第一人称检视、转柄、张掌换握或学习 Source/CSGO 手部骨架：[源动作与分指配合](references/source-hand-animation-study.md)。保留前臂、腕部、五指及武器独立关系；源观察可复用。符文剑检视 V35 已否定归档，V36 动作得约八成认可；2026-09-16 的 V46 修正前臂旋前分布，V47 重建了转刀本身（接触点、节拍、进深），见 [双手近战动作](references/two-handed-melee.md)。

- 技能／魔法的左手凝聚、发射、脱手恢复，或翻掌导致手臂变细：[施法与完整骨段](references/casting-arm-volume.md)。业务状态和资源存档另读 [技能／魔法工作流](../ue5-skill-magic-workflow/SKILL.md)。

- 双手伐木斧、矿镐的待机/装备/奔跑、举顶下砸、腕肘修正与停帧：[双手工具动作](references/two-handed-tools.md)。固定接触、联动整臂，敌人与资源共用确认命中的反馈时钟。

- 单手采集工具及旧版模型迁移来源：[单手工具动作](references/single-hand-tools.md)。当前斧、镐已转双手，旧单手案例不代表最新装备或攻击姿态。

- 手枪动作、M1911/P9 迁移、空仓机械与回握缩尾：[手枪动作适配](references/pistol-adaptation.md)。M4 的拍击/装备拉栓合同不直接套到手枪。

- 制作或调整第一人称手套、衣物、袖口及独立换装：[第一人称手套与衣物标准工作流](references/first-person-equipment-workflow.md)。以认可的 V7 裸手拟合装备，沿用各原生骨架并复用动画，完成覆盖、材质、保存与配置接入；布料物理按宽松区域单独处理。旧材质分区与贴图细节按需读 [手部装备材质参考](references/hand-equipment-appearance.md)。

- 直立握把与棱镜阻手器共用动作、新增“垂直握把类”成员：[垂直握把类母版](references/vertical-grip-family.md)。复用已接受的 VRE 手型与原动作时序，按尺寸校准整手方向和握点；小阻手器用自然拳形包住。

- 第一人称翻越/攀爬、点按及空中接墙、镜头选墙、支撑失效与强控中断、表面适配：[攀爬接触与镜头交接](references/traversal-contact.md)。

- 复刻／迁移参考动作、或动手前要先量（可达性、指尖到目标、视锥+近平面穿模、局部 vs 世界向量、换弹可见性、重定向共轭）：[先量后写](references/measure-before-writing.md)。
- 手指扭曲、穿模、抓握、腕肘变形、重定时或冲击感：[姿态与接触方法](references/pose-contact.md)。
- 异形／宽长弹匣撑开虎口、拇指内收，或只需修一根手指：[异形弹匣自然抓握](references/irregular-magazine-grip.md)。优先选局部抓握区域，参考用户认可的 SVD 前半段包握与拇指向上延展，冻结已合适的其他关节。
- 配件缩放后改手指数，或握姿已正确但腕肘衔接僵硬：[配件手部与整臂优化](references/grip-arm-refinement.md)。先保留已接受接触，诊断腕部折弯与扭转，再联动肩肘支撑；具体案例数值不跨枪型照搬。
- 握把、阻手器及改造后握姿：[改造配件标准](../ue5-weapon-workflow/references/attachment-standard.md)。先复用已接受的成组手型，适配整手方向、握点与腕臂；必须用实际游戏掌侧、玩家视点及换弹回握验证，距离近或零相交不作为独立成功依据。
- 现成抓握源的镜像/重定向：[GitHub 抓握迁移](references/github-grasp-donor.md)；45° 握把、阻手器及前臂扭转误判：[已接受适配案例](references/grasp-canted-handstop.md)。
- MAT 编辑器、FK Control Rig、关键帧、烘焙及保存：[MAT 实操与边界](references/mat-editing.md)。
- 继续 M4 或防止恢复废案：[当前资产、时序与作者源](references/m4-baseline.md)。
- 发布候选、检查压缩、验证已应用和音画同步：[验收与工具入口](references/validation.md)。
- 需要"非接触类"上身氛围运动（持枪走动 sway、受击晃动、疲惫/放低武器）或第三视角/怪物全身动作素材，想用文本生成：[Kimodo 文本生成动作（备选工具）](references/kimodo-motion-tool.md)。整身 30 关节、无独立手指、无约束/接触帧输入；换弹、拉栓等接触关键动作仍走 MAT + Control Rig，采用前必须先做一次"只映射上身链"的重定向 + 实机画面闭环。

## 交付要求

按已授权范围完成候选、导入、实际引用和回归。交付可编辑 Blend/FBX 或 UE Control Rig 序列及实际模型/游戏预览；有音效变更时记录实际混音并核对接触，不用静音 GIF 证明同步。小改只检查相关动作及受影响的相邻状态，不重复跑无关大测试。

读图与视觉判读：需要自己看渲染、截图或候选图时**直接用会话内挂载的 `read_image` 工具**读本地图片路径；批量、headless 或不想让图片进会话历史时才用 `D:/FPS3D/FPSGAME/Tools/deepseek-vision.ps1`（用法与边界见 `D:/FPS3D/FPSGAME/Docs/deepseek-vision.md`）。读图只做定性确认和列差异；角度、朝向、偏移、接触位置和尺寸用像素测量；最终视觉与手感验收由用户决定。

会话内看图**直接用挂载的 `read_image` 工具**读图片路径（P95 分辨率不缩水，能追问）：图片字节会留在历史里，单线程内联图片累计到约 50 MB 就会 `413 Payload Too Large`，那条线程连同未完成的候选一起废掉；单线程控制在约 10 MB 以内、换一版开新线程。需要控制体积时再用 `D:/FPS3D/FPSGAME/Tools/shrink-for-view.ps1` 生成小副本，或改用 `Tools/deepseek-vision.ps1` 让图片完全不进会话（定量测量仍读原图）。

通用枪械、许可、ADS、装备数据和改造约束见 [UE5 枪械工作流](../ue5-weapon-workflow/SKILL.md)。


## PKM 失败案例（2026-09-22）

早期 Meshy `PKM20260921` 分支的手部与换弹开发已退役，后续用户提供的 `PKMLowpoly20260922` 不在此退役范围。跨枪手型、整臂支撑、左右手交接和视频遮挡边界见 [手部与整臂优化](references/grip-arm-refinement.md#失败案例pkm-持握与弹链换弹2026-09-22)；不要将早期废案的源脚本、接触参数或导入回执作为成功动作模板。低模分支的后拉／主动前推及声音时钟经验见 [换弹收尾与待机衔接](references/reload-handoff.md#拉柄后拉停顿主动前推pkm-低模分支2026-09-23)。

For independent third-person animation alongside the accepted first-person arms, see [player world body](../ue5-cpp-gameplay/references/player-world-body.md). Preserve shared gameplay contact timing.
