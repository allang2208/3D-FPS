# M-07 盲祷者：Meshy 模型、布料与怪物接入

**2026-10-03 [V37 主体灰色材质修复](BlindSupplicantM07BodyMaterialV37.md)：V36 让身体材质分区的膜片折边参与布料，但遗漏了主体母材质的 Clothing 用途，日志明确显示引擎改用默认材质。主体材质槽与四张贴图完整；现已补齐用途、编译并后台实际保存，导入脚本同步补齐该设置。背膜物理、原外形、动作及数值保留，未游戏或视觉验收。**

**2026-10-03 [V36 巫婆式背膜物理](BlindSupplicantM07WitchClothV36.md)：用户反馈 V34／V35 缺少物理摆动，现保留 V35 修好的蒙皮，重做左右连续隐藏代理，复用当前 WitchRebuilt 下摆的稳定显示捕获、Chaos 配置和稀疏自碰撞。1,170 个模拟顶点、234 个固定点，根部固定、下缘渐放；身体材质中的膜片折边共用布料并统一接缝过渡。12 m 恢复、16 m 外渐退并暂停，死亡／击倒切回蒙皮。原显示网格、三档 LOD、代理和 AI/F6 蓝图已后台实际保存；commandlet 在保存后退出时出现 Python 插件异常，详情及构建状态见记录。未游戏或视觉测试，仍待用户体验。**

**2026-10-03 [V35 下部膜片蒙皮与法术数值](BlindSupplicantM07MembraneMagicV35.md)：V34 仍存在下缘扭曲，源排查定位到身体／腿部权重混入、接缝跳变，以及颈部长膜链对下缘的牵拉。现改为胸部主体支撑、同侧膜片小幅跟随、连续接缝权重，保留原几何和动作，重建距离 LOD。属性收益折算后的最终魔攻设为 60，火球／冰锥／闪电减伤前伤害为 144／120／132。原网格和 AI/F6 蓝图已后台实际保存，未游戏或视觉验收。**

**2026-10-03 [横扫命中体与移动加速](BlindSupplicantM07MeleeSpeed20261003.md)：用户反馈横扫无伤害。现用 V32 接触姿态的爪尖偏向侧面约 1 m，原爪尖小球漏掉正前方玩家；改为覆盖手掌到爪尖的胶囊，保留原窗口和单次结算。慢走／追击 42／86 → 63／129 cm/s，动画按实际速度同步 1.5 倍，步态切换阈值同步调整。Game／Editor 构建完成，原 AI/F6 蓝图已实际保存，未游戏测试。**

**2026-10-03 [低矮遮挡索敌与施法](BlindSupplicantM07MagicSight20261003.md)：首次发现、目标保持和施法起手改为头部到玩家上半身的直线可见性，释放从实际法术出口重新确认通路，火球／冰锥沿用提前量并避开被遮挡的预测瞄点。Game／Editor 必要构建完成，未测试。**

**2026-10-03 [V34 完整背膜统一驱动](BlindSupplicantM07CoherentMembraneV34.md)：从 V33 回退版继续，完整背膜使用原骨骼蒙皮，移除碎片布料捕获和粒子模拟；六片末端增加有限阻尼弯曲，额外手臂避让降至 4°。原几何、UV、权重及现有动作引用保留，原网格与 AI/F6 蓝图已实际保存。Game／Editor 构建完成，未进行游戏或视觉测试。**

**2026-10-03 [V33 收势转移动支撑与背膜回退](BlindSupplicantM07RecoverMembraneV33.md)：按用户要求离线复现两端贴地、混合中段脚底陷入约 22 cm，增加 M07 专用过渡支撑补偿，保留 V32 攻击主体和 V25 移动。用户否定 V31 背膜后，已从修改前备份完整恢复网格／布料包，并单独恢复蓝图中的原避让角度，保留最新动画引用。Game／Editor 构建及蓝图后台保存完成，未游戏测试。连续面片与统一驱动的新方案已记录但尚未接入，正式角色保持回退状态。**

**2026-10-03 近战腿部更新为 [V32 待机腿姿支撑](BlindSupplicantM07IdleLegSupportV32.md)：用户认可 V30 已贴地，但反馈小腿关节组合仍扭曲。现按实际 V20 待机校准膝盖弯曲方向和大腿／小腿旋转，整条腿共用待机弯曲平面，小腿只做同轴屈伸；收小骨盆位移，保留上身挥击和逐脚支撑。两段 2 秒攻击与原 AI/F6 蓝图已后台实际保存，无新增运行时 IK，V30 悬浮施法和 V31 背膜继续使用。未游戏测试，由用户体验。**

**2026-10-03 背膜更新为 [V31 代理与布料稳定性](BlindSupplicantM07MembraneStabilityV31.md)：按用户要求检查发现隐藏代理存在无固定点碎片及狭长面。保留原显示外形和蒙皮，清理隐藏模拟面、将无锚点碎片改为骨骼跟随，平滑活动掩码、收紧摆幅并调整阻尼与惯性；重新生成显示捕获，额外骨骼避让上限 18°→6°。新隐藏代理、原 V18 显示网格的布料绑定／配置及原 AI/F6 蓝图已后台保存，V30 动作等引用保留。完成源数据检查，未游戏测试或视觉验收，由用户试玩确认。**

**2026-10-03 近战腿部和施法更新为 [V30 脚底支撑与悬浮施法](BlindSupplicantM07SupportHoverV30.md)：从已保存 V27／V28 读取姿态，保留上身动作。近战改为逐脚支撑、短踏转脚、屈膝承重；施法缓慢升空约 40 cm，松膝垂脚，释放后下降并屈膝 recover，到 2.4 秒回站姿。两段近战、两段施法和原 AI/F6 蓝图已后台实际保存，命中／释放时间、技能数值、移动和 V29 死亡保留。纯动画修改，无新增运行时 IK 或原生构建；未测试，由用户体验。**

**2026-10-03 死亡更新为 [V29 按来袭反方向倒地](BlindSupplicantM07DirectionalDeathV29.md)：八段 2.8 秒的方向动作，正面受击后仰，侧后受击朝远离来袭方倒地；保持原朝向，骨盆带动全身失衡，双脚错时脱离支撑，肩臂滞后松落。死亡时按实际骨盆轨道选择一次，1.68 秒交给既有共享布娃娃。八段正式动画及原 AI/F6 蓝图已后台保存，Editor 必要构建完成；未游戏测试，由用户体验。V25 移动、V27 近战和 V28 施法继续使用。**

日期：2026-10-01。目标工程：`D:/FPS3D/FPSGAME`，UE 5.8.2。

**2026-10-03 [V28 动作库施法与近战距离](BlindSupplicantM07LibraryCastV28.md)：用户否定 V24 施法，现选本地 Vefects `SnappySpell_Vexa` 的完整左手施法，按解剖端点重定向带分段扭转骨的臂链，统一放慢后拆为连续的 1.1 秒蓄力与 1.3 秒释放。出手仍在释放后 0.30 秒，离身偏移仍为 65 cm。近战基础距离 180→220 cm，现有 1.5 倍下有效距离 270→330 cm；V27 近战动画与命中时序保留。两段正式动画、制作源与现有 AI/F6 蓝图均已后台保存，未游戏测试。**

**2026-10-03 用户认可 V27 攻击主体，恢复段另行修订：原近静止尾段后只有 0.3 秒全身回收，造成停住再快速复位。当前 `V27ContinuousRecovery` 从 1.0 秒开始身体、肩臂、手腕依次连续收势，2.0 秒回待机；前 1 秒逐骨姿态保留、命中合同保留。按本次要求完成离线曲线排查，左右正式动画及原 AI/F6 蓝图已后台保存；未游戏测试，恢复段仍由用户体验。**

**2026-10-03 V27 下陷修订：用户反馈攻击陷入地下。已禁用把地面根运动写入 pelvis 的操作，保留真正骨盆重定向，并以实际脚底蒙皮烘焙竖直接地。仍使用 V27 左右攻击路径与原时序；修订 `V27PelvisGroundingFix` 的原生素材、可编辑源、导出及两段正式资产和蓝图均已后台保存，未游戏测试。**

**2026-10-03 当前攻击为 [V27 动作库完整挥击](BlindSupplicantM07LibrarySweepV27.md)：用户否定 V26 的整臂扭曲、身体穿模与打击感，要求直接选库复用。现采用 `ZombieAnimationPack/anim_Attack_D` 完整踏步转体挥抓，UE 原生重定向，四肢对应关节复制，肩部整体避让并制作左右版本。两段 2.00 秒动画与现有 AI/F6 蓝图已后台保存，命中窗口同步到 0.50–0.70 秒。V25 移动、V24 施法保留；未测试，由用户体验。**

**2026-10-03 [V26 百目原参考整臂横扫](BlindSupplicantM07ReferenceChainSweepV26.md) 已被用户否定并由 V27 替换：当时使用百目实际 `Attack_Biped_Melee_A` 肩肘腕与身体数据，以当前自然待机校准单一肘铰链并限制转掌；保存成功后用户仍反馈扭曲、身体穿模和打击感弱，因此该解算不得作为已认可的横扫模板。**

**2026-10-03 [V25 移动避让与重制横扫](BlindSupplicantM07ClearanceSweepV25.md)：移动继续使用，横扫已因用户反馈扭曲由 V26 替换。V25 保留原腿脚与步频，将摆臂留在身体前侧并烘焙组织避让；原生节点改为组织宽度采样、完整爪部胶囊与 LOD 分档的有限修正。当轮四段动画与现有 AI/F6 蓝图实际保存，Game 构建完成；因 UE 占用延后的 Editor DLL 构建已在 V26 交付时补齐。未测试，不宣称无穿模或已获得性能收益。**

**2026-10-03 最新施法引用为 [V24 联动施法与前移蓄积](BlindSupplicantM07FlowCastV24.md)：重制沉身蓄势、肩肘前送、腕掌与手指错时释放、右臂配重及缓慢收手；蓄力／释放各 1.10 秒，出手仍在释放段 0.30 秒。火球和冰锥蓄积中心沿角色正前方前移 65 cm，并从同一点发射。两段动画、原 AI/F6 蓝图及偏移属性已后台实际保存，必要 Editor/Game 构建完成。V23 移动及其余动作保留；未运行、渲染或测试，待用户体验。**

**2026-10-03 最新移动引用为 [V23 内向掌心与随步摆臂](BlindSupplicantM07InwardArmSwingV23.md)：用户反馈 V22 腿脚基本没有问题，但手部僵硬、掌心朝外。本轮复制 V22 原腿脚、骨盆、胸背及背膜曲线，只修改锁骨与臂掌，让掌心分别朝身体内侧，整臂按对侧迈步摆动，肘腕小幅跟随。两段动画与原 AI／F6 蓝图已后台实际保存，3.2／2.4 秒周期和 42／86 cm/s 速度保持原值。本轮未运行、渲染或测试，手部修订仍待用户体验。**

**2026-10-03 [V22 沉重慢步与全身联动](BlindSupplicantM07HeavyGaitV22.md) 是 V23 保留的腿脚与身体动作基础：用户要求重新开发类似巨人／机器人的缓慢步态。慢走／追击的 3.2／2.4 秒循环、42／86 cm/s 制作源及游戏速度已制作并后台保存。用户随后反馈腿脚基本没有问题，手部由 V23 继续调整；不作为整身动画已验收的记录。**

**2026-10-03 早前曾按用户要求保持 V21 并整理发布，随后用户重新授权本轮移动动画开发。327 份退役制作文件已归入本机 trash，当前资产与有效制作输入保留，经验同步至怪物 SKILL；当时源码公开范围、恢复依赖和未验收边界见 [本次整理发布](BlindSupplicantM07Publication20261003.md)。**

**2026-10-03 [V21 完整参考跑姿](BlindSupplicantM07FullReferenceGaitV21.md) 已由 V22 接替：当时重新观察指定视频前方中央角色的连续姿态，重制明显屈肘、腰胯前持／回收、落脚后下沉、折膝收跟及骨盆／胸肩联动。两段独立动画与现有 AI/F6 蓝图引用曾后台实际保存；当时制作源和游戏速度为慢走 120、追击 210 cm/s，满速预期周期为 1.667／1.333 秒。用户随后表示仍不符合预期；该版不作为认可模板。**

**2026-10-03 [V20 掌心、整臂与提前量](BlindSupplicantM07PalmArmMotionV20.md)：移动引用已由 V21 接替；该版待机、左右横扫整臂起势／收势和左右镜像卷指继续保留。五段独立动画及现有 AI/F6 蓝图引用当时已后台保存。火球／冰柱在实际出手帧按目标速度和弹速计算提前量，闪电瞄准释放时位置；Game／Editor 构建已完成。原模型、UV、权重、83 骨参考、背膜／布料、技能数值及 CD 保留；未运行游戏或测试。**

**2026-10-03 V19 移动基础曾接入 [V19 指定视频参考候选](BlindSupplicantM07VideoLocomotionV19.md)：实际读取用户指定视频 2:00–2:05 的怪物 Jog，以本机 CC0 完整人形动作作基础适配微前倾、低手屈肘、骨盆／胸肩联动与普通人体膝关节。两段独立动画及现有 AI/F6 蓝图已后台保存；V18 显示模型、83 骨参考、原权重、背膜、布料和其余动作保留。AI 速度仍为 160／360 cm/s，源速度为 135／270 cm/s，追击实际预期循环约 1 秒。原付费动作轨道未取得，这是视频参考仿制候选；未运行游戏或测试。**

**2026-10-02 [V18 全身动作与低成本背膜接触](BlindSupplicantM07BodyMotionV18.md)：左右横扫让非攻击手保持自然下垂，加入骨盆向前压重与胸肩跟进；重新制作慢走／追击的支撑、步频和全身配合。保留 V17 原显示几何、UV、83 骨参考、V16 手臂及 V17 腿部权重，重做原背膜臂侧接触代理，采用有限鳃骨避让与近距低密度布料。新版模型、代理／布料／LOD、四段动作及 AI/F6 蓝图已实际保存，原生默认引用与最终 Editor/Game 构建均已完成。未运行游戏或性能测试，由用户从 F6 重新生成测试。**

同日移动修复已落盘：原 V18 慢走／追击制作时误沿用权重源的 `REST` 模式，FBX 烘焙为恒定 T 字参考姿态。现已切换 `POSE` 重新制作并替换两段动作、保存原 AI/F6 蓝图，原模型及其他 V18 资产保留；详见上述 V18 记录和 `BodyMotionV18/ue_locomotion_export_repair_v18.json`。未运行游戏测试。

2026-10-03 另修复主场景导航加载：M07 的 V08 导航 Actor 曾持久保存强制载图重建，用户测试期间处于 395.35 秒的空网格重建窗口，导致追击目标投影失败、速度为零。现已关闭该标志并后台重建、实际保存 DayNight_Lighting 的 92 个 M07 tiles，保留现有体型规格和 Dynamic。回执为 `BodyMotionV18/NavigationLoadRepair/ue_navigation_load_repair_v18.json`；必要 Editor 构建已完成，未运行游戏测试。

**[V16 手臂连续蒙皮与有力横扫](BlindSupplicantM07ArmSweepV16.md) 的手臂权重继续沿用，横扫由 V18 接替：重求 13,011 个肩肘腕身体顶点，横扫恢复百目的重心转移、腰肩先行、快速横掠和跟随，左右运行时长约 .85／.92 秒。近战播放倍率 1.30，命中窗口同速换算，近战伤害 36。V16 独立模型留存为历史候选；V17 从该原模型继续局部修改腿部。**

**[V15 死亡接地与全身动作](BlindSupplicantM07MotionRecoveryV15.md) 的死亡已由 V29 接替，施法已由 V28 接替，魔法冷却合同继续沿用。V17 的共同膝铰链与局部腿权重保留；V15 当时在 1.44 秒交给物理，当前 V29 为 1.68 秒。火球、冰柱和闪电按正式玩家一级技能默认 CD 统一为 12 秒，积蓄起手计时、未释放被打断退回冷却，更换元素不能绕过整体施法间隔。**

**[V14 百目式横扫与三元素施法](BlindSupplicantM07CombatMagicV14.md) 的三元素执行器、默认魔攻 40 与基础伤害 64／56／60 继续沿用。V14 左右横扫由 V16 接替，移动、死亡、施法动作与 CD 由 V15 接替；V14 独立冷却 8／10／12 秒是历史数值。**

**2026-10-02 V12 已被用户判定失败，反馈为膝部错位、攻击扭臂和严重卡顿。[V13 原模型局部修复](BlindSupplicantM07OriginalV13.md) 是当前模型的几何、UV、布料、三档 LOD 和身体碰撞基础；手臂与腿部局部权重先后由 V16、V17 接替。采用的巫婆稀疏自排斥和距离渐退方案继续保留。运行表现由用户测试，未宣称合格。历史 [V12](BlindSupplicantM07RunningCollisionV12.md)、[V11](BlindSupplicantM07HandsArmsV11.md) 和 [V09](BlindSupplicantM07OriginalV09.md) 记录保留。**

## V05 制作与接入历史（已被用户否定）

补做胸肩、颈部、腰腹、骨盆和双侧大腿到膝部的连续表面，以关节轴线的最小旋转拟合保留皮肤；成熟手指权重、原感知头及装具保留。动作沿用 V04 的父骨转换与参考帧修正，网格与动作使用统一厘米参考和骨架命名，重新制作布料与碰撞。

历史保存回执：`SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryV05/ue_anatomy_delivery_v05.json`。组合可编辑源：同目录 `M07_AnatomyAndMotion_V05.blend`。用户已否定 V05；供体身体及补建表面没有继续进入 OriginalV06。V04 保存记录仍保留在 `BlindSupplicantM07RecoveryV04.md`，用户亦已否定其外观。

## V03 制作与接入历史（已被用户否定）

V03 曾将供体皮肤分区作为整身，并导出唯一左右手和成熟关节/五指权重；本轮发现该供体缺少衣物覆盖的骨盆与大腿，因此此前“连续人体”的称呼不准确。原多眼头及装具、身体 UV 图集、鳃膜与代理保留作历史输入。

12 段身体动作重新制作；慢走/追击复用巫婆 Foundation 的完整 Quinn 步态并做长肢适配，上肢使用稳定解剖肘平面、弯肘余量、腕部旋转分担与自然轻曲手指。运行代码同步两种步态的支撑相位和初始播放倍率。实际是否自然、关节是否合格，由用户从 F6 重新生成观察。

实际回执为 `SourceAssets/BlindSupplicantM07Meshy20261001/Authoring/AnatomyV03/ue_anatomy_delivery_v03.json`；完整模型与动作编辑源为同目录 `M07_AnatomyAndMotion_V03.blend`。本轮没有启动编辑器或游戏，也没有截图、渲染、播放布料或自动测试。

## V02 制作与接入历史

本次使用用户在 Meshy 网页生成并提供的 `Meshy_AI_Veilwing_07_1001123357_texture.glb`，身高按约 3.1 m 制作。V02 保留原头部、装具、暴露主体和身体 UV，修正主体权重，将六片鳃膜改为依据原轮廓及肩背连接重建的连续几何；它不是原高模的精确自动切分。多眼感知头部、长臂与五指、编号颈环、旧腕箍和背部监测装具继续保留。

现有 `BP_BlindSupplicantM07` 已保存新显示资产 `SK_M07_ContinuousV02` 的引用，12 个身体动作的预览模型引用已同步保存，动作轨道和骨架保留。新显示资产从 FBX 直接导入正确厘米坐标及根骨参考尺度 100，六片膜共用一个含六岛的布料资产，按所属膜片捕获映射；身体碰撞复用按同一参考帧重建并保存的 `PA_M07`。旧 `SK_M07` 保留为失败版记录。

原生角色和动画类沿用已有共享 Behavior Tree、战斗与击倒流程，F6「怪物生成」中的 **「盲祷者 M-07」** 入口保留。此前保存的声音、12 个身体动作及 DayNight_Lighting 地图中的 312 cm 导航继续沿用；本轮没有重新运行导航或游戏测试。

| 制作项 | 当前状态 |
| --- | --- |
| 原始模型与 V01 制作源 | 保留，用于来源追溯及失败版记录 |
| V02 Blender 源、连续膜、曲面代理、图集与 FBX | 已保存 |
| `SK_M07_ContinuousV02`、`M07_Gills`、`PA_M07`、角色蓝图及 12 动作的预览引用 | 已实际后台导入或更新，并保存 |
| 单资产六岛布料与同片捕获映射 | 已保存；12,524 个显示点由布料捕获，1,126 个保留蒙皮；3,666 模拟点、6,624 三角形、286 固定点，最大位移 8 cm |
| 布料身体碰撞 | 引用已保存的现有 `PA_M07`，16 个物理体、15 个约束；片间自碰撞设置已写入 |
| 必要 Editor／Game 构建 | 后台构建成功；不代表运行验收 |
| 共享 AI、战斗、受击、死亡布娃娃、F6 注册与既有导航 | 接入保留；运行效果由用户测试 |
| 轮廓、肩背连接、蒙皮、布料摆动、动作接触、AI 与性能体验 | 本轮未运行、未截图、未渲染、未做视觉或用户验收 |

V02 按用户工作规则完成必要后台制作、构建、导出、实际导入和保存，没有为查看结果主动启动 UE 编辑器或游戏。`Saved/BuildEditor/m07-FPSGAMEEditor-20261001-234118.log` 与 `m07-FPSGAME-20261001-234145.log` 记录构建成功；`Saved/Logs/M07Import-20261001-234940.log` 末尾记录 `Python script executed successfully`。构建成功、包保存和运行效果分别记录，没有运行证明旧截图中的长三角片已消失。

V02 最终状态以 `SourceAssets/BlindSupplicantM07Meshy20261001/Authoring/FragmentRepairV02/ue_fragment_repair_delivery.json` 为准，记录 `saved=true`、`runtime_tested=false`、`visual_tested=false`。根目录的 `production_status.json`、`gameplay_delivery.json` 保留此前制作及游戏接入记录；最初的 `ue_delivery.json` 记录首轮导入历史，不代表当前 V02 资产状态。

## 用户测试入口

由用户自行打开 UE 的 `D:/FPS3D/FPSGAME/FPSGAME.uproject`，进入现有测试地图 `/Game/GameMaps/DayNight_Lighting`，在 F6 的「怪物生成」中选择 **「盲祷者 M-07」** 并重新生成角色，观察新保存的 V21 移动、V20 横扫、现有鳃膜避让及运行流畅度。生成目录使用真实角色蓝图：

```text
/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07.BP_BlindSupplicantM07_C
```

该怪物约 310 cm 高，导航净空按 312 cm、半径 50 cm 制作。首次可在开阔、有导航覆盖的位置生成一只；狭窄走廊和低门洞是否允许通行应符合该体型。F6 注册的生成占地参数为 100 cm。

用户可按实际体验关注六片膜与身体的避让、逐片呼吸、长肢体蒙皮和脚底接触、追击及左右交替攻击、受击和起身、死亡向布娃娃的过渡。贴墙倾听发生在闲置且正前方约 120 cm 内有墙面时；角色进入追击、攻击、受控或死亡状态会中断该演出。上述是使用说明，本任务没有自动运行这些测试。

## V02 历史保存 UE 资产

以下路径均属于 `/Game/Monsters/BlindSupplicantM07/`。

| 路径 | 内容 |
| --- | --- |
| `SK_M07_ContinuousV02` | V02 当时的角色显示资产；原主体与六片重建连续膜，保留其厘米坐标和根骨参考尺度 100 |
| `SK_M07` | 已被替换的失败显示资产，保留错误单位重导入记录；当前角色不使用它 |
| `SK_M07_Skeleton` | 完整人体、五指和鳃膜骨链，共 81 骨 |
| `BP_BlindSupplicantM07` | 角色蓝图，父类 `ABlindSupplicantMonster`，保存模型、动作、声音和 AI 引用 |
| `PA_M07` | 按 V02 正确参考帧重建并保存的现有资产；16 个人体物理体、15 个约束，用于身体及布料碰撞、查询、击倒和死亡布娃娃 |
| `Animations/A_M07_GillBreathing_Source` | 四秒鳃膜骨链呼吸源动作 |
| `Animations/A_M07_Idle` 等 12 个动作 | 待机、缓行、追击、左右近战、受击、死亡、贴墙倾听、眩晕、倒地及两种起身 |
| `Materials/M07_Body` | 原始身体 PBR，已保存 Skeletal Mesh Usage |
| `Materials/M07_Gills` | V02 六片连续膜共用组织材质与一个显示 section，使用 3×2 连续 UV 图集 |
| `Materials/M07_Gill_01` 至 `M07_Gill_06` | V01 六片独立组织材质历史记录 |
| `Textures/T_M07_Gills_V02_*` | V02 膜片 BaseColor、Roughness、Metallic、Normal 图集 |
| `Textures/T_M07_base`、`T_M07_rough`、`T_M07_metal`、`T_M07_normal` | 原始 2K PBR 通道；法线按 UE 约定翻转绿色通道 |
| `Audio/SW_M07_WallMimic` | 八秒临时内部求救声，空间声源附着头部 |

AI 控制器使用项目现有 `/Game/Monsters/AI/BP_MonsterAIController`，并沿用共享 `BT_Monster`。本次没有另建与共享树竞争目标和移动控制的 AI 状态机。

## V01 身体与六片鳃膜制作历史

本节保留用户已否定版本的制作记录，以下自动分区、多显示 section、2,162 个代理点及 10 cm 位移预算不代表当前 V02。当前六片膜采用原轮廓参考下的连续几何重建，源数据、权重、绑定和参考帧修订见 [V02 文档](BlindSupplicantM07FragmentRepairV02.md)。

原始 GLB 已原样保留。其 SHA-256 为 `06acb6cf86a78ed3c53a1150cff77ba05636c1ea56cfc3b3044e92b70f0e69bc`，含 933,829 个顶点、1,745,634 个三角形，原文件没有骨架、蒙皮或动画。原表面分配到主体与六个鳃膜显示区域，暂未主动减面。该面数属于原始外观母版，不能称为已经优化的运行预算。

人体重建采用巫婆工作流中的整身人体源：`SourceAssets/WitchMeshy20260919/Authoring/LayeredV04/Sources/Nurse_SourceSkinWalk.fbx`。保留完整源后进行连续体型适配，并派生被膜片遮挡的身体填补网格；未拼接其他手脚或替换 Meshy 感知头部。

六片显示区依据人体保护体积和膜层导向进行网格测地分区。自动分界、人体贴合、填补区域纹理投射和初步蒙皮仍需用户看实际动作后确认，不能声称已精确还原原画六片自然连接边界。原始材质是不透明单材质且没有透明贴图，本次 UE 组织材质独立设置双面半透明；现有输入为 2K，不能称为 4K 贴图成品。

六片低密度模拟代理共 2,162 顶点、3,778 三角形。肩背连接根部共 114 个固定顶点，自由区域最大位移 10 cm；人体避让使用 11 个骨骼局部胶囊。Blender 中六片显示网格已绑定对应代理的 Surface Deform，碰撞网格按人体骨骼驱动。默认关闭 Blender 布料制作模式，显示网格保持原 Armature 蒙皮；制作源中的 Text 块 `M07_ClothAuthoringMode.py` 提供模式开关，避免骨骼与代理重复施加位移。

本次多层互碰制作方案把六个不相连的物理膜片合并到同一粒子集合，六个显示 section 保留各自的捕获映射，并将捕获粒子索引映射到共用模拟网格。专用 `UM07InteractingClothingAsset` 继承巫婆的稳定捕获类，解决普通衣物类重复绑定 LOD 时只允许首个显示 section 的限制。共用 Chaos 自碰撞厚度按 1 cm 制作，使用同一组人体胶囊。此方案的最终包保存状态见本页首表及最新制作回执，不能以单独打开六个衣物自碰撞开关声称片间互碰完成。

呼吸来自六组具有相位差的鳃膜骨链，衣物求解负责垂坠、摆动与避让；骨链收缩展开和低密度布料共同驱动活体“斗篷”。本次没有播放布料模拟或渲染，因此不声称已确认膜片穿插、摆幅和最终透明效果。

## 动作与战斗接入

身体动作全部导入同一 `SK_M07_Skeleton`，源按 30 fps 制作，水平移动采用原地动作。缓行沿用实际 Nurse 源步态，通过源／目标静止骨架和尺度数据适配 M-07 长肢体；追击为该步态的加速及幅度调整。待机、长臂左右攻击、受击、死亡和贴墙倾听是本次 M-07 编排，不称为独立捕捉的动作。

| 动作资产 | 时长 | 用途 |
| --- | --- | --- |
| `A_M07_Idle` | 4.0 s | 低头垂臂待机及分相呼吸 |
| `A_M07_SlowWalk` | 3.3 s | 缓行 |
| `A_M07_Chase` | 1.5 s | 追击，按实际速度调整播放率 |
| `A_M07_MeleeLeft` | 1.5 s | 左侧长臂攻击，伤害接触点 0.68 s |
| `A_M07_MeleeRight` | 1.667 s | 右侧长臂攻击，伤害接触点 0.78 s |
| `A_M07_Hit` | 0.9 s | 共享受击流程的方向性演出 |
| `A_M07_Death` | 2.4 s | 播到 60% 后从同一采样姿势转布娃娃 |
| `A_M07_WallListen` | 3.2 s | 闲置贴墙倾听 |
| `A_M07_Dizzy` | 2.4 s | 眩晕循环 |
| `A_M07_Fall` | 0.833 s | 击倒 |
| `A_M07_GetUp` | 1.5 s | 仰面起身 |
| `A_M07_ProneGetUp` | 2.3 s | 俯卧起身 |

`ABlindSupplicantMonster` 复用 `ANurseZombie` 的生命、状态、奖励、尸体和共享战斗权威；`UBlindSupplicantAnimInstance` 负责 M-07 骨架上的动作表现。近战左右交替，接触窗口默认 0.16 s，伤害继续使用共享攻击时钟；没有在动画中增加第二套伤害计时。受击、弹反、眩晕、击倒和起身沿用现有组件合同，枪械受击是否进入硬直仍由共享武器与韧性规则决定。

死亡动作默认在 1.44 s，即 2.4 s 的 60%，采样并保持当时身体姿势，再由共享击倒组件启动死亡布娃娃。尸体冻结后暂停衣物模拟；奖励及死亡抢占继续由父类处理。该过渡已经编写和接入，实际连续性仍由用户测试。

为使 F6 入口可用，角色保存了可编辑的临时数值：基础生命 420、伤害 36、等级 7、精英、经验 360、缓行 90 cm/s、追击 145 cm/s、基础攻击范围 180 cm、警戒半径 1,400 cm、尸体时间 18 s。生命等最终运行值仍受项目共享倍率和战斗规则影响。这些数值属于本次接入初值，尚无用户平衡性确认。

## 感知身份与临时声音

设计身份是深层收容区的感知型实验体：研究人员把鳃膜当作新增感知器官，而它实际正成为岩层深处某个庞大存在的“耳朵”。名字中的“盲”不构成删除原画多眼头部的依据。膜片继续表现为蓝灰分支纹路的活体半透明组织，保留肩背连接、层叠边缘和斗篷剪影。

贴墙演出在闲置时以每秒一次的有限距离查询寻找正前方竖直墙面，随后切换倾听循环并播放头部空间求救声。它不改变共享树的目标选择与移动，不新增穿墙感知或声音诱饵技能。进入战斗、受击、击倒、死亡或结束角色生命周期时中断声音和倾听。声音重播间隔默认 24 s，音量 0.65。

临时声音文本为“有人吗……救救我……”，由本机离线 Microsoft Huihui Desktop 中文语音生成，叠加低声呼吸和设施反射后保存为八秒、44.1 kHz、单声道 PCM16 WAV。`Audio/audio_production.json` 与 `tts_source.json` 保存来源和制作参数。它是本地内部原型声音，未冒充真人配音成品，公开再分发条件尚未单独确认。

## 导航与 F6

角色胶囊半径 50 cm、半高 155 cm，NavAgent 半径 50 cm、高度 312 cm、台阶 40 cm。关闭按角色胶囊自动覆盖 NavAgent，避免把 312 cm 规格改回普通人形。`Config/DefaultEngine.ini` 追加 `BlindSupplicantM07` SupportedAgent，保留现有各代理的索引与参数。

导航制作入口为 `UBlindSupplicantNavigationAuthoring`，目标 `/Game/GameMaps/DayNight_Lighting`。制作流程使用对应 SupportedAgents 和导航覆盖体，执行实际 Recast 构建，再保存地图；异步加载锁仅在无界面制作流程完成加载后解除，已有编辑器中的未保存地图不直接覆盖。最终落盘使用已运行编辑器中的原生代理配置、同步 `RebuildNavigation` 和 `save_map`，用户退出 PIE 后已完成构建与保存。`gameplay_delivery.json` 的 navigation 部分记录此次保存操作；本任务未运行寻路或游戏验收。

F6 注册位于 `Source/FPSGAME/Development/DevelopmentSpawnComponent.cpp`，ID 为 `BlindSupplicantM07`，中文标签为「盲祷者 M-07」，引用已经保存的真实蓝图类。本次没有把它自动放置到关卡，也没有自动进入 PIE。

## 制作源与可继续编辑的文件

制作根目录：`D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/`。

| 文件／目录 | 内容 |
| --- | --- |
| `Original/Meshy_AI_Veilwing_07_1001123357_texture.glb` | 用户选定的网页外观母版，原样保留 |
| `Inputs/M07_original_concept.png`、`front.png`、`side.png`、`back.png` | 原图与独立正侧背参考，比例参照人、标签、环境和特写不进入模型输入 |
| `M07_Meshy_Web_ThreeViews.zip` | 已交付的三视图及中文网页生成说明 |
| `Authoring/M07_Separated_Master.blend` | 完整人体源、主体、六片显示膜、骨架、初步蒙皮、模拟代理、碰撞与呼吸源 |
| `Authoring/cloth_ue_manifest.json` | 六片固定点／位移与 11 个人体局部碰撞胶囊数据 |
| `Authoring/blender_cloth_binding.json` | 六片 Surface Deform 与人体碰撞源保存回执 |
| `Authoring/BeforeInteractingGills/SK_M07.uasset` | 合并膜片模拟前的六片物理源备份 |
| `Authoring/DayNight_Lighting.before-m07-navigation.umap` | 导航制作前的本任务地图备份 |
| `Delivery/SK_M07_Display.fbx` | 显示模型和骨架，模拟代理不进入显示 |
| `Delivery/SK_M07_ClothBuildSource.fbx` | 显示模型、骨架和六片低密度衣物代理 |
| `Delivery/A_M07_GillBreathing_Source.fbx` | 独立鳃膜呼吸源 |
| `Motion/M07_GameplayMotion.blend`、`motion_manifest.json` | 八个身体／身份动作源、实际体型适配和接触时点记录 |
| `Motion/M07_ControlMotion.blend`、`control_motion_manifest.json` | 眩晕、倒地和两种起身源及出处 |
| `Motion/A_M07_*.fbx` | 12 个已导入 UE 的身体动作导出 |
| `Audio/M07_WallMimic_RawHuihui.wav`、`SC_M07_WallMimic.wav` | 离线语音原始文件及带呼吸／反射的导入源 |
| `Textures/` | 原始 2K PBR 和拆出的通道 |
| `Authoring/FragmentRepairV02/` | 当前 V02 制作源、连续膜、图集、FBX 和最终保存回执 |
| `production_status.json`、`ue_delivery.json`、`gameplay_delivery.json` | 此前总状态、首轮外观保存历史及游戏接入回执；当前修订以 V02 最终回执为准 |

制作脚本位于 `Tools/BlindSupplicantM07/`：模型和 Blender 布料分别使用 `author_character.py`、`bind_blender_cloth.py`；身体动作使用 `author_gameplay_motion.py`、`author_control_motion.py`；物理和声音分别使用 `author_physics.py`、`author_mimic_audio.ps1/.py`；UE 资产分别由 `import_assets.py`、`import_gameplay.py` 保存。重建模型源会影响后续绑定和动作，不应把初始建模脚本当作无条件续跑入口覆盖已经完成的修改。

原生代码位于 `Source/FPSGAME/Monsters/`：`BlindSupplicantMonster`、`BlindSupplicantAnimInstance`、`BlindSupplicantAuthoring`、`M07InteractingClothingAsset`、`BlindSupplicantPhysicsAuthoring` 和 `BlindSupplicantNavigationAuthoring`。共享数值和战斗仅增加 M-07 识别分支。

`build_editor.ps1` 提供必要 Editor／Game 构建；`run_import_background.ps1` 执行无界面导入和保存。已有目标编辑器运行时，制作通过现有批次桥进行，不另起进程覆盖它已加载或未保存的资产。本次没有主动关闭、重启编辑器或向其他对话发送协调消息。

V02 制作入口位于同一工具目录：`repair_source_v02.py` 保存连续几何、权重与图集，`import_unified_frame_v02.py` 实际导入新厘米参考帧资产并保存布料、身体碰撞、角色及动作预览引用，`complete_fragment_repair_v02_background.ps1` 负责必要后台构建和导入。该次后台执行已经完成；后续观察由用户自行开 UE 并通过 F6 重新生成角色。

## 输入路线与来源记录

用户选择的是 Meshy 网页路线，本次没有提交 API 付费生成。保留的 `meshy_settings.json`、`meshy_pipeline.py` 和 `run_meshy.ps1` 属于 API 备选入口；`api_execution_enabled` 保持关闭。再次生成需由用户另行指定，不能为本地布料或动作精修自动重抽外观候选。

原图由用户提供，三视图衍生由内置 imagegen 制作，三维外观母版由用户在 Meshy 网页生成并选定。原图和模型未公开发布；账户档位及资产使用条件随实际下载来源记录。人体步态沿用项目已有 Nurse 来源；控制动作继续使用项目现有 CC0-1.0 源，具体仓库、提交、许可文件和适配路径保存在 `Motion/control_motion_manifest.json`，其中 Mesh2Motion 源提交为 `2d3d1ff03247d9e7e830d1ae375653da4e2146e2`。

本次参考工作流为本机的 `ue5-monster-workflow`、其 `meshy-humanoid.md`／`robed-humanoid-recovery.md`，以及 `asset-model-workflow` 的 Meshy 管线资料。实际交付路径按用户已选网页模型继续本地开发；源制作、包保存和用户测试保持各自明确的状态。
