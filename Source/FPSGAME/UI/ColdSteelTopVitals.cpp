#include "ColdSteelHUDWidget.h"
#include "ColdSteelResourceMeter.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"

void UColdSteelHUDWidget::BuildTopVitals(UCanvasPanel* Root)
{
    TopVitalsSurface=MakeSurface(ColdSteelUI::GlassTint,ReferenceUnits(12),ColdSteelUI::Border,ReferenceUnits(1));
    TopVitalsSurface->SetVisibility(ESlateVisibility::HitTestInvisible);
    TopVitalsSurface->SetPadding(FMargin(ReferenceUnits(16),ReferenceUnits(8)));
    auto* SurfaceSlot=Root->AddChildToCanvas(TopVitalsSurface);SurfaceSlot->SetAnchors(FAnchors(.5f,0));SurfaceSlot->SetAlignment(FVector2D(.5f,0));SurfaceSlot->SetPosition(FVector2D(0,ReferenceUnits(12)));SurfaceSlot->SetAutoSize(true);
    auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();TopVitalsSurface->SetContent(Row);
    auto AddResource=[&](const TCHAR* Caption,TObjectPtr<UColdSteelResourceMeter>& Meter,TObjectPtr<UTextBlock>& Value){
        auto* Width=WidgetTree->ConstructWidget<USizeBox>();Width->SetWidthOverride(ReferenceUnits(160));Row->AddChildToHorizontalBox(Width)->SetPadding(FMargin(0,0,ReferenceUnits(16),0));
        auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Width->SetContent(Column);
        auto* Label=MakeReferenceText(Caption,14,ColdSteelUI::TextSecondary);Label->SetJustification(ETextJustify::Center);Column->AddChildToVerticalBox(Label);
        auto* Height=WidgetTree->ConstructWidget<USizeBox>();Height->SetHeightOverride(ReferenceUnits(9));Column->AddChildToVerticalBox(Height)->SetPadding(FMargin(0,ReferenceUnits(3),0,ReferenceUnits(3)));
        Meter=WidgetTree->ConstructWidget<UColdSteelResourceMeter>();Height->SetContent(Meter);
        Value=MakeReferenceText(TEXT("— / —"),14,ColdSteelUI::TextPrimary,true);Value->SetJustification(ETextJustify::Center);Value->SetAutoWrapText(false);Column->AddChildToVerticalBox(Value);
    };
    AddResource(TEXT("生命"),TopHealthMeter,TopHealthValue);AddResource(TEXT("魔法"),TopManaMeter,TopManaValue);TopManaMeter->SetValue(0,true);
    auto* Width=WidgetTree->ConstructWidget<USizeBox>();Width->SetMinDesiredWidth(ReferenceUnits(52));Row->AddChildToHorizontalBox(Width)->SetVerticalAlignment(VAlign_Center);
    auto* LevelColumn=WidgetTree->ConstructWidget<UVerticalBox>();Width->SetContent(LevelColumn);
    auto* Label=MakeReferenceText(TEXT("等级"),14,ColdSteelUI::TextSecondary);Label->SetJustification(ETextJustify::Center);LevelColumn->AddChildToVerticalBox(Label);
    TopLevelValue=MakeReferenceText(TEXT("—"),20,ColdSteelUI::Accent,true,true);TopLevelValue->SetJustification(ETextJustify::Center);LevelColumn->AddChildToVerticalBox(TopLevelValue);
    RefreshTopVitals();
}

void UColdSteelHUDWidget::RefreshTopVitals()
{
    if(!TopHealthMeter||!TopManaMeter||!TopLevelValue)return;
    if(!StatusModel&&GetGameInstance())StatusModel=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto Update=[](UColdSteelResourceMeter* Meter,UTextBlock* Label,float Value,float Maximum,bool Mana){
        const bool Valid=FMath::IsFinite(Value)&&FMath::IsFinite(Maximum)&&Maximum>0;
        const float Current=Valid?FMath::Clamp(Value,0.f,Maximum):0.f;
        const float Ratio=Valid?Current/Maximum:0.f;Meter->SetValue(Ratio,Mana);
        const FText Text=FText::FromString(Valid?FString::Printf(TEXT("%.0f / %.0f"),Current,Maximum):TEXT("— / —"));if(!Label->GetText().EqualTo(Text))Label->SetText(Text);
        Label->SetColorAndOpacity(!Mana&&Valid&&Ratio<=.25f?ColdSteelUI::Danger:ColdSteelUI::TextPrimary);
    };
    const auto* Pawn=GetOwningPlayerPawn();const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    Update(TopHealthMeter,TopHealthValue,Health?Health->Health:0,Health?Health->MaxHealth:0,false);
    Update(TopManaMeter,TopManaValue,StatusModel?StatusModel->Mana():0,StatusModel?StatusModel->Derived(TEXT("maxMp")):0,true);
    const FText Level=FText::FromString(StatusModel?FString::FromInt(StatusModel->Level):TEXT("—"));if(!TopLevelValue->GetText().EqualTo(Level))TopLevelValue->SetText(Level);
}
