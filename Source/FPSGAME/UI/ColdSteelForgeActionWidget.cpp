#include "ColdSteelForgeActionWidget.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "../Building/ForgingSystem.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/BackgroundBlur.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Border.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ProgressBar.h"
#include "Components/SizeBox.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/TextBlock.h"

UTextBlock* UColdSteelForgeActionWidget::Text(const FString& Caption,float Pixels,bool bNumeric)
{
    auto* Label=WidgetTree->ConstructWidget<UTextBlock>();
    Label->SetText(FText::FromString(Caption));Label->SetAutoWrapText(true);
    Label->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    Labels.Add({Label,Pixels,bNumeric});return Label;
}

void UColdSteelForgeActionWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* Root=WidgetTree->ConstructWidget<UCanvasPanel>();WidgetTree->RootWidget=Root;
    PanelSize=WidgetTree->ConstructWidget<USizeBox>();
    auto* PanelSlot=Root->AddChildToCanvas(PanelSize);
    PanelSlot->SetAnchors(FAnchors(.5f,1.f));PanelSlot->SetAlignment(FVector2D(.5f,1.f));PanelSlot->SetAutoSize(true);
    Panel=WidgetTree->ConstructWidget<UBorder>();PanelSize->SetContent(Panel);
    auto* Layers=WidgetTree->ConstructWidget<UOverlay>();Panel->SetContent(Layers);
    Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();
    auto* BlurSlot=Layers->AddChildToOverlay(Blur);BlurSlot->SetHorizontalAlignment(HAlign_Fill);BlurSlot->SetVerticalAlignment(VAlign_Fill);
    Content=WidgetTree->ConstructWidget<UBorder>();
    auto* ContentSlot=Layers->AddChildToOverlay(Content);ContentSlot->SetHorizontalAlignment(HAlign_Fill);ContentSlot->SetVerticalAlignment(VAlign_Fill);
    auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();Content->SetContent(Stack);
    Heading=Text(TEXT("锻造 · 准备落锤"),16);HeadingSlot=Stack->AddChildToVerticalBox(Heading);
    auto* Metrics=WidgetTree->ConstructWidget<UHorizontalBox>();Stack->AddChildToVerticalBox(Metrics);
    auto Metric=[&](const FString& Caption,UTextBlock*& Label)
    {
        auto* Card=WidgetTree->ConstructWidget<UBorder>();Cards.Add(Card);
        auto* CardSlot=Metrics->AddChildToHorizontalBox(Card);CardSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));CardSlots.Add(CardSlot);
        auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Card->SetContent(Column);
        Label=Text(Caption,12);Label->SetColorAndOpacity(ColdSteelUI::TextTertiary);Column->AddChildToVerticalBox(Label);
        auto* Value=Text(TEXT("—"),16,true);Column->AddChildToVerticalBox(Value);return Value;
    };
    UTextBlock* Label=nullptr;TimeValue=Metric(TEXT("当前光圈"),Label);TimeLabel=Label;
    HitsValue=Metric(TEXT("有效命中"),Label);QualityValue=Metric(TEXT("工艺伤害"),Label);
    TimerSize=WidgetTree->ConstructWidget<USizeBox>();Timer=WidgetTree->ConstructWidget<UProgressBar>();TimerSize->SetContent(Timer);
    Timer->SetFillColorAndOpacity(ColdSteelUI::Accent);TimerSlot=Stack->AddChildToVerticalBox(TimerSize);
    Hint=Text(TEXT("光圈逐渐缩小 · 对准后左键落锤 · 回锤后等待下一处 · Esc 结算返回"),12);
    Hint->SetColorAndOpacity(ColdSteelUI::TextSecondary);HintSlot=Stack->AddChildToVerticalBox(Hint);
    UpdateLayout();
}

void UColdSteelForgeActionWidget::UpdateLayout()
{
    const float NewScale=FMath::Max(.1f,ColdSteelUI::PixelScale(this));
    const float NewWidth=FMath::Min(600.f,FMath::Max(1.f,float(UWidgetLayoutLibrary::GetViewportSize(this).X)-24.f));
    if(FMath::IsNearlyEqual(Scale,NewScale,.001f)&&FMath::IsNearlyEqual(Width,NewWidth,.5f))return;
    Scale=NewScale;Width=NewWidth;PanelSize->SetWidthOverride(Width/Scale);
    if(auto* Position=Cast<UCanvasPanelSlot>(PanelSize->Slot))Position->SetPosition(FVector2D(0,-124/Scale));
    for(const auto& L:Labels)if(auto* Label=L.Widget.Get())Label->SetFont(L.Numeric?GunsmithUI::NumberFont(L.Pixels/Scale):GunsmithUI::TextFont(L.Pixels/Scale));
    Panel->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1/Scale));Panel->SetPadding(1/Scale);
    Content->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale,FLinearColor::Transparent,0));Content->SetPadding(12/Scale);
    Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);
    Blur->SetCornerRadius(FVector4(10,10,10,10)/Scale);Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,10/Scale));
    for(const auto& C:Cards)if(auto* Card=C.Get())
    {
        Card->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));
        Card->SetPadding(FMargin(10/Scale,6/Scale));
    }
    for(int32 I=0;I<CardSlots.Num();++I)if(auto* CardSlot=CardSlots[I].Get())CardSlot->SetPadding(FMargin(I?4/Scale:0,0,0,0));
    HeadingSlot->SetPadding(FMargin(0,0,0,8/Scale));TimerSlot->SetPadding(FMargin(0,8/Scale,0,0));HintSlot->SetPadding(FMargin(0,8/Scale,0,0));
    TimerSize->SetHeightOverride(3/Scale);
    FProgressBarStyle Progress;
    Progress.SetBackgroundImage(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(45),1.5f/Scale,FLinearColor::Transparent,0));
    Progress.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White,1.5f/Scale,FLinearColor::Transparent,0));Timer->SetWidgetStyle(Progress);
}

void UColdSteelForgeActionWidget::Refresh(const UColdSteelForgingSystem* System,bool Finishing,bool Feedback,bool Hit)
{
    if(!Heading||!System)return;UpdateLayout();
    const double Time=System->Elapsed();const int32 Hits=System->Job().Hits;
    const bool Swing=System->StrikeInProgress(),Waiting=System->TargetIndex()==INDEX_NONE;
    auto Set=[](UTextBlock* T,const FString& S){if(T->GetText().ToString()!=S)T->SetText(FText::FromString(S));};
    Set(Heading,Finishing?TEXT("淬火 · 冷却剑坯"):Time<0?TEXT("准备 · 等待落锤"):Swing?TEXT("落锤 · 当前热区已锁定")
        :Feedback?(Hit?TEXT("落点准确 · 回锤中"):TEXT("未命中 · 回锤中")):Waiting?TEXT("间歇 · 等待下一处热区")
        :FString::Printf(TEXT("锻打 · 第 %d / %d 处热区"),System->ResolvedTargets()+1,System->TargetCount));
    Set(TimeLabel,Finishing?TEXT("正在冷却"):Time<0?TEXT("准备倒计时"):Swing?TEXT("落锤接触"):Waiting?TEXT("间歇倒计时"):TEXT("光圈剩余"));
    Set(TimeValue,Finishing?TEXT("—"):FString::Printf(TEXT("%.1f s"),System->PhaseRemaining()));
    Set(HitsValue,FString::Printf(TEXT("%02d / 20"),Hits));
    const double Percent=-25.+2.5*Hits;Set(QualityValue,FString::Printf(TEXT("%+.1f%%"),Percent));
    QualityValue->SetColorAndOpacity(Percent>0?ColdSteelUI::Success:Percent<0?ColdSteelUI::Danger:ColdSteelUI::TextPrimary);
    Heading->SetColorAndOpacity(Feedback&&!Finishing?(Hit?ColdSteelUI::Success:ColdSteelUI::Warning):ColdSteelUI::TextPrimary);
    Timer->SetPercent(float(System->ResolvedTargets())/System->TargetCount);
    Set(Hint,Finishing?TEXT("正在冷却工件，完成后返回铸造台。"):TEXT("光圈逐渐缩小 · 对准后左键落锤 · 回锤后等待下一处 · Esc 结算返回"));
}
