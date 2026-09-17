#include "ColdSteelQuickSlot.h"
#include "../Weapons/RuneSwordComponent.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelQuickDrag.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelUIStyle.h"
#include "SColdSteelCooldownMask.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSIceSpikeComponent.h"
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

void UColdSteelQuickSlot::Configure(UColdSteelHUDWidget* Owner,int32 SlotIndex,FName InFixedSkill)
{
    HUD=Owner;Index=SlotIndex;FixedSkill=InFixedSkill;
    // 专属槽的键位标注与固定技能一起给定（如 F · 快速进战），不走混放键位表。
    FixedKeyLabel=FixedSkill.IsNone()?FString():TEXT("F");
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
        auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Value));
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
    Key=Text(FixedSkill.IsNone()?ColdSteelQuickBar::KeyLabel(Index):FixedKeyLabel);Key->SetFont(ColdSteelUI::NumberFont(9/Scale));Key->SetColorAndOpacity(ColdSteelUI::Accent);
    auto* K=Overlay->AddChildToOverlay(Key);K->SetHorizontalAlignment(HAlign_Right);K->SetVerticalAlignment(VAlign_Bottom);K->SetPadding(FMargin(0,0,4/Scale,2/Scale));
    Count=Text(TEXT(""));Count->SetFont(ColdSteelUI::NumberFont(9/Scale,true));auto* C=Overlay->AddChildToOverlay(Count);
    C->SetHorizontalAlignment(HAlign_Center);C->SetVerticalAlignment(VAlign_Top);C->SetPadding(FMargin(0,1/Scale,0,0));
    Refresh();
}

void UColdSteelQuickSlot::NativeTick(const FGeometry& Geometry,float DeltaTime)
{
    Super::NativeTick(Geometry,DeltaTime);
    BlinkElapsed=FMath::Fmod(BlinkElapsed+DeltaTime,ColdSteelQuickSlotFX::KeyPeriod);
    if(Key)Key->SetRenderOpacity(ColdSteelQuickSlotFX::KeyOpacity(BlinkElapsed));
    if(FlashElapsed<ColdSteelQuickSlotFX::FlashDuration)
    {
        FlashElapsed=FMath::Min(ColdSteelQuickSlotFX::FlashDuration,FlashElapsed+DeltaTime);
        ReadyFlash->SetRenderOpacity(ColdSteelQuickSlotFX::FlashOpacity(FlashElapsed));
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
        if(Displayed.Skill==TEXT("fireball"))
        {
            if(const auto* Ability=Player->FindComponentByClass<UFPSFireballComponent>())
            {Notice=Ability->IsHandOccupiedNotice();NoticeAlpha=Ability->HandNoticeAlpha();NoticeRise=Ability->HandNoticeRise();}
        }
        else if(Displayed.Skill==TEXT("iceSpike"))
        {
            if(const auto* Ability=Player->FindComponentByClass<UFPSIceSpikeComponent>())
            {Notice=Ability->IsHandOccupiedNotice();NoticeAlpha=Ability->HandNoticeAlpha();NoticeRise=Ability->HandNoticeRise();}
        }
    }
    if(State)
    {
        State->SetRenderOpacity(Notice?NoticeAlpha:1.f);
        State->SetRenderTranslation(FVector2D(0,Notice?-NoticeRise:0));
    }
}

void UColdSteelQuickSlot::Refresh()
{
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Model||!Icon)return;
    // 专属槽不读混放绑定，恒显固定技能；其余数据（图标、冷却、变暗）走同一条显示路径。
    const auto Binding=FixedSkill.IsNone()?Model->QuickBinding(Index):[&]{FColdSteelQuickBinding B;B.Skill=FixedSkill;return B;}();
    const auto* Item=Model->ResolveQuickItem(Index);
    const bool BindingChanged=!bLoaded||!(Binding==Displayed);
    if(BindingChanged)
    {
        bLoaded=true;Displayed=Binding;FString Path,Name;
        if(const auto* D=Model->QuickSkillDefinition(Binding.Skill)){Path=D->Icon;Name=D->Name;}
        else if(!Binding.ItemDefinition.IsEmpty())
        {const auto Template=Item?*Item:Model->CreateItem(Binding.ItemDefinition);Path=ColdSteelInventory::Text(Template,TEXT("ue_icon"));Name=ColdSteelInventory::Text(Template,TEXT("name"));}
        Texture=nullptr;
        if(!Path.IsEmpty())
        {
            if(auto* Found=Textures.Find(Path))Texture=*Found;
            else {Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Path);Textures.Add(Path,Texture);}
        }
        Icon->SetBrushFromTexture(Texture,true);Icon->SetVisibility(Texture?ESlateVisibility::HitTestInvisible:ESlateVisibility::Hidden);
        const float Pixels=Binding.Skill.IsNone()?40.f:48.f;
        IconFrame->SetWidthOverride(Pixels/ColdSteelUI::PixelScale(this));IconFrame->SetHeightOverride(Pixels/ColdSteelUI::PixelScale(this));
        FallbackIcon->SetVisibility(!Texture&&!Binding.IsEmpty()?ESlateVisibility::HitTestInvisible:ESlateVisibility::Hidden);
        const FString KeyText=FixedSkill.IsNone()?ColdSteelQuickBar::KeyLabel(Index):FixedKeyLabel;
        SetToolTipText(FText::FromString(FixedSkill.IsNone()?(Binding.IsEmpty()?FString::Printf(TEXT("%s · 拖入主动技能或消耗品"),*KeyText):
            FString::Printf(TEXT("%s · %s\n拖到空槽移动，拖到其他内容交换；拖出快捷栏解绑"),*Name,*KeyText)):
            FString::Printf(TEXT("%s · %s\n按 %s 直接触发；冷却结束后可用"),*KeyText,*Name,*KeyText)));
    }
    FString Message;float Fraction=0,Remaining=0;bool Dim=false;
    Count->SetText(FText::GetEmpty());
    if(Binding.Skill==TEXT("fireball"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<UFPSFireballComponent>():nullptr;
        if(Ability){Message=Ability->StatusText();Fraction=Ability->CooldownFraction();}
        // The refusal notice answers the press itself, so it outranks the countdown.
        if(Fraction>0&&!(Ability&&Ability->IsHandOccupiedNotice()))Remaining=Model->FireballCooldown();
        Dim=!Model->CanSpendMana(Model->FireballStats().ManaCost)&&(!Ability||(!Ability->IsPrepared()&&!Ability->IsFlying()));
    }
    else if(Binding.Skill==TEXT("iceSpike"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<UFPSIceSpikeComponent>():nullptr;
        if(Ability){Message=Ability->StatusText();Fraction=Ability->CooldownFraction();if(Ability->ActiveCount()>0)Count->SetText(FText::AsNumber(Ability->ActiveCount()));}
        // The refusal notice answers the press itself, so it outranks the countdown.
        if(Fraction>0&&!(Ability&&Ability->IsHandOccupiedNotice()))Remaining=Model->IceSpikeCooldown();
        Dim=!Model->CanSpendMana(Model->IceSpikeStats().ManaCost)&&(!Ability||Ability->ActiveCount()==0);
    }
    else if(Binding.Skill==TEXT("heavyStrike"))
    {
        const auto* Player=GetOwningPlayerPawn();const auto* Ability=Player?Player->FindComponentByClass<URuneSwordComponent>():nullptr;
        Dim=!Ability||!Ability->IsEquipped()||!Model->CanSpendStamina(Model->StaminaSettings().MeleeCost);
        if(!Ability||!Ability->IsEquipped())Message=TEXT("需近战");
        else if(Ability->HeavyChargeFraction()>0)Message=FString::Printf(TEXT("%.0f%%"),Ability->HeavyChargeFraction()*100);
        else if(Ability->IsBusy())Message=TEXT("动作中");
    }
    else if(Binding.Skill==TEXT("dodge"))
    {
        if(const auto* Player=GetOwningPlayerPawn<AFPSGAMECharacter>();Player&&Player->IsDodging())Message=TEXT("闪避");
        Dim=!Model->CanSpendStamina(Model->DodgeStaminaCost());
    }
    else if(Binding.Skill==TEXT("quickCombat"))
    {
        // 剑类或单持手枪：单手砸击只要求右手，双持时左手被副枪占用。
        const auto* Player=GetOwningPlayerPawn<AFPSGAMECharacter>();
        const bool bReady=(Player&&Player->IsPistolWeapon()&&!Player->IsDualWieldingPistols())
            ||(Player&&Player->FindComponentByClass<URuneSwordComponent>()&&Player->FindComponentByClass<URuneSwordComponent>()->IsEquipped());
        Fraction=Model->QuickCombatCooldownDuration()>0?Model->QuickCombatCooldown()/Model->QuickCombatCooldownDuration():0.f;
        // The equip hint outranks the countdown: an unusable slot explains why.
        if(bReady)Remaining=Model->QuickCombatCooldown();else Message=TEXT("需剑/枪");
        // Availability darkening mirrors the mask: unusable while cooling, or without a matching weapon.
        Dim=!bReady||Fraction>0.f;
    }
    else if(!Binding.ItemDefinition.IsEmpty())
    {
        const int64 Quantity=Item?Item->Count:0;Count->SetText(FText::FromString(FString::Printf(TEXT("%lld"),Quantity)));Count->SetColorAndOpacity(Quantity>0?ColdSteelUI::Success:ColdSteelUI::Danger);Dim=Quantity==0;
        if(Item&&Item->Cooldown>0){Remaining=Item->Cooldown;Fraction=FMath::Clamp(Remaining/FMath::Max(.1f,float(ColdSteelInventory::Number(*Item,TEXT("useCooldown")))),0.f,1.f);}
    }
    if(Remaining>0)Message=FString::Printf(TEXT("%.1f"),Remaining);
    State->SetFont(Remaining>0?ColdSteelUI::NumberFont(9/ColdSteelUI::PixelScale(this),true):ColdSteelUI::TextFont(9/ColdSteelUI::PixelScale(this)));
    State->SetText(FText::FromString(Message));
    if(BindingChanged)
    {
        CooldownFraction=DisplayedCooldownFraction=CooldownTransitionFrom=Fraction;
        CooldownTransitionElapsed=ColdSteelQuickSlotFX::MaskTransition;
        FlashElapsed=ColdSteelQuickSlotFX::FlashDuration;ReadyFlash->SetRenderOpacity(0);
        CooldownMask->SetFraction(Fraction);
    }
    else if(Fraction!=CooldownFraction)
    {
        if(CooldownFraction>0&&Fraction<=0)
        {
            FlashElapsed=0;ReadyFlash->SetRenderOpacity(ColdSteelQuickSlotFX::FlashOpacity(0));
        }
        CooldownTransitionFrom=DisplayedCooldownFraction;CooldownFraction=Fraction;CooldownTransitionElapsed=0;
    }
    // Availability darkening is separate from CD; the black mask carries cooling.
    Icon->SetColorAndOpacity(Dim?FLinearColor(.55f,.55f,.55f,1):FLinearColor::White);
    FallbackIcon->SetRenderOpacity(Dim?.55f:1.f);
}
FReply UColdSteelQuickSlot::NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent& E)
{
    // 专属槽只读：不响应按下捕获，也就不会进入拖动流程。
    if(!FixedSkill.IsNone())return FReply::Unhandled();
    if(E.GetEffectingButton()!=EKeys::LeftMouseButton||!HUD.IsValid())return FReply::Unhandled();
    const auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(Model->QuickBinding(Index).IsEmpty())return FReply::Handled();
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
    if(auto* D=Cast<UColdSteelQuickDrag>(Operation))return HUD->DropQuickDrag(D,Index);
    if(auto* D=Cast<UColdSteelItemDrag>(Operation))return HUD->DropInventoryOnQuickBar(D,Index);
    return false;
}
