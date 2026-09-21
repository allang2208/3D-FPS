# 陨星与灼锋焰甲

案例 `Docs/Skills/fire-magic-migration-20260921.md`，实际配置 `Content/ColdSteelData/skills.json`。两项使用 `FPSFireMagicComponent`，模型为 `ColdSteelFireMagicModel.cpp`，陨星 Actor 为 `FPSMeteorStrike`。原 game-dev 数值保留 K=1..20，范围每单位1.5cm，不套用后续调整过的火球伤害公式。

- 用户指定 `meteor.requiresStaff=false` 先直接施放；保留开关与已有 staff 词条接口，不能声称完整法杖已迁移。
- 陨星原版最终实现无地面预警红圈：实体燃烧岩体、0.65秒坠落、中心全额至边缘半额爆炸、2秒眩晕、3层灼烧、每0.5秒火场及叠灼烧；火场无油面。三维落点用准星，地面/顶板射线忽略身体，伤害筛选保留地层与遮挡。
- 焰甲12→30秒，非魔法有效命中追加独立魔法伤害，光环每0.5秒；不增加防御。武器火焰取实际刀刃/枪口端点，脚边显示环不代表完整伤害半径。
- 附伤必须清除 ActiveTrainingHit / ActiveFireballRewards 上下文，避免计作武器精通击杀或吞掉角色即时击杀奖励；不回调武器结算入口，不递归触发。
- 火场/焰甲结束汇总技能XP，多目标按某一轮有效可修炼命中至少两个判定。死亡/切场景清理不交未结束修炼。版本16补入新技能和冷却；活动效果不存档。
- VFX作者入口 `Tools/Skills/build_fire_magic_assets.py`，独立 `/Game/Skills/FireMagic20260921`。继承青铜火把 / Vefects火焰时保留 System 生命周期和 SpriteAlignment绑定。岩体为暗色实体加熔裂纹，不使用透明火苗替代主体。原火球资产保持原路径与现有效果。
- PNG制作源、原音频转码及出处在 `SourceAssets/FireMagic20260921`，恢复工具 `prepare_fire_magic_sources.py` 与共用技能图标恢复清单。已完成制作/保存及必要Editor构建，未测试、未PIE、未渲染验收。

## 当前火焰 RealisticV5（2026-09-22）

用户不满意 SplineV4，授权改用现有其他素材。当前路径 `/Game/Skills/FireMagic20260921/RealisticV5`，作者 `Tools/Skills/build_fire_magic_realistic.py`，七阶段同下。焰甲/火场采用 Realistic Vol.2，陨星包覆火采用 Military Trench，爆燃采用 Realistic `P_Explosion_Big_A` 来源材质。读取原 Cascade 参数后适配 Niagara；图集分别 8×4、6×6、12×12，动态 X/Y 是遮罩偏移/透明度指数，爆燃 X 是 Glow。保留完整原材质图并补曝光补偿，按项目曝光缩减源 HDR 参数。记录 `Docs/Skills/fire-magic-realistic-v5-20260922.md`；资产与常规 Editor 构建完成，未进行实机/视觉测试。写实 V3 岩体和游戏规则保留。

## 历史候选 SplineV4（2026-09-21）

用户要求试用 Free Spline VFX。V4 两项技能的火焰曾统一来自 `_SplineVFX` 的 FireFlame / FireFury 8×8 序列，烟气来自同包 fog3。作者 `Tools/Skills/build_fire_magic_spline.py`（materials、weapon、aura、mantle、trail、ground、impact），输出 `/Game/Skills/FireMagic20260921/SplineV4`，具体运行/预载路径与参考方案见 `Docs/Skills/fire-magic-spline-vfx-20260921.md`。原系统含样条依赖与 Self 循环，采用项目独立 Niagara 适配，保留连续层 System 生命周期、SpriteAlignment 和软边材质，不原样搬运整套样条系统。陨星保留 RealisticV3 岩体、0.65 秒命中和玩法数值，加入世界空间尾焰扰动、烟气、错相位爆燃与淡出。原火球和资产包不改。未进行游戏/效果测试，不能记为用户已认可。

## 图标、动作与 V2 作者链（2026-09-21）

SplineV4 黑焰修复：用户实机反馈火焰全黑。实际新火焰母材质缺少火把已使用的 `EyeAdaptationInverse`，曝光压低 RGB 而 AlphaComposite 继续遮挡背景。当前 `M_SplineFireSoft` 和烟气副本 `M_SplineSmoke` 的最终发光均加入曝光补偿，原透明度/DepthFade/软边与帧序列保持；作者 `build_fire_magic_spline.compensate_exposure()` 同步。三个实例的连接已定向检查、材质已编译保存，未做实机效果测试。不要仅放大 EmissiveGain，也不要修改全场景曝光解决局部火焰。

**陨星主体后续更新：** 用户反馈 V2 岩体和蜂窝熔裂纹偏卡通，当前主体切到 `/Game/Skills/FireMagic20260921/RealisticV3/SM_MeteorNaturalRock` 和 `MI_MeteorNaturalRock`。来源是 RuralAustralia Rock_M_02 模型与完整原材质副本，仅居中缩放、轻度烧黑，保留真实纹理、粗糙度、法线，不再添加程序熔裂纹或自发光。作者 `Tools/Skills/build_meteor_realistic.py`；记录 `Docs/Skills/meteor-realistic-assets-20260921.md`。下文 V2 的图标、动作仍在用；V2 火焰先后被 SplineV4、RealisticV5 替换，旧系统与岩体保留为重建链输入。未进行游戏或视觉验收。

详见 `Docs/Skills/fire-magic-polish-plan-20260921.md`。六边图标为 `meteor_hex.png` / `flame_armor_hex.png`，不要恢复为旧方框。焰甲使用既有凝聚手势（0.95 秒抬手、0.50 秒回收，沿用施法速度），在凝聚完成时通过一次性回调生效；陨星仍使用推掌。

新作者入口 `Tools/Skills/build_fire_magic_polish.py`，阶段为 `materials → mesh → weapon → mantle → trail → ground`，目录 `/Game/Skills/FireMagic20260921/PolishV2`。`NS_ArmorTorchJets` 双层喷流取真实刀刃端点，外层保留世界空间运动余焰；在武器姿态更新后采样。`SM_MeteorEroded` + `M_MeteorCrust` 使用不规则岩体和局部三维熔裂纹，运行最长边约 80cm；独立贴体焰、尾焰、扩散余火及 12 块视觉碎片。保留 0.65 秒命中合同和全部玩法数值。出处、作者记录及图标源在 `SourceAssets/FireMagicPolish20260921`；未进行游戏或视觉验收。

## 整理与恢复边界（2026-09-22）

材质适配经验见 [原生火焰材质与 Niagara 适配](native-fire-vfx.md)。RealisticV5 仍调用 SplineV4 作者函数并复制其系统容器；初版、PolishV2 与 SplineV4 不是可直接删除的废案。现用视觉是 RealisticV5 火焰 + RealisticV3 岩体。归档清单与公开恢复边界见项目 `Docs/Skills/skills-magic-publication-20260922.md`。
