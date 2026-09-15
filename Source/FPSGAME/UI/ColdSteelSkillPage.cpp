#include "ColdSteelSkillPage.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelQuickDrag.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Skills/ColdSteelSkillRules.h"
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

namespace { bool Additional(FName Id){return Id==TEXT("swordMastery")||Id==TEXT("machineGunMastery")||Id==TEXT("shotgunMastery")||Id==TEXT("bowMastery");} }
void UColdSteelSkillPage::SetHUD(UColdSteelHUDWidget* Owner){HUD=Owner;}
FReply UColdSteelSkillPage::NativeOnPreviewMouseButtonDown(const FGeometry& G,const FPointerEvent& E)
{
    PendingDragSkill=NAME_None;
    if(!bDetail&&HUD.IsValid()&&E.GetEffectingButton()==EKeys::LeftMouseButton)
    {
        const TPair<FName,TSharedPtr<SButton>> Cards[]={{TEXT("iceSpike"),IceSpikeDetailButton},{TEXT("fireball"),FireballDetailButton},{TEXT("dodge"),DodgeDetailButton},{TEXT("heavyStrike"),HeavyDetailButton}};
        for(const auto& Card:Cards)
        {
            if(!Card.Value||!Card.Value->GetCachedGeometry().IsUnderLocation(E.GetScreenSpacePosition()))continue;
            PendingDragSkill=Card.Key;const auto& Geometry=Card.Value->GetCachedGeometry();
            PressedSkillBounds=FSlateRect(Geometry.LocalToAbsolute(FVector2D::ZeroVector),Geometry.LocalToAbsolute(Geometry.GetLocalSize()));
            return FReply::Handled().CaptureMouse(TakeWidget()).DetectDrag(TakeWidget(),EKeys::LeftMouseButton);
        }
    }
    return Super::NativeOnPreviewMouseButtonDown(G,E);
}
FReply UColdSteelSkillPage::NativeOnMouseButtonUp(const FGeometry& G,const FPointerEvent& E)
{
    const FName Id=PendingDragSkill;PendingDragSkill=NAME_None;
    if(!Id.IsNone()&&E.GetEffectingButton()==EKeys::LeftMouseButton)
    {if(PressedSkillBounds.ContainsPoint(E.GetScreenSpacePosition()))OpenDetail(Id);return FReply::Handled().ReleaseMouseCapture();}
    return Super::NativeOnMouseButtonUp(G,E);
}
void UColdSteelSkillPage::NativeOnDragDetected(const FGeometry&,const FPointerEvent& E,UDragDropOperation*& Out)
{
    const FName Id=PendingDragSkill;PendingDragSkill=NAME_None;
    if(!Id.IsNone()&&HUD.IsValid())Out=HUD->StartQuickDrag(Id,INDEX_NONE,Id==TEXT("iceSpike")?&IceSpikeIconBrush:Id==TEXT("heavyStrike")?&HeavyIconBrush:Id==TEXT("fireball")?&FireballIconBrush:&DodgeIconBrush,E.GetScreenSpacePosition());
}

TSharedRef<SWidget> UColdSteelSkillPage::RebuildWidget()
{
    Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if (Model && !IconTexture)
    {
        TArray<uint8> Bytes;
        if (FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->RifleDefinition().Icon)))
            IconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if (IconTexture) { IconBrush.SetResourceObject(IconTexture); IconBrush.DrawAs=ESlateBrushDrawType::Image; }
    }
    SAssignNew(Root,SBox); RefreshLayout(); return Root.ToSharedRef();
}
const FColdSteelSkillDefinition& UColdSteelSkillPage::Definition(FName Id) const
{ if(Id==TEXT("iceSpike"))return Model->IceSpikeDefinition();if(Additional(Id)||Id==TEXT("heavyStrike"))return Model->MasteryDefinition(Id);if(Id==TEXT("fireball"))return Model->FireballDefinition();if(Id==TEXT("criticalStrike"))return Model->CriticalStrikeDefinition();if(Id==TEXT("pistolMastery"))return Model->PistolDefinition();return Id==TEXT("dodge")?Model->DodgeDefinition():(Id==TEXT("dexterousHands")?Model->DexterousHandsDefinition():Model->RifleDefinition()); }
FColdSteelSkillProgress UColdSteelSkillPage::Progress(FName Id) const
{ if(Id==TEXT("iceSpike"))return Model->IceSpikeProgress();if(Additional(Id)||Id==TEXT("heavyStrike"))return Model->MasteryProgress(Id);if(Id==TEXT("fireball"))return Model->FireballProgress();if(Id==TEXT("criticalStrike"))return Model->CriticalStrikeProgress();if(Id==TEXT("pistolMastery"))return Model->PistolProgress();return Id==TEXT("dodge")?Model->DodgeProgress():(Id==TEXT("dexterousHands")?Model->DexterousHandsProgress():Model->RifleProgress()); }
void UColdSteelSkillPage::ReleaseSlateResources(bool bReleaseChildren)
{ Super::ReleaseSlateResources(bReleaseChildren); Scroll.Reset(); Root.Reset();IceSpikeDetailButton.Reset(); DetailButton.Reset();PistolDetailButton.Reset();CriticalDetailButton.Reset();FireballDetailButton.Reset();HeavyDetailButton.Reset();DodgeDetailButton.Reset();DexterousHandsDetailButton.Reset(); BackButton.Reset(); FilterButtons.Reset(); }
void UColdSteelSkillPage::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);
    if (!FMath::IsNearlyEqual(Scale,ColdSteelUI::PixelScale(this))) RefreshLayout();
}
void UColdSteelSkillPage::SetLayoutWidth(float Pixels)
{
    if(FMath::IsNearlyEqual(PageWidth,Pixels,.5f))return;
    PageWidth=Pixels;RefreshLayout();
}
void UColdSteelSkillPage::RefreshLayout()
{
    const float Offset=Scroll?Scroll->GetScrollOffset():0;
    Scale=ColdSteelUI::PixelScale(this); ActionStyle=ColdSteelUI::ButtonStyle(Scale);
    CardBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale);
    IconBrush.ImageSize=FVector2D(48/Scale);
    DodgeIconBrush.ImageSize=FVector2D(48/Scale);
    DexterousHandsIconBrush.ImageSize=FVector2D(48/Scale);
    PistolIconBrush.ImageSize=FVector2D(48/Scale);
    CriticalIconBrush.ImageSize=FVector2D(48/Scale);
    HeavyIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!HeavyIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->MasteryDefinition(TEXT("heavyStrike")).Icon)))HeavyIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(HeavyIconTexture){HeavyIconBrush.SetResourceObject(HeavyIconTexture);HeavyIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    FireballIconBrush.ImageSize=FVector2D(48/Scale);
    IceSpikeIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!IceSpikeIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->IceSpikeDefinition().Icon)))IceSpikeIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(IceSpikeIconTexture){IceSpikeIconBrush.SetResourceObject(IceSpikeIconTexture);IceSpikeIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    if(Model&&!FireballIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->FireballDefinition().Icon)))FireballIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(FireballIconTexture){FireballIconBrush.SetResourceObject(FireballIconTexture);FireballIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    if(Model&&!CriticalIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->CriticalStrikeDefinition().Icon)))CriticalIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(CriticalIconTexture){CriticalIconBrush.SetResourceObject(CriticalIconTexture);CriticalIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    if(Model&&!PistolIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->PistolDefinition().Icon)))PistolIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(PistolIconTexture){PistolIconBrush.SetResourceObject(PistolIconTexture);PistolIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    if(Model&&!DodgeIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->DodgeDefinition().Icon)))DodgeIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(DodgeIconTexture){DodgeIconBrush.SetResourceObject(DodgeIconTexture);DodgeIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    if(Model&&!DexterousHandsIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->DexterousHandsDefinition().Icon)))DexterousHandsIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(DexterousHandsIconTexture){DexterousHandsIconBrush.SetResourceObject(DexterousHandsIconTexture);DexterousHandsIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    if (Root) { Root->SetWidthOverride(PageWidth/Scale);Root->SetHAlign(HAlign_Fill);Root->SetContent(BuildPage()); if(Scroll) Scroll->SetScrollOffset(Offset); }
}
TSharedRef<SWidget> UColdSteelSkillPage::Label(const FString& Value,float Pixels,const FLinearColor& Color,bool bNumeric) const
{
    return SNew(STextBlock).Text(FText::FromString(Value)).Font(bNumeric?ColdSteelUI::NumberFont(Pixels*.75f/Scale):ColdSteelUI::TextFont(Pixels*.75f/Scale))
        .ColorAndOpacity(Color).AutoWrapText(false);
}
TSharedRef<SWidget> UColdSteelSkillPage::Paragraph(const FString& Value,float Pixels,const FLinearColor& Color,float Width) const
{
    return SNew(STextBlock).Text(FText::FromString(Value)).Font(ColdSteelUI::TextFont(Pixels*.75f/Scale))
        .ColorAndOpacity(Color).AutoWrapText(false).WrapTextAt(FMath::Max(1.f,Width)/Scale).LineHeightPercentage(1.4f);
}
TSharedRef<SWidget> UColdSteelSkillPage::Overview(bool bCompact,FName Id)
{
    const auto& D=Definition(Id);
    const bool Compact=PageWidth<440;
    const TCHAR* Tags=Id==TEXT("dodge")?TEXT("身法 / 位移 / 主动"):(Id==TEXT("dexterousHands")?TEXT("敏捷 / 换弹 / 被动"):TEXT("步枪 / 远程 / 被动"));
    const FSlateBrush* SkillIcon=Id==TEXT("dodge")?&DodgeIconBrush:(Id==TEXT("dexterousHands")?&DexterousHandsIconBrush:&IconBrush);
    if(Id==TEXT("pistolMastery")){Tags=TEXT("手枪 / 远程 / 被动");SkillIcon=&PistolIconBrush;}
    if(Id==TEXT("criticalStrike")){Tags=TEXT("暴击 / 幸运 / 被动");SkillIcon=&CriticalIconBrush;}
    if(Id==TEXT("fireball")){Tags=TEXT("火焰 / 范围 / 主动魔法");SkillIcon=&FireballIconBrush;}
    if(Id==TEXT("iceSpike")){Tags=TEXT("寒冰 / 齐射 / 主动魔法");SkillIcon=&IceSpikeIconBrush;}
    if(Id==TEXT("heavyStrike")){Tags=TEXT("近战 / 蓄力 / 主动");SkillIcon=&HeavyIconBrush;}
    if(Additional(Id))Tags=TEXT("武器精通 / 被动");
    auto LevelLabel=[this,Id](){return SNew(STextBlock).Text_Lambda([this,Id]{return FText::FromString(FString::Printf(TEXT("Lv.%d / %d"),Progress(Id).Level,Definition(Id).MaxLevel));})
        .Font(ColdSteelUI::NumberFont(16*.75f/Scale,true)).ColorAndOpacity(ColdSteelUI::Accent).AutoWrapText(false);};
    auto Identity=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[Label(D.Name,20,ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,4/Scale,0,0)[Paragraph(Tags,12,ColdSteelUI::TextSecondary,PageWidth-64-60-(Compact?0:128))];
    if(Compact)Identity->AddSlot().AutoHeight().Padding(0,6/Scale,0,0)[LevelLabel()];
    return SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,12/Scale,0)
                [SNew(SBox).Visibility(Additional(Id)?EVisibility::Collapsed:EVisibility::Visible).WidthOverride(48/Scale).HeightOverride(48/Scale)[SNew(SImage).Image(SkillIcon)]]
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Identity]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8/Scale,0)
                [SNew(SBox).Visibility(Compact?EVisibility::Collapsed:EVisibility::Visible)[LevelLabel()]]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,12/Scale,0,0)[SNew(STextBlock)
            .Text_Lambda([this,Id]{const auto P=Progress(Id);const int32 Need=ColdSteelSkills::ExperienceRequired(Definition(Id),P.Level);
                return FText::FromString(Need?FString::Printf(TEXT("修炼    %d / %d"),P.Experience,Need):TEXT("修炼完成 · 已达最高等级"));})
            .Font(ColdSteelUI::NumberFont(12*.75f/Scale)).ColorAndOpacity(ColdSteelUI::TextSecondary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6/Scale,0,0)[SNew(SBox).HeightOverride(4/Scale)
            [SNew(SProgressBar).Percent_Lambda([this,Id]()->TOptional<float>{const auto P=Progress(Id);const int32 Need=ColdSteelSkills::ExperienceRequired(Definition(Id),P.Level);return Need?FMath::Clamp(float(P.Experience)/Need,0.f,1.f):1.f;})
                .FillColorAndOpacity(ColdSteelUI::Accent)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(bCompact?TEXT("在实战中修炼 · 查看技能详情"):D.Description,14,ColdSteelUI::TextSecondary,PageWidth-76)];
}
FString UColdSteelSkillPage::EffectValue(int32 Index,bool bNext) const
{
    if(bNext&&Progress(SelectedSkill).Level>=Definition(SelectedSkill).MaxLevel)return TEXT("MAX");
    if(SelectedSkill==TEXT("heavyStrike"))
    {
        const auto E=Model->MasteryEffect(SelectedSkill,Progress(SelectedSkill).Level+(bNext?1:0));
        if(Index==0)return FString::Printf(TEXT("×%.1f"),E.HeavyMultiplier);
        if(Index==1)return FString::Printf(TEXT("%.2f s"),E.HeavyChargeSeconds);
        return FString::Printf(TEXT("+%d"),E.Strength);
    }
    if(Additional(SelectedSkill))
    {
        const auto E=Model->MasteryEffect(SelectedSkill,Progress(SelectedSkill).Level+(bNext?1:0));
        if(Index==0)return FString::Printf(TEXT("+%.0f%%"),E.DamagePercent*100);
        if(Index==1)return FString::Printf(TEXT("+%.0f"),E.FlatDamage);
        if(Index==2)return FString::Printf(TEXT("+%d"),E.Strength+E.Constitution+E.Dexterity);
        if(Index==3)return FString::Printf(TEXT("−%.0f%%"),E.CooldownReduction*100);
        return FString::Printf(TEXT("+%.1f"),SelectedSkill==TEXT("machineGunMastery")?E.SpreadDelay:E.Knockback);
    }
    if(SelectedSkill==TEXT("iceSpike"))
    {
        const auto E=Model->IceSpikeStats(Model->IceSpikeProgress().Level+(bNext?1:0));
        switch(Index)
        {
        case 0:return FString::Printf(TEXT("%.0f"),E.Damage);
        case 1:return FString::Printf(TEXT("%d"),E.Count);
        case 2:return FString::Printf(TEXT("%.0f"),E.Damage*E.Count);
        case 3:return FString::Printf(TEXT("%.0f"),E.DamageBase);
        case 4:return FString::Printf(TEXT("%.2f ×"),E.MagicMultiplier);
        case 5:return FString::Printf(TEXT("%.2f ×"),E.IntMultiplier);
        case 6:return FString::Printf(TEXT("%.0f"),E.ManaCost);
        case 7:return FString::Printf(TEXT("%.1f s"),E.Cooldown);
        case 8:return FString::Printf(TEXT("%.0f m"),E.Range/100);
        case 9:return FString::Printf(TEXT("%.0f m/s"),E.Speed/100);
        default:return FString::Printf(TEXT("%.0f s"),E.HoverDuration);
        }
    }
    if(SelectedSkill==TEXT("fireball"))
    {
        const auto E=Model->FireballStats(Model->FireballProgress().Level+(bNext?1:0));
        if(Index==0)return FString::Printf(TEXT("%.0f"),E.Damage);
        if(Index==1)return FString::Printf(TEXT("%.2f m"),E.Radius/100);
        if(Index==2)return FString::Printf(TEXT("%.0f"),E.ManaCost);
        if(Index==3)return FString::Printf(TEXT("%.1f s"),E.Cooldown);
        if(Index==4)return FString::Printf(TEXT("%.0f m"),E.Range/100);
        if(Index==6)return FString::Printf(TEXT("%.2f ×"),E.MagicMultiplier);
        return FString::Printf(TEXT("%.0f m/s"),E.Speed/100);
    }
    if(SelectedSkill==TEXT("criticalStrike"))
    {
        const auto E=Model->CriticalStrikeEffect(Model->CriticalStrikeProgress().Level+(bNext?1:0));
        if(Index==0)return FString::Printf(TEXT("+%.0f%%"),E.CriticalDamageBonus*100);
        if(Index==1)return FString::Printf(TEXT("%.2fx"),1+E.CriticalDamageBonus);
        return FString::Printf(TEXT("+%d"),E.Luck);
    }
    if(SelectedSkill==TEXT("dexterousHands"))
    {
        const auto E=Model->DexterousHandsEffect(Model->DexterousHandsProgress().Level+(bNext?1:0));
        return Index==0?FString::Printf(TEXT("+%d"),E.Dexterity):FString::Printf(TEXT("+%.0f%%"),E.ReloadSpeed*100);
    }
    if(SelectedSkill==TEXT("dodge"))
    {
        const auto E=Model->DodgeEffect(Model->DodgeProgress().Level+(bNext?1:0));
        if(Index==0)return FString::Printf(TEXT("+%.1f m"),E.DodgeDistanceCM/100);
        if(Index==1)return FString::Printf(TEXT("−%.1f%%"),E.DodgeCostReduction*100);
        return FString::Printf(TEXT("%.2f"),Model->StaminaSettings().DodgeCost*(1-E.DodgeCostReduction));
    }
    const bool Pistol=SelectedSkill==TEXT("pistolMastery");
    const auto E=Pistol?Model->PistolEffect(Model->PistolProgress().Level+(bNext?1:0)):Model->RifleEffect(Model->RifleProgress().Level+(bNext?1:0));
    if(Index==0)return FString::Printf(TEXT("+%.0f%%"),E.DamagePercent*100);
    if(Index==1)return FString::Printf(TEXT("+%.0f"),E.FlatDamage);
    if(Index==2)return FString::Printf(TEXT("+%d"),Pistol?E.Dexterity:E.Wisdom);
    return FString::Printf(TEXT("+%.0f%%"),(Pistol?E.MoveSpeed:E.WeakpointPercent)*100);
}
TSharedRef<SWidget> UColdSteelSkillPage::EffectRow(const FString& Caption,int32 Index)
{
    auto Value=[this,Index](bool Next){return SNew(STextBlock)
        .Text_Lambda([this,Index,Next]{return FText::FromString(EffectValue(Index,Next));}).Font(ColdSteelUI::NumberFont(16*.75f/Scale))
        .ColorAndOpacity(Next?ColdSteelUI::Success:ColdSteelUI::TextPrimary).AutoWrapText(false);};
    if(PageWidth<480)
        return SNew(SBorder).BorderImage(&CardBrush).Padding(FMargin(12/Scale,10/Scale))
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[Label(Caption,14,ColdSteelUI::TextSecondary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,8/Scale,0,0)[SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1)[SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()[Label(TEXT("当前等级"),12,ColdSteelUI::TextTertiary)]
                        +SVerticalBox::Slot().AutoHeight().Padding(0,4/Scale,0,0)[Value(false)]]
                    +SHorizontalBox::Slot().FillWidth(1)[SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()[Label(TEXT("下一等级"),12,ColdSteelUI::TextTertiary)]
                        +SVerticalBox::Slot().AutoHeight().Padding(0,4/Scale,0,0)[Value(true)]]]];
    return SNew(SBorder).BorderImage(&CardBrush).Padding(FMargin(12/Scale,10/Scale))
        [SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[Label(Caption,14,ColdSteelUI::TextSecondary)]
            +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(100/Scale).HAlign(HAlign_Right)[Value(false)]]
            +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(100/Scale).HAlign(HAlign_Right)[Value(true)]]];
}
TSharedRef<SWidget> UColdSteelSkillPage::TrainingCard()
{
    const auto& D=Definition(SelectedSkill);
    auto Content=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12/Scale)[Label(TEXT("修炼方式"),16,ColdSteelUI::TextPrimary)];
    auto AddReward=[&](const FString& Name,int32 Experience){
        Content->AddSlot().AutoHeight().Padding(0,5/Scale)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[Label(Name,14,ColdSteelUI::TextSecondary)]
            +SHorizontalBox::Slot().AutoWidth().Padding(12/Scale,0,0,0)[Label(FString::Printf(TEXT("+%d XP"),Experience),14,ColdSteelUI::Success,true)]];
    };
    if(SelectedSkill==TEXT("heavyStrike"))
    {
        AddReward(TEXT("成功施放重击"),D.UseExperience);
        AddReward(TEXT("同次重击命中至少 2 个目标"),D.HeavyHit2Experience);
        AddReward(TEXT("同次重击直接击杀至少 2 个目标"),D.HeavyKill2Experience);
        AddReward(TEXT("同次重击命中至少 5 个目标"),D.HeavyHit5Experience);
        AddReward(TEXT("同次重击直接击杀至少 5 个目标"),D.HeavyKill5Experience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("单次重击只领取最高达成档，不叠加、不按人数倍增。4 个命中算一次 2 人命中档；5 个命中、2 个击杀取 5 人命中档。目标去重，只计存活的可修炼怪物；不计召唤物、尸体、持续伤害击杀。蓄力取消或未蓄满不算施放；完整空挥可得施放经验。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(Additional(SelectedSkill))
    {
        if(D.HitExperience)AddReward(TEXT("有效命中"),D.HitExperience);
        if(D.MultiHitExperience)AddReward(TEXT("一次攻击命中至少两个目标"),D.MultiHitExperience);
        if(D.CriticalExperience)AddReward(TEXT("暴击命中"),D.CriticalExperience);
        AddReward(TEXT("对应武器击杀"),D.KillExperience);
    }
    else
    if(SelectedSkill==TEXT("fireball"))
    {
        AddReward(TEXT("每命中一个目标"),D.Fireball.HitExperience);
        AddReward(TEXT("每击杀一个目标"),D.KillExperience);
        AddReward(TEXT("一次命中至少两个"),D.Fireball.MultiHitExperience);
        AddReward(TEXT("一次击杀至少两个"),D.Fireball.MultiKillExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("上述奖励可叠加，多目标奖励每颗火球各结算一次。火球暴击还可修炼暴击技能；直接命中与爆炸对同一目标只结算一次。空放、召唤物和无修炼目标不提供经验；满级后停止积累。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(SelectedSkill==TEXT("iceSpike"))
    {
        AddReward(TEXT("每次有效命中"),D.IceSpike.HitExperience);AddReward(TEXT("每次直接击杀"),D.IceSpike.KillExperience);
        AddReward(TEXT("整轮命中至少两次"),D.IceSpike.MultiHitExperience);AddReward(TEXT("整轮击杀至少两个"),D.IceSpike.MultiKillExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("整组冰锥结束后汇总，以上奖励可叠加；多枚命中同一目标也计入多次命中。多次命中和多杀额外奖励每轮各一次。空放、尸体、友方、召唤物与无修炼目标不计经验；暴击命中同时修炼暴击技能。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(SelectedSkill==TEXT("criticalStrike"))
    {
        AddReward(TEXT("暴击命中"),D.CriticalHitExperience);AddReward(TEXT("暴击击杀额外奖励"),D.CriticalKillExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(FString::Printf(TEXT("暴击击杀合计获得 %d 点经验，可与对应武器精通或火球修炼叠加。普通命中、普通击杀、持续伤害和召唤物不提供暴击修炼。满级后停止积累。"),D.CriticalHitExperience+D.CriticalKillExperience),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(SelectedSkill==TEXT("dodge"))
    {
        AddReward(TEXT("使用闪避"),D.UseExperience);AddReward(TEXT("成功闪避近战"),D.MeleeDodgeExperience);AddReward(TEXT("成功闪避远程"),D.RangedDodgeExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("无敌期间实际拦截敌人命中才算成功。每次闪避的近战、远程奖励各结算一次，可与使用经验叠加。环境伤害与持续毒伤不计修炼。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(SelectedSkill==TEXT("dexterousHands"))
    {
        AddReward(TEXT("完成换弹"),D.ReloadExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("一次换弹实际补入至少一发，结算一次修炼经验。普通与空仓换弹均可修炼；取消、满弹匣或没有补入弹药时不计。满级后停止积累。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else
    {
        AddReward(SelectedSkill==TEXT("pistolMastery")?TEXT("手枪击杀"):TEXT("步枪击杀"),D.KillExperience);AddReward(TEXT("有效暴击命中"),D.CriticalExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("要害击杀可叠加奖励。普通命中不增加修炼值；满级后停止积累。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    return SNew(SBorder).BorderImage(&CardBrush).Padding(16/Scale)[Content];
}
TSharedRef<SWidget> UColdSteelSkillPage::BuildPage()
{
    Scroll.Reset();
    IceSpikeDetailButton.Reset();
    DetailButton.Reset();PistolDetailButton.Reset();CriticalDetailButton.Reset();FireballDetailButton.Reset();HeavyDetailButton.Reset();DodgeDetailButton.Reset();DexterousHandsDetailButton.Reset();BackButton.Reset();FilterButtons.Reset();
    if (!Model) return Label(TEXT("技能数据暂不可用"),14,ColdSteelUI::TextSecondary);
    auto Column=SNew(SVerticalBox);
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
        if(Category<=1)for(FName Id:{FName(TEXT("swordMastery")),FName(TEXT("machineGunMastery")),FName(TEXT("shotgunMastery")),FName(TEXT("bowMastery"))})
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
            [SAssignNew(FireballDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("fireball")))[Overview(true,TEXT("fireball"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(IceSpikeDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("iceSpike")))[Overview(true,TEXT("iceSpike"))]];
        Column->AddSlot().FillHeight(1)[Scroll.ToSharedRef()];
        Column->AddSlot().AutoHeight().Padding(16/Scale,8/Scale)[Paragraph(TEXT("拖动主动技能卡到 Q/E/X/1–4；空槽移动，占用槽交换，拖出解绑。E 优先交互；左 Shift 短按仍可闪避。"),12,ColdSteelUI::TextTertiary,PageWidth-32)];
    }
    else
    {
        Column->AddSlot().AutoHeight().Padding(16/Scale,12/Scale)[SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight/Scale)
            [SAssignNew(BackButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Center).VAlign(VAlign_Center)
                .OnClicked_Lambda([this]{GoBack();return FReply::Handled();})[Label(TEXT("返回技能列表"),14,ColdSteelUI::TextPrimary)]]];
        SAssignNew(Scroll,SScrollBox).AllowOverscroll(EAllowOverscroll::No);
        Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[SNew(SBorder).BorderImage(&CardBrush).Padding(16/Scale)[Overview(false,SelectedSkill)]];
        if(PageWidth>=480)Scroll->AddSlot().Padding(28/Scale,4/Scale)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("技能收益"),16,ColdSteelUI::TextPrimary)]
            +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(100/Scale).HAlign(HAlign_Right)[Label(TEXT("当前等级"),12,ColdSteelUI::TextSecondary)]]
            +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(100/Scale).HAlign(HAlign_Right)[Label(TEXT("下一等级"),12,ColdSteelUI::Success)]]];
        else Scroll->AddSlot().Padding(28/Scale,4/Scale)[Label(TEXT("技能收益"),16,ColdSteelUI::TextPrimary)];
        if(SelectedSkill==TEXT("heavyStrike"))
        {
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("重击伤害倍率"),0)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("所需蓄力时间"),1)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("力量加成"),2)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("仅近战武器可施放。持符文剑按住左键蓄满后松开；也可拖入快捷栏，按一次自动蓄满释放。1 级倍率 2.5、蓄力 2 秒、力量 +1；每升一级倍率 +0.1、蓄力 −0.05 秒、力量 +1。释放时消耗一次近战体力，无额外冷却，收招结束才能再次使用。力量常驻并参与剑的属性伤害；中途换装、死亡或动作冲突取消蓄力，不保存进行中的动作。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
        }
        else if(Additional(SelectedSkill))
        {
            if(SelectedSkill!=TEXT("swordMastery"))Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("武器伤害倍率"),0)];
            if(SelectedSkill!=TEXT("shotgunMastery"))Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("固定伤害"),1)];
            if(SelectedSkill!=TEXT("swordMastery"))Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(SelectedSkill==TEXT("machineGunMastery")?TEXT("力量"):SelectedSkill==TEXT("shotgunMastery")?TEXT("体质"):TEXT("敏捷"),2)];
            if(SelectedSkill==TEXT("swordMastery")||SelectedSkill==TEXT("bowMastery"))Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("攻击间隔缩减"),3)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("属性被动常驻；使用对应武器修炼。伤害、强化、改造和附魔共用当前计算结果。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else
        if(SelectedSkill==TEXT("fireball"))
        {
            const TCHAR* Rows[]={TEXT("基础魔法伤害"),TEXT("爆炸半径"),TEXT("消耗魔法"),TEXT("结束后冷却"),TEXT("最大射程"),TEXT("飞行速度"),TEXT("魔攻倍率")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("将火球拖入快捷栏，按绑定键凝聚，再按该键朝准星发射。直接命中不受距离衰减，直击头部要害必定暴击；普通直击和爆炸波及目标各自随机判定暴击，同一目标只结算一次伤害与暴击加成。爆炸伤害从中心 100% 衰减至边缘 50%，掩体可阻挡。伤害半径与热浪最大扩散半径一致；显示伤害未扣目标魔防，也未计额外增伤和暴击。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Model->FireballDefinition().Fireball;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(FString::Printf(TEXT("伤害 = 魔攻 ×（%.2f +（等级 − 1）× %.2f），向下取整。蓝耗 = %.0f +（等级 − 1）× %.0f。基础冷却由 1 级 %.1f 秒逐级降至满级 %.1f 秒，常规减冷却最低 %.1f 秒。仅凝聚时扣蓝，最多悬浮 %.0f 秒，结束后计冷却；退出或死亡取消未结束的火球并保留冷却。"),T.MagicBase,T.MagicPerLevel,T.ManaCost,T.ManaCostPerLevel,T.Cooldown,T.MinimumCooldown,T.MinimumCooldown,T.HoverDuration),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("iceSpike"))
        {
            const TCHAR* Rows[]={TEXT("每枚基础伤害"),TEXT("冰锥数量"),TEXT("整轮理论伤害"),TEXT("固定伤害项"),TEXT("魔攻系数"),TEXT("智力系数"),TEXT("消耗魔法"),TEXT("整组结束后冷却"),TEXT("最大射程"),TEXT("飞行速度"),TEXT("最长悬浮时间")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("按绑定键凝聚整组冰锥，再按一次朝准星齐射。每枚到达瞄准点或碰撞后碎裂；不会追踪移动目标，也没有范围爆炸伤害。直击头部要害必定暴击，普通命中随机暴击，同一击只应用一次暴击加成。显示伤害未扣魔防、未计暴击和额外套装增伤；整轮数值假定全部有效命中。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Model->IceSpikeDefinition().IceSpike;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(FString::Printf(TEXT("每枚伤害 = 向下取整〔%.0f + %.0f × 等级 + 魔攻 ×（%.2f + %.2f × 等级）+ 智力 ×（%.2f + %.2f × 等级）〕，再计法杖改造增伤并取整。基础枚数 = %d + 向下取整〔（等级 − 1）÷ %d〕。凝聚仅扣一次魔法；全部结束或悬浮超时才开始冷却。更换武器或升级不改变已凝聚的这一组。"),T.DamageBase,T.DamagePerLevel,T.MagicBase,T.MagicPerLevel,T.IntBase,T.IntPerLevel,T.CountBase,T.CountLevelStep),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("criticalStrike"))
        {
            const TCHAR* Rows[]={TEXT("暴击伤害加成"),TEXT("技能暴击倍率"),TEXT("幸运")};
            for(int32 I=0;I<3;++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("幸运加成常驻。武器与火球命中可随机暴击，概率为暴击率减去目标暴击抵抗，最低为零。武器或火球直接击中头部要害时必定暴击，目标抗暴不抵消要害触发；火球爆炸波及的其他目标仍各自随机判定。同一击的暴击伤害加成只结算一次。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("暴击额外伤害 = 50% + 等级 × 5%；每级幸运 +1。技能倍率与步枪精通的既有要害倍率相乘，最终伤害向下取整。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("dodge"))
        {
            const TCHAR* Rows[]={TEXT("闪避距离增加"),TEXT("体力消耗减少"),TEXT("每次消耗体力")};
            for(int32 I=0;I<3;++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("方向键决定闪避方向；无输入时沿朝向。持续 0.3 秒，全程无敌；碰撞可能缩短实际距离。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("每级增加 0.1 米，体力消耗减少 1.5%。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("dexterousHands"))
        {
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("敏捷"),0)];
            Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("换弹速度"),1)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("被动效果常驻，适用于所有枪械。敏捷同时参与物理攻击、攻击速度与体力恢复的计算。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("每级敏捷 +1、换弹速度 +1%。实际换弹耗时 = 枪械与配件耗时 ÷（1 + 技能速度加成）。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
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
        Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(Pistol?TEXT("包含半自动手枪与左轮。伤害倍率只作用于武器贡献，不再额外叠加角色基础物攻；敏捷与巧手叠加。移速收益不改变闪避距离。暴击修炼包含随机暴击与实际要害命中。"):TEXT("伤害倍率只作用于武器贡献，不再额外叠加角色基础物攻。要害加成依实际命中部位判定。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        Column->AddSlot().FillHeight(1)[Scroll.ToSharedRef()];
    }
    return Column;
}
FReply UColdSteelSkillPage::SelectCategory(int32 Index)
{ Category=Index; if(Scroll)Scroll->SetScrollOffset(0); RefreshLayout(); return FReply::Handled().SetUserFocus(FilterButtons[Index].ToSharedRef(),EFocusCause::Navigation); }
FReply UColdSteelSkillPage::OpenDetail(FName Id)
{ SelectedSkill=Id;bDetail=true; if(Scroll)Scroll->SetScrollOffset(0); RefreshLayout(); return FReply::Handled().SetUserFocus(BackButton.ToSharedRef(),EFocusCause::Navigation); }
bool UColdSteelSkillPage::GoBack()
{ if(!bDetail)return false; bDetail=false; if(Scroll)Scroll->SetScrollOffset(0); RefreshLayout();auto Button=SelectedSkill==TEXT("dodge")?DodgeDetailButton:(SelectedSkill==TEXT("dexterousHands")?DexterousHandsDetailButton:DetailButton);if(SelectedSkill==TEXT("pistolMastery"))Button=PistolDetailButton;if(SelectedSkill==TEXT("criticalStrike"))Button=CriticalDetailButton;if(SelectedSkill==TEXT("fireball"))Button=FireballDetailButton;if(SelectedSkill==TEXT("heavyStrike"))Button=HeavyDetailButton;if(Button)FSlateApplication::Get().SetKeyboardFocus(Button,EFocusCause::Navigation); return true; }
