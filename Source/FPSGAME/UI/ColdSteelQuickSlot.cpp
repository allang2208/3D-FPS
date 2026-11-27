#include "ColdSteelQuickSlot.h"
#include "ColdSteelTextToolTip.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/PojunGrip.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "../Skills/FPSIceArmorComponent.h"
#include "../Skills/FPSLightningHasteComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/OffhandKukriComponent.h"
#include "../Weapons/Staff/StaffOffhandMeleeComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../Weapons/RuneOrbBladesComponent.h"
#include "../Weapons/StarMarrowComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIAudio.h"
#include "../Skills/FPSMagicArrowRainComponent.h"
#include "../Skills/FPSElementalArrowComponent.h"
#include "../Skills/FPSIlluminationArrowComponent.h"
#include "ColdSteelQuickDrag.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelUIStyle.h"
#include "SColdSteelCooldownMask.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSIceSpikeComponent.h"
#include "../Skills/FPSIceWallComponent.h"
#include "../Skills/FPSBlizzardComponent.h"
#include "../Skills/FPSLightningComponent.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "../Skills/FPSHolyLightComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/NativeWidgetHost.h"
#include "Components/ScaleBox.h"
#include "Components/ScaleBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/SizeBox.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "GameFramework/PlayerController.h"
#include "Rendering/DrawElements.h"

void UColdSteelQuickSlot::Configure(UColdSteelHUDWidget* Owner,int32 SlotIndex,FName InFixedSkill)
{
    HUD=Owner;Index=SlotIndex;FixedSkill=InFixedSkill;
    // 专属槽的键位标注与固定技能一起给定（如 F · 快速进战、G · 环绕飞剑），不走混放键位表。
    FixedKeyLabel=FixedSkill.IsNone()?FString():FixedSkill==TEXT("runeBlades")?TEXT("G"):TEXT("F");
    SetVisibility(ESlateVisibility::Visible);
    const float Scale=ColdSteelUI::PixelScale(this);
    auto* Overlay=WidgetTree->ConstructWidget<UOverlay>();WidgetTree->RootWidget=Overlay;
    Overlay->SetClipping(EWidgetClipping::ClipToBounds);
    auto Fill=[Overlay](UWidget* Widget)
    {
        auto* LayerSlot=Overlay->AddChildToOverlay(Widget);
        LayerSlot->SetHorizontalAlignment(HAlign_Fill);LayerSlot->SetVerticalAlignment(VAlign_Fill);
        return LayerSlot;
    };
    Icon=WidgetTree->ConstructWidget<UImage>();Icon->SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* Fit=WidgetTree->ConstructWidget<UScaleBox>();Fit->SetStretch(EStretch::ScaleToFit);
    Fit->SetStretchDirection(EStretchDirection::Both);Fit->SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* FitSlot=Cast<UScaleBoxSlot>(Fit->AddChild(Icon));
    FitSlot->SetHorizontalAlignment(HAlign_Center);FitSlot->SetVerticalAlignment(VAlign_Center);
    IconFrame=WidgetTree->ConstructWidget<USizeBox>();IconFrame->SetWidthOverride(48/Scale);IconFrame->SetHeightOverride(48/Scale);
    IconFrame->SetContent(Fit);IconFrame->SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* I=Overlay->AddChildToOverlay(IconFrame);I->SetHorizontalAlignment(HAlign_Center);I->SetVerticalAlignment(VAlign_Center);
    auto Text=[&](const FString& Value)
    {
        auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Value));T->SetAutoWrapText(false);
        T->SetFont(ColdSteelUI::TextFont(9/Scale));T->SetColorAndOpacity(ColdSteelUI::TextPrimary);
        T->SetShadowOffset(FVector2D(0,1/Scale));T->SetShadowColorAndOpacity(FLinearColor(0,0,0,.86f));
        T->SetVisibility(ESlateVisibility::HitTestInvisible);return T;
    };
    FallbackIcon=Text(TEXT("?"));FallbackIcon->SetFont(ColdSteelUI::TextFont(15/Scale));
    auto* F=Overlay->AddChildToOverlay(FallbackIcon);F->SetHorizontalAlignment(HAlign_Center);F->SetVerticalAlignment(VAlign_Center);
    auto* MaskHost=WidgetTree->ConstructWidget<UNativeWidgetHost>();MaskHost->SetVisibility(ESlateVisibility::HitTestInvisible);
    MaskHost->SetContent(SAssignNew(CooldownMask,SColdSteelCooldownMask).CornerRadius(7/Scale));Fill(MaskHost);
    State=Text(TEXT(""));auto* S=Overlay->AddChildToOverlay(State);S->SetHorizontalAlignment(HAlign_Center);S->SetVerticalAlignment(VAlign_Center);
    ReadyFlash=WidgetTree->ConstructWidget<UImage>();
    ReadyFlash->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::White,6/Scale,FLinearColor::Transparent,0));
    ReadyFlash->SetRenderOpacity(0);ReadyFlash->SetVisibility(ESlateVisibility::HitTestInvisible);Fill(ReadyFlash);
    Key=Text(FixedSkill.IsNone()?ColdSteelQuickBar::KeyLabel(Index):FixedKeyLabel);Key->SetFont(ColdSteelUI::NumberFont(9/Scale));Key->SetColorAndOpacity(ColdSteelUI::HUDGoldLight);
    auto* K=Overlay->AddChildToOverlay(Key);K->SetHorizontalAlignment(HAlign_Right);K->SetVerticalAlignment(VAlign_Bottom);K->SetPadding(FMargin(0,0,4/Scale,2/Scale));
    Count=Text(TEXT(""));Count->SetFont(ColdSteelUI::NumberFont(9/Scale,true));auto* C=Overlay->AddChildToOverlay(Count);
    C->SetHorizontalAlignment(HAlign_Center);C->SetVerticalAlignment(VAlign_Top);C->SetPadding(FMargin(0,1/Scale,0,0));
    SetDisplayScale(Scale);Refresh();
}

void UColdSteelQuickSlot::SetDisplayScale(float Scale)
{
    Scale=FMath::Max(.01f,Scale);
    if(!IconFrame||FMath::IsNearlyEqual(DisplayScale,Scale,.0001f))return;
    DisplayScale=Scale;
    const float Pixels=Displayed.Skill.IsNone()?40.f:48.f;
    IconFrame->SetWidthOverride(Pixels/Scale);IconFrame->SetHeightOverride(Pixels/Scale);
    FallbackIcon->SetFont(ColdSteelUI::TextFont(15/Scale));
    auto StateFont=State->GetFont();StateFont.Size=9/Scale;State->SetFont(StateFont);
    Key->SetFont(ColdSteelUI::NumberFont(9/Scale));Count->SetFont(ColdSteelUI::NumberFont(9/Scale,true));
    for(auto* Label:{FallbackIcon.Get(),State.Get(),Key.Get(),Count.Get()})Label->SetShadowOffset(FVector2D(0,1/Scale));
    CastChecked<UOverlaySlot>(Key->Slot)->SetPadding(FMargin(0,0,4/Scale,2/Scale));
    CastChecked<UOverlaySlot>(Count->Slot)->SetPadding(FMargin(0,1/Scale,0,0));
    ReadyFlash->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::White,6/Scale,FLinearColor::Transparent,0));
    CooldownMask->SetCornerRadius(7/Scale);
}

void UColdSteelQuickSlot::NativeTick(const FGeometry& Geometry,float DeltaTime)
{
    Super::NativeTick(Geometry,DeltaTime);
    const auto* PC=GetOwningPlayer();
    const FKey InputKey=FixedSkill.IsNone()?ColdSteelQuickBar::Key(Index):FixedSkill==TEXT("runeBlades")?EKeys::G:EKeys::F;
    const bool Gold=!Displayed.IsEmpty()&&(IsHovered()||bGoldPrepared||(PC&&PC->IsInputKeyDown(InputKey)));
    if(Gold!=bGoldHighlighted){bGoldHighlighted=Gold;if(const auto Widget=GetCachedWidget())Widget->Invalidate(EInvalidateWidgetReason::Paint);}
    BlinkElapsed=FMath::Fmod(BlinkElapsed+DeltaTime,ColdSteelQuickSlotFX::KeyPeriod);
    if(Key)Key->SetRenderOpacity(ColdSteelQuickSlotFX::KeyOpacity(BlinkElapsed));
    if(FlashElapsed<ActiveFlashDuration)
    {
        FlashElapsed=FMath::Min(ActiveFlashDuration,FlashElapsed+DeltaTime);
        ReadyFlash->SetRenderOpacity(FlashStrength*ColdSteelQuickSlotFX::FlashOpacity(
            FlashElapsed*ColdSteelQuickSlotFX::FlashDuration/ActiveFlashDuration));
    }
    if(CooldownTransitionElapsed<ColdSteelQuickSlotFX::MaskTransition)
    {
        CooldownTransitionElapsed=FMath::Min(ColdSteelQuickSlotFX::MaskTransition,CooldownTransitionElapsed+DeltaTime);
        DisplayedCooldownFraction=FMath::Lerp(CooldownTransitionFrom,CooldownFraction,
            CooldownTransitionElapsed/ColdSteelQuickSlotFX::MaskTransition);
        CooldownMask->SetFraction(DisplayedCooldownFraction);
    }
    // A rejected left-hand request blinks in place for its window instead of
    // queueing, so the slot drives that pulse for the bound spell.
    bool Notice=false;float NoticeAlpha=1.f,NoticeRise=0.f;
    if(const auto* Player=GetOwningPlayerPawn())
    {
        if(FireMagic::IsSkill(Displayed.Skill))
        {
            if(const auto* Ability=Player->FindComponentByClass<UFPSFireMagicComponent>())
            {Notice=Ability->IsHandOccupiedNotice(Displayed.Skill);NoticeAlpha=Ability->HandNoticeAlpha();NoticeRise=Ability->HandNoticeRise();}
        }
        else if(Displayed.Skill==TEXT("fireball"))
        {
            if(const auto* Ability=Player->FindComponentByClass<UFPSFireballComponent>())
            {Notice=Ability->IsHandOccupiedNotice();NoticeAlpha=Ability->HandNoticeAlpha();NoticeRise=Ability->HandNoticeRise();}
        }
        else if(Displayed.Skill==TEXT("lightningHaste"))
        {
            if(const auto* Ability=Player->FindComponentByClass<UFPSLightningHasteComponent>())
            {Notice=Ability->IsHandOccupiedNotice();NoticeAlpha=Ability->HandNoticeAlpha();NoticeRise=Ability->HandNoticeRise();}
        }
        else if(Displayed.Skill==TEXT("iceArmor"))
        {
            if(const auto* Ability=Player->FindComponentByClass<UFPSIceArmorComponent>())
            {Notice=Ability->IsHandOccupiedNotice();NoticeAlpha=Ability->HandNoticeAlpha();NoticeRise=Ability->HandNoticeRise();}
        }
        else if(Displayed.Skill==TEXT("iceSpike"))
        {
            if(const auto* Ability=Player->FindComponentByClass<UFPSIceSpikeComponent>())
            {Notice=Ability->IsHandOccupiedNotice();NoticeAlpha=Ability->HandNoticeAlpha();NoticeRise=Ability->HandNoticeRise();}
        }
        else if(Displayed.Skill==TEXT("iceWall"))
        {
            if(const auto* Ability=Player->FindComponentByClass<UFPSIceWallComponent>())
            {Notice=Ability->IsHandOccupiedNotice();NoticeAlpha=Ability->HandNoticeAlpha();NoticeRise=Ability->HandNoticeRise();}
        }
        else if(Displayed.Skill==TEXT("blizzard"))
        {
            if(const auto* Ability=Player->FindComponentByClass<UFPSBlizzardComponent>())
            {Notice=Ability->IsHandOccupiedNotice();NoticeAlpha=Ability->HandNoticeAlpha();NoticeRise=Ability->HandNoticeRise();}
        }
        else if(ElectricMagic::IsSkill(Displayed.Skill))
        {
            if(const auto* Ability=Player->FindComponentByClass<UFPSElectricMagicComponent>())
            {Notice=Ability->IsHandOccupiedNotice(Displayed.Skill);NoticeAlpha=Ability->HandNoticeAlpha();NoticeRise=Ability->HandNoticeRise();}
        }
        else if(Displayed.Skill==TEXT("lightningStrike"))
        {
            if(const auto* Ability=Player->FindComponentByClass<UFPSLightningComponent>())
            {Notice=Ability->IsHandOccupiedNotice();NoticeAlpha=Ability->HandNoticeAlpha();NoticeRise=Ability->HandNoticeRise();}
        }
        else if(Displayed.Skill==TEXT("holyLight"))
        {
            if(const auto* Ability=Player->FindComponentByClass<UFPSHolyLightComponent>())
            {Notice=Ability->IsHandOccupiedNotice();NoticeAlpha=Ability->HandNoticeAlpha();NoticeRise=Ability->HandNoticeRise();}
        }
    }
    if(State)
    {
        State->SetRenderOpacity(Notice?NoticeAlpha:1.f);
        State->SetRenderTranslation(FVector2D(0,Notice?-NoticeRise/FMath::Max(.01f,DisplayScale):0));
    }
}

void UColdSteelQuickSlot::Refresh()
{
    TRACE_CPUPROFILER_EVENT_SCOPE(ColdSteelQuickSlot_Refresh);
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Model||!Icon)return;
    // 专属槽不读混放绑定，恒显固定技能；其余数据（图标、冷却、变暗）走同一条显示路径。
    const auto* Staff=GetOwningPlayerPawn()?GetOwningPlayerPawn()->FindComponentByClass<UStaffWeaponComponent>():nullptr;
    const auto* StarCharge=GetOwningPlayerPawn()?GetOwningPlayerPawn()->FindComponentByClass<UStarMarrowComponent>():nullptr;
    const auto Binding=FixedSkill.IsNone()?Model->QuickBinding(Index):[&]
    {
        FColdSteelQuickBinding B;B.Skill=FixedSkill;
        if(FixedSkill==TEXT("runeBlades"))
        {
            if(StarCharge&&StarCharge->IsEquipped())B.Skill=TEXT("starMarrowCharge");
            else if(Staff&&Staff->HasIlluminationSpecial())B.Skill=TEXT("staffLight");
        }
        return B;
    }();
    const auto* Item=Model->ResolveQuickItem(Index);
    const FString WaterIcon=Item&&Item->Definition==TEXT("mineral_water")?ColdSteelInventory::Text(*Item,TEXT("ue_icon")):FString();
    const auto* ElementAbility=GetOwningPlayerPawn()?GetOwningPlayerPawn()->FindComponentByClass<UFPSElementalArrowComponent>():nullptr;
    const EArrowElement SelectedElement=ElementAbility?ElementAbility->Selected():EArrowElement::Fire;
    const FString ElementIcon=Binding.Skill==TEXT("elementalArrow")?ElementalArrow::Icon(SelectedElement):FString();
    const bool ChargeSlot=Binding.Skill==TEXT("starMarrowCharge");
    auto* ChargeIcon=ChargeSlot&&StarCharge?StarCharge->ShortcutIcon():nullptr;
    const bool BindingChanged=!bLoaded||!(Binding==Displayed)||WaterIcon!=DisplayedWaterIcon||ElementIcon!=DisplayedElementIcon
        ||(ChargeSlot&&Texture.Get()!=ChargeIcon);
    if(BindingChanged)
    {
        bLoaded=true;Displayed=Binding;DisplayedWaterIcon=WaterIcon;DisplayedElementIcon=ElementIcon;FString Path,Name;
        if(const auto* D=Model->QuickSkillDefinition(Binding.Skill)){Path=D->Icon;Name=D->Name;}
        else if(!Binding.ItemDefinition.IsEmpty())
        {const auto Template=Item?*Item:Model->CreateItem(Binding.ItemDefinition);Path=ColdSteelInventory::Text(Template,TEXT("ue_icon"));Name=ColdSteelInventory::Text(Template,TEXT("name"));}
        if(!ElementIcon.IsEmpty()){Path=ElementIcon;Name=FString(TEXT("元素箭 · "))+ElementalArrow::Name(SelectedElement);}
        Texture=ChargeIcon;
        if(ChargeSlot){Path.Reset();Name=TEXT("充能");}
        if(!Path.IsEmpty())
        {
            if(auto* Found=Textures.Find(Path))Texture=*Found;
            else {Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Path);Textures.Add(Path,Texture);}
        }
        Icon->SetBrushFromTexture(Texture,true);Icon->SetVisibility(Texture?ESlateVisibility::HitTestInvisible:ESlateVisibility::Hidden);
        const float Pixels=Binding.Skill.IsNone()?40.f:48.f;
        IconFrame->SetWidthOverride(Pixels/ColdSteelUI::PixelScale(this));IconFrame->SetHeightOverride(Pixels/ColdSteelUI::PixelScale(this));
        FallbackIcon->SetVisibility(!Texture&&!Binding.IsEmpty()?ESlateVisibility::HitTestInvisible:ESlateVisibility::Hidden);
        FallbackIcon->SetText(FText::FromString(ChargeSlot?TEXT("充"):TEXT("?")));
        const FString KeyText=FixedSkill.IsNone()?ColdSteelQuickBar::KeyLabel(Index):FixedKeyLabel;
        FString Hint;
        if(ChargeSlot)
            Hint=FString::Printf(TEXT("G · 充能\n消耗最大魔法值的 %.0f%%，持续 %.0f s。\n伤害+%.0f%%，全部伤害转为魔法伤害。\n充能结束后可再次使用。"),
                UStarMarrowComponent::ManaFraction*100.f,UStarMarrowComponent::Duration,(UStarMarrowComponent::DamageMultiplier-1.)*100.);
        else if(Binding.Skill==TEXT("elementalArrow"))
            Hint=FString::Printf(TEXT("%s · %s\n短按搭箭／取消；长按 0.3 秒切换元素，冷却中仍可打开圆盘。\n三元素分别冷却，只与对应原魔法共用冷却；选中冷却元素后，待就绪短按搭箭。"),*KeyText,*Name);
        else if(FixedSkill.IsNone())
            Hint=Binding.IsEmpty()?FString::Printf(TEXT("%s · 拖入主动技能或消耗品"),*KeyText):
                FString::Printf(TEXT("%s · %s\n拖到空槽移动，拖到其他内容交换；拖出快捷栏解绑"),*Name,*KeyText);
        else if(Binding.Skill==TEXT("staffLight"))
            Hint=FString::Printf(TEXT("%s · %s\n按 G 开启／关闭照明；无冷却、无消耗"),*KeyText,*Name);
        else
            Hint=FString::Printf(TEXT("%s · %s\n按 %s 直接触发；冷却结束后可用"),*KeyText,*Name,*KeyText);
        ColdSteelToolTip::Set(*this,FText::FromString(Hint));
    }
    FString Message;float Fraction=0,Remaining=0;bool Dim=false;
    bGoldPrepared=false;
    Count->SetText(FText::GetEmpty());
    if(Binding.Skill==TEXT("illuminationArrow"))
    {
        const auto* P=GetOwningPlayerPawn();const auto* Ability=P?P->FindComponentByClass<UFPSIlluminationArrowComponent>():nullptr;
        Remaining=Model->IlluminationArrowCooldown();Fraction=Remaining/FMath::Max(.1f,Model->IlluminationArrowCooldownDuration());
        if(Ability){Message=Ability->StatusText();bGoldPrepared=Ability->IsPrepared();}
        Dim=!Model->ActiveBow()||(!bGoldPrepared&&!Model->CanSpendMana(Model->SpellManaCost(Binding.Skill)));
        if(!Model->ActiveBow())Message=TEXT("需要装备弓");
    }
    else if(Binding.Skill==TEXT("elementalArrow"))
    {
        Remaining=Model->ElementalArrowCooldown(SelectedElement);
        Fraction=Remaining/FMath::Max(.1f,Model->ElementalArrowCooldownDuration(SelectedElement));
        FString Why;const bool CanPrepare=Model->CanPrepareElementalArrow(SelectedElement,Why);
        // Keep the selection shortcut available; only the mask shows this element's CD.
        Dim=!Model->ActiveBow()||!Model->CanBindQuickSkill(TEXT("elementalArrow"));
        if(ElementAbility){Message=ElementAbility->StatusText();bGoldPrepared=ElementAbility->IsPrepared();}
        if(!CanPrepare&&!bGoldPrepared)Message=Remaining>0?TEXT("长按切换"):Why;
    }
    else if(Binding.Skill==TEXT("magicArrowRain"))
    {
        const auto* P=GetOwningPlayerPawn();const auto* Ability=P?P->FindComponentByClass<UFPSMagicArrowRainComponent>():nullptr;
        Remaining=Model->MagicArrowRainCooldown();
        Fraction=Remaining/FMath::Max(.1f,Model->MagicArrowRainCooldownDuration());
        if(Ability){Message=Ability->StatusText();bGoldPrepared=Ability->IsPrepared();}
        Dim=!Model->ActiveBow()||(!bGoldPrepared&&!Model->CanSpendMana(Model->SpellManaCost(Binding.Skill)));
        if(!Model->ActiveBow())Message=TEXT("需要装备弓");
    }
    else if(Binding.Skill==TEXT("lightningHaste"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* A=Player?Player->FindComponentByClass<UFPSLightningHasteComponent>():nullptr;
        if(A){Message=A->StatusText();Fraction=A->CooldownFraction();if(A->Remaining()>0)Count->SetText(FText::FromString(FString::Printf(TEXT("%.0fs"),FMath::CeilToFloat(A->Remaining()))));}
        if(Fraction>0&&!(A&&A->IsHandOccupiedNotice()))Remaining=Model->LightningHasteCooldown();
        Dim=!Model->CanSpendMana(Model->SpellManaCost(Binding.Skill));
    }
    else if(Binding.Skill==TEXT("iceArmor"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* A=Player?Player->FindComponentByClass<UFPSIceArmorComponent>():nullptr;
        if(A){Message=A->StatusText();Fraction=A->CooldownFraction();if(A->Remaining()>0)Count->SetText(FText::FromString(FString::Printf(TEXT("%.0fs"),FMath::CeilToFloat(A->Remaining()))));}
        if(Fraction>0&&!(A&&A->IsHandOccupiedNotice()))Remaining=Model->IceArmorCooldown();
        Dim=!Model->CanSpendMana(Model->SpellManaCost(Binding.Skill));
    }
    else if(FireMagic::IsSkill(Binding.Skill))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<UFPSFireMagicComponent>():nullptr;
        if(Ability)
        {
            Message=Ability->StatusText(Binding.Skill);Fraction=Ability->CooldownFraction(Binding.Skill);
            if(Binding.Skill==TEXT("flameArmor")&&Ability->ArmorRemaining()>0)
                Count->SetText(FText::FromString(FString::Printf(TEXT("%.0fs"),FMath::CeilToFloat(Ability->ArmorRemaining()))));
        }
        if(Fraction>0&&!(Ability&&Ability->IsHandOccupiedNotice(Binding.Skill)))Remaining=Model->FireMagicCooldown(Binding.Skill);
        Dim=!Model->CanSpendMana(Model->SpellManaCost(Binding.Skill));
        if(Model->FireMagicDefinition(Binding.Skill).FireMagic.bRequiresStaff&&!Model->HasEquippedStaff())
        {Dim=true;Remaining=0;Message=TEXT("需要法杖");}
    }
    else if(Binding.Skill==TEXT("fireball"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<UFPSFireballComponent>():nullptr;
        if(Ability){Message=Ability->StatusText();Fraction=Ability->CooldownFraction();bGoldPrepared=Ability->IsPrepared();}
        // The refusal notice answers the press itself, so it outranks the countdown.
        if(Fraction>0&&!(Ability&&Ability->IsHandOccupiedNotice()))Remaining=Model->FireballCooldown();
        Dim=!Model->CanSpendMana(Model->SpellManaCost(Binding.Skill))&&(!Ability||(!Ability->IsPrepared()&&!Ability->IsFlying()));
    }
    else if(Binding.Skill==TEXT("blizzard"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<UFPSBlizzardComponent>():nullptr;
        if(Ability){Message=Ability->StatusText();Fraction=Ability->CooldownFraction();}
        if(Fraction>0&&!(Ability&&Ability->IsHandOccupiedNotice()))Remaining=Model->BlizzardCooldown();
        Dim=!Model->CanSpendMana(Model->SpellManaCost(Binding.Skill))&&(!Ability||!Ability->HasUnreleasedCast());
        if(Model->BlizzardDefinition().Blizzard.bRequiresStaff&&!Model->HasEquippedStaff())
        {Dim=true;bGoldPrepared=false;Remaining=0;Message=TEXT("需要法杖");}
    }
    else if(Binding.Skill==TEXT("iceWall"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<UFPSIceWallComponent>():nullptr;
        if(Ability){Message=Ability->StatusText();Fraction=Ability->CooldownFraction();bGoldPrepared=Ability->IsPrepared();}
        if(Fraction>0&&!(Ability&&Ability->IsHandOccupiedNotice()))Remaining=Model->IceWallCooldown();
        Dim=!Model->CanSpendMana(Model->SpellManaCost(Binding.Skill))&&(!Ability||!Ability->IsPrepared());
        if(Model->IceWallDefinition().IceWall.bRequiresStaff&&!Model->HasEquippedStaff())
        {Dim=true;bGoldPrepared=false;Remaining=0;Message=TEXT("需要法杖");}
    }
    else if(Binding.Skill==TEXT("iceSpike"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<UFPSIceSpikeComponent>():nullptr;
        if(Ability){Message=Ability->StatusText();Fraction=Ability->CooldownFraction();if(Ability->ActiveCount()>0)Count->SetText(FText::AsNumber(Ability->ActiveCount()));}
        // The refusal notice answers the press itself, so it outranks the countdown.
        if(Fraction>0&&!(Ability&&Ability->IsHandOccupiedNotice()))Remaining=Model->IceSpikeCooldown();
        Dim=!Model->CanSpendMana(Model->SpellManaCost(Binding.Skill))&&(!Ability||Ability->ActiveCount()==0);
    }
    else if(ElectricMagic::IsSkill(Binding.Skill))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<UFPSElectricMagicComponent>():nullptr;
        if(Ability)
        {
            Message=Ability->StatusText(Binding.Skill);Fraction=Ability->CooldownFraction(Binding.Skill);
            bGoldPrepared=Ability->UnreleasedSkill()==Binding.Skill;
            if(Binding.Skill==TEXT("stormDomain")&&Ability->DomainRemaining()>0)
                Count->SetText(FText::FromString(FString::Printf(TEXT("%.0fs"),FMath::CeilToFloat(Ability->DomainRemaining()))));
        }
        if(Fraction>0&&!bGoldPrepared&&!(Ability&&Ability->IsHandOccupiedNotice(Binding.Skill)))Remaining=Model->ElectricMagicCooldown(Binding.Skill);
        Dim=!Model->CanSpendMana(Model->SpellManaCost(Binding.Skill))&&!bGoldPrepared;
        if(Model->ElectricMagicDefinition(Binding.Skill).ElectricMagic.bRequiresStaff&&!Model->HasEquippedStaff())
        {Dim=true;bGoldPrepared=false;Remaining=0;Message=TEXT("需要法杖");}
    }
    else if(Binding.Skill==TEXT("lightningStrike"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<UFPSLightningComponent>():nullptr;
        if(Ability){Message=Ability->StatusText();Fraction=Ability->CooldownFraction();}
        if(Fraction>0&&!(Ability&&Ability->IsHandOccupiedNotice()))Remaining=Model->LightningCooldown();
        Dim=!Model->CanSpendMana(Model->SpellManaCost(Binding.Skill));
    }
    else if(Binding.Skill==TEXT("holyLight"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<UFPSHolyLightComponent>():nullptr;
        if(Ability){Message=Ability->StatusText();Fraction=Ability->CooldownFraction();}
        if(Fraction>0&&!(Ability&&Ability->IsHandOccupiedNotice()))Remaining=Model->HolyLightCooldown();
        Dim=!Model->CanSpendMana(Model->SpellManaCost(Binding.Skill));
    }
    else if(Binding.Skill==TEXT("leapStrike"))
    {
        Remaining=Model->LeapStrikeCooldown();
        const float Duration=Model->LeapStrikeCooldownDuration();
        Fraction=Duration>0.f?Remaining/Duration:0.f;
        const auto* Player=GetOwningPlayerPawn();
        const auto* Tool=Player?Player->FindComponentByClass<UProductionToolComponent>():nullptr;
        Message=Tool?Tool->LeapStrikeStatusText():TEXT("需双手锤");Dim=!Message.IsEmpty();
    }
    else if(Binding.Skill==TEXT("chainSlash"))
    {
        Remaining=Model->ChainSlashCooldown();
        const float Duration=Model->ChainSlashCooldownDuration();
        Fraction=Duration>0.f?Remaining/Duration:0.f;
        const auto* Player=GetOwningPlayerPawn();
        const auto* Sword=Player?Player->FindComponentByClass<URuneSwordComponent>():nullptr;
        Message=Sword?Sword->ChainSlashStatusText():TEXT("需双手剑");
        Dim=!Message.IsEmpty();
    }
    else if(Binding.Skill==TEXT("shadowStepSlash"))
    {
        Remaining=Model->ShadowStepCooldown();
        const float Duration=Model->ShadowStepCooldownDuration();
        Fraction=Duration>0.f?Remaining/Duration:0.f;
        const auto* Player=GetOwningPlayerPawn();
        const auto* Kukri=Player?Player->FindComponentByClass<UKukriWeaponComponent>():nullptr;
        const auto* Offhand=Player?Player->FindComponentByClass<UOffhandKukriComponent>():nullptr;
        const bool bKukriHeld=Kukri&&Kukri->IsEquipped();
        const bool bOffhandHeld=!bKukriHeld&&Offhand&&(Offhand->IsEquipped()||UStaffOffhandMeleeComponent::IsEquippedOn(Player));
        const float FollowRem=bKukriHeld?Kukri->ShadowStepFollowupRemaining():bOffhandHeld?Offhand->ShadowStepFollowupRemaining():0.f;
        if(FollowRem>0.f)
        {
            bGoldPrepared=true;Remaining=0.f;Fraction=0.f;
            Message=TEXT("追斩");
            Count->SetText(FText::FromString(FString::Printf(TEXT("%.1fs"),FollowRem)));
            Dim=false;
        }
        else
        {
            Message=bKukriHeld?Kukri->ShadowStepStatusText():bOffhandHeld?Offhand->ShadowStepStatusText():TEXT("需单手刀斧");
            Dim=!Message.IsEmpty();
        }
    }
    else if(Binding.Skill==TEXT("swordUppercut"))
    {
        Remaining=Model->SwordUppercutCooldown();
        const float Duration=Model->SwordUppercutCooldownDuration();
        Fraction=Duration>0.f?Remaining/Duration:0.f;
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<URuneSwordComponent>():nullptr;
        const auto* HammerItem=Model->ActiveProductionTool();
        const auto* Tool=Player?Player->FindComponentByClass<UProductionToolComponent>():nullptr;
        const auto* Kukri=Player?Player->FindComponentByClass<UKukriWeaponComponent>():nullptr;
        const auto* Offhand=Player?Player->FindComponentByClass<UOffhandKukriComponent>():nullptr;
        Message=HammerItem&&PojunGrip::UsesHammerMotion(*HammerItem)&&Tool?
            Tool->UppercutStatusText():Kukri&&Kukri->IsEquipped()?Kukri->UppercutStatusText():
            Offhand&&(Offhand->IsEquipped()||UStaffOffhandMeleeComponent::IsEquippedOn(Player))?Offhand->UppercutStatusText():
            Ability?Ability->UppercutStatusText():TEXT("需近战");
        Dim=!Message.IsEmpty();
    }
    else if(Binding.Skill==TEXT("heavyStrike"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<URuneSwordComponent>():nullptr;
        // The kukri's heavy strike (KukriHeavy.cpp): same stamina gate and charge readout as the sword's.
        const auto* Kukri=Player?Player->FindComponentByClass<UKukriWeaponComponent>():nullptr;
        const float Charge=Kukri&&Kukri->IsEquipped()?Kukri->HeavyChargeFraction():Ability?Ability->HeavyChargeFraction():0.f;
        const bool bBusy=Kukri&&Kukri->IsEquipped()?Kukri->IsBusy():Ability&&Ability->IsBusy();
        const bool bMelee=(Kukri&&Kukri->IsEquipped())||(Ability&&Ability->IsEquipped());
        Dim=!bMelee||!Model->CanSpendStamina(ColdSteelMelee::HeavyReleaseStamina(Model->Equipped(),Model));
        if(!bMelee)Message=TEXT("需近战");
        else if(Charge>0)Message=FString::Printf(TEXT("%.0f%%"),Charge*100);
        else if(bBusy)Message=TEXT("动作中");
    }
    else if(Binding.Skill==TEXT("whirlwind"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<URuneSwordComponent>():nullptr;
        const auto* Tool=Player?Player->FindComponentByClass<UProductionToolComponent>():nullptr;
        const auto* HammerItem=Model->ActiveProductionTool();
        const bool Hammer=Tool&&Tool->IsEquipped()&&HammerItem&&PojunGrip::UsesHammerMotion(*HammerItem);
        Remaining=Model->WhirlwindCooldown();
        Fraction=Model->WhirlwindCooldownDuration()>0?Remaining/Model->WhirlwindCooldownDuration():0.f;
        const auto* Kukri=Player?Player->FindComponentByClass<UKukriWeaponComponent>():nullptr;
        const auto* StaffPair=Player?Player->FindComponentByClass<UStaffOffhandMeleeComponent>():nullptr;
        const bool StaffBlade=StaffPair&&StaffPair->IsEquipped();
        const bool KukriHeld=!Hammer&&Kukri&&(Kukri->IsEquipped()||StaffBlade);
        const bool Melee=Hammer||KukriHeld||(Ability&&Ability->IsEquipped());
        const bool Busy=Hammer?Tool->IsBusy():KukriHeld?(Kukri->IsBusy()||(StaffBlade&&!StaffPair->CanWhirlwind())):Ability&&Ability->IsBusy();
        const bool Enough=Model->CanSpendStamina(Model->WhirlwindStats().StaminaCost);
        Dim=!Melee||!Enough||Remaining>0||Busy;
        if(!Melee)Message=TEXT("需近战");
        else if(Hammer?Tool->IsWhirlwindActive():KukriHeld?Kukri->IsWhirlwindActive():Ability&&Ability->IsWhirlwindActive())Message=TEXT("旋风");
        else if(!Enough)Message=TEXT("体力不足");
        else if(Busy)Message=TEXT("动作中");
    }
    else if(Binding.Skill==TEXT("dodge"))
    {
        if(const auto* Player=GetOwningPlayerPawn<AFPSGAMECharacter>();Player&&Player->IsDodging())Message=TEXT("闪避");
        Dim=!Model->CanSpendStamina(Model->DodgeStaminaCost());
    }
    else if(Binding.Skill==TEXT("quickCombat"))
    {
        // This is the selected weapon's complete action cycle, not a skill CD.
        Remaining=Model->QuickCombatCooldown();
        const float Duration=Model->QuickCombatCooldownDuration();
        Fraction=Duration>0.f?Remaining/Duration:0.f;
        const float Cost=Model->QuickCombatStaminaCost();
        const bool EnoughStamina=Model->CanSpendStamina(Cost);
        const bool EnoughMana=!ColdSteelBow::AuroraRiser(Model,Model->ActiveBow())||Model->CanSpendMana(Model->AdjustedManaCost(Cost));
        Dim=Remaining>0.f||!EnoughStamina||!EnoughMana;
        if(!EnoughStamina)Message=TEXT("体力不足");
        else if(!EnoughMana)Message=TEXT("魔法不足");
    }
    else if(Binding.Skill==TEXT("staffLight"))
    {
        Dim=!Staff||!Staff->HasIlluminationSpecial();
        if(Staff&&Staff->IsIlluminationOn()){Message=TEXT("已点亮");bGoldPrepared=true;}
    }
    else if(ChargeSlot)
    {
        Remaining=StarCharge?StarCharge->Remaining():0.f;
        Fraction=Remaining/UStarMarrowComponent::Duration;
        const bool Enough=Model->CanSpendMana(FMath::Max(0.f,Model->Derived(TEXT("maxMp")))*UStarMarrowComponent::ManaFraction);
        const bool Pending=StarCharge&&StarCharge->IsActivationPending();
        const bool Ready=StarCharge&&StarCharge->CanActivate()&&!Pending&&Enough;
        Dim=!Ready;bGoldPrepared=Ready;
        if(Remaining>0.f)Count->SetText(FText::FromString(TEXT("充能中")));
        else if(Pending)Message=TEXT("释放中");
        else if(!Enough)Message=TEXT("魔法不足");
        else if(!Ready)Message=TEXT("暂不可用");
    }
    else if(Binding.Skill==TEXT("runeBlades"))
    {
        // 与 G 槽显隐和实际施放共用当前主手判定，不能用所有双手剑共用的 IsEquipped。
        const auto* Player=GetOwningPlayerPawn();
        const auto* Blades=Player?Player->FindComponentByClass<URuneOrbBladesComponent>():nullptr;
        const bool Ready=Blades&&Blades->SwordEquipped();
        Fraction=Blades?Blades->CooldownFraction():0.f;
        Remaining=Blades?Blades->CooldownRemaining():0.f;
        Dim=!Ready||Fraction>0.f;
        if(!Ready)Message=TEXT("需符文长剑");
        else if(Blades->IsOrbitActive())
        {
            Message=TEXT("待发射");
            Count->SetText(FText::AsNumber(Blades->AvailableBladeCount()));
            bGoldPrepared=true;
        }
    }
    else if(!Binding.ItemDefinition.IsEmpty())
    {
        // 背包+夹层合并计数：槽位显示同类消耗品总数；消耗目标由 ResolveQuickItem 优先取背包堆。
        const int64 Quantity=Model->QuickItemCount(Index);Count->SetText(FText::FromString(FString::Printf(TEXT("%lld"),Quantity)));Count->SetColorAndOpacity(Quantity>0?ColdSteelUI::Success:ColdSteelUI::Danger);Dim=Quantity==0;
        if(Item&&Item->Definition==TEXT("mineral_water"))Count->SetText(FText::FromString(FString::Printf(TEXT("%d/2"),FMath::Clamp(int32(ColdSteelInventory::Number(*Item,TEXT("remainingUses"),2)),1,2))));
        if(Item&&Item->Cooldown>0){Remaining=Item->Cooldown;Fraction=FMath::Clamp(Remaining/FMath::Max(.1f,float(ColdSteelInventory::Number(*Item,TEXT("useCooldown")))),0.f,1.f);}
    }
    if(Remaining>0)Message=FString::Printf(TEXT("%.1f"),Remaining);
    State->SetFont(Remaining>0?ColdSteelUI::NumberFont(9/ColdSteelUI::PixelScale(this),true):ColdSteelUI::TextFont(9/ColdSteelUI::PixelScale(this)));
    State->SetText(FText::FromString(Message));
    // Explicit receipts distinguish a successful reduction from normal countdown,
    // passive cooldown acceleration, and a slot/element being rebound.
    const FName CooldownSkill=Binding.Skill==TEXT("elementalArrow")?ElementalArrow::Spell(SelectedElement):Binding.Skill;
    uint32 ReductionRevision=Model->CooldownReductionRevision(CooldownSkill);
    if(Binding.Skill==TEXT("runeBlades"))
    {
        const auto* Player=GetOwningPlayerPawn();
        const auto* Blades=Player?Player->FindComponentByClass<URuneOrbBladesComponent>():nullptr;
        ReductionRevision=Blades?Blades->CooldownReductionRevision():0;
    }
    const bool Reduced=!BindingChanged&&ReductionRevision!=LastCooldownReductionRevision;
    const bool Finished=!BindingChanged&&CooldownFraction>0.f&&Fraction<=0.f;
    LastCooldownReductionRevision=ReductionRevision;
    if(BindingChanged)
    {
        CooldownFraction=DisplayedCooldownFraction=CooldownTransitionFrom=Fraction;
        CooldownTransitionElapsed=ColdSteelQuickSlotFX::MaskTransition;
        ActiveFlashDuration=ColdSteelQuickSlotFX::FlashDuration;FlashStrength=1.f;
        FlashElapsed=ActiveFlashDuration;ReadyFlash->SetRenderOpacity(0);
        CooldownMask->SetFraction(Fraction);
    }
    else if(Fraction!=CooldownFraction)
    {
        CooldownTransitionFrom=DisplayedCooldownFraction;CooldownFraction=Fraction;CooldownTransitionElapsed=0;
    }
    if(Finished||Reduced)
    {
        // Completion retains the stronger 0.6 s flash. A hit reduction uses the
        // same white eased pulse, shorter and softer; events coalesce per refresh.
        ActiveFlashDuration=Finished?ColdSteelQuickSlotFX::FlashDuration:.24f;
        FlashStrength=Finished?1.f:.55f;
        FlashElapsed=0.f;
        ReadyFlash->SetRenderOpacity(FlashStrength*ColdSteelQuickSlotFX::FlashOpacity(0.f));
    }
    // Availability darkening is separate from CD; the black mask carries cooling.
    Icon->SetColorAndOpacity(Dim?FLinearColor(.55f,.55f,.55f,1):FLinearColor::White);
    FallbackIcon->SetRenderOpacity(Dim?.55f:1.f);
}
int32 UColdSteelQuickSlot::NativePaint(const FPaintArgs& Args,const FGeometry& Geometry,const FSlateRect& Clip,FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,bool Enabled) const
{
    const int32 Result=Super::NativePaint(Args,Geometry,Clip,Elements,Layer,Style,Enabled);
    if(!bGoldHighlighted)return Result;
    const float U=1.f/ColdSteelUI::PixelScale(this);
    const auto Brush=ColdSteelUI::RoundedBrush(FLinearColor::Transparent,6*U,ColdSteelUI::HUDGoldLight,1.5f*U);
    // MakeBox takes the fill tint explicitly; style tint alone paints a white
    // box over the icon for the entire prepared / hover / key-held highlight.
    FSlateDrawElement::MakeBox(Elements,Result+1,Geometry.ToPaintGeometry(),&Brush,ESlateDrawEffect::None,
        Brush.GetTint(Style)*Style.GetColorAndOpacityTint());
    return Result+1;
}

FReply UColdSteelQuickSlot::NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent& E)
{
    // 专属槽只读：不响应按下捕获，也就不会进入拖动流程。
    if(!FixedSkill.IsNone())return FReply::Unhandled();
    if(E.GetEffectingButton()!=EKeys::LeftMouseButton||!HUD.IsValid())return FReply::Unhandled();
    const auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(Model->QuickBinding(Index).IsEmpty())return FReply::Handled();
    ColdSteelUIAudio::Play(this,ColdSteelUIAudio::ECue::Slot);
    return FReply::Handled().CaptureMouse(TakeWidget()).DetectDrag(TakeWidget(),EKeys::LeftMouseButton);
}
FReply UColdSteelQuickSlot::NativeOnMouseButtonUp(const FGeometry&,const FPointerEvent&)
{return FReply::Handled().ReleaseMouseCapture();}
void UColdSteelQuickSlot::NativeOnDragDetected(const FGeometry&,const FPointerEvent& E,UDragDropOperation*& Out)
{
    if(!FixedSkill.IsNone())return;
    if(HUD.IsValid())Out=HUD->StartQuickDrag(NAME_None,Index,&Icon->GetBrush(),E.GetScreenSpacePosition());
}
bool UColdSteelQuickSlot::NativeOnDragOver(const FGeometry&,const FDragDropEvent& E,UDragDropOperation* Operation)
{
    if(!FixedSkill.IsNone())return false;
    if(!HUD.IsValid())return false;
    if(auto* D=Cast<UColdSteelQuickDrag>(Operation)){HUD->UpdateQuickDrag(D,E.GetScreenSpacePosition());return true;}
    if(auto* D=Cast<UColdSteelItemDrag>(Operation)){HUD->UpdateInventoryDrag(D,E.GetScreenSpacePosition());return true;}
    return false;
}
bool UColdSteelQuickSlot::NativeOnDrop(const FGeometry&,const FDragDropEvent&,UDragDropOperation* Operation)
{
    if(!FixedSkill.IsNone())return false;
    if(!HUD.IsValid())return false;
    if(auto* D=Cast<UColdSteelQuickDrag>(Operation))
    {
        const bool bDropped=HUD->DropQuickDrag(D,Index);
        if(bDropped)ColdSteelUIAudio::Play(this,ColdSteelUIAudio::ECue::SlotDrop);
        return bDropped;
    }
    if(auto* D=Cast<UColdSteelItemDrag>(Operation))
    {
        const bool bDropped=HUD->DropInventoryOnQuickBar(D,Index);
        if(bDropped)ColdSteelUIAudio::Play(this,ColdSteelUIAudio::ECue::SlotDrop);
        return bDropped;
    }
    return false;
}
