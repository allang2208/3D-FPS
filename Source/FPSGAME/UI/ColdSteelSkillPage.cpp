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

void UColdSteelSkillPage::SetHUD(UColdSteelHUDWidget* Owner){HUD=Owner;}
FReply UColdSteelSkillPage::NativeOnPreviewMouseButtonDown(const FGeometry& G,const FPointerEvent& E)
{
    PendingDragSkill=NAME_None;
    if(!bDetail&&HUD.IsValid()&&E.GetEffectingButton()==EKeys::LeftMouseButton)
    {
        const TPair<FName,TSharedPtr<SButton>> Cards[]={{TEXT("leapStrike"),LeapStrikeDetailButton},{TEXT("chainSlash"),ChainSlashDetailButton},{TEXT("shadowStepSlash"),ShadowStepDetailButton},{TEXT("illuminationArrow"),IlluminationArrowDetailButton},{TEXT("elementalArrow"),ElementalArrowDetailButton},{TEXT("magicArrowRain"),MagicArrowRainDetailButton},{TEXT("lightningHaste"),LightningHasteDetailButton},{TEXT("iceArmor"),IceArmorDetailButton},{TEXT("swordUppercut"),UppercutDetailButton},{TEXT("stormDomain"),ElectricDetailButtons.FindRef(TEXT("stormDomain"))},{TEXT("thunderLance"),ElectricDetailButtons.FindRef(TEXT("thunderLance"))},{TEXT("blizzard"),BlizzardDetailButton},{TEXT("absoluteZero"),AbsoluteZeroDetailButton},{TEXT("iceWall"),IceWallDetailButton},{TEXT("dragonBreath"),DragonBreathDetailButton},{TEXT("meteor"),MeteorDetailButton},{TEXT("flameArmor"),FlameArmorDetailButton},{TEXT("holyLight"),HolyLightDetailButton},{TEXT("lightningStrike"),LightningDetailButton},{TEXT("iceSpike"),IceSpikeDetailButton},{TEXT("fireball"),FireballDetailButton},{TEXT("dodge"),DodgeDetailButton},{TEXT("heavyStrike"),HeavyDetailButton},{TEXT("quickCombat"),QuickCombatDetailButton},{TEXT("whirlwind"),WhirlwindDetailButton}};
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
    if((Id==TEXT("leapStrike")||Id==TEXT("chainSlash")||Id==TEXT("shadowStepSlash")||Id==TEXT("illuminationArrow")||Id==TEXT("magicArrowRain")||Id==TEXT("elementalArrow"))&&HUD.IsValid()){Out=HUD->StartQuickDrag(Id,INDEX_NONE,MasteryIconBrushes.Find(Id),E.GetScreenSpacePosition());return;}
    if(Id==TEXT("swordUppercut")&&HUD.IsValid())
    {Out=HUD->StartQuickDrag(Id,INDEX_NONE,&UppercutIconBrush,E.GetScreenSpacePosition());return;}
    if(!Id.IsNone()&&HUD.IsValid())Out=HUD->StartQuickDrag(Id,INDEX_NONE,Id==TEXT("lightningHaste")?&LightningHasteIconBrush:Id==TEXT("iceArmor")?&IceArmorIconBrush:ElectricMagic::IsSkill(Id)?ElectricIconBrushes.Find(Id):Id==TEXT("blizzard")?&BlizzardIconBrush:Id==TEXT("absoluteZero")?&AbsoluteZeroIconBrush:Id==TEXT("iceWall")?&IceWallIconBrush:Id==TEXT("dragonBreath")?&DragonBreathIconBrush:Id==TEXT("meteor")?&MeteorIconBrush:Id==TEXT("flameArmor")?&FlameArmorIconBrush:Id==TEXT("holyLight")?&HolyLightIconBrush:Id==TEXT("lightningStrike")?&LightningIconBrush:Id==TEXT("whirlwind")?&WhirlwindIconBrush:Id==TEXT("iceSpike")?&IceSpikeIconBrush:Id==TEXT("heavyStrike")?&HeavyIconBrush:Id==TEXT("fireball")?&FireballIconBrush:Id==TEXT("quickCombat")?&QuickCombatIconBrush:&DodgeIconBrush,E.GetScreenSpacePosition());
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
    if(Model)for(FName Id:{FName(TEXT("leapStrike")),FName(TEXT("chainSlash")),FName(TEXT("shadowStepSlash")),FName(TEXT("twoHandedMastery")),FName(TEXT("oneHandedMastery")),FName(TEXT("swordMastery")),FName(TEXT("bluntMastery")),FName(TEXT("machineGunMastery")),FName(TEXT("shotgunMastery")),FName(TEXT("bowMastery")),FName(TEXT("heartPiercingArrow")),FName(TEXT("magicArrowRain")),FName(TEXT("elementalArrow")),FName(TEXT("illuminationArrow"))})
    {
        if(MasteryIconBrushes.Contains(Id))continue;
        auto& Brush=MasteryIconBrushes.Add(Id);
        const FString& Path=Model->MasteryDefinition(Id).Icon;
        TArray<uint8> Bytes;
        if(!Path.IsEmpty()&&FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Path)))
        {
            auto* Texture=FImageUtils::ImportBufferAsTexture2D(Bytes);
            if(Texture){MasteryIconTextures.Add(Id,Texture);Brush.SetResourceObject(Texture);Brush.DrawAs=ESlateBrushDrawType::Image;}
        }
    }
    for(int32 I=1;I<=3;++I)
    {
        const FName Key(*FString::Printf(TEXT("elementArrowIcon%d"),I));
        if(MasteryIconBrushes.Contains(Key))continue;
        auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/ElementalArrow::Icon(EArrowElement(I)));
        if(Texture){MasteryIconTextures.Add(Key,Texture);auto& B=MasteryIconBrushes.Add(Key);B.SetResourceObject(Texture);B.DrawAs=ESlateBrushDrawType::Image;}
    }
    SAssignNew(Root,SBox); RefreshLayout(); return Root.ToSharedRef();
}
const FColdSteelSkillDefinition& UColdSteelSkillPage::Definition(FName Id) const
{ if(Id==TEXT("lightningHaste"))return Model->LightningHasteDefinition();if(Id==TEXT("iceArmor"))return Model->IceArmorDefinition();if(Id==TEXT("leapStrike")||Id==TEXT("swordUppercut")||Id==TEXT("chainSlash")||Id==TEXT("shadowStepSlash"))return Model->MasteryDefinition(Id);if(ElectricMagic::IsSkill(Id))return Model->ElectricMagicDefinition(Id);if(Id==TEXT("blizzard"))return Model->BlizzardDefinition();if(Id==TEXT("absoluteZero"))return Model->AbsoluteZeroDefinition();if(Id==TEXT("iceWall"))return Model->IceWallDefinition();if(FireMagic::IsSkill(Id))return Model->FireMagicDefinition(Id);if(Id==TEXT("holyLight"))return Model->HolyLightDefinition();if(Id==TEXT("lightningStrike"))return Model->LightningDefinition();if(Id==TEXT("iceSpike"))return Model->IceSpikeDefinition();if(Id==TEXT("quickCombat"))return Model->QuickCombatDefinition();if(Additional(Id)||Id==TEXT("heavyStrike")||Id==TEXT("whirlwind")||Id==TEXT("dashAttack"))return Model->MasteryDefinition(Id);if(Id==TEXT("fireball"))return Model->FireballDefinition();if(Id==TEXT("criticalStrike"))return Model->CriticalStrikeDefinition();if(Id==TEXT("pistolMastery"))return Model->PistolDefinition();return Id==TEXT("dodge")?Model->DodgeDefinition():(Id==TEXT("dexterousHands")?Model->DexterousHandsDefinition():Model->RifleDefinition()); }
FColdSteelSkillProgress UColdSteelSkillPage::Progress(FName Id) const
{ if(Id==TEXT("lightningHaste"))return Model->MasteryProgress(Id);if(Id==TEXT("iceArmor"))return Model->MasteryProgress(Id);if(Id==TEXT("leapStrike")||Id==TEXT("swordUppercut")||Id==TEXT("chainSlash")||Id==TEXT("shadowStepSlash"))return Model->MasteryProgress(Id);if(ElectricMagic::IsSkill(Id))return Model->ElectricMagicProgress(Id);if(Id==TEXT("blizzard"))return Model->BlizzardProgress();if(Id==TEXT("absoluteZero"))return Model->AbsoluteZeroProgress();if(Id==TEXT("iceWall"))return Model->IceWallProgress();if(FireMagic::IsSkill(Id))return Model->FireMagicProgress(Id);if(Id==TEXT("holyLight"))return Model->HolyLightProgress();if(Id==TEXT("lightningStrike"))return Model->LightningProgress();if(Id==TEXT("iceSpike"))return Model->IceSpikeProgress();if(Id==TEXT("quickCombat"))return Model->QuickCombatProgress();if(Additional(Id)||Id==TEXT("heavyStrike")||Id==TEXT("whirlwind")||Id==TEXT("dashAttack"))return Model->MasteryProgress(Id);if(Id==TEXT("fireball"))return Model->FireballProgress();if(Id==TEXT("criticalStrike"))return Model->CriticalStrikeProgress();if(Id==TEXT("pistolMastery"))return Model->PistolProgress();return Id==TEXT("dodge")?Model->DodgeProgress():(Id==TEXT("dexterousHands")?Model->DexterousHandsProgress():Model->RifleProgress()); }
void UColdSteelSkillPage::ReleaseSlateResources(bool bReleaseChildren)
{ LeapStrikeDetailButton.Reset();ShadowStepDetailButton.Reset();IlluminationArrowDetailButton.Reset();ElementalArrowDetailButton.Reset();MagicArrowRainDetailButton.Reset();LightningHasteDetailButton.Reset();IceArmorDetailButton.Reset();ChainSlashDetailButton.Reset();UppercutDetailButton.Reset();ElectricDetailButtons.Reset();BlizzardDetailButton.Reset();AbsoluteZeroDetailButton.Reset();IceWallDetailButton.Reset();Super::ReleaseSlateResources(bReleaseChildren); Scroll.Reset(); Root.Reset();DragonBreathDetailButton.Reset();MeteorDetailButton.Reset();FlameArmorDetailButton.Reset();LightningDetailButton.Reset();HolyLightDetailButton.Reset();IceSpikeDetailButton.Reset(); DetailButton.Reset();PistolDetailButton.Reset();CriticalDetailButton.Reset();FireballDetailButton.Reset();HeavyDetailButton.Reset();DodgeDetailButton.Reset();DexterousHandsDetailButton.Reset();QuickCombatDetailButton.Reset();WhirlwindDetailButton.Reset();DashAttackDetailButton.Reset(); BackButton.Reset(); FilterButtons.Reset(); }
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
    for(auto& Pair:MasteryIconBrushes)Pair.Value.ImageSize=FVector2D(48/Scale);
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
    IceArmorIconBrush.ImageSize=FVector2D(48/Scale);
    LightningHasteIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!LightningHasteIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->LightningHasteDefinition().Icon)))LightningHasteIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(LightningHasteIconTexture){LightningHasteIconBrush.SetResourceObject(LightningHasteIconTexture);LightningHasteIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
    if(Model&&!IceArmorIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->IceArmorDefinition().Icon)))IceArmorIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(IceArmorIconTexture){IceArmorIconBrush.SetResourceObject(IceArmorIconTexture);IceArmorIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
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
    AbsoluteZeroIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!AbsoluteZeroIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->AbsoluteZeroDefinition().Icon)))AbsoluteZeroIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(AbsoluteZeroIconTexture){AbsoluteZeroIconBrush.SetResourceObject(AbsoluteZeroIconTexture);AbsoluteZeroIconBrush.DrawAs=ESlateBrushDrawType::Image;}
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
    DragonBreathIconBrush.ImageSize=FVector2D(48/Scale);
    if(Model&&!DragonBreathIconTexture)
    {
        TArray<uint8> Bytes;
        if(FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Model->FireMagicDefinition(TEXT("dragonBreath")).Icon)))DragonBreathIconTexture=FImageUtils::ImportBufferAsTexture2D(Bytes);
        if(DragonBreathIconTexture){DragonBreathIconBrush.SetResourceObject(DragonBreathIconTexture);DragonBreathIconBrush.DrawAs=ESlateBrushDrawType::Image;}
    }
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
    const float Points = Pixels * .75f / Scale;
    return SNew(STextBlock).Text(FText::FromString(Value))
        .Font(bNumeric ? ColdSteelUI::NumberFont(Points) : ColdSteelUI::TextFont(Points, Pixels >= 16))
        .ColorAndOpacity(Color).AutoWrapText(false);
}
TSharedRef<SWidget> UColdSteelSkillPage::Paragraph(const FString& Value,float Pixels,const FLinearColor& Color,float Width) const
{
    return SNew(STextBlock).Text(FText::FromString(Value)).Font(ColdSteelUI::TextFont(Pixels*.75f/Scale))
        .ColorAndOpacity(Color).AutoWrapText(false).WrapTextAt(FMath::Max(1.f,Width)/Scale).LineHeightPercentage(1.4f);
}
// Rules and formula prose: shown on the full page, collapsed (no slot padding) when embedded in the skill tree.
TSharedRef<SWidget> UColdSteelSkillPage::Note(const FString& Value,float Pixels,const FLinearColor& Color,float Width) const
{
    if(bEmbedded)return SNew(SBox).Visibility(EVisibility::Collapsed);
    return Paragraph(Value,Pixels,Color,Width);
}
TSharedRef<SWidget> UColdSteelSkillPage::Overview(bool bCompact,FName Id)
{
    const auto& D=Definition(Id);
    const bool Compact=PageWidth<440;
    const TCHAR* Tags=Id==TEXT("dodge")?TEXT("身法 / 位移 / 主动"):(Id==TEXT("dexterousHands")?TEXT("换弹 / 拉弓 / 被动"):TEXT("步枪 / 远程 / 被动"));
    const FSlateBrush* SkillIcon=Id==TEXT("dodge")?&DodgeIconBrush:(Id==TEXT("dexterousHands")?&DexterousHandsIconBrush:&IconBrush);
    if(Id==TEXT("pistolMastery")){Tags=TEXT("手枪 / 远程 / 被动");SkillIcon=&PistolIconBrush;}
    if(Id==TEXT("criticalStrike")){Tags=TEXT("暴击 / 幸运 / 被动");SkillIcon=&CriticalIconBrush;}
    if(Id==TEXT("fireball")){Tags=TEXT("火焰 / 范围 / 主动魔法");SkillIcon=&FireballIconBrush;}
    if(Id==TEXT("lightningHaste")){Tags=TEXT("雷电 / 强化 / 动作加速 · 无需法杖");SkillIcon=&LightningHasteIconBrush;}
    if(Id==TEXT("iceArmor")){Tags=TEXT("寒冰 / 防护 / 初级魔法 · 无需法杖");SkillIcon=&IceArmorIconBrush;}
    if(Id==TEXT("iceSpike")){Tags=TEXT("寒冰 / 齐射 / 主动魔法");SkillIcon=&IceSpikeIconBrush;}
    if(Id==TEXT("blizzard")){Tags=TEXT("寒冰 / 区域 / 高级魔法");SkillIcon=&BlizzardIconBrush;}
    if(Id==TEXT("absoluteZero")){Tags=TEXT("寒冰 / 极寒环爆 / 终极魔法");SkillIcon=&AbsoluteZeroIconBrush;}
    if(Id==TEXT("iceWall")){Tags=TEXT("寒冰 / 掩体 / 主动魔法");SkillIcon=&IceWallIconBrush;}
    if(Id==TEXT("meteor")){Tags=TEXT("火焰 / 陨星 / 主动魔法");SkillIcon=&MeteorIconBrush;}
    if(Id==TEXT("flameArmor")){Tags=TEXT("火焰 / 附魔光环 / 主动魔法");SkillIcon=&FlameArmorIconBrush;}
    if(Id==TEXT("dragonBreath")){Tags=TEXT("火焰 / 扇形持续 / 终极魔法");SkillIcon=&DragonBreathIconBrush;}
    if(Id==TEXT("holyLight")){Tags=TEXT("圣光 / 敌伤友疗 / 主动魔法");SkillIcon=&HolyLightIconBrush;}
    if(ElectricMagic::IsSkill(Id)){Tags=Id==TEXT("stormDomain")?TEXT("闪电 / 随身领域 / 主动魔法"):TEXT("闪电 / 蓄力贯穿 / 主动魔法");SkillIcon=ElectricIconBrushes.Find(Id);}
    if(Id==TEXT("lightningStrike")){Tags=TEXT("闪电 / 连锁 / 主动魔法");SkillIcon=&LightningIconBrush;}
    if(Id==TEXT("dashAttack")){Tags=TEXT("近战 / 下劈 / 被动");SkillIcon=&DashAttackIconBrush;}
    if(Id==TEXT("whirlwind")){Tags=TEXT("近战 / 范围 / 主动");SkillIcon=&WhirlwindIconBrush;}
    if(Id==TEXT("heavyStrike")){Tags=TEXT("近战 / 蓄力 / 主动");SkillIcon=&HeavyIconBrush;}
    if(Id==TEXT("swordUppercut")){Tags=TEXT("近战 / 上挑 / 主动");SkillIcon=&UppercutIconBrush;}
    if(Id==TEXT("chainSlash")){Tags=TEXT("双手剑或破军长柄 / 四段连斩 / 主动武技");SkillIcon=MasteryIconBrushes.Find(Id);}
    if(Id==TEXT("shadowStepSlash")){Tags=TEXT("单手刀斧限定 / 穿身二段追斩 / 主动武技");SkillIcon=MasteryIconBrushes.Find(Id);}
    if(Id==TEXT("quickCombat")){Tags=TEXT("近战 / 打击 / 主动");SkillIcon=&QuickCombatIconBrush;}
    if(Additional(Id))
    {
        SkillIcon=MasteryIconBrushes.Find(Id);
        Tags=Id==TEXT("twoHandedMastery")?TEXT("双手近战 / 根基 / 被动"):Id==TEXT("oneHandedMastery")?TEXT("单手刀斧 / 暴击 / 被动"):
            Id==TEXT("swordMastery")?TEXT("双手刀剑 / 近战 / 被动"):Id==TEXT("bluntMastery")?TEXT("双手钝器 / 近战 / 被动"):Id==TEXT("machineGunMastery")?TEXT("机枪 / 远程 / 被动"):
            Id==TEXT("shotgunMastery")?TEXT("霰弹枪 / 远程 / 被动"):TEXT("弓箭 / 远程 / 被动");
    }
    if(Id==TEXT("leapStrike")){Tags=TEXT("双手锤或破军长柄 / 范围重砸 / 主动武技");SkillIcon=MasteryIconBrushes.Find(Id);}
    auto LevelLabel=[this,Id](){return SNew(STextBlock).Text_Lambda([this,Id]{return FText::FromString(FString::Printf(TEXT("Lv.%d / %d"),Progress(Id).Level,Definition(Id).MaxLevel));})
        .Font(ColdSteelUI::NumberFont(16*.75f/Scale,true)).ColorAndOpacity(ColdSteelUI::Accent).AutoWrapText(false);};
    if(Id==TEXT("illuminationArrow"))Tags=TEXT("弓限定 / 标记显形 / 主动");
    if(Id==TEXT("elementalArrow"))Tags=TEXT("弓限定 / 三元素附魔 / 主动");
    if(Id==TEXT("magicArrowRain"))Tags=TEXT("弓限定 / 范围魔法 / 主动");
    if(Id==TEXT("heartPiercingArrow"))Tags=TEXT("弓限定 / 持续拉弓 / 被动战技");
    TSharedRef<SWidget> Brief=Paragraph(bCompact?TEXT("在实战中修炼 · 查看技能详情"):D.Description,14,ColdSteelUI::TextSecondary,PageWidth-76);
    if(Id==TEXT("leapStrike")&&bCompact)
        Brief=SNew(STextBlock).Text_Lambda([this]
        {
            const auto C=Model->LeapStrikeStats();
            return FText::FromString(FString::Printf(TEXT("伤害 / 削韧 %.1f%% · 冷却 %.1f s\n半径 %.1f m · 跳距 %.1f m · 体力 %.1f"),
                C.DamageMultiplier*100.f,C.CooldownSeconds,C.RadiusCM/100.f,C.ReachCM/100.f,C.StaminaCost));
        }).Font(ColdSteelUI::TextFont(14*.75f/Scale)).ColorAndOpacity(ColdSteelUI::TextSecondary)
            .AutoWrapText(false).WrapTextAt(FMath::Max(1.f,PageWidth-76)/Scale).LineHeightPercentage(1.4f);
    if(Id==TEXT("chainSlash")&&bCompact)
        Brief=SNew(STextBlock).Text_Lambda([this]
        {
            const auto C=Model->ChainSlashStats();
            return FText::FromString(FString::Printf(TEXT("每段伤害 / 削韧 %.1f%% · 共4段\n冷却 %.1f s · 体力 %.1f"),C.DamageMultiplier*100.f,C.CooldownSeconds,C.StaminaCost));
        }).Font(ColdSteelUI::TextFont(14*.75f/Scale)).ColorAndOpacity(ColdSteelUI::TextSecondary)
            .AutoWrapText(false).WrapTextAt(FMath::Max(1.f,PageWidth-76)/Scale).LineHeightPercentage(1.4f);
    if(Id==TEXT("shadowStepSlash")&&bCompact)
        Brief=SNew(STextBlock).Text_Lambda([this]
        {
            const auto C=Model->ShadowStepStats();
            return FText::FromString(FString::Printf(TEXT("一段 %.0f%% / 二段 %.0f%% · 突进 %.1f m\n冷却 %.1f s · 体力 %.1f"),C.Stage1DamageMultiplier*100.f,C.Stage2DamageMultiplier*100.f,C.DashDistanceCM/100.f,C.CooldownSeconds,C.StaminaCost));
        }).Font(ColdSteelUI::TextFont(14*.75f/Scale)).ColorAndOpacity(ColdSteelUI::TextSecondary)
            .AutoWrapText(false).WrapTextAt(FMath::Max(1.f,PageWidth-76)/Scale).LineHeightPercentage(1.4f);
    if(Id==TEXT("heartPiercingArrow")&&bCompact)
        Brief=SNew(STextBlock).Text_Lambda([this,Id]
        {
            const auto S=HeartPiercingArrow::ForModel(Model);
            return FText::FromString(FString::Printf(TEXT("持续拉弓 >%.1f 秒 · 满拉伤害 ×%.2f\n箭速 ×%.0f · 目标穿透 +%d（最多 %d 个）"),
                S.ChargeSeconds,S.DamageMultiplier,S.SpeedMultiplier,S.TargetPenetration,S.TargetPenetration+1));
        }).Font(ColdSteelUI::TextFont(14*.75f/Scale)).ColorAndOpacity(ColdSteelUI::TextSecondary)
            .AutoWrapText(false).WrapTextAt(FMath::Max(1.f,PageWidth-76)/Scale).LineHeightPercentage(1.4f);
    if(Id==TEXT("magicArrowRain")&&bCompact)
        Brief=Paragraph(TEXT("搭箭附魔 → 长按左键选点 → 满蓄松手\n空爆后锥形箭雨 · 保持期间持续耗体耗蓝"),14,ColdSteelUI::TextSecondary,PageWidth-76);
    if(Id==TEXT("illuminationArrow")&&bCompact)Brief=Paragraph(TEXT("沿途扫描 · 命中双倍标记 · 持续照明\n普通箭伤害 / 破除隐身 / 承伤加深"),14,ColdSteelUI::TextSecondary,PageWidth-76);
    if(Id==TEXT("elementalArrow")&&bCompact)Brief=Paragraph(TEXT("短按搭箭 · 长按圆盘切换 · 松开左键射击\n火焰爆炸 / 寒冰散射 / 闪电放射"),14,ColdSteelUI::TextSecondary,PageWidth-76);
    auto Identity=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[Label(D.Name,20,ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,4/Scale,0,0)[Paragraph(Tags,12,ColdSteelUI::TextSecondary,PageWidth-64-60-(Compact?0:128))];
    if(Compact)Identity->AddSlot().AutoHeight().Padding(0,6/Scale,0,0)[LevelLabel()];
    return SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,12/Scale,0)
                [SNew(SBox).WidthOverride(48/Scale).HeightOverride(48/Scale)[SNew(SImage).Image(SkillIcon)]]
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
        +SVerticalBox::Slot().AutoHeight().Padding(0,12/Scale,0,0)[Brief];
}
void UColdSteelSkillPage::ShowEmbeddedDetail(FName Id,float Width)
{
    if(bEmbedded&&bDetail&&SelectedSkill==Id&&FMath::IsNearlyEqual(PageWidth,Width,.5f))return;
    bEmbedded=true;bDetail=true;SelectedSkill=Id;PageWidth=Width;
    if(Scroll)Scroll->SetScrollOffset(0);
    if(Root)RefreshLayout();
}
FReply UColdSteelSkillPage::SelectCategory(int32 Index)
{ Category=Index; if(Scroll)Scroll->SetScrollOffset(0); RefreshLayout(); return FReply::Handled().SetUserFocus(FilterButtons[Index].ToSharedRef(),EFocusCause::Navigation); }
FReply UColdSteelSkillPage::OpenDetail(FName Id)
{ SelectedSkill=Id;bDetail=true; if(Scroll)Scroll->SetScrollOffset(0); RefreshLayout(); return FReply::Handled().SetUserFocus(BackButton.ToSharedRef(),EFocusCause::Navigation); }
bool UColdSteelSkillPage::GoBack()
{ if(!bDetail)return false; bDetail=false; if(Scroll)Scroll->SetScrollOffset(0); RefreshLayout();auto Button=SelectedSkill==TEXT("dodge")?DodgeDetailButton:(SelectedSkill==TEXT("dexterousHands")?DexterousHandsDetailButton:DetailButton);if(SelectedSkill==TEXT("swordUppercut"))Button=UppercutDetailButton;if(SelectedSkill==TEXT("chainSlash"))Button=ChainSlashDetailButton;if(SelectedSkill==TEXT("leapStrike"))Button=LeapStrikeDetailButton;if(SelectedSkill==TEXT("shadowStepSlash"))Button=ShadowStepDetailButton;if(SelectedSkill==TEXT("pistolMastery"))Button=PistolDetailButton;if(SelectedSkill==TEXT("criticalStrike"))Button=CriticalDetailButton;if(SelectedSkill==TEXT("fireball"))Button=FireballDetailButton;if(SelectedSkill==TEXT("heavyStrike"))Button=HeavyDetailButton;if(SelectedSkill==TEXT("quickCombat"))Button=QuickCombatDetailButton;if(SelectedSkill==TEXT("whirlwind"))Button=WhirlwindDetailButton;if(SelectedSkill==TEXT("dashAttack"))Button=DashAttackDetailButton;if(ElectricMagic::IsSkill(SelectedSkill))Button=ElectricDetailButtons.FindRef(SelectedSkill);if(SelectedSkill==TEXT("lightningStrike"))Button=LightningDetailButton;if(SelectedSkill==TEXT("holyLight"))Button=HolyLightDetailButton;if(SelectedSkill==TEXT("dragonBreath"))Button=DragonBreathDetailButton;if(SelectedSkill==TEXT("meteor"))Button=MeteorDetailButton;if(SelectedSkill==TEXT("flameArmor"))Button=FlameArmorDetailButton;if(SelectedSkill==TEXT("lightningHaste"))Button=LightningHasteDetailButton;if(SelectedSkill==TEXT("iceArmor"))Button=IceArmorDetailButton;if(SelectedSkill==TEXT("iceWall"))Button=IceWallDetailButton;if(SelectedSkill==TEXT("blizzard"))Button=BlizzardDetailButton;if(Button)FSlateApplication::Get().SetKeyboardFocus(Button,EFocusCause::Navigation); return true; }
