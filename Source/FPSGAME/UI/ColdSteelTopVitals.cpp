#include "ColdSteelHUDWidget.h"
#include "ColdSteelResourceMeter.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelHUDLayout.h"
#include "ColdSteelWorldClock.h"
#include "../FPSWeatherManager.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/Border.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/GridPanel.h"
#include "Components/GridSlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/BackgroundBlur.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"

UTextBlock* UColdSteelHUDWidget::MakeTopHUDText(const FString& Text,float Pixels,const FLinearColor& Color,bool Numeric,bool Medium)
{
    auto* Label=WidgetTree->ConstructWidget<UTextBlock>();Label->SetText(FText::FromString(Text));Label->SetColorAndOpacity(Color);
    const float Points=Pixels*.75f/ColdSteelUI::PixelScale(this);
    Label->SetFont(Numeric?ColdSteelUI::NumberFont(Points,Medium):ColdSteelUI::TextFont(Points,Medium));
    TopHUDLabels.Add({Label,Pixels,Numeric,Medium});return Label;
}

void UColdSteelHUDWidget::BuildTopVitals(UCanvasPanel* Root)
{
    TopVitalsSurface=WidgetTree->ConstructWidget<UBorder>();FSlateBrush Empty;Empty.DrawAs=ESlateBrushDrawType::NoDrawType;TopVitalsSurface->SetBrush(Empty);
    TopVitalsSurface->SetVisibility(ESlateVisibility::HitTestInvisible);
    TopVitalsSurface->SetPadding(FMargin(0));
    auto* SurfaceSlot=Root->AddChildToCanvas(TopVitalsSurface);SurfaceSlot->SetAnchors(FAnchors(0,1));SurfaceSlot->SetAlignment(FVector2D(0,1));SurfaceSlot->SetZOrder(27);
    TopVitalsBlur=WidgetTree->ConstructWidget<UBackgroundBlur>();TopVitalsBlur->SetPadding(FMargin(0));TopVitalsBlur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);
    TopVitalsBlur->SetOverrideAutoRadiusCalculation(true);TopVitalsBlur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);TopVitalsSurface->SetContent(TopVitalsBlur);
    TopVitalsTint=MakeSurface(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius,ColdSteelUI::Border,1);TopVitalsBlur->SetContent(TopVitalsTint);
    TopVitalsGrid=WidgetTree->ConstructWidget<UGridPanel>();TopVitalsTint->SetContent(TopVitalsGrid);
    auto AddResource=[&](const TCHAR* Caption,TObjectPtr<UColdSteelResourceMeter>& Meter,TObjectPtr<UTextBlock>& Value){
        auto* Card=MakeSurface(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius,FLinearColor::Transparent,0);
        TopVitalsGrid->AddChildToGrid(Card,0,TopResourceCards.Num());TopResourceCards.Add(Card);
        auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Card->SetContent(Column);
        auto* Meta=WidgetTree->ConstructWidget<UHorizontalBox>();Column->AddChildToVerticalBox(Meta)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        auto* Label=MakeTopHUDText(Caption,14,ColdSteelUI::TextSecondary);Meta->AddChildToHorizontalBox(Label)->SetVerticalAlignment(VAlign_Center);
        Value=MakeTopHUDText(TEXT("— / —"),16,ColdSteelUI::TextPrimary,true);Value->SetJustification(ETextJustify::Right);Value->SetAutoWrapText(false);
        auto* ValueSlot=Meta->AddChildToHorizontalBox(Value);ValueSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));ValueSlot->SetVerticalAlignment(VAlign_Center);
        auto* Height=WidgetTree->ConstructWidget<USizeBox>();Column->AddChildToVerticalBox(Height);TopMeterSizes.Add(Height);
        Meter=WidgetTree->ConstructWidget<UColdSteelResourceMeter>();Height->SetContent(Meter);
    };
    AddResource(TEXT("生命"),TopHealthMeter,TopHealthValue);AddResource(TEXT("魔法"),TopManaMeter,TopManaValue);TopManaMeter->SetValue(0,true);
    TopLevelSize=WidgetTree->ConstructWidget<USizeBox>();TopVitalsGrid->AddChildToGrid(TopLevelSize,0,2);
    TopLevelSurface=MakeSurface(ColdSteelUI::Content,ColdSteelUI::CardRadius,ColdSteelUI::Border,1);TopLevelSurface->SetVerticalAlignment(VAlign_Center);TopLevelSize->SetContent(TopLevelSurface);
    auto* LevelColumn=WidgetTree->ConstructWidget<UVerticalBox>();TopLevelSurface->SetContent(LevelColumn);
    auto* Label=MakeTopHUDText(TEXT("等级"),12,ColdSteelUI::HUDGoldLight);Label->SetJustification(ETextJustify::Center);LevelColumn->AddChildToVerticalBox(Label);
    TopLevelValue=MakeTopHUDText(TEXT("—"),20,ColdSteelUI::TextPrimary,true,true);TopLevelValue->SetJustification(ETextJustify::Center);LevelColumn->AddChildToVerticalBox(TopLevelValue);
    WorldClock=WidgetTree->ConstructWidget<UColdSteelWorldClock>();WorldClock->SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* ClockSlot=Root->AddChildToCanvas(WorldClock);ClockSlot->SetAnchors(FAnchors(1,0));ClockSlot->SetAlignment(FVector2D(1,0));ClockSlot->SetZOrder(27);
    UpdateTopHUDLayout(GetCachedGeometry());RefreshTopVitals();RefreshWorldClock();
}

void UColdSteelHUDWidget::UpdateTopHUDLayout(const FGeometry& Geometry)
{
    if(!TopVitalsSurface||!WorldClock)return;
    const float S=ColdSteelUI::PixelScale(this);
    FVector2D View=Geometry.GetLocalSize();if(View.X<100||View.Y<100)View=UWidgetLayoutLibrary::GetViewportSize(this)/S;
    if(View.X<100||View.Y<100)View=FVector2D(1280,720)/S;
    if(TopHUDViewport.Equals(View,.1f)&&FMath::IsNearlyEqual(TopHUDScale,S,.0001f))return;
    TopHUDViewport=View;TopHUDScale=S;
    const float ViewWidth=View.X*S,Gap=ColdSteelUI::HUDGap;
    const FColdSteelHUDLayout Layout(ViewWidth);
    // Keep the existing central skill bar at its original anchor. Small windows lift
    // the left card above the bar instead of shrinking text or overlapping slots.
    const float LeftSpace=ViewWidth*.5f-330.f-2*Gap;
    const bool LiftVitals=LeftSpace<340.f;
    const float VitalsWidth=FMath::Min(440.f,FMath::Max(1.f,LiftVitals?ViewWidth-2*Gap:LeftSpace));
    const float Height=136.f,Bottom=LiftVitals?132.f:Gap;
    auto* VitalsSlot=Cast<UCanvasPanelSlot>(TopVitalsSurface->Slot);VitalsSlot->SetPosition(FVector2D(Gap/S,-Bottom/S));VitalsSlot->SetSize(FVector2D(VitalsWidth/S,Height/S));
    auto* ClockSlot=Cast<UCanvasPanelSlot>(WorldClock->Slot);ClockSlot->SetPosition(FVector2D(-Gap/S,Layout.CornerTop/S));ClockSlot->SetSize(FVector2D(Layout.CornerWidth/S,Layout.CornerHeight/S));
    TopHUDBottom=(Layout.CornerTop+Layout.CornerHeight)/S;
    TopVitalsTint->SetPadding(FMargin(12/S,10/S));TopVitalsTint->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10/S,ColdSteelUI::Border,1/S));
    TopVitalsBlur->SetCornerRadius(FVector4(10/S));TopVitalsBlur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,10/S));
    TopVitalsGrid->SetColumnFill(0,0);TopVitalsGrid->SetColumnFill(1,1);TopVitalsGrid->SetColumnFill(2,0);
    TopVitalsGrid->SetRowFill(0,1);TopVitalsGrid->SetRowFill(1,1);
    for(int32 I=0;I<TopResourceCards.Num();++I)
    {
        auto* Card=TopResourceCards[I].Get();Card->SetPadding(FMargin(6/S,4/S));Card->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,8/S,FLinearColor::Transparent,0));
        auto* CardSlot=Cast<UGridSlot>(Card->Slot);CardSlot->SetRow(I);CardSlot->SetColumn(1);CardSlot->SetPadding(FMargin(12/S,0,0,I==0?6/S:0));
        CardSlot->SetHorizontalAlignment(HAlign_Fill);CardSlot->SetVerticalAlignment(VAlign_Fill);
        TopMeterSizes[I]->SetHeightOverride(10/S);Cast<UVerticalBoxSlot>(TopMeterSizes[I]->Slot)->SetPadding(FMargin(0,6/S,0,0));
    }
    for(auto* Value:{TopHealthValue.Get(),TopManaValue.Get()})Cast<UHorizontalBoxSlot>(Value->Slot)->SetPadding(FMargin(8/S,0,0,0));
    auto* LevelSlot=Cast<UGridSlot>(TopLevelSize->Slot);LevelSlot->SetRow(0);LevelSlot->SetColumn(0);LevelSlot->SetRowSpan(2);LevelSlot->SetHorizontalAlignment(HAlign_Fill);LevelSlot->SetVerticalAlignment(VAlign_Fill);
    TopLevelSize->SetWidthOverride(64/S);TopLevelSurface->SetPadding(FMargin(6/S,4/S));TopLevelSurface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,8/S,ColdSteelUI::HUDGold,1/S));
    for(const auto& E:TopHUDLabels)if(auto* T=E.Widget.Get())T->SetFont(E.Numeric?ColdSteelUI::NumberFont(E.Pixels*.75f/S,E.Medium):ColdSteelUI::TextFont(E.Pixels*.75f/S,E.Medium));
    WorldClock->SetDisplayScale(S);
}

void UColdSteelHUDWidget::RefreshWorldClock()
{
    if(!WorldClock)return;
    const auto* Weather=HUDWeatherSource.Get();
    WorldClock->SetTime(Weather?Weather->GetScheduleDay()+1:0,Weather?Weather->NormalizedDayTime:0,Weather!=nullptr);
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
