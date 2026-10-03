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
        const TPair<FName,TSharedPtr<SButton>> Cards[]={{TEXT("swordUppercut"),UppercutDetailButton},{TEXT("stormDomain"),ElectricDetailButtons.FindRef(TEXT("stormDomain"))},{TEXT("thunderLance"),ElectricDetailButtons.FindRef(TEXT("thunderLance"))},{TEXT("blizzard"),BlizzardDetailButton},{TEXT("iceWall"),IceWallDetailButton},{TEXT("meteor"),MeteorDetailButton},{TEXT("flameArmor"),FlameArmorDetailButton},{TEXT("holyLight"),HolyLightDetailButton},{TEXT("lightningStrike"),LightningDetailButton},{TEXT("iceSpike"),IceSpikeDetailButton},{TEXT("fireball"),FireballDetailButton},{TEXT("dodge"),DodgeDetailButton},{TEXT("heavyStrike"),HeavyDetailButton},{TEXT("quickCombat"),QuickCombatDetailButton},{TEXT("whirlwind"),WhirlwindDetailButton}};
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
    if(Id==TEXT("swordUppercut")&&HUD.IsValid())
    {Out=HUD->StartQuickDrag(Id,INDEX_NONE,&UppercutIconBrush,E.GetScreenSpacePosition());return;}
    if(!Id.IsNone()&&HUD.IsValid())Out=HUD->StartQuickDrag(Id,INDEX_NONE,ElectricMagic::IsSkill(Id)?ElectricIconBrushes.Find(Id):Id==TEXT("blizzard")?&BlizzardIconBrush:Id==TEXT("iceWall")?&IceWallIconBrush:Id==TEXT("meteor")?&MeteorIconBrush:Id==TEXT("flameArmor")?&FlameArmorIconBrush:Id==TEXT("holyLight")?&HolyLightIconBrush:Id==TEXT("lightningStrike")?&LightningIconBrush:Id==TEXT("whirlwind")?&WhirlwindIconBrush:Id==TEXT("iceSpike")?&IceSpikeIconBrush:Id==TEXT("heavyStrike")?&HeavyIconBrush:Id==TEXT("fireball")?&FireballIconBrush:Id==TEXT("quickCombat")?&QuickCombatIconBrush:&DodgeIconBrush,E.GetScreenSpacePosition());
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
{ if(Id==TEXT("swordUppercut"))return Model->MasteryDefinition(Id);if(ElectricMagic::IsSkill(Id))return Model->ElectricMagicDefinition(Id);if(Id==TEXT("blizzard"))return Model->BlizzardDefinition();if(Id==TEXT("iceWall"))return Model->IceWallDefinition();if(FireMagic::IsSkill(Id))return Model->FireMagicDefinition(Id);if(Id==TEXT("holyLight"))return Model->HolyLightDefinition();if(Id==TEXT("lightningStrike"))return Model->LightningDefinition();if(Id==TEXT("iceSpike"))return Model->IceSpikeDefinition();if(Id==TEXT("quickCombat"))return Model->QuickCombatDefinition();if(Additional(Id)||Id==TEXT("heavyStrike")||Id==TEXT("whirlwind")||Id==TEXT("dashAttack"))return Model->MasteryDefinition(Id);if(Id==TEXT("fireball"))return Model->FireballDefinition();if(Id==TEXT("criticalStrike"))return Model->CriticalStrikeDefinition();if(Id==TEXT("pistolMastery"))return Model->PistolDefinition();return Id==TEXT("dodge")?Model->DodgeDefinition():(Id==TEXT("dexterousHands")?Model->DexterousHandsDefinition():Model->RifleDefinition()); }
FColdSteelSkillProgress UColdSteelSkillPage::Progress(FName Id) const
{ if(ElectricMagic::IsSkill(Id))return Model->ElectricMagicProgress(Id);if(Id==TEXT("blizzard"))return Model->BlizzardProgress();if(Id==TEXT("iceWall"))return Model->IceWallProgress();if(FireMagic::IsSkill(Id))return Model->FireMagicProgress(Id);if(Id==TEXT("holyLight"))return Model->HolyLightProgress();if(Id==TEXT("lightningStrike"))return Model->LightningProgress();if(Id==TEXT("iceSpike"))return Model->IceSpikeProgress();if(Id==TEXT("quickCombat"))return Model->QuickCombatProgress();if(Additional(Id)||Id==TEXT("heavyStrike")||Id==TEXT("whirlwind")||Id==TEXT("dashAttack"))return Model->MasteryProgress(Id);if(Id==TEXT("fireball"))return Model->FireballProgress();if(Id==TEXT("criticalStrike"))return Model->CriticalStrikeProgress();if(Id==TEXT("pistolMastery"))return Model->PistolProgress();return Id==TEXT("dodge")?Model->DodgeProgress():(Id==TEXT("dexterousHands")?Model->DexterousHandsProgress():Model->RifleProgress()); }
void UColdSteelSkillPage::ReleaseSlateResources(bool bReleaseChildren)
{ UppercutDetailButton.Reset();ElectricDetailButtons.Reset();BlizzardDetailButton.Reset();IceWallDetailButton.Reset();Super::ReleaseSlateResources(bReleaseChildren); Scroll.Reset(); Root.Reset();MeteorDetailButton.Reset();FlameArmorDetailButton.Reset();LightningDetailButton.Reset();HolyLightDetailButton.Reset();IceSpikeDetailButton.Reset(); DetailButton.Reset();PistolDetailButton.Reset();CriticalDetailButton.Reset();FireballDetailButton.Reset();HeavyDetailButton.Reset();DodgeDetailButton.Reset();DexterousHandsDetailButton.Reset();QuickCombatDetailButton.Reset();WhirlwindDetailButton.Reset();DashAttackDetailButton.Reset(); BackButton.Reset(); FilterButtons.Reset(); }
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
    UppercutIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!UppercutIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Definition(TEXT("swordUppercut")).Icon)))UppercutIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(UppercutIconTexture){UppercutIconBrush.SetResourceObject(UppercutIconTexture);UppercutIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    if(Model&&!HeavyIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->MasteryDefinition(TEXT("heavyStrike")).Icon)))HeavyIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(HeavyIconTexture){HeavyIconBrush.SetResourceObject(HeavyIconTexture);HeavyIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    FireballIconBrush.ImageSize=FVector2D(48/Scale);
    IceSpikeIconBrush.ImageSize=FVector2D(48/Scale);
    for(const FName Id:{FName(TEXT("stormDomain")),FName(TEXT("thunderLance"))})
    {
        auto& Brush=ElectricIconBrushes.FindOrAdd(Id);Brush.ImageSize=FVector2D(48/Scale);
        if(Model&&!ElectricIconTextures.FindRef(Id))
        {
            TArray<uint8> Bytes;if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Definition(Id).Icon)))
                ElectricIconTextures.Add(Id,FImageUtils::ImportBufferAsTexture2D(Bytes));
        }
        Brush.SetResourceObject(ElectricIconTextures.FindRef(Id));Brush.DrawAs=ESlateBrushDrawType::Image;
    }
    BlizzardIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!BlizzardIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->BlizzardDefinition().Icon)))BlizzardIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(BlizzardIconTexture){BlizzardIconBrush.SetResourceObject(BlizzardIconTexture);BlizzardIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    IceWallIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!IceWallIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->IceWallDefinition().Icon)))IceWallIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(IceWallIconTexture){IceWallIconBrush.SetResourceObject(IceWallIconTexture);IceWallIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    LightningIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!LightningIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->LightningDefinition().Icon)))LightningIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(LightningIconTexture){LightningIconBrush.SetResourceObject(LightningIconTexture);LightningIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    MeteorIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!MeteorIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->FireMagicDefinition(TEXT("meteor")).Icon)))MeteorIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(MeteorIconTexture){MeteorIconBrush.SetResourceObject(MeteorIconTexture);MeteorIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    FlameArmorIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!FlameArmorIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->FireMagicDefinition(TEXT("flameArmor")).Icon)))FlameArmorIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(FlameArmorIconTexture){FlameArmorIconBrush.SetResourceObject(FlameArmorIconTexture);FlameArmorIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    HolyLightIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!HolyLightIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->HolyLightDefinition().Icon)))HolyLightIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(HolyLightIconTexture){HolyLightIconBrush.SetResourceObject(HolyLightIconTexture);HolyLightIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    DashAttackIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!DashAttackIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->MasteryDefinition(TEXT("dashAttack")).Icon)))DashAttackIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(DashAttackIconTexture){DashAttackIconBrush.SetResourceObject(DashAttackIconTexture);DashAttackIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    WhirlwindIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!WhirlwindIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->MasteryDefinition(TEXT("whirlwind")).Icon)))WhirlwindIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(WhirlwindIconTexture){WhirlwindIconBrush.SetResourceObject(WhirlwindIconTexture);WhirlwindIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    QuickCombatIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!QuickCombatIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->QuickCombatDefinition().Icon)))QuickCombatIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(QuickCombatIconTexture){QuickCombatIconBrush.SetResourceObject(QuickCombatIconTexture);QuickCombatIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
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
    if(Id==TEXT("swordUppercut"))
    {
        // No level or training presentation until this motion has gameplay tuning.
        return SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,12/Scale,0)
                    [SNew(SBox).WidthOverride(48/Scale).HeightOverride(48/Scale)[SNew(SImage).Image(&UppercutIconBrush)]]
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(SVerticalBox)
                    +SVerticalBox::Slot().AutoHeight()[Label(D.Name,20,ColdSteelUI::TextPrimary)]
                    +SVerticalBox::Slot().AutoHeight().Padding(0,4/Scale,0,0)
                        [Paragraph(TEXT("持剑 / 上挑 / 主动"),12,ColdSteelUI::TextSecondary,PageWidth-124)]]]
            +SVerticalBox::Slot().AutoHeight().Padding(0,12/Scale,0,0)
                [Paragraph(bCompact?TEXT("拖入快捷栏使用 · 当前开放动作试用"):D.Description,14,ColdSteelUI::TextSecondary,PageWidth-76)];
    }
    const bool Compact=PageWidth<440;
    const TCHAR* Tags=Id==TEXT("dodge")?TEXT("身法 / 位移 / 主动"):(Id==TEXT("dexterousHands")?TEXT("敏捷 / 换弹 / 被动"):TEXT("步枪 / 远程 / 被动"));
    const FSlateBrush* SkillIcon=Id==TEXT("dodge")?&DodgeIconBrush:(Id==TEXT("dexterousHands")?&DexterousHandsIconBrush:&IconBrush);
    if(Id==TEXT("pistolMastery")){Tags=TEXT("手枪 / 远程 / 被动");SkillIcon=&PistolIconBrush;}
    if(Id==TEXT("criticalStrike")){Tags=TEXT("暴击 / 幸运 / 被动");SkillIcon=&CriticalIconBrush;}
    if(Id==TEXT("fireball")){Tags=TEXT("火焰 / 范围 / 主动魔法");SkillIcon=&FireballIconBrush;}
    if(Id==TEXT("iceSpike")){Tags=TEXT("寒冰 / 齐射 / 主动魔法");SkillIcon=&IceSpikeIconBrush;}
    if(Id==TEXT("blizzard")){Tags=TEXT("寒冰 / 区域 / 主动魔法");SkillIcon=&BlizzardIconBrush;}
    if(Id==TEXT("iceWall")){Tags=TEXT("寒冰 / 掩体 / 主动魔法");SkillIcon=&IceWallIconBrush;}
    if(Id==TEXT("meteor")){Tags=TEXT("火焰 / 陨星 / 主动魔法");SkillIcon=&MeteorIconBrush;}
    if(Id==TEXT("flameArmor")){Tags=TEXT("火焰 / 附魔光环 / 主动魔法");SkillIcon=&FlameArmorIconBrush;}
    if(Id==TEXT("holyLight")){Tags=TEXT("圣光 / 敌伤友疗 / 主动魔法");SkillIcon=&HolyLightIconBrush;}
    if(ElectricMagic::IsSkill(Id)){Tags=Id==TEXT("stormDomain")?TEXT("闪电 / 随身领域 / 主动魔法"):TEXT("闪电 / 蓄力贯穿 / 主动魔法");SkillIcon=ElectricIconBrushes.Find(Id);}
    if(Id==TEXT("lightningStrike")){Tags=TEXT("闪电 / 连锁 / 主动魔法");SkillIcon=&LightningIconBrush;}
    if(Id==TEXT("dashAttack")){Tags=TEXT("近战 / 下劈 / 被动");SkillIcon=&DashAttackIconBrush;}
    if(Id==TEXT("whirlwind")){Tags=TEXT("近战 / 范围 / 主动");SkillIcon=&WhirlwindIconBrush;}
    if(Id==TEXT("heavyStrike")){Tags=TEXT("近战 / 蓄力 / 主动");SkillIcon=&HeavyIconBrush;}
    if(Id==TEXT("quickCombat")){Tags=TEXT("近战 / 打击 / 主动");SkillIcon=&QuickCombatIconBrush;}
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
    if(FireMagic::IsSkill(SelectedSkill))
    {
        const auto C=Model->FireMagicStats(SelectedSkill,Progress(SelectedSkill).Level+(bNext?1:0));
        const bool Meteor=SelectedSkill==TEXT("meteor");
        switch(Index)
        {
        case 0:return FString::Printf(TEXT("%.0f"),C.Damage);
        case 1:return FString::Printf(TEXT("%.0f / %.1fs"),C.AuraDamage,C.TickSeconds);
        case 2:return FString::Printf(TEXT("%.2f m"),(Meteor?C.Radius:C.AuraRadius)/100);
        case 3:return FString::Printf(TEXT("%.0f s"),C.Duration);
        case 4:return FString::Printf(TEXT("%.0f"),C.ManaCost);
        case 5:return FString::Printf(TEXT("%.1f s"),C.Cooldown);
        case 6:return FString::Printf(TEXT("%.2f m"),C.AuraRadius/100);
        case 7:return FString::Printf(TEXT("%.2f m"),C.Range/100);
        case 8:return FString::Printf(TEXT("%.2f s"),C.FallSeconds);
        case 9:return FString::Printf(TEXT("%.1f s"),C.StunSeconds);
        case 10:return FString::Printf(TEXT("%d 层 / %.1fs"),C.BurnStacks,C.BurnSeconds);
        }
    }
    if(SelectedSkill==TEXT("holyLight"))
    {
        const auto C=Model->HolyLightStats(Model->HolyLightProgress().Level+(bNext?1:0));
        switch(Index)
        {
        case 0:return FString::Printf(TEXT("%.0f"),C.Damage);
        case 1:return FString::Printf(TEXT("%.0f"),C.Healing);
        case 2:return FString::Printf(TEXT("%.0f ×"),C.ZombieMultiplier);
        case 3:return FString::Printf(TEXT("%.0f"),C.ManaCost);
        case 4:return FString::Printf(TEXT("%.1f s"),C.Cooldown);
        case 5:return FString::Printf(TEXT("%.1f m"),C.Range/100);
        case 6:return FString::Printf(TEXT("%.1f m"),C.AimRadius/100);
        case 7:return FString::Printf(TEXT("%.2f ×"),C.MagicMultiplier);
        case 8:return FString::Printf(TEXT("%.2f ×"),C.IntelligenceMultiplier);
        case 9:return FString::Printf(TEXT("%.2f ×"),C.WisdomMultiplier);
        default:return FString::Printf(TEXT("%.1f + %.1f s"),C.Duration,C.Fade);
        }
    }
    if(ElectricMagic::IsSkill(SelectedSkill))
    {
        const auto C=Model->ElectricMagicStats(SelectedSkill,Progress(SelectedSkill).Level+(bNext?1:0));
        const bool Storm=SelectedSkill==TEXT("stormDomain");const auto& H=C.Hit;
        switch(Index)
        {
        case 0:return FString::Printf(TEXT("%.0f"),H.Damage*(Storm?1.f:C.ChargeBonus));
        case 1:return FString::Printf(TEXT("%.0f"),H.ManaCost);
        case 2:return FString::Printf(TEXT("%.1f s"),H.Cooldown);
        case 3:return FString::Printf(TEXT("%.2f m"),(Storm?C.Radius:H.Range)/100);
        case 4:return FString::Printf(TEXT("%.1f s"),Storm?C.Duration:C.MaxCharge);
        case 5:return Storm?FString::FromInt(H.Count):FString::Printf(TEXT("%.2f m"),C.Knockback/100);
        case 6:return Storm?FString::Printf(TEXT("%.2f m"),H.ChainRange/100):FString::Printf(TEXT("%.2f ×"),C.ChargeBonus);
        case 7:return FString::Printf(TEXT("%.0f%%"),(Storm?H.ChainDecay:C.StackDamage)*100);
        case 8:return FString::Printf(TEXT("%.2f s"),Storm?H.StunSeconds:C.MinCharge);
        case 9:return FString::Printf(TEXT("+%d / %.1f s"),H.ElectrifyStacks,H.ElectrifyDuration);
        case 10:return FString::Printf(TEXT("%.2f ×"),H.MagicMultiplier);
        default:return FString::Printf(TEXT("%.2f ×"),H.IntelligenceMultiplier);
        }
    }
    if(SelectedSkill==TEXT("lightningStrike"))
    {
        const auto C=Model->LightningStats(Model->LightningProgress().Level+(bNext?1:0));
        switch(Index)
        {
        case 0:return FString::Printf(TEXT("%.0f"),C.Damage);
        case 1:return FString::Printf(TEXT("%d"),C.Count);
        case 2:return FString::Printf(TEXT("%.0f%%"),C.ChainDecay*100);
        case 3:return FString::Printf(TEXT("%.2f s"),C.StunSeconds);
        case 4:return FString::Printf(TEXT("%.0f"),C.ManaCost);
        case 5:return FString::Printf(TEXT("%.1f s"),C.Cooldown);
        case 6:return FString::Printf(TEXT("%.1f m"),C.Range/100);
        case 7:return FString::Printf(TEXT("%.1f m"),C.AimRadius/100);
        case 8:return FString::Printf(TEXT("%.1f m"),C.ChainRange/100);
        case 9:return FString::Printf(TEXT("%.2f ×"),C.MagicMultiplier);
        case 10:return FString::Printf(TEXT("%.2f ×"),C.IntelligenceMultiplier);
        case 11:return FString::Printf(TEXT("+%d / %.1f s"),C.ElectrifyStacks,C.ElectrifyDuration);
        case 12:return FString::Printf(TEXT("%.0f%%"),C.ElectricBonusPerStack*100);
        case 13:return FString::Printf(TEXT("%d / %.1f s"),C.OverloadStacks,C.OverloadStun);
        case 14:return FString::Printf(TEXT("%.0f"),C.OverloadDamage);
        default:return FString::Printf(TEXT("%.2f m"),C.OverloadRange/100);
        }
    }
    if(SelectedSkill==TEXT("dashAttack"))
    {
        const auto C=Model->DashAttackStats(Progress(SelectedSkill).Level+(bNext?1:0));
        switch(Index)
        {
        case 0:return FString::Printf(TEXT("×%.2f"),C.DamageMultiplier);
        case 1:return FString::Printf(TEXT("%.2f 秒"),C.ReadySeconds);
        case 2:return FString::Printf(TEXT("%.1f"),C.StaminaCost);
        case 3:return C.RangeCM>0.f?FString::Printf(TEXT("%.2f 米"),C.RangeCM/100.f):FString::Printf(TEXT("兵器范围 + %.2f 米"),C.RangeBonusCM/100.f);
        case 4:return C.RangeCM>0.f?FString::Printf(TEXT("%.2f 米"),C.KnockbackCM/100.f):FString::Printf(TEXT("兵器击退 + %.2f 米"),C.KnockbackBonusCM/100.f);
        case 5:return FString::Printf(TEXT("%.0f°"),C.ArcDegrees);
        default:return C.RangeCM>0.f?FString::Printf(TEXT("%.0f"),C.Damage):TEXT("需装备近战武器");
        }
    }
    if(SelectedSkill==TEXT("whirlwind"))
    {
        const int32 L=Progress(SelectedSkill).Level+(bNext?1:0);const auto C=Model->WhirlwindStats(L);
        if(Index==0)return FString::Printf(TEXT("×%.1f"),C.DamageMultiplier);
        if(Index==1)return FString::Printf(TEXT("+%d"),Model->MasteryEffect(SelectedSkill,L).Strength);
        if(Index==2)return FString::Printf(TEXT("%.1f 秒"),C.CooldownSeconds);
        if(Index==3)return FString::Printf(TEXT("%.0f"),C.StaminaCost);
        if(Index==4)return FString::Printf(TEXT("%.2f 米"),C.RadiusCM/100.f);
        if(Index==5)return FString::Printf(TEXT("%.2f 米"),C.KnockbackCM/100.f);
        return FString::Printf(TEXT("%.1f 秒"),C.StunSeconds);
    }
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
        return FString::Printf(TEXT("+%.0f%%"),(1.f/FMath::Max(.05f,1.f-E.CooldownReduction)-1.f)*100);
    }
    if(SelectedSkill==TEXT("blizzard"))
    {
        const auto E=Model->BlizzardStats(Model->BlizzardProgress().Level+(bNext?1:0));
        switch(Index)
        {
        case 0:return FString::Printf(TEXT("%.0f"),E.Damage);
        case 1:return FString::Printf(TEXT("%.2f × %.2f m"),E.RadiusX*.02f,E.RadiusY*.02f);
        case 2:return FString::Printf(TEXT("%.1f s"),E.Duration);
        case 3:return FString::Printf(TEXT("%.1f s"),E.TickSeconds);
        case 4:return FString::Printf(TEXT("%.0f"),E.ManaCost);
        case 5:return FString::Printf(TEXT("%.1f s"),E.Cooldown);
        case 6:return FString::Printf(TEXT("%.2f m"),E.Range*.01f);
        default:return FString::Printf(TEXT("%d 层 / %.1f s / 每层 %.1f%%"),E.ChillStacks,E.ChillSeconds,E.ChillSlow*100);
        }
    }
    if(SelectedSkill==TEXT("iceWall"))
    {
        const auto E=Model->IceWallStats(Model->IceWallProgress().Level+(bNext?1:0));
        switch(Index)
        {
        case 0:return FString::Printf(TEXT("%.0f"),E.Damage);
        case 1:return FString::Printf(TEXT("%d"),E.Count);
        case 2:return FString::Printf(TEXT("%.2f m"),E.Width()/100);
        case 3:return FString::Printf(TEXT("%.1f / %.1f m"),E.HighHeight/100,E.LowHeight/100);
        case 4:return FString::Printf(TEXT("%.1f s"),E.Duration);
        case 5:return FString::Printf(TEXT("%.0f"),E.ManaCost);
        case 6:return FString::Printf(TEXT("%.1f s"),E.Cooldown);
        case 7:return FString::Printf(TEXT("%.1f m"),E.Range/100);
        case 8:return FString::Printf(TEXT("%.1f m"),E.ChillRadius/100);
        case 10:return FString::Printf(TEXT("%.0f"),E.MaxHealth);
        default:return FString::Printf(TEXT("%d 层 / %.1f s"),E.ChillStacks,E.ChillInterval);
        }
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
        case 5:return FString::Printf(TEXT("%.1f s"),Model->IceSpikeDefinition().IceSpike.MinimumCooldown);
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
    if(SelectedSkill==TEXT("quickCombat"))
    {
        const int32 L=Model->QuickCombatProgress().Level+(bNext?1:0);
        const auto C=Model->QuickCombatStats(L);
        const auto& T=Model->QuickCombatDefinition().QuickCombat;
        if(Index==0)return TEXT("F");
        if(Index==1)return FString::Printf(TEXT("%.0f"),C.Damage);
        if(Index==2)return FString::Printf(TEXT("×%.2f"),(T.StrengthFactorBase+T.StrengthFactorPerLevel*FMath::Min(L,Model->QuickCombatDefinition().MaxLevel))*C.DamageMultiplier);
        if(Index==3)return FString::Printf(TEXT("%.2f"),C.StaminaCost);
        if(Index==4)return FString::Printf(TEXT("%.1f m"),C.KnockbackCM/100);
        if(Index==5)return TEXT("无");
        return FString::Printf(TEXT("−%.0f%%"),FMath::Clamp(T.StaminaReductionPerLevel*(FMath::Clamp(L,1,Model->QuickCombatDefinition().MaxLevel)-1),0.f,1.f)*100.f);
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
    if(FireMagic::IsSkill(SelectedSkill))
    {
        AddReward(TEXT("每次有效命中"),D.FireMagic.HitExperience);
        AddReward(TEXT("每次直接击杀"),D.FireMagic.KillExperience);
        AddReward(TEXT("同一轮范围命中至少两个（每次施法一次）"),D.FireMagic.MultiHitExperience);
        AddReward(TEXT("同次施法直接击杀至少两个"),D.FireMagic.MultiKillExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(FString::Printf(TEXT("火场或焰甲结束时统一结算，奖励可叠加。持续区域每轮有效命中也可修炼；空放、尸体、友方和召唤物不计，后续灼烧击杀不计本技能修炼。死亡或离开场景清除未完成修炼。随机暴击同时修炼暴击技能。升级所需经验为当前等级×%d，最高%d级。"),D.ExperiencePerLevel,D.MaxLevel),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(SelectedSkill==TEXT("dashAttack"))
    {
        AddReward(TEXT("每命中一个目标"),D.HitExperience);
        AddReward(TEXT("同次命中至少 2 个目标（额外一次）"),D.MultiHitExperience);
        AddReward(TEXT("每直接击杀一个目标"),D.KillExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("命中人数×1 + 多目标额外3 + 击杀人数×15，动作结束统一结算；挥空不加经验。同一目标每次只计一次，不计尸体、召唤物或后续持续伤害击杀。命中同时修炼武器精通与暴击。升级所需经验=100×当前等级，最高20级。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(SelectedSkill==TEXT("whirlwind"))
    {
        AddReward(TEXT("每命中一个目标"),D.HitExperience);
        AddReward(TEXT("同次命中至少 2 个目标（额外一次）"),D.MultiHitExperience);
        AddReward(TEXT("每直接击杀一个目标"),D.KillExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("沿用原风车：命中人数×1 + 多目标额外3 + 击杀人数×15，可叠加。每个目标每次只计一次，旋转结束统一结算；挥空不加经验。只计命中前存活的可修炼目标，不计尸体、召唤物或后续持续伤害击杀。升级所需经验=100×当前等级，最高20级。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(SelectedSkill==TEXT("heavyStrike"))
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
    else if(SelectedSkill==TEXT("holyLight"))
    {
        AddReward(TEXT("每次命中／治疗"),D.HolyLight.HitExperience);AddReward(TEXT("每次直接击杀"),D.HolyLight.KillExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("有效敌伤或友疗每次计一次，直接击杀额外奖励。满血友疗／自愈按原版仍可修炼；无目标、失败、尸体不计。随机伤害暴击同时修炼暴击技能，治疗不暴击。升级所需经验为当前等级×100，最高20级。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(ElectricMagic::IsSkill(SelectedSkill))
    {
        const auto& T=D.ElectricMagic;
        AddReward(TEXT("每有效命中一个目标"),T.HitExperience);AddReward(TEXT("每直接击杀一个目标"),T.KillExperience);
        AddReward(TEXT("一次命中至少两个"),T.MultiHitExperience);AddReward(TEXT("整次击杀至少两个"),T.MultiKillExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(SelectedSkill==TEXT("stormDomain")?
            TEXT("整片雷云自然结束后统一结算；任一落雷连锁命中至少两个，额外奖励每片云一次。死亡或离场清除未结束雷云，不结算该场修炼。"):
            TEXT("光束释放结束统一结算，多目标奖励每束各一次。蓄力不足、取消、空放、尸体、友方和召唤物不提供修炼。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
        Content->AddSlot().AutoHeight().Padding(0,8/Scale,0,0)[Paragraph(TEXT("以上奖励可叠加；过载保留角色击杀经验，不额外计算技能修炼。随机暴击同时修炼暴击技能。升级所需经验为当前等级×100，最高20级。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(SelectedSkill==TEXT("lightningStrike"))
    {
        AddReward(TEXT("每命中一个目标"),D.Lightning.HitExperience);AddReward(TEXT("每直接击杀一个目标"),D.Lightning.KillExperience);
        AddReward(TEXT("同次命中至少两个"),D.Lightning.MultiHitExperience);AddReward(TEXT("同次击杀至少两个"),D.Lightning.MultiKillExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("同次连锁结束后统一结算，以上奖励可叠加；多目标奖励每次各一次。无目标、失败施法、尸体、友方、召唤物不提供修炼；过载保留角色击杀经验，不额外计算闪电修炼。随机暴击同时修炼暴击技能。升级所需经验为当前等级×100，最高20级。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(SelectedSkill==TEXT("blizzard"))
    {
        AddReward(TEXT("每拍有效命中"),D.Blizzard.HitExperience);AddReward(TEXT("每次直接击杀"),D.Blizzard.KillExperience);
        AddReward(TEXT("一拍命中至少两个"),D.Blizzard.MultiHitExperience);AddReward(TEXT("整场击杀至少两个"),D.Blizzard.MultiKillExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("每 0.5 秒分别计命中与击杀，持续结束统一结算；两个额外奖励每场各一次。召唤物、友方、尸体与无修炼目标不计经验；死亡或离场清除未结束区域，不结算该场修炼。随机暴击同时修炼暴击技能。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(SelectedSkill==TEXT("iceWall"))
    {
        AddReward(TEXT("每次落点有效命中"),D.IceWall.HitExperience);AddReward(TEXT("每次直接击杀"),D.IceWall.KillExperience);
        AddReward(TEXT("同次命中至少两个"),D.IceWall.MultiHitExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("每个目标在成墙瞬间只结算一次；多目标奖励每堵墙一次。寒冷光环与阻挡本身不刷经验；空放、尸体、友方和召唤物不计修炼。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
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
    else if(SelectedSkill==TEXT("quickCombat"))
    {
        AddReward(TEXT("触发快速进战"),D.UseExperience);
        AddReward(TEXT("使用技能击杀目标"),D.KillExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("动作实际开始后扣一次体力并获得施放修炼，挥空也算；动作未结束时重复按键不重复扣费或计经验。可修炼目标被本次打击直接击杀时额外获得击杀经验，每次施放至多一个目标。命中按当前武器精通与暴击规则修炼。满级后停止积累。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
    }
    else if(SelectedSkill==TEXT("dexterousHands"))
    {
        AddReward(TEXT("完成换弹"),D.ReloadExperience);
        if(D.MeleeHitExperience)AddReward(TEXT("近战武器命中"),D.MeleeHitExperience);
        if(D.MeleeKillExperience)AddReward(TEXT("近战武器击杀（含命中）"),D.MeleeKillExperience+D.MeleeHitExperience);
        Content->AddSlot().AutoHeight().Padding(0,12/Scale,0,0)[Paragraph(TEXT("一次换弹实际补入至少一发，结算一次修炼经验；取消、满弹匣或没有补入弹药时不计。近战兵器命中可修炼目标即结算，剑与配重锤打击都算；击杀合计获得命中与击杀两档。满级后停止积累。"),12,ColdSteelUI::TextTertiary,PageWidth-76)];
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
    ElectricDetailButtons.Reset();LightningDetailButton.Reset();HolyLightDetailButton.Reset();
    IceSpikeDetailButton.Reset();
    BlizzardDetailButton.Reset();IceWallDetailButton.Reset();
    UppercutDetailButton.Reset();DetailButton.Reset();PistolDetailButton.Reset();CriticalDetailButton.Reset();FireballDetailButton.Reset();HeavyDetailButton.Reset();DodgeDetailButton.Reset();DexterousHandsDetailButton.Reset();BackButton.Reset();FilterButtons.Reset();
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
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(IceWallDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("iceWall")))[Overview(true,TEXT("iceWall"))]];
        if(Category==0||Category==2||Category==3)Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)
            [SAssignNew(BlizzardDetailButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Fill).ContentPadding(16/Scale)
                .OnClicked_UObject(this,&ThisClass::OpenDetail,FName(TEXT("blizzard")))[Overview(true,TEXT("blizzard"))]];
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
        Column->AddSlot().FillHeight(1)[Scroll.ToSharedRef()];
        Column->AddSlot().AutoHeight().Padding(16/Scale,8/Scale)[Paragraph(TEXT("拖动主动技能卡到 Q/E/X/1–4；空槽移动，占用槽交换，拖出解绑。快速进战也可直接按 F 触发。E 优先交互；左 Shift 短按仍可闪避。"),12,ColdSteelUI::TextTertiary,PageWidth-32)];
    }
    else
    {
        Column->AddSlot().AutoHeight().Padding(16/Scale,12/Scale)[SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight/Scale)
            [SAssignNew(BackButton,SButton).ButtonStyle(&ActionStyle).HAlign(HAlign_Center).VAlign(VAlign_Center)
                .OnClicked_Lambda([this]{GoBack();return FReply::Handled();})[Label(TEXT("返回技能列表"),14,ColdSteelUI::TextPrimary)]]];
        SAssignNew(Scroll,SScrollBox).AllowOverscroll(EAllowOverscroll::No);
        Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[SNew(SBorder).BorderImage(&CardBrush).Padding(16/Scale)[Overview(false,SelectedSkill)]];
        if(SelectedSkill==TEXT("swordUppercut"))
        {
            Scroll->AddSlot().Padding(16/Scale,4/Scale,16/Scale,12/Scale)
                [Paragraph(TEXT("在技能列表把上挑拖到 Q/E/X/1–4 任意快捷槽，装备剑后按绑定键使用。每次播放完整蓄势、斜挑、带出和回位，结束后即可再次触发。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)
                [Paragraph(TEXT("本阶段不结算伤害，不扣体力或魔法，不设额外冷却，也不提供等级与修炼项目。快捷栏绑定照常保存。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Column->AddSlot().FillHeight(1)[Scroll.ToSharedRef()];
            return Column;
        }
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
            if(SelectedSkill==TEXT("swordMastery")||SelectedSkill==TEXT("bowMastery"))Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(TEXT("攻击速度提升"),3)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(SelectedSkill==TEXT("machineGunMastery")
                ?TEXT("属性被动常驻；使用对应武器修炼。伤害、强化、改造和附魔共用当前计算结果。持机枪类武器时移动速度 ×0.67（减速 33%），收起武器或改持其他武器即恢复。")
                :TEXT("属性被动常驻；使用对应武器修炼。伤害、强化、改造和附魔共用当前计算结果。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
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
        else if(SelectedSkill==TEXT("blizzard"))
        {
            const TCHAR* Rows[]={TEXT("每拍魔法伤害"),TEXT("椭圆区域全轴"),TEXT("持续时间"),TEXT("伤害间隔"),TEXT("消耗魔法"),TEXT("起手冷却"),TEXT("最大施法距离"),TEXT("每拍寒冷")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("拖入快捷栏后，瞄准地面按绑定键施放。有效起手锁定区域、扣蓝并开始冷却，施法手势接触帧生成暴风雪；持续伤害与落雪、坠冰视觉独立。区域在原地保持，每 0.5 秒伤害一次并叠加寒冷，友方不受伤；墙体与不同楼层可阻挡。无需法杖；短时左手动作结束后施放，双持手枪拒绝施法。起手失败不消费，未释放时死亡、打开菜单或动作中断退还实际蓝耗并清除冷却。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("等级 L：每拍伤害＝向下取整〔5+2L+(魔攻+智力)×(0.12+0.02L)〕；再应用冰系、法术与链式词条。半轴＝(200+8L)、(124+5L)，每单位 1.5 cm；持续＝5+floor((L−1)×5/19) 秒，冷却＝40−floor((L−1)×5/19) 秒。1级共10拍，20级共20拍；显示伤害未扣魔防，也未计暴击和额外套装增伤。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("iceWall"))
        {
            const TCHAR* Rows[]={TEXT("成墙物理伤害"),TEXT("冰墙段数"),TEXT("墙体宽度"),TEXT("高墙 / 矮墙"),TEXT("持续时间"),TEXT("消耗魔法"),TEXT("发射后冷却"),TEXT("最大施法距离"),TEXT("寒冷光环范围"),TEXT("光环叠层节拍"),TEXT("墙体生命")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("装备法杖后，拖入快捷栏并按绑定键凝聚。凝聚完成后指向地面显示冰墙模型：绿色可放置、红色不可放置；按 R 切换高墙和矮墙。再按绑定键，冰块快速升空消失，冰墙从预览落点上方砸下，落地扬起烟尘与寒雾。命中同时施加物理伤害、击退与寒冷减速，之后每秒叠加一次寒冷光环。高墙阻挡移动和投射物，矮墙顶面可供机枪脚架支撑。未释放时切走法杖会取消凝聚并退蓝。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("保留原版伤害：向下取整〔10 + 10×等级 + 智力×（1 + 0.25×等级）+ 精神×（1 + 0.25×等级）〕，按物防结算。段数5 + 2×（等级−1）；持续10 + 0.5×（等级−1）秒。凝聚只扣一次蓝，发射开始冷却，切换形态不重复扣费。未发射的凝聚到期、死亡或优先权打断退还实际蓝耗；已发射的不退。墙体、飞行种子和预览不跨读档恢复。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("iceSpike"))
        {
            const TCHAR* Rows[]={TEXT("每枚基础伤害"),TEXT("冰锥数量"),TEXT("整轮理论伤害"),TEXT("固定伤害项"),TEXT("魔攻系数"),TEXT("常规最低冷却"),TEXT("消耗魔法"),TEXT("整组结束后冷却"),TEXT("最大射程"),TEXT("飞行速度"),TEXT("最长悬浮时间")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("按绑定键凝聚整组冰锥，再按一次朝准星齐射。每枚到达瞄准点或碰撞后碎裂；不会追踪移动目标，也没有范围爆炸伤害。目标已被击杀时，后续冰锥不再被尸体吃掉，会继续飞向后方目标或射程终点。直击头部要害必定暴击，普通命中随机暴击，同一击只应用一次暴击加成。显示伤害未扣魔防、未计暴击和额外套装增伤；整轮数值假定全部有效命中。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Model->IceSpikeDefinition().IceSpike;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(FString::Printf(TEXT("每枚伤害 = 向下取整〔%.0f + %.1f × 等级 + 魔攻 ×（%.3f + %.3f × 等级）〕，再计法杖改造增伤并取整；不再单独计算智力，与火球同口径。基础枚数 = %d + 向下取整〔（等级 − 1）÷ %d〕。蓝耗 = %.0f +（等级 − 1）× %.0f，基础冷却由 1 级 %.1f 秒逐级降至满级 %.1f 秒。凝聚仅扣一次魔法；全部结束或悬浮超时才开始冷却。更换武器或升级不改变已凝聚的这一组。"),T.DamageBase,T.DamagePerLevel,T.MagicBase,T.MagicPerLevel,T.CountBase,T.CountLevelStep,T.ManaCost,T.ManaCostPerLevel,T.Cooldown,T.MinimumCooldown),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(FireMagic::IsSkill(SelectedSkill))
        {
            const bool Meteor=SelectedSkill==TEXT("meteor");
            const TCHAR* Rows[]={Meteor?TEXT("爆炸中心伤害"):TEXT("武器命中附加魔法伤害"),Meteor?TEXT("熔火持续伤害"):TEXT("近身灼烧伤害"),Meteor?TEXT("爆炸半径"):TEXT("灼烧光环半径"),TEXT("持续时间"),TEXT("魔力消耗"),TEXT("冷却时间"),TEXT("熔火半径"),TEXT("施法距离"),TEXT("陨落时间"),TEXT("爆炸眩晕"),TEXT("爆炸灼烧")};
            for(int32 I=0;I<(Meteor?UE_ARRAY_COUNT(Rows):6);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(Meteor?TEXT("准星指向地面召唤陨星。爆炸从中心全额衰减至边缘50%，施加眩晕与3层灼烧；落地熔火每0.5秒伤害一次，并附加1层灼烧。当前可以直接施放。"):TEXT("左手施法后获得持续焰甲。存续期间，近战、枪械等非魔法攻击命中存活敌人时追加独立魔法伤害，脚边光环持续灼烧附近敌人。法术和焰甲附伤不会递归触发。该魔法不额外增加防御值。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("伤害取施法时的魔攻与智力。动作实际起手扣蓝并开始冷却，排队不扣费；中断保留已消耗资源。冷却与技能等级存档，活动火场和焰甲不跨场景或读档恢复。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("holyLight"))
        {
            const TCHAR* Rows[]={TEXT("敌方基础伤害"),TEXT("友方治疗生命"),TEXT("僵尸伤害倍率"),TEXT("消耗魔法"),TEXT("起手冷却"),TEXT("最大施法距离"),TEXT("准星射线附近范围"),TEXT("魔攻系数"),TEXT("智力系数"),TEXT("智慧系数"),TEXT("光柱持续／淡出")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("拖入快捷栏后按一次，圣光降临准星附近的可见目标：敌人受魔法伤害，友方回复生命。按住 Alt 再按绑定键对自己施放；E 仍优先执行场景交互。治疗不超过生命上限，不复活尸体。僵尸类受到双倍伤害；锁定伤害只随机判定暴击，没有要害加成。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Model->HolyLightDefinition().HolyLight;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(FString::Printf(TEXT("基础量 = 向下取整〔%.0f + %.0f×等级 + 魔攻×（%.2f+%.2f×等级）+ 智力×（%.2f+%.2f×等级）+ 智慧×（%.2f+%.2f×等级）〕。基础冷却 %.0f 秒，每 %d 级台阶减少 %.0f 秒。伤害和治疗分别应用当前武器的对应词条，治疗不继承链式增伤和暴击；伤害显示未计目标魔防、暴击及额外套装增伤。"),T.AmountBase,T.AmountPerLevel,T.MagicBase,T.MagicPerLevel,T.IntelligenceBase,T.IntelligencePerLevel,T.WisdomBase,T.WisdomPerLevel,T.Cooldown,T.CooldownLevelStep,T.CooldownStepReduction),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("排队、缺蓝、无目标、超距或遮挡不消费。有效起手扣蓝并开始冷却；释放接触帧再次确认锁定目标，落空不返还。短时左手动作结束后施放，双持手枪拒绝施法；死亡、退出或打开菜单取消未释放动作。光柱跟随目标，持续时间不是持续伤害。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(ElectricMagic::IsSkill(SelectedSkill))
        {
            const bool Storm=SelectedSkill==TEXT("stormDomain");
            const TCHAR* Rows[]={Storm?TEXT("主落雷基础伤害"):TEXT("满蓄力基础伤害"),TEXT("消耗魔法"),TEXT("起手冷却"),Storm?TEXT("随身领域半径"):TEXT("最大贯穿距离"),Storm?TEXT("雷云持续时间"):TEXT("满蓄力时间"),Storm?TEXT("每次最多命中目标"):TEXT("命中击退距离"),Storm?TEXT("逐跳传导距离"):TEXT("满蓄力伤害倍率"),Storm?TEXT("每跳伤害衰减"):TEXT("每层感电额外增伤"),Storm?TEXT("命中眩晕"):TEXT("最短有效蓄力"),TEXT("感电层数／持续时间"),TEXT("魔攻系数"),TEXT("智力系数")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(Storm?
                TEXT("拖入快捷栏后按一次，头顶雷云随玩家移动；立即落雷，此后每0.9秒选择最近的可见敌人，再向邻近目标传导。墙壁遮挡目标与连锁。持续时间10～13秒，半径与目标数随等级提高，9级和17级各增加一个传导目标。"):
                TEXT("长按快捷栏绑定键充能，0.5秒后松开可发射，2.5秒充至100%后保持，松键释放。蓄力期间保持原地，可自由转动视角瞄准；十字准星随充能收拢，未满充在准星标示的范围内随机散射，满充合并为一个点并提示已充能完毕。法杖前方显示电系魔法阵；鼠标点击槽位起手后再次点击也可释放。光束贯穿敌人，遇墙停止，附带击退和两层感电。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Definition(SelectedSkill).ElectricMagic;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(FString::Printf(TEXT("基础伤害 = 向下取整〔%.0f + %.0f×等级 + 魔攻×（%.2f+%.2f×等级）+ 智力×（%.2f+%.2f×等级）〕，再应用当前魔法装备增伤。显示值未扣目标魔防，未计感电、暴击和要害。"),T.DamageBase,T.DamagePerLevel,T.MagicBase,T.MagicPerLevel,T.IntelligenceBase,T.IntelligencePerLevel),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(Storm?
                TEXT("起手一次扣蓝并开始30秒冷却，雷云不会持续扣蓝。每跳保留上一跳70%伤害。命中短暂眩晕、叠加感电，满层触发范围过载。未释放动作取消时退蓝并清除本次冷却；已生成雷云持续生效。"):
                TEXT("伤害乘以蓄力比例、1.3倍满蓄力倍率及〔1＋命中前感电层数×10%〕。不足0.5秒松开、控制打断或取消，退还本次蓝耗并清除冷却；有效发射保留消耗。末端爆闪仅为视觉效果。两种电系魔法均可空手施放；双持手枪时不能施法。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("lightningStrike"))
        {
            const TCHAR* Rows[]={TEXT("主目标基础伤害"),TEXT("最多命中目标"),TEXT("每跳伤害衰减"),TEXT("命中眩晕"),TEXT("消耗魔法"),TEXT("起手冷却"),TEXT("最大施法距离"),TEXT("准星射线附近范围"),TEXT("逐跳传导距离"),TEXT("魔攻系数"),TEXT("智力系数"),TEXT("命中感电层数／时长"),TEXT("每层电伤增加"),TEXT("过载层数／眩晕"),TEXT("过载基础伤害"),TEXT("过载范围")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("拖入快捷栏，按一次锁定准星附近可见敌人。每跳寻找上一目标附近最近且未命中的可见敌人，墙壁阻挡连锁。锁定命中随机判定暴击，不视为直击要害。伤害显示未扣目标魔防、未计感电、暴击与额外套装增伤。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            const auto& T=Model->LightningDefinition().Lightning;
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(FString::Printf(TEXT("主目标伤害 = 向下取整〔%.0f + %.0f×等级 + 魔攻×（%.2f + %.2f×等级）+ 智力×（%.2f + %.2f×等级）〕，再计算当前法杖／魔杖加成。基础目标数 = %d + 向下取整〔（等级−1）÷%d〕，在6、11、16级各增加一个目标。"),T.DamageBase,T.DamagePerLevel,T.MagicBase,T.MagicPerLevel,T.IntelligenceBase,T.IntelligencePerLevel,T.CountBase,T.CountLevelStep),12,ColdSteelUI::TextTertiary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("有效起手一次扣蓝并开始冷却；排队、缺蓝、无目标、超距或遮挡不扣资源。释放接触帧重新判断原目标，失效则落空并保留已消耗资源。感电层数和持续时间累加，到期清空；叠满触发过载并清层，对附近敌人电击，不再叠感电。换装不改变已开始施法的快照；死亡、退出、打开菜单取消未释放动作，不恢复在途电弧。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
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
        else if(SelectedSkill==TEXT("dashAttack"))
        {
            const TCHAR* Rows[]={TEXT("伤害倍率"),TEXT("连续奔跑准备时间"),TEXT("体力消耗（含当前配装）"),TEXT("下劈范围（含当前配装）"),TEXT("击退距离"),TEXT("命中扇区"),TEXT("下劈伤害（含当前武器）")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("持近战兵器按住左 Shift 向前奔跑，就绪后按左键，经0.25秒前摇衔接下劈。准备时间从1级1秒降至20级0.43秒；蓄满后滑铲、滑铲跳和空中减速均保留就绪，可继续按住 Shift 在空中释放。松开冲刺、发动其他动作，或落地后不再奔跑会重新计时；未蓄满时只在地面奔跑积累。未就绪按左键使用普通攻击；被动技能不需绑定快捷栏。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("伤害倍率=1.75+0.05×等级。基础消耗20体力，受当前近战配装耗体修正；一次出招只扣一次。0.25秒前摇向前突进1米，空中释放保留竖直运动和重力；碰撞阻挡突进，保留原有收势且无回弹。下劈命中正前方60°扇区（左右各30°），每个目标一次；基础版附带击退。完整收势后恢复操作，下一次需重新奔跑准备，无独立冷却。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("whirlwind"))
        {
            const TCHAR* Rows[]={TEXT("近战伤害倍率"),TEXT("常驻力量"),TEXT("冷却时间"),TEXT("体力消耗"),TEXT("横扫半径（含当前范围加成）"),TEXT("击退距离"),TEXT("眩晕时间")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("仅可持近战兵器施放，生产工具与枪械不可用。待机转为横持后旋转横扫，命中短暂停帧。伤害倍率=1.5+0.1×等级；力量+等级；冷却=10−0.2×等级秒；体力=20+等级。数值、修炼与旧风车一致；1级1.6倍、9.8秒、21体力，20级3.5倍、6秒、40体力。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("半径=(120+5×等级+80)×1.5厘米，再乘当前近战范围系数；击退3.75米、眩晕2.5秒。施放开始扣体力并开始冷却；取消保留已消耗资源，已发生命中照常结算。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
        }
        else if(SelectedSkill==TEXT("quickCombat"))
        {
            const TCHAR* Rows[]={TEXT("触发快捷键"),TEXT("打击伤害（含当前力量）"),TEXT("力量系数"),TEXT("体力消耗"),TEXT("击退距离"),TEXT("额外技能冷却"),TEXT("成长体力减耗")};
            for(int32 I=0;I<UE_ARRAY_COUNT(Rows);++I)Scroll->AddSlot().Padding(16/Scale,4/Scale)[EffectRow(Rows[I],I)];
            Scroll->AddSlot().Padding(16/Scale,16/Scale,16/Scale,12/Scale)[TrainingCard()];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,12/Scale)[Paragraph(TEXT("按 F 或快捷栏绑定键发动当前武器的快速近战：剑使用配重锤，枪械使用各自的砸击动作。伤害取当前等级、力量和武器快速近战倍率；击退与体力消耗包含装备修正。命中不附加眩晕。技能成长降低体力消耗。"),14,ColdSteelUI::TextSecondary,PageWidth-44)];
            Scroll->AddSlot().Padding(16/Scale,0,16/Scale,16/Scale)[Paragraph(TEXT("没有独立冷却。蓄势、释放与收手构成一个完整动作周期，全部结束后即可再次使用。快捷栏遮罩和倒计时跟随当前武器的真实动作时间，并计入攻速与命中停顿；动作中重复按键无效，体力不足时不能发动。"),12,ColdSteelUI::TextTertiary,PageWidth-44)];
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
{ if(!bDetail)return false; bDetail=false; if(Scroll)Scroll->SetScrollOffset(0); RefreshLayout();auto Button=SelectedSkill==TEXT("dodge")?DodgeDetailButton:(SelectedSkill==TEXT("dexterousHands")?DexterousHandsDetailButton:DetailButton);if(SelectedSkill==TEXT("swordUppercut"))Button=UppercutDetailButton;if(SelectedSkill==TEXT("pistolMastery"))Button=PistolDetailButton;if(SelectedSkill==TEXT("criticalStrike"))Button=CriticalDetailButton;if(SelectedSkill==TEXT("fireball"))Button=FireballDetailButton;if(SelectedSkill==TEXT("heavyStrike"))Button=HeavyDetailButton;if(SelectedSkill==TEXT("quickCombat"))Button=QuickCombatDetailButton;if(SelectedSkill==TEXT("whirlwind"))Button=WhirlwindDetailButton;if(SelectedSkill==TEXT("dashAttack"))Button=DashAttackDetailButton;if(ElectricMagic::IsSkill(SelectedSkill))Button=ElectricDetailButtons.FindRef(SelectedSkill);if(SelectedSkill==TEXT("lightningStrike"))Button=LightningDetailButton;if(SelectedSkill==TEXT("holyLight"))Button=HolyLightDetailButton;if(SelectedSkill==TEXT("meteor"))Button=MeteorDetailButton;if(SelectedSkill==TEXT("flameArmor"))Button=FlameArmorDetailButton;if(SelectedSkill==TEXT("iceWall"))Button=IceWallDetailButton;if(SelectedSkill==TEXT("blizzard"))Button=BlizzardDetailButton;if(Button)FSlateApplication::Get().SetKeyboardFocus(Button,EFocusCause::Navigation); return true; }
