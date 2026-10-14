# 第三人称免费双手剑全身动作来源

2026-10-05。用户未购买 GreatSword Animset，改为寻找免费来源；随后授权按推荐继续适配。原包已从作者免费入口下载，Jason 动画资产与运行时接入已落盘；没有启动 UE 界面、游戏或渲染验收。

## 已取得的原始文件

全部保存在 `SourceAssets/ThirdPersonSwordFree20261005/`。`Kevin-receipt.json`、`KayKit-receipt.json` 记录作者来源、免费文件 ID、原包大小、SHA-256 与文件清单。`skeleton-action-catalog.json` 记录实际骨架、动作名、时长和动画轨道。

### Kevin Iglesias — Human Melee Animations FREE

- 作者入口：<https://kevdev.itch.io/human-melee-animatons-free>
- 已取得作者当前的 Godot/Unreal 免费包：`Kevin-free-author-download.zip`，13,524,662 字节；解压到 `Kevin/`。
- 免费原包包含 FBX、男女模型、武器模型，以及 `Animations/HumanMeleeAnimationsFREE_BlenderFiles.zip` 中的 Blender 源文件。
- 本次读取的男性骨架有 56 根骨，包含躯干、头、四肢和手指，属于全身动作源。
- `HumanM@Attack2H01.fbx`：1.600 秒，免费版的一招双手武器攻击。
- `HumanM@CombatIdle2H01.fbx`：1.333 秒，双手战斗待机。
- `HumanM@WeaponHold2H01.fbx` 是持握姿态，不算另一招攻击。女性版本也包含对应动作。
- 包内共 94 个动画文件不等于 94 招剑攻击；其中包括男女版本、移动方向、原地/根运动、其他武器类型和持握姿态。
- 包内 `Human Melee Animations 2.0 FREE.pdf` 的许可页写明 Standard Asset Store EULA，允许免版税商用、不允许转售、不要求署名。原始文件仅留本机，不作为公开源码附件。
- 官方文档：<https://www.keviniglesias.com/documentation/Human%20Melee%20Animations%20FREE.pdf>
- 作者页面留言曾说明双手/长柄待机的左臂 IK 导出问题，并已宣布修复 FBX 与 Blender。本次直接取得当前作者包，不使用旧镜像；此声明不代表已验证 Jason 重定向效果。

### Kay Lousberg — KayKit Character Animations 1.1

- 作者入口：<https://kaylousberg.itch.io/kaykit-character-animations>
- 已取得免费 1.1 包：`KayKit-free-author-download.zip`，14,858,957 字节；解压到 `KayKit/`。未取得收费 Blender SOURCE 档。
- 包内 `KayKit_Character_Animations_1.1/License.txt` 明确 CC0，允许个人、教育和商业用途，署名非必须。
- 实际读取 `Rig_Medium_CombatMelee.glb`：23 根全身骨，包含下列双手动作；FBX 同目录也有对应动画集。

| 动作名 | 用途 | 原始时长 |
| --- | --- | --- |
| Melee_2H_Attack_Chop | 下劈 | 1.633 秒 |
| Melee_2H_Attack_Slice | 斩击 | 1.100 秒 |
| Melee_2H_Attack_Spin | 旋转攻击 | 2.400 秒 |
| Melee_2H_Attack_Spinning | 另一旋转动作 | 0.667 秒 |
| Melee_2H_Attack_Stab | 突刺 | 1.600 秒 |
| Melee_2H_Idle | 双手待机 | 1.067 秒 |

同集另有 `Melee_Block`、`Melee_Block_Attack`、`Melee_Block_Hit`、`Melee_Blocking`，但名称没有标明双手剑专用，不能直接视为符合当前剑握法。Rig_Large 另含双手 Attack、Slam、Idle，未列入上述 Medium 招式数。

作者明确这些动画按 KayKit 角色制作，重定向到其他角色可能不理想。其骨架简化且没有逐指骨链，不能将动作数更多等同于更适合写实 Jason。

## 适配建议与当前边界

优先将 Kevin 的男性双手攻击和待机作为写实角色适配基准；KayKit 用作突刺、旋转等缺失招式的全身动作候选。两者均须重定向到当前 Jason 骨架，并按剑柄尺寸处理双手接触，不能把源 FBX 直接写成当前 Skeleton 的动画。

接入时需要让第三人称攻击的骨盆、胸、头和两臂共同来自全身动画，停止该动作中的第一人称 `ActionHands` 与武器机械轨迹覆盖，保留实际攻击的业务时钟和伤害窗口。头部拉伸仍需独立定位，不能仅凭换动画宣称修复。

## 后续适配与接入

实际保存路径：`/Game/Characters/JasonPlayer20261003/SwordFullBody20261005/`。

- `Donors/`：完整保存的作者原始 Mesh、Skeleton、动画；早期 `Sources/` 是未完成依赖保存的导入中间产物，不用于运行时或重制。
- `Rig/`：Kevin、KayKit 到 Jason 的独立 IK Rig/Retargeter。KayKit 的三关节手臂终点选 `wrist`，不把它简化的 `hand` 手指块误作腕关节。
- `Animations/`：10 条 Jason 动画，`assets-saved.json` 记录实际路径和动作时长。
- `player_body.json` 新增 13 个 `Melee.FullBody.*` 键；其中 Idle 作为保留源，普通持剑跑步继续使用此前已接入的普通持握循环。

| 当前动作 | 全身来源/处理 |
| --- | --- |
| Slash1、Slash2、Thrust、HeavyRelease | Kevin Attack2H01；普通三连击均复用第一刀 |
| Overhead、DashOverhead | KayKit 双手 Chop；冲刺预备段沿现有 ActionEntryFraction 对齐 |
| Uppercut | 完整 Chop 全身动作反向派生；并非免费包原生上挑 |
| Whirlwind | KayKit 双手 Spin；剔除源动作整体朝向，避免和角色自身旋转叠加 |
| Charge | Kevin 攻击的预备段，按已有蓄力/取消权重取样 |
| Guard、GuardHit、GuardBreak | KayKit 格挡/格挡受击，加当前剑的双手握柄约束 |
| Pommel | KayKit Block Attack 作为全身反击来源，加双手握柄约束；并非原生剑柄打击动作 |

`FPSBodySwordMotion.h` 统一选择动作；`FPSBodySwordPose.inl` 在普通姿态之后、受击和握指层之前混合完整全身姿态。站立攻击使用源腿部运动；移动、下蹲、空中和特殊移动逐渐保留已有下身。两手按完整动画的肘部弯面解算，整组握点限于可达范围，不拉长手臂。

2026-10-06 按用户要求，将第三人称 `Slash2`、`Thrust` 的动画引用改为 `Slash1` 使用的 Kevin Attack2H01，并同步发布脚本。三个动作键继续独立保留，沿各段既有命中/收势窗口采样；第一人称与攻击判定不变，旧 Slice/Stab 资产保留。此项仅配置修改，无需 C++ 编译；重新进入游玩、创建角色组件时读取新配置，未运行游戏测试。

攻击时 `FPSPlayerBodyMotion.cpp` 停止采集第一人称动态手腕/剑身轨迹，仅保留静态装备握姿和剑部件绑定；原生第一人称动画、伤害、库存及命中窗口不变。源 Contact/Release 标记根据手部运动放置，运行时再映射到实际业务窗口；这是制作时序，不代表游戏观感已经验收。

### 头部修正

读取 Jason 脸部后处理图后，确认 `EnableHeadMovementIK` 默认值为 true，且图中使用 `CR_MetaHuman_HeadMovement_IK_Proc`。当前全身模型已经提供完整颈/头链，因此在玩家头部组件注册后关闭这一个额外 IK 开关，保留面部 RigLogic，不修改共享作者蓝图。`FPSPlayerHeadAnimInstance` 改为复制共同骨链的局部姿态。身体与头的共同骨链绑定和父子层级已在本轮前面的定向排查中读取。

### 构建和生效状态

Game 目标后台构建成功：`Saved/free-sword-game-build-local-20261005.log`，28/28，产物 `Binaries/Win64/FPSGAME.exe`。首次 UBA 构建因无法创建共享内存退出，随后使用本次命令行的 `-NoUBA` 完成构建，没有改全局构建配置。

用户确认两个 FPSGAME 编辑器均已关闭后，使用 `Tools/Build/Build-Editor.ps1` 完成 Editor 构建：`Saved/BuildEditor/build-20261005-232826.log`，29/29，已链接 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。Game 与 Editor 均包含本批源码修正。

没有自行启动、关闭或重启编辑器，没有执行游戏测试。头部修正、上挑反向派生、格挡和剑柄反击的源动作适配仍需用户实际体验。

## 2026-10-06 第三人称旋风设计记录

用户随后确认开始制作，分段动作、换脚和接入记录见 [第三人称旋风制作](third-person-whirlwind-20261006.md)。以下保留初始来源比较与设计背景。

用户要求开始设计旋风攻击，并寻找可参考或复用的动作。本次读取了当前技能、第三人称采样代码、现有资产清单及 KayKit GLB 源轨道；没有启动编辑器、游戏或渲染。源轨迹读取脚本与结果位于 `SourceAssets/ThirdPersonWhirlwind20261006/read_source_motion.py`、`source-motion.json`。

### 可复用来源

1. **KayKit `Melee_2H_Attack_Spin`，2.4 秒。** 原始动作已在本地，Jason 版本已接入 `Melee.FullBody.Whirlwind`。读取源轨道可见：约 0–0.6 秒起势，随后转一圈并小幅过冲，约 1.8 秒回到累计 -360°，之后完成收势。可参考起势与刹停；不适合把完整单圈动作直接压成当前两圈技能。
2. **KayKit `Melee_2H_Attack_Spinning`，约 0.667 秒。** 原始文件和 UE donor 已保存，尚无对应 Jason 正式动画。源根轨道转 -360°，首尾手、脚及骨盆位置闭合；适合作为连续横扫的循环参考。双脚相对根的位移不足 0.01 cm，不能原样当作写实人物的换脚动画。
3. 原有 `A_RuneSword_WhirlwindV5` 及 V6 收势属于第一人称来源，仅延续已经认可的技能节奏和外展回位意图，不作为第三人称全身动作母版。

作者页面再次确认 KayKit 动画为 CC0，可免费商用，FBX/GLTF 可供重定向；同时提醒非 KayKit 人物仍需适配：[KayKit Character Animations](https://kaylousberg.itch.io/kaykit-character-animations)。网上其他大剑包暂未找到比本地两条来源更直接、且已确认免费取得的两圈全身动作，不新增商业包依赖。

### 推荐动作方案

沿用 `skills.json` 的基础作者时钟：起势 0.5 秒、旋转 0.8 秒、收势 0.52 秒，总计 1.82 秒，累计 -720°。实战时间仍受原有攻速和命中停帧影响。

| 阶段 | 身体与剑 | 腿脚设计 |
| --- | --- | --- |
| 0–0.5 秒：压低蓄势 | 重心轻降，双手收剑到侧腰；胸髋小幅反向蓄力，肘部保留弯曲，末段连续展开 | 小幅开步，膝盖朝脚尖方向；承重前脚准备以前脚掌转轴 |
| 0.5–1.3 秒：两圈横扫 | 采用 Spinning 的横扫持握参考，剑维持腰至下胸高度，两手同握柄；第一圈直接接第二圈 | 交替前脚掌支撑与另一脚短促垫步；每半圈换承重，离地脚留出间隙，不把两脚锁地转完整两圈 |
| 1.3–1.82 秒：制动回位 | 末圈减速后保持短暂外展，双手随剑回到当前持剑待机 | 跨出小步制动，膝髋吸收惯性，最后恢复稳定站姿 |

起势/收势可从 Spin 提取后适配；旋转段以 Spinning 为上身参考，重做 Jason 腿脚。先制作独立候选 `Start / Loop / End`，不覆盖现有可回退资产。源角色较简化、缺少逐指骨链，手指继续采用当前武器实际握柄关系。

### 接入设计

- 当前第三人称旋风把单条 Spin 的中间 25%–75% 映射到整段旋转；控制器却沿 `WhirlwindFeel::Phase` 转两圈。改为按同一个累计旋转角采样循环与脚步，减速和命中停帧一起暂停，不再按单条动作的固定比例估算。
- 只扣除源动画的整体根朝向，再由角色提供 -720°；保留胸髋之间的小幅相对扭转。当前按骨盆方向扣整体朝向的方式会一并消掉部分蓄力，制作时需要区分根旋转与身体反拧。
- 腿部接管普通待机的脚锁定权重。支撑脚采用短暂脚掌接触，抬脚时释放约束；不把普通站立双脚锁定套到高速旋转上。结束后平滑交回原有地面 IK。
- 双手、剑体共用握持解算与动作时钟，头颈随胸廓自然转动，限制相对偏转并保留原生骨长；不让头部持续追踪固定世界方向。
- 保留伤害范围、命中去重、冷却、体力、攻速与命中停帧。保持此前普通三连击复用第一刀的设置。

本轮交付为来源比较、源轨迹记录和上述设计。尚未重做、导入或切换新的旋风动画，未进行运行测试或视觉验收。

## 2026-10-06 上挑与冲刺竖劈的候选调查

用户要求寻找可套用或参考的第三人称全身动作。本轮仅读取当前实现、筛选素材并取得免费候选源；没有修改运行配置、导入 UE 动画或启动游戏。

### 当前实现

- `Melee.FullBody.Uppercut` 仍引用 `J_Sword_Uppercut`。`Tools/PlayerBody/retarget_free_sword_jason.py` 用 `duration*(1-i/(count-1))` 将整条 KayKit Chop 倒序派生，起势和回收也一起倒放；它不是作者原生的上挑。
- `DashOverhead` 与普通 `Overhead` 均由 `FPSBodySwordMotion::Clip` 选到同一条 KayKit `Melee_2H_Attack_Chop`。当前只沿 `ActionEntryFraction` 缩短/对齐预备段，没有独立的冲刺制动全身片段。

### 新取得的免费参考

从 [Quaternius 官方 UAL2 免费入口](https://quaternius.itch.io/universal-animation-library-2) 取得 `Universal Animation Library 2[Standard].zip`，免费 upload id `17958478`。作者网页和包内 License.txt 均标注 CC0。没有取得收费 Source 档。

制作源目录为 `SourceAssets/ThirdPersonSwordCandidates20261006/`，其中 `UAL2-receipt.json` 记录来源、散列、文件表，`UAL2_Standard.glb` 是官方 Unreal/Godot 导出。`read_candidates.py` 读取 GLB 全身骨链及动画轨道，结果在 `source-trajectories.json`；未渲染，轨迹分析不等于 Jason 重定向观感验收。

| 已读取的源片段 | 时长 | 候选用途与限制 |
| --- | --- | --- |
| UAL2 `Sword_Heavy_Combo` | 4.333 s | 约 0.9–1.15 s 右腕从低位向前上方提起，可参考上挑的躯干发力；约 2.3–2.8 s 有举手过顶到向前下方落手的动作，可参考竖劈和沉髋。需要裁段、重新组织双手持握及收势。 |
| UAL2 `Sword_Dash` | 1.567 s | 可参考冲刺中的压低重心与落步；源右腕没有形成清楚的过顶预备，不能仅凭名称当作现成冲刺竖劈。 |
| 本地 KayKit Medium `Melee_2H_Attack_Chop` | 1.633 s | 当前已有 Jason 重定向和双手约束，可作为竖劈基础；需要单独制作冲刺进入、前脚制动和回位。 |
| 本地 KayKit Large `Melee_2H_Slam` | 2.833 s | 巨型角色的高举、重砸和停顿参考。体型、手距和动作幅度与 Jason 差异较大，不优先直接替换。 |

UAL2 中上述两条剑动作的左右腕明显分开运动：Heavy Combo 的双腕间距约 27–138 cm，Dash 约 29–146 cm。由源轨道推断，它们不满足当前双手固定同握剑柄的要求；应提取发力/脚步参考，再制作完整双手姿态。不能把它们直接描述成已可用的双手大剑成品。

### 推荐下一步

1. 上挑独立制作：下沉收剑到髋侧 → 蹬地伸髋 → 双手向前上方挑出 → 屈肘收回。参考 UAL2 上提段，保留当前 Jason 骨长及真实柄距，取消整段下劈倒放。
2. 冲刺竖劈独立制作并分配单独动作键：持剑跑步 → 现有短预备窗口举剑 → 前脚制动、向前下方竖劈 → 沉髋回位。以已有 Chop 的适配为基础，借鉴 UAL2 末段下斩，保留已有冲刺位移和命中时钟，不叠加源根运动。
3. 在本轮已读取的免费来源中，尚未确认可直接替换的原生双手上挑。当前候选属于可复用基础和动作参考，尚未重定向、保存新 UE 资产或切换运行引用。

### 后续制作（2026-10-06）

用户进一步明确：已有自制第一人称上挑，第三人称满足设计语义即可。已据此独立制作并后台保存 `SwordActions20261006/Animations/J_Sword_Uppercut` 和 `J_Sword_DashOverhead`，发布两个运行角色键。上面的“整段倒放”仅描述制作前的第三人称旧实现，不指自制第一人称上挑。具体作者源、时序和交付状态见 [第三人称上挑与冲刺竖劈](third-person-sword-actions-20261006.md)。
