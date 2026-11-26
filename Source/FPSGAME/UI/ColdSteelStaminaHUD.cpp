#include "ColdSteelHUDWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "../WorldGeneration/VillageSiegeControl.h"
#include "../Movement/HorseRiderComponent.h"
#include "../Movement/StableRidingHorse.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelResourceMeter.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/GridPanel.h"
#include "Components/GridSlot.h"
#include "Components/SizeBox.h"
#include "Components/ScaleBox.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/ProgressBar.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/KukriDecisiveComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/WeaponBipodDeploymentComponent.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"

namespace
{
FString FormatStamina(float Current,float Maximum)
{
    return FString::Printf(TEXT("%.1f / %.0f"),Current,Maximum);
}
}

void UColdSteelHUDWidget::BuildStamina(UCanvasPanel* Root)
{
    auto* Tracks=WidgetTree->ConstructWidget<UGridPanel>();
    Tracks->SetVisibility(ESlateVisibility::HitTestInvisible);
    Tracks->SetColumnFill(0,1.f);
    Tracks->SetRowFill(1,1.f);
    StaminaSlot=Root->AddChildToCanvas(Tracks);
    StaminaSlot->SetAnchors(FAnchors(.5f,1));StaminaSlot->SetAlignment(FVector2D(.5f,1));StaminaSlot->SetZOrder(29);

    // Both tracks share a flexible meter column and the width of the widest number.
    const auto AddTrack=[&](int32 Row,TObjectPtr<USizeBox>& TrackSize,TObjectPtr<UColdSteelResourceMeter>& Meter,TObjectPtr<UTextBlock>& Value)
    {
        TrackSize=WidgetTree->ConstructWidget<USizeBox>();
        auto* TrackSlot=Tracks->AddChildToGrid(TrackSize,Row,0);
        TrackSlot->SetHorizontalAlignment(HAlign_Fill);
        TrackSlot->SetVerticalAlignment(VAlign_Center);
        Meter=WidgetTree->ConstructWidget<UColdSteelResourceMeter>();
        TrackSize->SetContent(Meter);

        Value=WidgetTree->ConstructWidget<UTextBlock>();
        Value->SetJustification(ETextJustify::Right);
        Value->SetAutoWrapText(false);
        Value->SetShadowOffset(FVector2D(1,1));
        Value->SetShadowColorAndOpacity(FLinearColor(0,0,0,.8f));
        auto* NumberSlot=Tracks->AddChildToGrid(Value,Row,1);
        NumberSlot->SetHorizontalAlignment(HAlign_Right);
        NumberSlot->SetVerticalAlignment(VAlign_Center);
    };
    AddTrack(0,MountStaminaMeterSize,MountStaminaMeter,MountStaminaText);
    AddTrack(1,StaminaMeterSize,StaminaMeter,StaminaValue);
    MountStaminaMeterSize->SetVisibility(ESlateVisibility::Collapsed);
    MountStaminaText->SetVisibility(ESlateVisibility::Collapsed);
    DisplayedStaminaMount.Reset();
    StaminaLayoutScale=0.f;

    auto* Hints=WidgetTree->ConstructWidget<UVerticalBox>();Hints->SetVisibility(ESlateVisibility::HitTestInvisible);
    BottomHintsSlot=Root->AddChildToCanvas(Hints);
    BottomHintsSlot->SetAnchors(FAnchors(.5f,1));BottomHintsSlot->SetAlignment(FVector2D(.5f,1));BottomHintsSlot->SetZOrder(29);
    BottomHintRows.Reset();
    const auto AddHint=[&]()
    {
        auto* Height=WidgetTree->ConstructWidget<USizeBox>();
        Hints->AddChildToVerticalBox(Height)->SetHorizontalAlignment(HAlign_Fill);BottomHintRows.Add(Height);
        auto* Fit=WidgetTree->ConstructWidget<UScaleBox>();Fit->SetStretch(EStretch::ScaleToFit);Fit->SetStretchDirection(EStretchDirection::DownOnly);Height->SetContent(Fit);
        auto* Text=WidgetTree->ConstructWidget<UTextBlock>();Fit->SetContent(Text);
        Text->SetJustification(ETextJustify::Center);Text->SetAutoWrapText(false);
        Text->SetShadowOffset(FVector2D(1,1));Text->SetShadowColorAndOpacity(FLinearColor(0,0,0,.8f));
        Text->SetVisibility(ESlateVisibility::Collapsed);Height->SetVisibility(ESlateVisibility::Collapsed);return Text;
    };
    // Fixed top-to-bottom order. Collapsed rows relinquish their space; the container grows upward.
    CaptureEscapeHint=AddHint();DecisiveMainHint=AddHint();DecisiveOffhandHint=AddHint();DashAttackReadyText=AddHint();
    DisplayedMountStamina=FIntPoint(-1,-1);
    CaptureEscapeHint->SetColorAndOpacity(ColdSteelUI::Warning);
    DisplayedCaptureEscapeHits=INDEX_NONE;
    UpdateStaminaLayout(GetCachedGeometry());RefreshStamina();
}
void UColdSteelHUDWidget::UpdateStaminaLayout(const FGeometry& Geometry)
{
    if(!StaminaSlot)return;
    const float S=ColdSteelUI::PixelScale(this);
    FVector2D View=Geometry.GetLocalSize();if(View.X<100)View=UWidgetLayoutLibrary::GetViewportSize(this)/S;
    if(View.X<100)return;
    const float HotbarHeight=HotbarCanvasSlot?HotbarCanvasSlot->GetSize().Y:66/S;
    const float Bottom=HotbarCanvasSlot?-HotbarCanvasSlot->GetPosition().Y:12/S;
    StaminaSlot->SetPosition(FVector2D(0,-Bottom-FMath::Max(HotbarHeight,66/S)-10/S));
    const auto* HintPawn=GetOwningPlayerPawn();
    const auto* HintHealth=HintPawn?HintPawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const bool ShowCombatHints=HintPawn&&!(HintHealth&&HintHealth->IsDead())&&!bInventoryOpen&&!bExternalDrawerOpen;
    if(DashAttackReadyText)
    {
        // Share the existing action hint row; read actual deployment state,
        // without running support traces or a second progress timer in the HUD.
        auto* Pawn=GetOwningPlayerPawn();const auto* Character=Cast<AFPSGAMECharacter>(Pawn);
        const auto* Bipod=Character?Character->BipodDeployment.Get():nullptr;
        const auto State=Bipod?Bipod->GetDeploymentState():EWeaponBipodDeploymentState::Unavailable;
        FString ActionHint;bool Complete=false;float PreparationProgress=0.f;
        const float CowboyHintOpacity=Character?Character->GetCowboyReloadHintOpacity():0.f;
        const auto* Electric=Pawn?Pawn->FindComponentByClass<UFPSElectricMagicComponent>():nullptr;
        const bool bChargingLance=Electric&&Electric->IsCharging();
        const auto* PC=GetOwningPlayer<AFPSGAMEPlayerController>();
        const auto* Siege=PC?PC->GetSiegeControl():nullptr;
        const auto* Station=Siege?Siege->OperatedStation():nullptr;
        if(Station)
        {
            if(Station->GetReloadProgress(PreparationProgress))
            {
                const TCHAR* Name=Station->IsTrebuchet()?TEXT("投石机"):TEXT("弩炮");
                Complete=PreparationProgress>=1.f;
                ActionHint=Complete?FString::Printf(TEXT("%s装填完成"),Name):
                    FString::Printf(TEXT("%s装填  %d%%"),Name,FMath::FloorToInt(PreparationProgress*100.f));
            }
        }
        else if(bChargingLance)
        {
            PreparationProgress=Electric->LanceChargeFraction();Complete=PreparationProgress>=1.f;
            ActionHint=Complete?TEXT("已充能完毕"):FString::Printf(TEXT("雷枪充能  %d%%"),FMath::FloorToInt(PreparationProgress*100.f));
        }
        else if(CowboyHintOpacity>0.f)
        {
            ActionHint=TEXT("已自动换弹");Complete=true;PreparationProgress=1.f;
        }
        else if(State==EWeaponBipodDeploymentState::Deploying || State==EWeaponBipodDeploymentState::Deployed)
        {
            Complete=State==EWeaponBipodDeploymentState::Deployed;
            PreparationProgress=Complete?1.f:FMath::Clamp(Bipod->GetDeploymentBlend(),0.f,1.f);
            const int32 Percent=FMath::Clamp(FMath::FloorToInt(Bipod->GetDeploymentBlend()*100.f),0,99);
            ActionHint=Complete?TEXT("已部署脚架"):FString::Printf(TEXT("部署脚架  %d%%"),Percent);
        }
        else
        {
            const auto* Sword=Pawn?Pawn->FindComponentByClass<URuneSwordComponent>():nullptr;
            const auto* Tool=Pawn?Pawn->FindComponentByClass<UProductionToolComponent>():nullptr;
            const auto* HeavyKukri=Pawn?Pawn->FindComponentByClass<UKukriWeaponComponent>():nullptr;
            const float Charge=FMath::Clamp(Tool&&Tool->IsEquipped()?Tool->HeavyChargeFraction():
                HeavyKukri&&HeavyKukri->IsEquipped()?HeavyKukri->HeavyChargeFraction():Sword?Sword->HeavyChargeFraction():0.f,0.f,1.f);
            if(Charge>0.f)
            {
                Complete=Charge>=1.f;PreparationProgress=Charge;
                const int32 Percent=FMath::Clamp(FMath::FloorToInt(Charge*100.f),0,99);
                ActionHint=Complete?TEXT("重击蓄力完成 · 100%")
                    :FString::Printf(TEXT("重击蓄力  %d%%"),Percent);
            }
            else
            {
                const auto* Kukri=Pawn?Pawn->FindComponentByClass<UKukriWeaponComponent>():nullptr;
                const float Ready=Tool&&Tool->IsEquipped()?Tool->DashReadyFraction():
                    Kukri&&Kukri->IsEquipped()?Kukri->DashReadyFraction():Sword?Sword->DashReadyFraction():0.f;
                Complete=Ready>=1.f;PreparationProgress=FMath::Clamp(Ready,0.f,1.f);
                if(Ready>0.f)
                    ActionHint=Complete
                        ?(Character&&Character->IsSprinting()?TEXT("冲刺攻击就绪 · 左键"):TEXT("冲刺攻击就绪 · 保持 Shift"))
                        :FString::Printf(TEXT("冲刺攻击准备  %.0f%%"),Ready*100.f);
            }
        }
        DashAttackReadyText->SetVisibility(!ShowCombatHints||ActionHint.IsEmpty()?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
        DashAttackReadyText->SetRenderOpacity(!Station&&!bChargingLance&&CowboyHintOpacity>0.f?CowboyHintOpacity:1.f);
        const FText Hint=FText::FromString(ActionHint);
        if(!DashAttackReadyText->GetText().EqualTo(Hint))DashAttackReadyText->SetText(Hint);
        // Shared readiness ramp: red -> yellow -> blue -> green at equal progress intervals.
        DashAttackReadyText->SetColorAndOpacity(ColdSteelUI::ActionProgressColor(PreparationProgress));
        DashAttackReadyText->SetFont(ColdSteelUI::TextFont(16*.75f/S));
    }
    const auto* Pendant=HintPawn?HintPawn->FindComponentByClass<UKukriDecisiveComponent>():nullptr;
    for(int32 Hand=0;Hand<2;++Hand)
    {
        auto* Text=Hand==0?DecisiveMainHint.Get():DecisiveOffhandHint.Get();if(!Text)continue;
        float Progress=0.f;
        const bool Show=ShowCombatHints&&Pendant&&Pendant->PreparationForHand(Hand!=0,Progress);
        Text->SetVisibility(Show?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        if(!Show)continue;
        const TCHAR* HandName=Hand==0?TEXT("主手"):TEXT("副手");
        const FText Hint=FText::FromString(Progress>=1.f
            ?FString::Printf(TEXT("%s · 藏锋就绪 · 一决待发"),HandName)
            :FString::Printf(TEXT("%s · 藏锋蓄势  %d%%"),HandName,FMath::Clamp(FMath::FloorToInt(Progress*100.f),0,99)));
        if(!Text->GetText().EqualTo(Hint))Text->SetText(Hint);
        Text->SetColorAndOpacity(FMath::Lerp(FLinearColor(.25f,.75f,.85f),FLinearColor(.3f,.56f,1.f),Progress));
        Text->SetFont(ColdSteelUI::TextFont(16*.75f/S));
    }
    if(CaptureEscapeHint)
    {
        const auto* Pawn=GetOwningPlayerPawn();
        const auto* Capture=Pawn?Pawn->FindComponentByClass<UBoundCongregateCaptureComponent>():nullptr;
        const bool Show=ShowCombatHints&&Capture&&Capture->IsHeld();
        CaptureEscapeHint->SetVisibility(Show?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        if(Show)
        {
            const int32 Hits=Capture->GetEscapeHits();
            DisplayedCaptureEscapeHits=Hits;
            const FText Hint=FText::Format(NSLOCTEXT("ColdSteelHUD","TentacleEscapeHintV30",
                "缠绕 · F 挣脱 {0}/{1} · 射击触手 {2}/{3}"),FText::AsNumber(Hits),
                FText::AsNumber(UBoundCongregateCaptureComponent::RequiredEscapeHits),
                FText::AsNumber(FMath::CeilToInt(Capture->GetTentacleHealth())),
                FText::AsNumber(FMath::CeilToInt(Capture->GetTentacleMaxHealth())));
            if(!CaptureEscapeHint->GetText().EqualTo(Hint))CaptureEscapeHint->SetText(Hint);
            CaptureEscapeHint->SetFont(ColdSteelUI::TextFont(18*.75f/S));
        }
        else DisplayedCaptureEscapeHits=INDEX_NONE;
    }
    auto* Mount=ShowCombatHints?UHorseRiderComponent::MountOf(HintPawn):nullptr;
    const bool ShowMount=Mount!=nullptr;
    if(ShowMount!=(MountStaminaMeterSize->GetVisibility()!=ESlateVisibility::Collapsed))
    {
        const auto MountRowVisibility=ShowMount?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed;
        MountStaminaMeterSize->SetVisibility(MountRowVisibility);
        MountStaminaText->SetVisibility(MountRowVisibility);
        CastChecked<UGridPanel>(MountStaminaText->GetParent())->SetRowFill(0,ShowMount?1.f:0.f);
        DisplayedMountStamina=FIntPoint(-1,-1);
    }
    if(Mount)
    {
        if(DisplayedStaminaMount.Get()!=Mount || DisplayedMountStamina.X<0)
        {
            MountStaminaMeter->ResetAnimation();
            DisplayedStaminaMount=Mount;
        }
        const float Current=Mount->GetStamina(),Maximum=Mount->GetMaximumStamina();
        const float Ratio=Current/FMath::Max(1.f,Maximum);
        MountStaminaMeter->SetSemanticValue(Ratio,ColdSteelUI::MountStamina,ColdSteelUI::MountStaminaDeep,false);
        const FIntPoint Numbers(FMath::RoundToInt(Current*10.f),FMath::RoundToInt(Maximum));
        if(DisplayedMountStamina!=Numbers)
        {
            DisplayedMountStamina=Numbers;
            MountStaminaText->SetText(FText::FromString(FormatStamina(Current,Maximum)));
        }
        const FLinearColor& NumberColor=Ratio<=.25f?ColdSteelUI::Warning:ColdSteelUI::TextPrimary;
        if(MountStaminaText->GetColorAndOpacity().GetSpecifiedColor()!=NumberColor)
            MountStaminaText->SetColorAndOpacity(NumberColor);
    }
    const UTextBlock* HintTexts[]={CaptureEscapeHint.Get(),DecisiveMainHint.Get(),DecisiveOffhandHint.Get(),DashAttackReadyText.Get()};
    int32 VisibleRows=0;
    for(int32 I=0;I<BottomHintRows.Num();++I)
    {
        auto* Row=BottomHintRows[I].Get();
        const bool Visible=HintTexts[I]&&HintTexts[I]->GetVisibility()!=ESlateVisibility::Collapsed;
        Row->SetVisibility(Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        Row->SetHeightOverride(22/S);Cast<UVerticalBoxSlot>(Row->Slot)->SetPadding(FMargin(0,0,0,6/S));
        VisibleRows+=Visible?1:0;
    }
    const float TrackHeight=22.f/S;
    const FVector2D TracksSize(FMath::Min(360.f/S,FMath::Max(1.f,View.X-24/S)),TrackHeight*(ShowMount?2.f:1.f));
    if(StaminaSlot->GetSize()!=TracksSize)StaminaSlot->SetSize(TracksSize);
    if(BottomHintsSlot)
    {
        BottomHintsSlot->SetPosition(StaminaSlot->GetPosition()-FVector2D(0,TracksSize.Y+3.f/S));
        BottomHintsSlot->SetSize(FVector2D(FMath::Min(600.f/S,FMath::Max(1.f,View.X-24/S)),VisibleRows*28/S));
    }
    if(StaminaLayoutView.Equals(View,.1f)&&FMath::IsNearlyEqual(S,StaminaLayoutScale,.0001f))return;
    StaminaLayoutView=View;StaminaLayoutScale=S;
    const auto NumberFont=ColdSteelUI::NumberFont(16*.75f/S);
    for(auto* Value:{StaminaValue.Get(),MountStaminaText.Get()})
    {
        Value->SetFont(NumberFont);
        CastChecked<UGridSlot>(Value->Slot)->SetPadding(FMargin(10/S,0,0,0));
    }
    for(auto* Track:{StaminaMeterSize.Get(),MountStaminaMeterSize.Get()})Track->SetHeightOverride(9/S);
}
void UColdSteelHUDWidget::RefreshStamina()
{
    if(!StatusModel&&GetGameInstance())StatusModel=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!StaminaMeter||!StatusModel)return;
    const float Current=StatusModel->Stamina(),Max=StatusModel->MaxStamina(),Ratio=Current/FMath::Max(1.f,Max);
    StaminaMeter->SetStaminaValue(Ratio);
    const FString Value=FormatStamina(Current,Max);
    const FText Text=FText::FromString(Value);if(!StaminaValue->GetText().EqualTo(Text))StaminaValue->SetText(Text);
    StaminaValue->SetColorAndOpacity(Ratio<=.25f?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
    SetCharacterValue(TEXT("stamina"),Value);SetAnimatedBarValue(StaminaSheetBar,Ratio);
}
