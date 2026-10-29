# 尼泊尔弯刀第三人称动作来源 · 2026-10-24

本轮按用户要求搜索本地库与 Fab。读取源文件清单、GLB 动画名称／时长和商店作者说明；没有播放或渲染动作，没有重定向、导入或替换弯刀第三人称配置。以下是可用来源与适配候选，不是视觉验收结果。

## 本地已有素材

搜索范围：当前工程 `Content`、`SourceAssets`、`D:/FPS3D/VaultCache` 与 `D:/FPS3D/资产/sword`。本地缓存不能代表账户中尚未下载的完整 Fab 购买库。

| 来源 | 实际找到的片段 | 当前可用程度 |
| --- | --- | --- |
| Kevin Iglesias Human Melee Animations FREE | `HumanM@CombatIdle1H01.fbx`、`HumanM@Attack1H01_R.fbx`、`HumanM@Attack1H01_L.fbx`；女性版本同样存在 | 有单手待机及右／左手攻击源文件。右手只有一条普通攻击，不能当作完整三连击库。可先作为弯刀待机候选 |
| KayKit Character Animations 1.1 | `Melee_1H_Attack_Chop` 1.067 s、`Jump_Chop` 1.333 s、`Slice_Diagonal` 1.000 s、`Slice_Horizontal` 1.367 s、`Stab` 1.600 s | 五条单手攻击已存在于 UE Donors 目录，能供横砍、斜砍、下劈、跳劈和突刺适配。此 CombatMelee 包无 `Melee_1H_Idle`；不能将双手待机视为单手待机 |
| Quaternius Universal Animation Library 2 Standard | `Sword_Regular_A/B/C`、A/B 收势、`Sword_Regular_Combo` 3.000 s、`Sword_Heavy_Combo` 4.333 s、`Sword_Dash` 1.567 s、`Sword_Block` 1.233 s | GLB 内真实片段已读出，UE 里也有原始 Donor 包。历史来源记录将其归为单手剑候选；适合进一步挑选完整身体连击。没有名为单手持剑待机的片段 |

精确位置：

- Kevin：`SourceAssets/ThirdPersonSwordFree20261005/Kevin/Animations/Male/Combat/1H/`。作者来源记录：同批 `Kevin-receipt.json`，原地址 <https://kevdev.itch.io/human-melee-animatons-free>。现有 UE Kevin Donors 目录只列出此前导入的双手动作与骨架，不能把单手 FBX 的存在写成已经为弯刀导入。
- KayKit 源：`SourceAssets/ThirdPersonSwordFree20261005/KayKit/KayKit_Character_Animations_1.1/Animations/gltf/Rig_Medium/Rig_Medium_CombatMelee.glb`；UE 包：`Content/Characters/JasonPlayer20261003/SwordFullBody20261005/Donors/KayKit/SK_KayKit_Medium_Anim_Melee_1H_Attack_*.uasset`。本地原包 `License.txt` 标注 CC0；作者来源 <https://kaylousberg.itch.io/kaykit-character-animations>。
- UAL2 源：`SourceAssets/ThirdPersonSwordCandidates20261006/UAL2_Standard.glb`；UE 包：`Content/Characters/JasonPlayer20261003/SwordDonorRepair20261006/Source/Donor/A_UAL2_Armature_Sword_*.uasset`。同目录原始 `License.txt` 标注 CC0；作者来源 <https://quaternius.itch.io/universal-animation-library-2>。

这些素材使用各自源骨架；应从原始单手源开始适配当前玩家骨架及右手握点。此前为双手剑修过的握柄与左手接触版本不作为弯刀原生动作。

## Fab 候选

以下均来自本轮打开的 Fab 正式商品页，数量按作者描述，不合并为独立招式数；镜像、Root Motion／In-place、分段与收势会计入包数量。页面未返回可靠的当前价格，不记录价格。

| 候选 | 作者列出的内容 | 适用判断 |
| --- | --- | --- |
| [RamsterZ — One Hand Sword Attacks And Finishers](https://www.fab.com/listings/9edc266e-cefb-49d2-9121-ea70835a0cd9) | 67 条：3 待机、11 攻击、25 移动、4 格挡、5 闪避、3 受击、16 配对；支持左右手镜像 | 按动作覆盖看，适合优先看作基础单手近战整套候选。作者页面明确是动画包，不包含玩法蓝图 |
| [GameDevHero — One Handed Sword Animation V6](https://www.fab.com/listings/9d469b35-3c47-4240-99f4-ed5042aaa1d0) | UE5 mannequin；335 条及 FBX，2 待机、攻击／分段／回待机、八方向走跑、翻滚、闪避和 dash；含 In-place 与 Root Motion 版本 | 适合需要更多攻击与移动变化、后续精修源文件的路线；官方页面注明包含于 GDH All Animation Bundle，已有该包时应先查库 |
| [scabbard — One Handed Sword Animset Pro](https://www.fab.com/listings/4ee684a3-df87-4462-a005-2d7ca13851a7) | 110 条：4 待机／蹲姿相关、27 移动、24 攻击（含地面连击、冲刺与空中攻击）、6 格挡、2 切换，以及转身、跳跃、受击等 | 按清单看，适合覆盖更丰富的动作状态。商品页标注 Stylish／Stylized；画面风格需另行选定 |

预览入口：[V6 官方概览](https://youtu.be/7ikOp95jzLs)、[Animset Pro 官方预览](https://youtu.be/Xq-Tvn6MxZE)；RamsterZ 的预览入口位于其商品页。链接已从正式页面取得，本轮未播放作姿态验收。

排除或降级：

- [One Handed Sword Animations V3](https://www.fab.com/listings/22c64a1a-85ce-4379-9e98-f92383e74266) 的实时正式页面新增说明：作者因旧版质量不达当前标准而暂不销售、正在翻新。搜索摘要未显示此段，不能据旧摘要推荐立即购买。
- [Kukri FPS Animation Pack](https://www.fab.com/listings/0e423d3c-07c4-4961-9d53-8de500a7b0bf) 标明 FPS 相机动作；[First Person Knife Animation Set](https://www.fab.com/listings/0beb58c4-f42d-459b-a745-cd96dbcf7770) 明确仅适用于第一人称。它们不作为本轮全身第三人称来源。
- 剑盾、双持、双手剑动作会带入左手约束，不列为单手弯刀整套首选。现有 Paragon Kwang 双手剑与 Sevarog 战锤动作不直接替换到弯刀。

## 建议接续

本地路线可从 Kevin 单手待机、KayKit 横砍／斜砍／突刺和 UAL2 全身连击候选开始，优点是不必先添购；代价是需要统一不同来源的起势、收势、步法和握刀姿态。

如果希望整套动作风格更统一，先选 RamsterZ 或 V6 的正式预览。仅凭本次清单尚不能确认原生单手上挑、刀柄砸击和持续旋风均已覆盖；这些招式需单独选片和适配。适配时保留现有弯刀攻击／武技时钟、权威命中与真实位移合同，第三人称不另行扣体力或结算伤害。
