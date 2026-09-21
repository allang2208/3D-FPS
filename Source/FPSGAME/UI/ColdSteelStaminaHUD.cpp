#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelResourceMeter.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/ProgressBar.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"
#include "../Weapons/RuneSwordComponent.h"

void UColdSteelHUDWidget::BuildStamina(UCanvasPanel* Root)
{
    auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();Row->SetVisibility(ESlateVisibility::HitTestInvisible);
    StaminaSlot=Root->AddChildToCanvas(Row);StaminaSlot->SetAnchors(FAnchors(.5f,1));StaminaSlot->SetAlignment(FVector2D(.5f,1));StaminaSlot->SetZOrder(29);
    StaminaMeterSize=WidgetTree->ConstructWidget<USizeBox>();
    auto* MeterSlot=Row->AddChildToHorizontalBox(StaminaMeterSize);MeterSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));MeterSlot->SetVerticalAlignment(VAlign_Center);
    StaminaMeter=WidgetTree->ConstructWidget<UColdSteelResourceMeter>();StaminaMeterSize->SetContent(StaminaMeter);StaminaMeter->SetStaminaValue(0);
    StaminaValue=WidgetTree->ConstructWidget<UTextBlock>();StaminaValue->SetJustification(ETextJustify::Right);StaminaValue->SetAutoWrapText(false);
    StaminaValue->SetShadowOffset(FVector2D(1,1));StaminaValue->SetShadowColorAndOpacity(FLinearColor(0,0,0,.8f));
    Row->AddChildToHorizontalBox(StaminaValue)->SetVerticalAlignment(VAlign_Center);
    DashAttackReadyText=WidgetTree->ConstructWidget<UTextBlock>();
    DashAttackReadyText->SetJustification(ETextJustify::Center);
    DashAttackReadyText->SetShadowOffset(FVector2D(1,1));DashAttackReadyText->SetShadowColorAndOpacity(FLinearColor(0,0,0,.8f));
    auto* DashSlot=Root->AddChildToCanvas(DashAttackReadyText);
    DashSlot->SetAnchors(FAnchors(.5f,1));DashSlot->SetAlignment(FVector2D(.5f,1));DashSlot->SetZOrder(29);
    DashAttackReadyText->SetVisibility(ESlateVisibility::Collapsed);
    UpdateStaminaLayout(GetCachedGeometry());RefreshStamina();
}
void UColdSteelHUDWidget::UpdateStaminaLayout(const FGeometry& Geometry)
{
    if(!StaminaSlot)return;
    const float S=ColdSteelUI::PixelScale(this);
    FVector2D View=Geometry.GetLocalSize();if(View.X<100)View=UWidgetLayoutLibrary::GetViewportSize(this)/S;
    if(View.X<100)return;
    const float HotbarHeight=HotbarCanvasSlot&&HotbarCanvasSlot->Content?HotbarCanvasSlot->Content->GetDesiredSize().Y:66/S;
    const float Bottom=HotbarCanvasSlot?-HotbarCanvasSlot->GetPosition().Y:12/S;
    StaminaSlot->SetPosition(FVector2D(0,-Bottom-FMath::Max(HotbarHeight,66/S)-10/S));
    if(DashAttackReadyText)
    {
        auto* Pawn=GetOwningPlayerPawn();const auto* Sword=Pawn?Pawn->FindComponentByClass<URuneSwordComponent>():nullptr;
        const float Ready=Sword?Sword->DashReadyFraction():0.f;
        DashAttackReadyText->SetVisibility(Ready>0.f?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        const FText Hint=FText::FromString(Ready>=1.f?TEXT("冲刺攻击就绪 · 左键"):FString::Printf(TEXT("冲刺攻击准备  %.0f%%"),Ready*100.f));
        if(!DashAttackReadyText->GetText().EqualTo(Hint))DashAttackReadyText->SetText(Hint);
        DashAttackReadyText->SetColorAndOpacity(Ready>=1.f?ColdSteelUI::TextPrimary:ColdSteelUI::TextSecondary);
        DashAttackReadyText->SetFont(ColdSteelUI::TextFont(14*.75f/S));
        if(auto* DashCanvasSlot=Cast<UCanvasPanelSlot>(DashAttackReadyText->Slot))
        {DashCanvasSlot->SetPosition(StaminaSlot->GetPosition()+FVector2D(0,-25/S));DashCanvasSlot->SetSize(FVector2D(FMath::Min(360.f/S,FMath::Max(1.f,View.X-24/S)),22/S));}
    }
    if(StaminaLayoutView.Equals(View,.1f)&&FMath::IsNearlyEqual(S,StaminaLayoutScale,.0001f))return;
    StaminaLayoutView=View;StaminaLayoutScale=S;
    StaminaSlot->SetSize(FVector2D(FMath::Min(360.f/S,FMath::Max(1.f,View.X-24/S)),22/S));
    StaminaValue->SetFont(ColdSteelUI::NumberFont(16*.75f/S));
    StaminaMeterSize->SetHeightOverride(9/S);Cast<UHorizontalBoxSlot>(StaminaValue->Slot)->SetPadding(FMargin(10/S,0,0,0));
}
void UColdSteelHUDWidget::RefreshStamina()
{
    if(!StatusModel&&GetGameInstance())StatusModel=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!StaminaMeter||!StatusModel)return;
    const float Current=StatusModel->Stamina(),Max=StatusModel->MaxStamina(),Ratio=Current/FMath::Max(1.f,Max);
    StaminaMeter->SetStaminaValue(Ratio);
    const FString Value=FString::Printf(TEXT("%.1f / %.0f"),Current,Max);
    const FText Text=FText::FromString(Value);if(!StaminaValue->GetText().EqualTo(Text))StaminaValue->SetText(Text);
    StaminaValue->SetColorAndOpacity(Ratio<=.25f?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
    SetCharacterValue(TEXT("stamina"),Value);if(StaminaSheetBar)StaminaSheetBar->SetPercent(Ratio);
}
