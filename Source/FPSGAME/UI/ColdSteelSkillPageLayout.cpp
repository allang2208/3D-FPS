#include "ColdSteelSkillPage.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelQuickDrag.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Combat/CombatChill.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/SwordUppercutTuning.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/Bow/BowStats.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/Text/STextBlock.h"
#include "Framework/Application/SlateApplication.h"

#include "ColdSteelSkillPagePrivate.h"
using namespace ColdSteelSkillPagePrivate;

TSharedRef<SWidget> UColdSteelSkillPage::BuildPage()
{
    Scroll.Reset();
    ElectricDetailButtons.Reset();LightningDetailButton.Reset();HolyLightDetailButton.Reset();
    LightningHasteDetailButton.Reset();IceArmorDetailButton.Reset();IceSpikeDetailButton.Reset();
    BlizzardDetailButton.Reset();AbsoluteZeroDetailButton.Reset();IceWallDetailButton.Reset();
    ChainSlashDetailButton.Reset();LeapStrikeDetailButton.Reset();ShadowStepDetailButton.Reset();UppercutDetailButton.Reset();DetailButton.Reset();PistolDetailButton.Reset();CriticalDetailButton.Reset();FireballDetailButton.Reset();HeavyDetailButton.Reset();DodgeDetailButton.Reset();DexterousHandsDetailButton.Reset();BackButton.Reset();FilterButtons.Reset();
    if (!Model) return Label(TEXT("技能数据暂不可用"),14,ColdSteelUI::TextSecondary);
    auto Column=SNew(SVerticalBox);
    // 2026-11-17: 配置快捷魔法 removed; the skill tree header's 魔法轮盘 button configures the staff wheel.
    if (!bDetail)
    {
        auto Filters=SNew(SHorizontalBox);
        const TCHAR* Captions[]={TEXT("全部"),TEXT("被动"),TEXT("主动"),TEXT("魔法")};
        FilterButtons.SetNum(4);
        for(int32 I=0;I<4;++I) Filters->AddSlot().FillWidth(1).Padding(I?4/Scale:0,0,0,0)
            [SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight/Scale)[SAssignNew(FilterButtons[I],SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Center).VAlign(VAlign_Center)
                .OnClicked_UObject(this,&ThisClass::SelectCategory,I)[Label(Captions[I],14,Category==I?ColdSteelUI::TextPrimary:ColdSteelUI::TextTertiary)]]];
        Column->AddSlot().AutoHeight().Padding(16/Scale,12/Scale)[Filters];
        SAssignNew(Scroll,SScrollBox).AllowOverscroll(EAllowOverscroll::No);
        if(Category<=1)for(FName Id:{FName(TEXT("twoHandedMastery")),FName(TEXT("oneHandedMastery")),FName(TEXT("swordMastery")),FName(TEXT("bluntMastery")),FName(TEXT("machineGunMastery")),FName(TEXT("shotgunMastery")),FName(TEXT("bowMastery")),FName(TEXT("heartPiercingArrow"))})
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[SNew(SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale).OnClicked_UObject(this,&ThisClass::OpenDetail,Id)[Overview(true,Id)]];
        if(Category<=1) Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(DetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("rifleMastery")))[Overview(true,TEXT("rifleMastery"))]];
        if(Category<=1) Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(PistolDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("pistolMastery")))[Overview(true,TEXT("pistolMastery"))]];
        if(Category<=1) Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(CriticalDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("criticalStrike")))[Overview(true,TEXT("criticalStrike"))]];
        if(Category<=1) Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(DexterousHandsDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("dexterousHands")))[Overview(true,TEXT("dexterousHands"))]];
        if(Category==0||Category==2)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(DodgeDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("dodge")))[Overview(true,TEXT("dodge"))]];
        if(Category==0||Category==2)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(HeavyDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("heavyStrike")))[Overview(true,TEXT("heavyStrike"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(IlluminationArrowDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("illuminationArrow")))[Overview(true,TEXT("illuminationArrow"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(ElementalArrowDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("elementalArrow")))[Overview(true,TEXT("elementalArrow"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(MagicArrowRainDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("magicArrowRain")))[Overview(true,TEXT("magicArrowRain"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(FireballDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("fireball")))[Overview(true,TEXT("fireball"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(IceSpikeDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("iceSpike")))[Overview(true,TEXT("iceSpike"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(LightningHasteDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("lightningHaste")))[Overview(true,TEXT("lightningHaste"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(IceArmorDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("iceArmor")))[Overview(true,TEXT("iceArmor"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(IceWallDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("iceWall")))[Overview(true,TEXT("iceWall"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(BlizzardDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("blizzard")))[Overview(true,TEXT("blizzard"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(AbsoluteZeroDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("absoluteZero")))[Overview(true,TEXT("absoluteZero"))]];
        if(Category==0||Category==2||Category==3)for(const FName Id:{FName(TEXT("stormDomain")),FName(TEXT("thunderLance"))})
        {
            auto Button=SNew(SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,Id)[Overview(true,Id)];
            ElectricDetailButtons.Add(Id,Button);Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Button];
        }
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(LightningDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("lightningStrike")))[Overview(true,TEXT("lightningStrike"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(MeteorDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("meteor")))[Overview(true,TEXT("meteor"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(DragonBreathDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("dragonBreath")))[Overview(true,TEXT("dragonBreath"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(FlameArmorDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("flameArmor")))[Overview(true,TEXT("flameArmor"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(HolyLightDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("holyLight")))[Overview(true,TEXT("holyLight"))]];
        if(Category==0||Category==2)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(QuickCombatDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("quickCombat")))[Overview(true,TEXT("quickCombat"))]];
        if(Category<=1)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(DashAttackDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("dashAttack")))[Overview(true,TEXT("dashAttack"))]];
        if(Category==0||Category==2)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(WhirlwindDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("whirlwind")))[Overview(true,TEXT("whirlwind"))]];
        if(Category==0||Category==2)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(UppercutDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("swordUppercut")))[Overview(true,TEXT("swordUppercut"))]];
        if(Category==0||Category==2)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(ChainSlashDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("chainSlash")))[Overview(true,TEXT("chainSlash"))]];
        if(Category==0||Category==2)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(LeapStrikeDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("leapStrike")))[Overview(true,TEXT("leapStrike"))]];
        if(Category==0||Category==2)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(ShadowStepDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("shadowStepSlash")))[Overview(true,TEXT("shadowStepSlash"))]];
        Column->AddSlot().FillHeight(1)[Scroll.ToSharedRef()];
        Column->AddSlot().AutoHeight().Padding(16/Scale,8/Scale)[Paragraph(TEXT("拖动主动技能卡到 Q/E/X/1–0；空槽移动，占用槽交换，拖出解绑。F 为快速进战，G 为当前武器特殊功能，专属槽不可替换。E 优先交互；左 Shift 短按仍可闪避。"),12,ColdSteelUI::TextTertiary,PageWidth-32)];
    }
    else
    {
        if(!bEmbedded)Column->AddSlot().AutoHeight().Padding(16/Scale,12/Scale)[SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight/Scale)
            [SAssignNew(BackButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Center).VAlign(VAlign_Center)
                .OnClicked_Lambda([this]{GoBack();return FReply::Handled();})[Label(TEXT("返回技能列表"),14,ColdSteelUI::TextPrimary)]]];
        SAssignNew(Scroll,SScrollBox).AllowOverscroll(EAllowOverscroll::No).ScrollBarVisibility(bEmbedded?EVisibility::Collapsed:EVisibility::Visible);
        // Embedded in the skill tree, whose own header already shows icon, name, description, level and training
        // progress; rules and formulas (Note) stay on the full page only (2026-11-17).
        if(!bEmbedded)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[SNew(SBorder).BorderImage(&CardBrush).Padding(16/Scale)[Overview(false,SelectedSkill)]];
        const float ValueWidth=(PageWidth>=640?140.f:100.f)/Scale;
        if(PageWidth>=480)Scroll->AddSlot().Padding(bEmbedded?FMargin(16/Scale,0,28/Scale,6/Scale):FMargin(28/Scale,4/Scale))[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Bottom)[bEmbedded?StaticCastSharedRef<SWidget>(SNew(STextBlock).Text(FText::FromString(TEXT("技能收益")))
                .Font(ColdSteelUI::TextFont(12*.75f/Scale,true)).ColorAndOpacity(ColdSteelUI::HUDGold)):Label(TEXT("技能收益"),16,ColdSteelUI::TextPrimary)]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom)[SNew(SBox).WidthOverride(ValueWidth).HAlign(HAlign_Right)[Label(TEXT("当前等级"),12,ColdSteelUI::TextSecondary)]]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom)[SNew(SBox).WidthOverride(ValueWidth).HAlign(HAlign_Right)[Label(TEXT("下一等级"),12,ColdSteelUI::Success)]]];
        else if(bEmbedded)Scroll->AddSlot().Padding(16/Scale,6/Scale,16/Scale,4/Scale)[SNew(STextBlock).Text(FText::FromString(TEXT("技能收益")))
            .Font(ColdSteelUI::TextFont(12*.75f/Scale,true)).ColorAndOpacity(ColdSteelUI::HUDGold)];
        else Scroll->AddSlot().Padding(28/Scale,4/Scale)[Label(TEXT("技能收益"),16,ColdSteelUI::TextPrimary)];
        if(SelectedSkill==TEXT("leapStrike"))
        {
            const TCHAR* Labels[]={TEXT("武器伤害"),TEXT("韧性伤害"),TEXT("冷却时间"),TEXT("体力消耗"),TEXT("伤害半径"),TEXT("最大跳距"),TEXT("升级所需修炼")};
            for(int32 I=0;I<7;++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Labels[I],I)];
            const auto& T=Definition(SelectedSkill).LeapStrike;
            Scroll->AddSlot().Padding(16/Scale,12/Scale)[Note(FString::Printf(
                TEXT("1–20级线性成长：伤害与削韧 %.0f%%→%.0f%%，冷却 %.0f→%.0f s，体力 %.0f→%.0f，半径 %.1f→%.1f m，跳距 %.0f→%.0f m。"),
                T.DamageBase*100.f,T.DamageMax*100.f,T.CooldownBase,T.CooldownMin,T.StaminaBase,T.StaminaMax,
                T.RadiusBaseCM/100.f,T.RadiusMaxCM/100.f,T.ReachBaseCM/100.f,T.ReachMaxCM/100.f),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("按住选点，松开确认；选点不耗体。蓄力前扣足体力并开始冷却，中断不返还。蓄力0.5秒，通常腾空0.75秒，大落差持续下落；触地重砸。空中免控（减速除外），视角限制至触地。上方冷却与体力已计入装备修正。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[TrainingCard()];
        }
        else if(SelectedSkill==TEXT("chainSlash"))
        {
            const TCHAR* Labels[]={TEXT("每段武器伤害"),TEXT("每段韧性伤害"),TEXT("冷却时间"),TEXT("体力消耗"),TEXT("升级所需修炼")};
            const int32 Rows[]={0,4,1,2,3};
            for(int32 I=0;I<5;++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Labels[I],Rows[I])];
            const auto& T=Definition(SelectedSkill).ChainSlash;
            Scroll->AddSlot().Padding(16/Scale,12/Scale)[Note(FString::Printf(
                TEXT("1–20级线性成长：每段伤害与削韧 %.0f%%→%.0f%%，基础冷却 %.0f→%.0f s，基础体力 %.0f→%.0f。"),
                T.DamageBase*100.f,T.DamageMax*100.f,T.CooldownBase,T.CooldownMin,T.StaminaBase,T.StaminaMax),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("起手前扣足整次体力并开始冷却，体力不足无法施放；中断不返还。上方冷却与体力已计入当前装备修正。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[TrainingCard()];
        }
        else if(SelectedSkill==TEXT("shadowStepSlash"))
        {
            const TCHAR* Labels[]={TEXT("一段穿身斜斩"),TEXT("二段反手追斩"),TEXT("穿身突进距离"),TEXT("冷却时间"),TEXT("体力消耗"),TEXT("背身／破韧追斩暴击"),TEXT("升级所需修炼")};
            for(int32 I=0;I<7;++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Labels[I],I)];
            const auto& T=Definition(SelectedSkill).ShadowStep;
            Scroll->AddSlot().Padding(16/Scale,12/Scale)[Note(FString::Printf(
                TEXT("1–20级线性成长：一段 %.0f%%→%.0f%%，二段 %.0f%%→%.0f%%，突进 %.1f→%.1f m，冷却 %.0f→%.0f s，体力 %.0f→%.0f（二段追斩零耗体）。"),
                T.Stage1DamageBase*100.f,T.Stage1DamageMax*100.f,T.Stage2DamageBase*100.f,T.Stage2DamageMax*100.f,
                T.DashDistanceBaseCM/100.f,T.DashDistanceMaxCM/100.f,T.CooldownBase,T.CooldownMin,T.StaminaBase,T.StaminaMax),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("单手近战限定（单持、双持、手枪/法杖配副手弯刀或手斧皆可，不含火把与生产工具）。一段穿身穿透普通/精英敌人，遇领主/首领或墙体停止；整条突进轨迹矩形范围内的所有敌人均会受击并挂上掠影印记，终点瞬斩定格顿帧并解锁 0.9 秒追斩窗口。再按技能键或左键零体力挥出二段宽幅反手追斩，同步斩击前方与周身近身并引爆所有已标记的穿身目标（无需强转镜头，背身或破韧目标暴击率 +25%）。双持分左右手各 60%（合计 120%）分别触发暴击与附魔。起手扣体并开始冷却，中断不返还。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[TrainingCard()];
        }
        else if(SelectedSkill==TEXT("illuminationArrow"))
        {
            const TCHAR* Labels[]={TEXT("路径扫描半径"),TEXT("沿途标记时间"),TEXT("直击标记 / 照明"),TEXT("标记目标承伤"),TEXT("释放后冷却"),TEXT("射出魔法消耗"),TEXT("升级所需修炼")};
            const int32 Rows[]={0,1,6,2,3,4,5};
            for(int32 I=0;I<7;++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Labels[I],Rows[I])];
            Scroll->AddSlot().Padding(16/Scale,12/Scale)[Note(TEXT("按绑定键搭上照明箭；长按左键正常拉弓，松手射出。箭头白金光弧提供局部照明，射出后恢复普通箭。再次按技能键、切武器或打开菜单取消。射出才扣除一支箭、魔法并开始独立冷却；拉弓持续耗体，沿用节拍与穿心箭。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,8/Scale)[Note(TEXT("箭矢沿实际飞行路径连续扫描；实体墙和楼板遮挡探测，撞停或消失后停止扫描。沿途目标每箭扫描标记一次；直接命中的目标从命中时刷新双倍标记时长，后续扫描不会缩短已有标记。红色轮廓高亮，螳螂立即显形且期间无法隐身；所有来源伤害提高，同类标记取最高增伤，不相乘叠加。净化、免疫和死亡按现有状态规则处理。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,8/Scale)[Note(TEXT("命中位置留下白金光弧和持续照明，时长等于直击标记；命中怪物随目标移动，命中地面或墙面则留在落点。穿透命中各自留下光源，拾回箭矢不会提前熄灭。光源不追加扫描或伤害。箭矢本体按普通箭结算，保留蓄力、暴击、护甲、节拍与穿心箭效果，无照明技能额外伤害倍率。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,8/Scale,16/Scale,12/Scale)[TrainingCard()];
            const auto& D=Definition(SelectedSkill);
            auto Growth=SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12/Scale)[Label(TEXT("完整成长 · 20 级"),16,ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8/Scale)[Note(TEXT("线性成长。下表为基础冷却，装备冷却缩减另计；上方对照为当前装备下的实值。范围为半径，沿途标记从扫描时计算；直击标记与落点照明从命中时计算，持续时间翻倍。"),12,ColdSteelUI::TextSecondary,PageWidth-76)];
            if(PageWidth>=620)Growth->AddSlot().AutoHeight().Padding(0,0,0,8/Scale)[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(.65f)[Label(TEXT("等级"),12,ColdSteelUI::TextPrimary)]
                +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("半径"),12,ColdSteelUI::TextPrimary)]
                +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("沿途"),12,ColdSteelUI::TextPrimary)]
                +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("直击 / 照明"),12,ColdSteelUI::TextPrimary)]
                +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("增伤"),12,ColdSteelUI::TextPrimary)]
                +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("冷却"),12,ColdSteelUI::TextPrimary)]];
            for(int32 L=1;L<=D.MaxLevel;++L)
            {
                const auto C=IlluminationArrow::Evaluate(D.IlluminationArrow,L,D.MaxLevel);
                const auto Color=L==Progress(SelectedSkill).Level?ColdSteelUI::Accent:ColdSteelUI::TextSecondary;
                if(PageWidth>=620)Growth->AddSlot().AutoHeight().Padding(0,5/Scale)[SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(.65f)[Label(FString::Printf(TEXT("%02d"),L),14,Color,true)]
                    +SHorizontalBox::Slot().FillWidth(1)[Label(FString::Printf(TEXT("%.1f m"),C.Radius/100.f),14,Color,true)]
                    +SHorizontalBox::Slot().FillWidth(1)[Label(FString::Printf(TEXT("%.1f s"),C.Duration),14,Color,true)]
                    +SHorizontalBox::Slot().FillWidth(1)[Label(FString::Printf(TEXT("%.1f s"),IlluminationArrow::ImpactDuration(C)),14,Color,true)]
                    +SHorizontalBox::Slot().FillWidth(1)[Label(FString::Printf(TEXT("+%.1f%%"),C.DamageBonus*100),14,Color,true)]
                    +SHorizontalBox::Slot().FillWidth(1)[Label(FString::Printf(TEXT("%.1f s"),C.Cooldown),14,Color,true)]];
                else Growth->AddSlot().AutoHeight().Padding(0,6/Scale)[SNew(SVerticalBox)
                    +SVerticalBox::Slot().AutoHeight()[Label(FString::Printf(TEXT("Lv.%02d"),L),14,Color,true)]
                    +SVerticalBox::Slot().AutoHeight().Padding(0,4/Scale,0,0)[Paragraph(FString::Printf(TEXT("半径 %.1f m · 沿途 %.1f s\n直击 / 照明 %.1f s\n承伤 +%.1f%% · 冷却 %.1f s"),C.Radius/100.f,C.Duration,IlluminationArrow::ImpactDuration(C),C.DamageBonus*100,C.Cooldown),14,Color,PageWidth-76)]];
            }
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[SNew(SBorder).BorderImage(&CardBrush).Padding(16/Scale)[Growth]];
        }
        else if(SelectedSkill==TEXT("elementalArrow"))
        {
            const auto& D=Definition(SelectedSkill);const auto& T=D.ElementalArrow;
            const TCHAR* Labels[]={TEXT("火球伤害调用倍率"),TEXT("火焰箭基础魔法伤害"),TEXT("冰锥伤害调用倍率"),TEXT("每枚冰锥基础魔法伤害"),TEXT("闪电伤害调用倍率"),TEXT("每道闪电基础魔法伤害"),TEXT("三元素波及半径"),TEXT("每层寒冷减速 / 持续"),TEXT("闪电眩晕"),TEXT("升级所需修炼")};
            for(int32 I=0;I<10;++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Labels[I],I)];
            for(int32 I=1;I<=3;++I)
            {
                const auto E=EArrowElement(I);const auto C=Model->ElementalArrowStats(E);
                const FName Key(*FString::Printf(TEXT("elementArrowIcon%d"),I));
                const bool Learned=Model->MasteryProgress(ElementalArrow::Spell(E)).Level>0;
                Scroll->AddSlot().Padding(16/Scale,6/Scale)[SNew(SBorder).BorderImage(&CardBrush).Padding(16/Scale)[SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth().Padding(0,0,12/Scale,0)[SNew(SBox).WidthOverride(64/Scale).HeightOverride(64/Scale)[SNew(SImage).Image(MasteryIconBrushes.Find(Key))]]
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Paragraph(FString::Printf(TEXT("%s · %s\n射出 %.0f MP · %.1f 秒冷却"),ElementalArrow::Name(E),Learned?TEXT("可使用"):TEXT("对应魔法未学习"),C.ManaCost,C.Cooldown),14,ColdSteelUI::TextSecondary,PageWidth-152)]]];
            }
            Scroll->AddSlot().Padding(16/Scale,12/Scale)[Note(TEXT("短按绑定键搭上一支元素箭；长按 0.3 秒打开圆盘，冷却中仍可切换。三元素独立倒计时，只与各自原魔法共用冷却。移向元素后松键确认，已就绪则搭箭；选中冷却元素会保留选择，待就绪后短按搭箭。盘心或 Esc 取消选择。按住左键正常拉弓，松手射出；再次短按技能键取消附魔。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,8/Scale)[Note(TEXT("保留正常弓箭物理伤害、节拍奖励及穿心箭的伤害／箭速／穿透。元素爆发每支箭只触发一次；贯穿后的后续命中继续造成物理伤害。元素附伤不再乘穿心箭倍率。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            if(!bEmbedded)Scroll->AddSlot().Padding(16/Scale,8/Scale)[SNew(SBorder).BorderImage(&CardBrush).Padding(16/Scale)[Paragraph(FString::Printf(TEXT("射出蓝耗：对应魔法 ×%g，向上取整。\n持续拉弓：%g MP / 秒，同时沿用弓的持续体力消耗，停止自然回蓝。搭箭待机不扣维持蓝量。魔法不足以支付射出费用时自动收弓；取消不消耗箭支、不进入冷却，已发生的维持消耗不返还。"),T.ManaCostMultiplier,T.ManaPerSecond),14,ColdSteelUI::TextSecondary,PageWidth-76)]];
            Scroll->AddSlot().Padding(16/Scale,8/Scale)[Note(FString::Printf(TEXT("火焰：原火球伤害乘上方调用倍率，半径 ×%g，直击全伤，范围伤害沿用距离衰减。寒冰：向范围内可见敌人各发射一枚冰锥，原冰锥伤害乘调用倍率，附加 %.1f 秒寒冷。闪电：范围内可见敌人各承受一道放大后的闪电及 %.1f 秒眩晕。首目标同样受到元素伤害与控制。"),T.RadiusMultiplier,T.ChillSeconds,T.StunSeconds),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,8/Scale)[Note(TEXT("三元素共用上方波及半径，各自独立冷却，并分别与原魔法共用冷却；未学习对应魔法时不可用。实体墙与楼板遮挡波及，冰锥途中可被障碍截断。每个目标同次最多受一次元素伤害，控制遵守已有免疫规则。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,8/Scale)[Note(TEXT("元素箭与原魔法分别成长：元素箭等级提高调用倍率，原魔法等级与当前属性决定被放大的基础伤害。下一等级只预览元素箭升级，原魔法等级保持当前值。暴击、魔法增伤和目标魔防另行结算；射出时锁定本箭伤害。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,8/Scale,16/Scale,12/Scale)[TrainingCard()];
            auto Growth=SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12/Scale)[Label(FString::Printf(TEXT("完整成长 · %d 级"),D.MaxLevel),16,ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12/Scale)[Note(FString::Printf(
                    TEXT("2～%d 级：火焰每级 +%.2f，寒冰／闪电 +%.2f；%d～%d 级：每级分别 +%.2f / +%.2f。表中倍率作用于对应魔法的当前伤害。"),
                    T.GrowthChangeLevel,T.FireGrowth,T.ControlGrowth,T.GrowthChangeLevel+1,D.MaxLevel,T.FireLateGrowth,T.ControlLateGrowth),12,ColdSteelUI::TextSecondary,PageWidth-76)];
            if(PageWidth>=480)Growth->AddSlot().AutoHeight().Padding(0,0,0,8/Scale)[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(.75f)[Label(TEXT("等级"),14,ColdSteelUI::TextPrimary)]
                +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("火焰"),14,ColdSteelUI::TextPrimary)]
                +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("寒冰"),14,ColdSteelUI::TextPrimary)]
                +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("闪电"),14,ColdSteelUI::TextPrimary)]];
            for(int32 L=1;L<=D.MaxLevel;++L)
            {
                const float F=ElementalArrow::DamageMultiplier(T,EArrowElement::Fire,L),I=ElementalArrow::DamageMultiplier(T,EArrowElement::Ice,L),E=ElementalArrow::DamageMultiplier(T,EArrowElement::Lightning,L);
                const auto Color=L==Progress(SelectedSkill).Level?ColdSteelUI::Accent:ColdSteelUI::TextSecondary;
                if(PageWidth>=480)Growth->AddSlot().AutoHeight().Padding(0,5/Scale)[SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(.75f)[Label(FString::Printf(TEXT("Lv.%02d"),L),14,Color,true)]
                    +SHorizontalBox::Slot().FillWidth(1)[Label(FString::Printf(TEXT("×%.2f"),F),14,Color,true)]
                    +SHorizontalBox::Slot().FillWidth(1)[Label(FString::Printf(TEXT("×%.2f"),I),14,Color,true)]
                    +SHorizontalBox::Slot().FillWidth(1)[Label(FString::Printf(TEXT("×%.2f"),E),14,Color,true)]];
                else Growth->AddSlot().AutoHeight().Padding(0,5/Scale)[SNew(SVerticalBox)
                    +SVerticalBox::Slot().AutoHeight()[Label(FString::Printf(TEXT("Lv.%02d"),L),14,Color,true)]
                    +SVerticalBox::Slot().AutoHeight().Padding(0,4/Scale,0,0)[Paragraph(FString::Printf(TEXT("火焰 ×%.2f  /  寒冰 ×%.2f  /  闪电 ×%.2f"),F,I,E),14,Color,PageWidth-76)]];
            }
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[SNew(SBorder).BorderImage(&CardBrush).Padding(16/Scale)[Growth]];
        }
        else if(SelectedSkill==TEXT("magicArrowRain"))
        {
            const TCHAR* Labels[]={TEXT("单次范围魔法伤害"),TEXT("范围半径"),TEXT("最大选点距离"),TEXT("满蓄时间"),TEXT("基础魔法消耗"),TEXT("持续魔法消耗"),TEXT("持续体力消耗"),TEXT("释放后冷却")};
            for(int32 I=0;I<8;++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Labels[I],I)];
            const auto& T=Definition(SelectedSkill).MagicArrowRain;
            if(!bEmbedded)Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,8/Scale)[Label(TEXT("伤害成长"),16,ColdSteelUI::TextPrimary)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("主属性敏捷，副属性智力。伤害系数和每级成长均为敏捷∶智力＝2∶1；使用释放时包含装备、精通和状态修正的有效属性。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(
                TEXT("令 K＝技能等级−1：范围伤害＝向下取整〔%g＋%g×K＋敏捷×(%g＋%g×K)＋智力×(%g＋%g×K)〕。"),
                T.DamageBase,T.DamagePerLevel,T.DexterityBase,T.DexterityPerLevel,T.IntelligenceBase,T.IntelligencePerLevel),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("上方显示当前属性下的基础魔法伤害及升级后的数值。魔法增伤、暴击与目标魔防另行结算；面板魔攻不额外计入此公式。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            if(!bEmbedded)Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,8/Scale)[Label(TEXT("操作与释放"),16,ColdSteelUI::TextPrimary)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("按绑定键搭上绿色附魔箭；长按左键拉弓，镜头选择地面范围，满蓄后松手释放。再次按技能键、切武器或打开菜单取消；体力或魔法耗尽会平缓收弓，保留箭支，不会自动射出。未满蓄或落点无效时松手同样取消。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("准备时暂扣基础魔法；未射出取消会返还，持续拉弓已经消耗的资源不返还。真实离弦后消耗一支箭并开始冷却。保持期间暂停自然回体和回蓝；箭雨不叠加穿心箭或完美节拍奖励。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("引导箭在目标上方空爆，随后一次密集箭雨落下；同一目标只结算一次范围伤害。实体墙、顶板和楼层可以遮挡，途中撞墙不会在远端触发箭雨。绿色圆圈表示范围，短暂烟尘不造成持续伤害。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,8/Scale,16/Scale,12/Scale)[TrainingCard()];
        }
        else if(SelectedSkill==TEXT("heartPiercingArrow"))
        {
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("普通满拉箭伤害倍率"),0)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("额外目标穿透"),1)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("最多命中目标"),2)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("箭矢速度倍率"),3)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("连续拉弓时间"),4)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("持续拉弓耗体"),6)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("升级所需修炼"),5)];
            const auto& D=Definition(SelectedSkill);
            const auto& T=D.HeartPiercingArrow;
            const auto Current=HeartPiercingArrow::ForModel(Model);
            const double ChargeDrain=Model->ActiveBow()?ColdSteelBow::ChargeStaminaPerSecond(*Model->ActiveBow(),Model):Model->HeavyChargeStaminaPerSecond();
            if(!bEmbedded)Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,8/Scale)[Label(TEXT("触发与结算"),16,ColdSteelUI::TextPrimary)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(
                TEXT("持弓按住左键，从开始实际拉弦计时；当前装备持续超过 %.1f 秒并达到满拉后，进度条转红并脉冲，松手释放穿心箭。搭箭与举弓准备不计时，不需要绑定快捷键，无额外魔法消耗或技能冷却。"),Current.ChargeSeconds),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(
                TEXT("从实际拉弦开始持续消耗体力，满拉和穿心就绪后继续按住也会消耗，并暂停自然回体。当前每秒 %.1f 体力，受持续拉弓耗体改造与角色动作耗体倍率影响。松手或取消后停止，已消耗体力不返还；实际出箭仍另扣本次射击体力。体力耗尽时平缓收弓，保留箭支，不触发攻击。"),ChargeDrain),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(
                TEXT("倍率在普通满拉箭伤害上继续相乘，继承当前弓、箭种、精通、暴击与目标防御结算。每个穿透目标沿用同一发箭的伤害倍率与速度，不因穿透衰减；实体墙与地形仍会挡住箭。额外穿透耗尽后，箭停在最后目标上；一箭只留下一个可回收箭体。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(
                TEXT("收弓、换武器、死亡或动作打断都会取消本次蓄力，下次从零计时。穿心箭与普通拉弓共用拉弓速度，基础 %.1f 秒门槛随当前拉弓速度同比缩短或延长，完美节拍的下次拉弓加速同样生效。体力允许时可一直维持，松手才射箭。完美节拍仍按满拉窗口结算。"),T.ChargeSeconds),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,8/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,8/Scale,16/Scale,8/Scale)[Label(TEXT("完整成长 · 20 级"),16,ColdSteelUI::TextPrimary)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(
                TEXT("2～%d 级每级增加 %.2f 倍伤害，%d～%d 级每级增加 %.2f 倍；第 %d / %d 级分别获得第 2 / 3 次额外目标穿透。下表为技能基础成长，不含当前弓体改造；基础箭速与蓄力门槛不随等级改变。"),
                T.GrowthChangeLevel,T.EarlyGrowth,T.GrowthChangeLevel+1,D.MaxLevel,T.LateGrowth,T.SecondPenetrationLevel,T.ThirdPenetrationLevel),12,ColdSteelUI::TextSecondary,PageWidth-44)];
            auto Growth=SNew(SVerticalBox);
            auto AddGrowth=[&](const FString& Level,const FString& Damage,const FString& Targets,bool bMilestone)
            {
                const auto Color=bMilestone?ColdSteelUI::Accent:ColdSteelUI::TextSecondary;
                Growth->AddSlot().AutoHeight().Padding(0,5/Scale)[SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(.8f)[Label(Level,14,Color)]
                    +SHorizontalBox::Slot().FillWidth(1)[Label(Damage,14,Color)]
                    +SHorizontalBox::Slot().FillWidth(1.5f)[Label(Targets,14,Color)]];
            };
            AddGrowth(TEXT("等级"),TEXT("伤害倍率"),TEXT("穿透 / 最多目标"),true);
            for(int32 L=1;L<=D.MaxLevel;++L)
            {
                const auto S=HeartPiercingArrow::Evaluate(T,L);
                AddGrowth(FString::Printf(TEXT("Lv.%02d"),L),FString::Printf(TEXT("×%.2f"),S.DamageMultiplier),
                    FString::Printf(TEXT("+%d / %d 个"),S.TargetPenetration,S.TargetPenetration+1),
                    L==1||L==T.SecondPenetrationLevel||L==T.ThirdPenetrationLevel||L==D.MaxLevel);
            }
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[SNew(SBorder).BorderImage(&CardBrush).Padding(12/Scale)[Growth]];
        }
        else if(SelectedSkill==TEXT("swordUppercut"))
        {
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("基础伤害倍率"),0)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("力量加成"),1)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("升级所需修炼"),2)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("释放体力消耗"),3)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("基础冷却"),4)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("判定距离上限"),5)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("距离倍率（相对突刺）"),6)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("击飞效果：命中强制击飞普通怪物；精英、领主和首领仅在破韧期间可被击飞。本次上挑先结算伤害与削韧，若这一击造成破韧，也会立即击飞。未破韧或正在恢复韧性的目标不会被强制击飞。"),14,ColdSteelUI::TextPrimary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("持双手剑、双手锤或尼泊尔弯刀时按绑定快捷键使用，动作结束且冷却完成后可再次发动。上挑按自身等级套用重击倍率，武器重击改造结算后再乘70%。强化突刺型前方判定，每次命中一个目标；力量常驻。实际出手时一次扣除体力并开始冷却；蓄势取消不扣费、不进入冷却，出手时体力不足则取消。体力消耗和基础冷却不随等级变化。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& UppercutDefinition=Definition(SelectedSkill);
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(FString::Printf(
                TEXT("判定距离＝当前兵器突刺距离×%.2f×［1＋%.2f×（等级−1）］。探针与判定宽度提高%.0f%%，升级只继续延长前向距离。距离数值为上限，仍须武器扫掠接触且无遮挡；前踏位移另计。"),
                UppercutDefinition.UppercutRangeMultiplier,UppercutDefinition.UppercutReachGrowthPerLevel,(UppercutDefinition.UppercutRangeMultiplier-1.f)*100.f),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("heavyStrike"))
        {
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("重击伤害倍率"),0)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("所需蓄力时间"),1)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("蓄力体力消耗"),3)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("力量加成"),2)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(TEXT("仅近战武器可施放。持双手剑、战锤或尼泊尔弯刀按住左键蓄满后松开；双手剑与弯刀也可拖入快捷栏，按一次自动蓄满释放。1 级倍率 2.5、蓄力 2 秒、力量 +1；每升一级倍率 +0.1、蓄力 −0.05 秒、力量 +1。蓄力期间持续消耗体力并暂停自然恢复，蓄满后继续按住仍会扣除；松手或取消后停止，已消耗体力不返还。体力耗尽自动取消蓄力，双手与武器平滑收回至待机，不触发攻击。释放时另消耗当前重击的出手体力，体力不足则取消出手；无额外冷却，收招结束才能再次使用。力量常驻并参与武器属性伤害；中途换装、死亡或动作冲突取消蓄力，不保存进行中的动作。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
        }
        else if(Additional(SelectedSkill))
        {
            if(SelectedSkill!=TEXT("swordMastery"))
            {
                const TCHAR* DmgLabel=SelectedSkill==TEXT("bluntMastery")?TEXT("双手钝器伤害增加"):
                    SelectedSkill==TEXT("twoHandedMastery")?TEXT("双手武器伤害增加"):
                    SelectedSkill==TEXT("oneHandedMastery")?TEXT("单手武器伤害增加"):TEXT("武器伤害倍率");
                Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(DmgLabel,0)];
            }
            if(SelectedSkill!=TEXT("shotgunMastery")&&SelectedSkill!=TEXT("bluntMastery")&&SelectedSkill!=TEXT("twoHandedMastery")&&SelectedSkill!=TEXT("oneHandedMastery"))
                Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("固定伤害"),1)];
            if(!ColdSteelSkills::IsMeleeMastery(SelectedSkill))Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(SelectedSkill==TEXT("machineGunMastery")?TEXT("力量"):SelectedSkill==TEXT("shotgunMastery")?TEXT("体质"):TEXT("敏捷"),2)];
            if(SelectedSkill==TEXT("oneHandedMastery"))Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("暴击率增加"),4)];
            if(ColdSteelSkills::IsMeleeMastery(SelectedSkill)||SelectedSkill==TEXT("bowMastery"))Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(ColdSteelSkills::IsMeleeMastery(SelectedSkill)?TEXT("普通攻击速度提升"):TEXT("攻击速度提升"),3)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            FString Explanation;
            if(SelectedSkill==TEXT("twoHandedMastery"))
            {
                const auto& D=Definition(SelectedSkill);
                Explanation=FString::Printf(TEXT("适用所有双手剑与双手钝器（不含生产工具）。每级伤害+%.2f%%、普通攻击间隔−%.2f%%，%d级伤害+%.1f%%、间隔−%.1f%%。与双手剑精通、双手钝器精通叠加生效；使用双手武器命中或击杀时同步修炼。"),
                    D.DamagePercentPerLevel*100,D.CooldownReductionPerLevel*100,D.MaxLevel,D.DamagePercentPerLevel*D.MaxLevel*100,D.CooldownReductionPerLevel*D.MaxLevel*100);
            }
            else if(SelectedSkill==TEXT("oneHandedMastery"))
            {
                const auto& D=Definition(SelectedSkill);
                Explanation=FString::Printf(TEXT("适用单手弯刀与战术手斧（单持、双持及手枪/法杖副手均生效，不含火把与生产工具）。每级伤害+%.1f%%、普通攻击间隔−%.1f%%、暴击率+%.2f%%；%d级伤害+%.0f%%、间隔−%.0f%%（等效攻速+%.1f%%）、暴击率+%.1f%%。"),
                    D.DamagePercentPerLevel*100,D.CooldownReductionPerLevel*100,D.CriticalChancePerLevel,D.MaxLevel,D.DamagePercentPerLevel*D.MaxLevel*100,
                    D.CooldownReductionPerLevel*D.MaxLevel*100,(1.f/FMath::Max(.05f,1.f-D.CooldownReductionPerLevel*D.MaxLevel)-1.f)*100,D.CriticalChancePerLevel*D.MaxLevel);
            }
            else if(SelectedSkill==TEXT("bluntMastery"))
            {
                const auto& D=Definition(SelectedSkill);
                Explanation=FString::Printf(TEXT("专精双手钝器武器（包括双手战锤）。伤害加成＝等级×%.2f%%（%d级+%.2f%%），普通攻击间隔每级−%.2f%%（%d级−%.1f%%）；与双手武器精通叠满后共+25%%伤害、−20%%攻击间隔。原等级与经验保留，无需重新修炼。"),
                    D.DamagePercentPerLevel*100,D.MaxLevel,D.DamagePercentPerLevel*D.MaxLevel*100,
                    D.CooldownReductionPerLevel*100,D.MaxLevel,D.CooldownReductionPerLevel*D.MaxLevel*100);
            }
            else if(SelectedSkill==TEXT("swordMastery"))
                Explanation=TEXT("专精双手刀剑。每级固定伤害+1、普通攻击间隔−0.6%（20级固定伤害+20、间隔−12%）；与双手武器精通叠满后共+10%双手伤害、+20固定伤害、−20%普攻间隔（等效攻速+25%）。武技按自身公式继承武器伤害。");
            else if(SelectedSkill==TEXT("machineGunMastery"))
                Explanation=TEXT("属性被动常驻；使用对应武器修炼。伤害、强化、改造和附魔共用当前计算结果。精通加的力量计入角色属性；武器面板按原始分配与装备属性结算。持机枪类武器时移动速度 ×0.67（减速 33%），收起武器或改持其他武器即恢复。");
            else Explanation=TEXT("属性被动常驻；使用对应武器修炼。伤害、强化、改造和附魔共用当前计算结果。精通加的属性计入角色属性；武器面板按原始分配与装备属性结算。");
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(Explanation,12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else
        if(SelectedSkill==TEXT("fireball"))
        {
            const TCHAR* Rows[]={TEXT("基础魔法伤害"),TEXT("爆炸半径"),TEXT("消耗魔法"),TEXT("结束后冷却"),TEXT("最大射程"),TEXT("飞行速度"),TEXT("魔攻倍率")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("将火球拖入快捷栏，按绑定键凝聚，再按该键朝准星发射。直接命中不受距离衰减，直击头部要害必定暴击；普通直击和爆炸波及目标各自随机判定暴击，同一目标只结算一次伤害与暴击加成。爆炸伤害从中心 100% 衰减至边缘 50%，掩体可阻挡。伤害半径与热浪最大扩散半径一致；显示伤害未扣目标魔防，也未计额外增伤和暴击。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Model->FireballDefinition().Fireball;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(FString::Printf(TEXT("伤害 = 魔攻 ×（%.2f +（等级 − 1）× %.2f），向下取整。蓝耗 = %.0f +（等级 − 1）× %.0f。基础冷却由 1 级 %.1f 秒逐级降至满级 %.1f 秒，常规减冷却最低 %.1f 秒。仅凝聚时扣蓝，最多悬浮 %.0f 秒，结束后计冷却；退出或死亡取消未结束的火球并保留冷却。"),T.MagicBase,T.MagicPerLevel,T.ManaCost,T.ManaCostPerLevel,T.Cooldown,T.MinimumCooldown,T.MinimumCooldown,T.HoverDuration),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("blizzard"))
        {
            const TCHAR* Rows[]={TEXT("每拍魔法伤害"),TEXT("椭圆区域全轴"),TEXT("持续时间"),TEXT("伤害间隔"),TEXT("消耗魔法"),TEXT("释放后冷却"),TEXT("最大施法距离"),TEXT("每拍寒冷")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("需要装备法杖才能施放的高级寒冰魔法。拖入快捷栏，首次按绑定键扣蓝凝聚乌云；凝聚完成后，再次点按朝准星地面释放，或长按同键显示红色椭圆预览，松键锁定落点，前挥接触时释放。持有期间冷却暂停，成功释放后开始计时。区域在原地保持，每 0.5 秒伤害一次并叠加寒冷，友方不受伤；墙体与不同楼层可阻挡。落雪、坠冰为独立表现，不重复结算伤害。短时动作结束后施放；未装备法杖时提示“需要法杖”。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("打开菜单会收起预览，已凝聚的云仍保留；未释放前切走法杖、凝聚尚未完成时被打断、死亡、离场或持有满 30 秒，退还实际蓝耗并清除预留冷却。释放前发现落点失效可重新选点；联机权威释放失败则退款取消。范围每级增长，持续时间在 5、9、13、17、20 级增加；成长对下一次凝聚生效。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            const auto& T=Definition(SelectedSkill).Blizzard;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(FString::Printf(TEXT("令 K＝等级−1：每拍伤害＝向下取整〔%.0f+%.0f×K+魔攻×(%.2f+%.2f×K)〕，再应用施法媒介、冰系、法术与链式词条。智力通过魔攻生效。1级持续5秒共10拍，20级持续10秒共20拍；显示值未扣目标魔防，也未计暴击和额外套装增伤。"),T.DamageBase,T.DamagePerLevel,T.MagicBase,T.MagicPerLevel),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("absoluteZero"))
        {
            const TCHAR* Rows[]={TEXT("极寒环爆魔法伤害"),TEXT("绝对脆裂物理伤害"),TEXT("单枚冰墙碎冰伤害"),TEXT("环爆半径"),TEXT("蓄寒时长 / 减伤"),TEXT("消耗魔法"),TEXT("释放后冷却"),TEXT("内 / 外圈寒冷"),TEXT("寒冷增伤 / 封顶"),TEXT("引爆冰墙上限")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("终极寒冰魔法，仅当前装备法杖可施放。原地顿杖蓄寒期间获得高额全伤减免（若已激活坚冰铠甲，蓄寒更短且减伤提至 50%），随后以自身为中心 360° 爆发贴地极寒环浪，击退并重削韧、大额叠寒；实墙与楼板阻挡。目标已有每层寒冷均提升环爆主伤（免冻领主同样生效）；对已冻结或寒冷 ≥10 层的目标额外触发「绝对脆裂」物理碎冰爆（冻结享 ×1.5 物理易伤）并消耗冻结或 10 层寒气。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Definition(SelectedSkill).AbsoluteZero;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(FString::Printf(TEXT("冰墙组合技：寒潮扫过半径内己方实体冰墙时直接引爆（最多 %d 面），沿向外 ±%.0f° 扇面轰射物理碎冰弹幕（每面最多 %d 枚，随剩余耐久缩放，单目标前 %d 枚全伤、超出按 %.0f%% 递减）。令 K＝等级−1：主波＝%.0f+%.0f×K+魔攻×(%.2f+%.2f×K)；脆裂＝%.0f+%.0f×K+魔攻×(%.2f+%.2f×K)。未爆发前被打断或切走法杖全额退蓝并清冷却。"),T.MaxDetonatedWalls,T.WallShardConeDegrees,T.MaxShardsPerWall,T.MaxFullShardsPerTarget,T.OverflowShardScale*100.f,T.DamageBase,T.DamagePerLevel,T.MagicBase,T.MagicPerLevel,T.ShatterDamageBase,T.ShatterDamagePerLevel,T.ShatterMagicBase,T.ShatterMagicPerLevel),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("iceWall"))
        {
            const TCHAR* Rows[]={TEXT("成墙物理伤害"),TEXT("冰墙段数"),TEXT("墙体宽度"),TEXT("高墙 / 矮墙"),TEXT("持续时间"),TEXT("消耗魔法"),TEXT("发射后冷却"),TEXT("最大施法距离"),TEXT("寒冷光环范围"),TEXT("光环叠层节拍"),TEXT("墙体生命")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("装备法杖后，拖入快捷栏并按绑定键凝聚。凝聚完成后指向地面显示冰墙模型：绿色可放置、红色不可放置；按 R 切换高墙和矮墙。再按绑定键，冰块快速升空消失，冰墙从预览落点上方砸下，落地扬起烟尘与寒雾。命中同时施加物理伤害、击退与寒冷减速，之后每秒叠加一次寒冷光环。高墙阻挡移动和投射物，矮墙顶面可供机枪脚架支撑。未释放时切走法杖会取消凝聚并退蓝。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Definition(SelectedSkill).IceWall;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(TEXT("寒冷：每层移动速度−%.0f%%；所有来源共用层数，达到%d层触发冻结并消耗%d层。"),CombatChill::SlowPerStack*100.f,CombatChill::FreezeThreshold,CombatChill::FreezeCost),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(FString::Printf(TEXT("令 K＝等级−1：砸落伤害＝向下取整〔%.0f+%.0f×K+智力×(%.2f+%.2f×K)+精神×(%.2f+%.2f×K)〕，再计链式增伤，按目标物防结算。每个目标只结算一次砸落。段数、持续时间与墙体生命继续随等级成长。凝聚只扣一次蓝，发射开始冷却；未发射取消退还实际蓝耗，已发射不退。"),T.DamageBase,T.DamagePerLevel,T.IntelligenceBase,T.IntelligencePerLevel,T.WisdomBase,T.WisdomPerLevel),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("iceSpike"))
        {
            const TCHAR* Rows[]={TEXT("每枚基础伤害"),TEXT("冰锥数量"),TEXT("整轮理论伤害"),TEXT("固定伤害项"),TEXT("魔攻系数"),TEXT("常规最低冷却"),TEXT("消耗魔法"),TEXT("整组结束后冷却"),TEXT("最大射程"),TEXT("飞行速度"),TEXT("最长悬浮时间")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("按绑定键凝聚整组冰锥，再按一次朝准星齐射。每枚到达瞄准点或碰撞后碎裂；不会追踪移动目标，也没有范围爆炸伤害。目标已被击杀时，后续冰锥不再被尸体吃掉，会继续飞向后方目标或射程终点。直击头部要害必定暴击，普通命中随机暴击，同一击只应用一次暴击加成。显示伤害未扣魔防、未计暴击和额外套装增伤；整轮数值假定全部有效命中。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Model->IceSpikeDefinition().IceSpike;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(FString::Printf(TEXT("每枚伤害 = 向下取整〔%.0f + %.1f × 等级 + 魔攻 ×（%.3f + %.3f × 等级）〕，再计法杖改造增伤并取整；不再单独计算智力，与火球同口径。基础枚数 = %d + 向下取整〔（等级 − 1）÷ %d〕。蓝耗 = %.0f +（等级 − 1）× %.0f，基础冷却由 1 级 %.1f 秒逐级降至满级 %.1f 秒。凝聚仅扣一次魔法；全部结束或悬浮超时才开始冷却。更换武器或升级不改变已凝聚的这一组。"),T.DamageBase,T.DamagePerLevel,T.MagicBase,T.MagicPerLevel,T.CountBase,T.CountLevelStep,T.ManaCost,T.ManaCostPerLevel,T.Cooldown,T.MinimumCooldown),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("lightningHaste"))
        {
            const TCHAR* Rows[]={TEXT("移动速度增加"),TEXT("动作速度增加"),TEXT("持续时间"),TEXT("消耗魔法"),TEXT("生效后冷却")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("短暂引雷后，电弧环绕双手与双脚，提高移动、近战攻速、枪械射速、换弹、拉弓、施法与蓄力、武技、武器操作、格挡、翻越和物品使用速度。无需法杖，换武器后继续生效；生效期间不能重复施放。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Definition(SelectedSkill).LightningHaste;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(TEXT("令 K＝等级−1：移速增加 %.1f%%＋%.1f%%×K；动作速度增加 %.1f%%＋%.1f%%×K；持续 %.1f＋%.1f×K 秒；基础蓝耗 %.0f＋%.0f×K，基础冷却 %.0f 秒，从生效时计时。速度加成在原有速度基础上相乘，每个动作只计一次。"),T.MoveBase*100,T.MovePerLevel*100,T.ActionBase*100,T.ActionPerLevel*100,T.DurationBase,T.DurationPerLevel,T.ManaBase,T.ManaPerLevel,T.Cooldown),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(TEXT("冷却、持续伤害间隔、效果持续时间、弹速与跳跃重力保持原时间规则。施法前预扣魔法，未生效取消会退款；生效后死亡或离场结束，已取得的修炼保留。活动增益不跨存档恢复。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("iceArmor"))
        {
            const TCHAR* Rows[]={TEXT("物理防御增加"),TEXT("魔法防御增加"),TEXT("冰甲持续时间"),TEXT("寒冷脉冲半径"),TEXT("脉冲寒冷／间隔"),TEXT("寒冷刷新时长"),TEXT("每层减速"),TEXT("消耗魔法"),TEXT("起手冷却")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("无需法杖，按快捷键后以左手凝结冰甲。提高防御数值，不是独立护盾；受到有效近战直接伤害时，对攻击者叠加 1 层寒冷。周期脉冲对范围内未被实墙阻挡的敌人叠加 1 层寒冷，不造成直接伤害。寒冷只刷新时长，沿用寒冰体系的叠层减速与冻结。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Model->IceArmorDefinition().IceArmor;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(TEXT("物防增加 = 向下取整〔%.0f + %.1f × (等级−1) + 魔攻 × %.2f〕；魔防增加 = 向下取整〔%.0f + %.1f × (等级−1) + 魔攻 × %.2f〕。持续、范围、寒冷时长及冷却随等级成长，上表显示当前装备下的本级与下一级数值。"),T.PhysicalBase,T.PhysicalPerLevel,T.PhysicalMagic,T.MagicBase,T.MagicPerLevel,T.MagicMagic),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(TEXT("短时占手会排队，持续左手占用会提示。起手扣蓝并开始冷却；未释放取消或服务器拒绝会退款，生效后不退款。重新施放刷新冰甲，不叠加防御。数值在起手锁定，升级或换装在下次施法生效。等级、经验、冷却及快捷栏保存；活动冰甲不跨场景或读档恢复。第一人称显示镜头边缘透明冰片，第三人称显示随身体运动的分片冰甲。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("dragonBreath"))
        {
            const auto& D=Model->FireMagicDefinition(SelectedSkill);const auto& T=D.FireMagic;
            const TCHAR* Rows[]={TEXT("每跳魔法伤害"),TEXT("伤害间隔"),TEXT("扇形角度"),TEXT("扇形半径"),TEXT("持续时间"),TEXT("魔力消耗"),TEXT("冷却时间")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(TEXT("终极火焰魔法，仅当前装备法杖可释放。按绑定键后持续向前方%.0f°扇形喷火，每%.1f秒伤害一次，可转动视角改变喷吐方向。半径从1级%.0f米逐级增长至%d级%.0f米；墙体与完整楼板阻挡，栏杆与真实孔洞沿范围魔法规则处理。"),T.ArcDegrees,T.TickSeconds,T.RadiusBase/100,D.MaxLevel,T.RadiusMaximum/100),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(TEXT("每跳基础伤害=向下取整〔%.0f+%.0f×(等级−1)+魔攻×(%.2f+%.2f×(等级−1))〕，再应用当前法杖、魔法书与火系词条。面板不计目标魔防、随机暴击及条件附加伤害。伤害、消耗和持续在施法时锁定，途中升级不改变这一轮。"),T.DamageBase,T.DamagePerLevel,T.MagicBase,T.MagicPerLevel),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(TEXT("起手预扣魔力，开始喷吐后启动冷却；未喷出被取消会退款，已经喷出后中断不返还。持续期间占用持杖施法动作，切走法杖、死亡、受控或优先动作会结束。冷却、等级、经验与快捷栏绑定存档；喷火本身不跨场景或读档恢复。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(FireMagic::IsSkill(SelectedSkill))
        {
            const bool Meteor=SelectedSkill==TEXT("meteor");
            const TCHAR* Rows[]={Meteor?TEXT("爆炸中心伤害"):TEXT("武器命中附加魔法伤害"),Meteor?TEXT("熔火持续伤害"):TEXT("近身灼烧伤害"),Meteor?TEXT("爆炸半径"):TEXT("灼烧光环半径"),TEXT("持续时间"),TEXT("魔力消耗"),TEXT("冷却时间"),TEXT("熔火半径"),TEXT("施法距离"),TEXT("陨落时间"),TEXT("爆炸眩晕"),TEXT("爆炸灼烧")};
            for(int32 I=0;I<(Meteor?UE_ARRAY_COUNT(Rows):6);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(Meteor?TEXT("准星指向地面，长按技能快捷键或选中陨星后的法杖左键显示爆炸范围圆圈，松开锁定落点并施法。陨星始终从落点上方13.2米坠下，穿过沿途屋顶和掩体，到达标定点后撞击。爆炸从中心全额衰减至边缘50%，施加眩晕与3层灼烧；落地熔火每0.5秒伤害一次，并附加1层灼烧。仅当前装备法杖时可施放。"):TEXT("左手施法后获得持续焰甲。存续期间，近战、枪械等非魔法攻击命中存活敌人时追加独立魔法伤害，脚边光环持续灼烧附近敌人。法术和焰甲附伤不会递归触发。该魔法不额外增加防御值。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            if(Meteor)
            {
                const auto& T=Model->FireMagicDefinition(SelectedSkill).FireMagic;
                Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(TEXT("令 K＝等级−1：撞击伤害＝向下取整〔%.0f+%.0f×K+魔攻×(%.2f+%.2f×K)〕；每拍熔火＝向下取整〔%.0f+%.0f×K+魔攻×(%.2f+%.2f×K)〕。再应用施法媒介、火系、法术与链式词条；智力通过魔攻生效。面板显示撞击中心伤害，灼烧、暴击与目标魔防另行结算。"),T.DamageBase,T.DamagePerLevel,T.MagicBase,T.MagicPerLevel,T.AuraDamageBase,T.AuraDamagePerLevel,T.AuraMagicBase,T.AuraMagicPerLevel),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            }
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(Meteor?TEXT("伤害取施法时的魔攻与技能等级。动作实际起手扣蓝并开始冷却，排队不扣费；中断保留已消耗资源。冷却与技能等级存档，活动火场和焰甲不跨场景或读档恢复。"):
                TEXT("伤害、光环半径、持续时间、魔力消耗和冷却按各项成长配置计算，当前值及下一级值见上方对照。数值在起手时锁定，本轮途中升级或换装不重新计算基础快照，下一次施法使用新数值。脚边火环仅是表现，其大小不代表完整灼烧范围。起手预扣魔力并开始冷却；未释放取消或释放被服务器拒绝会退回预扣魔力并撤销本次冷却，已生效后不退款。状态免疫期间不能施放。冷却、等级与经验存档，活动焰甲不跨场景或读档恢复。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("holyLight"))
        {
            const TCHAR* Rows[]={TEXT("敌方基础伤害"),TEXT("友方治疗生命"),TEXT("僵尸伤害倍率"),TEXT("消耗魔法"),TEXT("起手冷却"),TEXT("最大施法距离"),TEXT("准星射线附近范围"),TEXT("魔攻系数"),TEXT("智力系数"),TEXT("智慧系数"),TEXT("光柱持续／淡出")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("拖入快捷栏后按一次，圣光降临准星附近的可见目标：敌人受魔法伤害，友方回复生命。按住 Alt 再按绑定键对自己施放；E 仍优先执行场景交互。治疗不超过生命上限，不复活尸体。僵尸类受到双倍伤害；锁定伤害只随机判定暴击，没有要害加成。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Model->HolyLightDefinition().HolyLight;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(TEXT("基础量 = 向下取整〔%.0f + %.0f×等级 + 魔攻×（%.2f+%.2f×等级）+ 智力×（%.2f+%.2f×等级）+ 智慧×（%.2f+%.2f×等级）〕。基础冷却 %.0f 秒，每 %d 级台阶减少 %.0f 秒。伤害和治疗分别应用当前武器的对应词条，治疗不继承链式增伤和暴击；伤害显示未计目标魔防、暴击及额外套装增伤。"),T.AmountBase,T.AmountPerLevel,T.MagicBase,T.MagicPerLevel,T.IntelligenceBase,T.IntelligencePerLevel,T.WisdomBase,T.WisdomPerLevel,T.Cooldown,T.CooldownLevelStep,T.CooldownStepReduction),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(TEXT("排队、缺蓝、无目标、超距或遮挡不消费。有效起手扣蓝并开始冷却；释放接触帧再次确认锁定目标，落空不返还。短时左手动作结束后施放，双持手枪拒绝施法；死亡、退出或打开菜单取消未释放动作。光柱跟随目标，持续时间不是持续伤害。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(ElectricMagic::IsSkill(SelectedSkill))
        {
            const bool Storm=SelectedSkill==TEXT("stormDomain");
            const TCHAR* Rows[]={Storm?TEXT("主落雷基础伤害"):TEXT("满蓄力基础伤害"),TEXT("消耗魔法"),TEXT("起手冷却"),Storm?TEXT("随身领域半径"):TEXT("最大贯穿距离"),Storm?TEXT("雷云持续时间"):TEXT("满蓄力时间"),Storm?TEXT("每次最多命中目标"):TEXT("命中击退距离"),Storm?TEXT("逐跳传导距离"):TEXT("满蓄力伤害倍率"),Storm?TEXT("每跳伤害衰减"):TEXT("每层感电额外增伤"),Storm?TEXT("命中眩晕"):TEXT("最短有效蓄力"),TEXT("感电层数／持续时间"),TEXT("魔攻系数")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(Storm?
                TEXT("拖入快捷栏后按一次，头顶雷云随玩家移动；立即落雷，此后每0.9秒选择最近的可见敌人，再向邻近目标传导。墙壁遮挡目标与连锁。持续时间10～13秒，半径与目标数随等级提高，9级和17级各增加一个传导目标。"):
                TEXT("长按快捷栏绑定键充能，0.5秒后松开可发射，2.5秒充至100%后保持，松键释放。蓄力期间保持原地，可自由转动视角瞄准；十字准星随充能收拢，未满充在准星标示的范围内随机散射，满充合并为一个点并提示已充能完毕。法杖前方显示电系魔法阵；鼠标点击槽位起手后再次点击也可释放。光束贯穿敌人，遇墙停止，附带击退和两层感电。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Definition(SelectedSkill).ElectricMagic;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(TEXT("令 K＝等级−1：基础伤害＝向下取整〔%.0f+%.0f×K+魔攻×(%.2f+%.2f×K)〕，再应用当前施法媒介与法术增伤。智力通过魔攻生效。雷枪另计蓄力倍率；显示值未扣目标魔防，未计感电、暴击和要害。"),T.DamageBase,T.DamagePerLevel,T.MagicBase,T.MagicPerLevel),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(Storm?
                TEXT("起手一次扣蓝并开始30秒冷却，雷云不会持续扣蓝。每跳保留上一跳70%伤害。命中短暂眩晕、叠加感电，满层触发范围过载。未释放动作取消时退蓝并清除本次冷却；已生成雷云持续生效。"):
                TEXT("伤害乘以蓄力比例、1.3倍满蓄力倍率及〔1＋命中前感电层数×10%〕。不足0.5秒松开、控制打断或取消，退还本次蓝耗并清除冷却；有效发射保留消耗。末端爆闪仅为视觉效果。雷暴领域和贯穿雷枪均需当前装备法杖。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("lightningStrike"))
        {
            const TCHAR* Rows[]={TEXT("主目标基础伤害"),TEXT("最多命中目标"),TEXT("每跳伤害衰减"),TEXT("命中眩晕"),TEXT("消耗魔法"),TEXT("起手冷却"),TEXT("最大施法距离"),TEXT("准星射线附近范围"),TEXT("逐跳传导距离"),TEXT("魔攻系数"),TEXT("智力系数"),TEXT("命中感电层数／时长"),TEXT("每层电伤增加"),TEXT("过载层数／眩晕"),TEXT("过载基础伤害"),TEXT("过载范围")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("拖入快捷栏，按一次锁定准星附近可见敌人。每跳寻找上一目标附近最近且未命中的可见敌人，墙壁阻挡连锁。锁定命中随机判定暴击，不视为直击要害。伤害显示未扣目标魔防、未计感电、暴击与额外套装增伤。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Model->LightningDefinition().Lightning;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(FString::Printf(TEXT("主目标伤害 = 向下取整〔%.0f + %.0f×等级 + 魔攻×（%.2f + %.2f×等级）+ 智力×（%.2f + %.2f×等级）〕，再计算当前法杖／魔杖加成。基础目标数 = %d + 向下取整〔（等级−1）÷%d〕，在6、11、16级各增加一个目标。"),T.DamageBase,T.DamagePerLevel,T.MagicBase,T.MagicPerLevel,T.IntelligenceBase,T.IntelligencePerLevel,T.CountBase,T.CountLevelStep),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(TEXT("有效起手一次扣蓝并开始冷却；排队、缺蓝、无目标、超距或遮挡不扣资源。释放接触帧重新判断原目标，失效则落空并保留已消耗资源。感电层数和持续时间累加，到期清空；叠满触发过载并清层，对附近敌人电击，不再叠感电。换装不改变已开始施法的快照；死亡、退出、打开菜单取消未释放动作，不恢复在途电弧。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("criticalStrike"))
        {
            const TCHAR* Rows[]={TEXT("暴击伤害"),TEXT("技能暴击倍率"),TEXT("幸运")};
            for(int32 I=0;I<3;++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("幸运加成常驻。武器与火球命中可随机暴击，概率为暴击率减去目标暴击抵抗，最低为零。武器或火球直接击中头部要害时必定暴击，目标抗暴不抵消要害触发；火球爆炸波及的其他目标仍各自随机判定。同一击的暴击伤害加成只结算一次。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(TEXT("暴击额外伤害 = 50% + 等级 × 5%；每级幸运 +1。技能倍率与步枪精通的既有要害倍率相乘，最终伤害向下取整。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("dodge"))
        {
            const TCHAR* Rows[]={TEXT("闪避距离增加"),TEXT("体力消耗减少"),TEXT("每次消耗体力")};
            for(int32 I=0;I<3;++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("方向键决定闪避方向；无输入时沿朝向。持续 0.3 秒，全程无敌；碰撞可能缩短实际距离。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(TEXT("每级增加 0.1 米，体力消耗减少 1.5%。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("dexterousHands"))
        {
            const auto& D=Model->DexterousHandsDefinition();
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("敏捷"),0)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("换弹速度"),1)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("拉弓速度"),2)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("被动效果常驻：换弹速度作用于枪械，拉弓速度作用于弓。技能敏捷参与物理攻击与近战攻速；体力恢复仍按基础和装备敏捷计算。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(FString::Printf(TEXT("每级敏捷 +%d、换弹速度 +%.0f%%、拉弓速度 +%.2f%%（满级 +%.0f%%）。拉弓速度与装备、附魔和改造的同类加成相加，满拉耗时再除以（1 + 总加成）；弓精通保留独立缩减。完美节拍跟随满拉时机，窗口长度不变。"),D.DexterityPerLevel,D.ReloadSpeedPerLevel*100,D.BowDrawSpeedPerLevel*100,D.BowDrawSpeedPerLevel*D.MaxLevel*100),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("dashAttack"))
        {
            const bool Ridge=Model->DashAttackStats().RectangleWidthCM>0.f;
            const TCHAR* Rows[]={TEXT("伤害倍率"),TEXT("连续奔跑准备时间"),TEXT("体力消耗（含当前配装）"),Ridge?TEXT("突刺距离（含当前配装）"):TEXT("下劈范围（含当前配装）"),TEXT("击退距离"),Ridge?TEXT("命中矩形宽度"):TEXT("命中扇区"),Ridge?TEXT("突刺伤害（含当前武器）"):TEXT("下劈伤害（含当前武器）")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            if(Ridge)
                Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("装备棱脊穿甲刃时，奔跑就绪后按左键直接向前突刺。伤害为原冲刺攻击的150%，额外获得20%物理护甲穿透。前方矩形的长度比原冲刺攻击远25%，每个目标只命中一次。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            else
            {
                Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("持近战兵器按住左 Shift 向前奔跑，就绪后按左键，经0.25秒前摇衔接下劈。准备时间从1级1秒降至20级0.43秒；蓄满后滑铲、滑铲跳和空中减速均保留就绪，可继续按住 Shift 在空中释放。松开冲刺、发动其他动作，或落地后不再奔跑会重新计时；未蓄满时只在地面奔跑积累。未就绪按左键使用普通攻击；被动技能不需绑定快捷栏。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
                Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(TEXT("伤害倍率=1.75+0.05×等级。基础消耗20体力，受当前近战配装耗体修正；一次出招只扣一次。0.25秒前摇向前突进1米，空中释放保留竖直运动和重力；碰撞阻挡突进，保留原有收势且无回弹。下劈命中正前方45°扇区（左右各22.5°），每个目标一次；基础版附带击退。完整收势后恢复操作，下一次需重新奔跑准备，无独立冷却。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            }
        }
        else if(SelectedSkill==TEXT("whirlwind"))
        {
            const TCHAR* Rows[]={TEXT("近战伤害倍率"),TEXT("常驻力量"),TEXT("冷却时间"),TEXT("体力消耗"),TEXT("横扫半径（含当前范围加成）"),TEXT("击退距离"),TEXT("眩晕时间")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(TEXT("仅可持近战兵器施放，生产工具与枪械不可用。待机转为横持后旋转横扫，命中短暂停帧。伤害倍率=1.5+0.1×等级；力量+等级；冷却=10−0.2×等级秒；体力=20+等级。数值、修炼与旧风车一致；1级1.6倍、9.8秒、21体力，20级3.5倍、6秒、40体力。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(TEXT("半径=(120+5×等级+80)×1.5厘米，再乘当前近战范围系数；击退3.75米、眩晕2.5秒。施放开始扣体力并开始冷却；取消保留已消耗资源，已发生命中照常结算。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("quickCombat"))
        {
            const bool WeaponInput=ColdSteelMelee::QuickCombatModifiers(Model).bQuickCombatUsesWeaponDamage;
            const TCHAR* Rows[]={TEXT("触发快捷键"),WeaponInput?TEXT("打击伤害（含当前武器）"):TEXT("打击伤害（含当前力量）"),WeaponInput?TEXT("武器伤害系数"):TEXT("力量系数"),TEXT("体力消耗"),TEXT("击退距离"),TEXT("额外技能冷却"),TEXT("成长体力减耗")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Note(WeaponInput?
                TEXT("按 F 或快捷栏绑定键发动锥形锤座前顶，对前方范围内的目标造成伤害并击退。当前战锤物理伤害代入原力量项，保留技能等级成长与快速近战增伤；击退与体力消耗包含装备修正。命中不附加眩晕。"):
                TEXT("按 F 或快捷栏绑定键发动当前武器的快速近战：剑使用配重锤，枪械使用各自的砸击动作。伤害取当前等级、力量和武器快速近战倍率；击退与体力消耗包含装备修正。命中不附加眩晕。技能成长降低体力消耗。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(TEXT("没有独立冷却。蓄势、释放与收手构成一个完整动作周期，全部结束后即可再次使用。快捷栏遮罩和倒计时跟随当前武器的独立动作时间与命中停顿，普通武器攻速不加速该武技；动作中重复按键无效，体力不足时不能发动。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else
        {
        const bool Pistol=SelectedSkill==TEXT("pistolMastery");
        const TCHAR* Rows[]={Pistol?TEXT("手枪伤害倍率"):TEXT("步枪伤害倍率"),Pistol?TEXT("手枪附加伤害"):TEXT("步枪附加伤害"),Pistol?TEXT("敏捷"):TEXT("精神"),Pistol?TEXT("持手枪移动速度"):TEXT("步枪要害伤害")};
        for(int32 I=0;I<4;++I) Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
        Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
        Scroll->AddSlot().Padding(16/Scale,12/Scale)[SNew(STextBlock).AutoWrapText(false).WrapTextAt(FMath::Max(1.f,PageWidth-44)/Scale).LineHeightPercentage(1.4f)
            .Text_Lambda([this,Pistol]{
                if(Pistol)return FText::FromString(ColdSteelSkills::IsPistol(Model->Equipped())&&!Model->ActiveProductionTool()?TEXT("当前已持手枪 · 全部收益生效"):TEXT("当前未持手枪 · 敏捷加成常驻，手枪伤害与移速收益在持枪时生效"));
                return FText::FromString(ColdSteelSkills::IsRifle(Model->Equipped())?TEXT("当前已装备步枪 · 全部收益生效"):TEXT("当前未装备步枪 · 精神加成常驻，武器收益在装备步枪后生效"));})
            .Font(ColdSteelUI::TextFont(14*.75f/Scale)).ColorAndOpacity(ColdSteelUI::Success)];
        Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Note(Pistol?TEXT("包含半自动手枪与左轮。伤害倍率只作用于武器贡献，不再额外叠加角色基础物攻；敏捷与巧手叠加。移速收益不改变闪避距离。精通加的敏捷计入角色属性与派生属性；手枪面板按原始分配与装备属性结算。暴击修炼包含随机暴击与实际要害命中。"):TEXT("伤害倍率只作用于武器贡献，不再额外叠加角色基础物攻。要害加成依实际命中部位判定。精通加的精神计入角色属性与派生属性；武器面板按原始分配与装备属性结算，不额外叠加。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        if(bEmbedded)Column->AddSlot().AutoHeight()[Scroll.ToSharedRef()];
        else Column->AddSlot().FillHeight(1)[Scroll.ToSharedRef()];
    }
    return Column;
}
