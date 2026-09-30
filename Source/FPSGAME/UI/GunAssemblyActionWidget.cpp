#include "GunAssemblyActionWidget.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "../Building/GunAssemblySystem.h"
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
#include "Rendering/DrawElements.h"

UTextBlock* UGunAssemblyActionWidget::Text(const FString& Caption,float Pixels,bool bNumeric)
{
    auto* Label=WidgetTree->ConstructWidget<UTextBlock>();
    Label->SetText(FText::FromString(Caption));Label->SetAutoWrapText(true);
    Label->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    Labels.Add({Label,Pixels,bNumeric});return Label;
}

void UGunAssemblyActionWidget::NativeOnInitialized()
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
    Heading=Text(TEXT("枪械组装 · 准备"),16);HeadingSlot=Stack->AddChildToVerticalBox(Heading);
    Details=Text(TEXT(""),14);Details->SetColorAndOpacity(ColdSteelUI::TextSecondary);DetailsSlot=Stack->AddChildToVerticalBox(Details);
    auto* Metrics=WidgetTree->ConstructWidget<UHorizontalBox>();Stack->AddChildToVerticalBox(Metrics);
    auto Metric=[&](const FString& Caption,UTextBlock*& Label)
    {
        auto* Card=WidgetTree->ConstructWidget<UBorder>();Cards.Add(Card);
        auto* CardSlot=Metrics->AddChildToHorizontalBox(Card);CardSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));CardSlots.Add(CardSlot);
        auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Card->SetContent(Column);
        Label=Text(Caption,12);Label->SetColorAndOpacity(ColdSteelUI::TextTertiary);Column->AddChildToVerticalBox(Label);
        auto* Value=Text(TEXT("—"),16,true);Column->AddChildToVerticalBox(Value);return Value;
    };
    UTextBlock* Label=nullptr;TimeValue=Metric(TEXT("持稳校准"),Label);TimeLabel=Label;
    HitsValue=Metric(TEXT("组件装配"),Label);QualityValue=Metric(TEXT("工艺评分"),Label);
    TimerSize=WidgetTree->ConstructWidget<USizeBox>();Timer=WidgetTree->ConstructWidget<UProgressBar>();TimerSize->SetContent(Timer);
    Timer->SetFillColorAndOpacity(ColdSteelUI::Accent);TimerSlot=Stack->AddChildToVerticalBox(TimerSize);
    Hint=Text(TEXT("左键拖放 · 滚轮 / Q、R 旋转 · 右键放回 · Esc 返回"),12);
    Hint->SetColorAndOpacity(ColdSteelUI::TextSecondary);HintSlot=Stack->AddChildToVerticalBox(Hint);
    UpdateLayout();
}

void UGunAssemblyActionWidget::UpdateLayout()
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
    HeadingSlot->SetPadding(FMargin(0,0,0,4/Scale));DetailsSlot->SetPadding(FMargin(0,0,0,8/Scale));TimerSlot->SetPadding(FMargin(0,8/Scale,0,0));HintSlot->SetPadding(FMargin(0,8/Scale,0,0));
    TimerSize->SetHeightOverride(3/Scale);
    FProgressBarStyle Progress;
    Progress.SetBackgroundImage(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(45),1.5f/Scale,FLinearColor::Transparent,0));
    Progress.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White,1.5f/Scale,FLinearColor::Transparent,0));Timer->SetWidgetStyle(Progress);
}

void UGunAssemblyActionWidget::Refresh(const UGunAssemblySystem* System,const FString& Message,int32 Selected,bool Held)
{
    if(!Heading||!System)return;UpdateLayout();
    bFinished=System->Job().bFinished;bCalibration=System->Assembled()&&!bFinished;Highlight=Selected;
    auto Set=[](UTextBlock* T,const FString& V){if(T->GetText().ToString()!=V)T->SetText(FText::FromString(V));};
    if(bFinished)
    {Set(Heading,FString::Printf(TEXT("%s 拼装完成 · %s · %.0f 分"),*System->ProductName(),*System->QualityName(System->Score()),System->Score()));Set(Details,System->BenefitText(System->Score()));Set(Hint,TEXT("成品已保存 · Enter 返回领取 · Esc 暂离"));}
    else if(bCalibration)
    {Set(Heading,FString::Printf(TEXT("持稳校准 · %.1f / %.1f 秒"),System->Job().CalibrationSeconds,System->Job().CalibrationDuration));Set(Details,Message.IsEmpty()?TEXT("按住左键，移动鼠标将准星保持在缓慢移动的圆圈内。"):Message);Set(Hint,TEXT("出圈暂停累计，不清零 · 松开左键暂停 · Esc 保存并返回"));}
    else
    {Set(Heading,FString::Printf(TEXT("%s 散件拼装 · %d / %d"),*System->ProductName(),System->InstalledCount(),System->Recipe().Parts.Num()));Set(Details,Message.IsEmpty()?(Selected>=0?System->Recipe().Parts[Selected].Name:TEXT("选择一件散件，拖到枪身上的对应轮廓")):Message);Set(Hint,Held?TEXT("滚轮 / Q、R 旋转 · 松开左键安装 · 右键放回 · Esc 保存并返回"):TEXT("按住左键拿取 · 按 Tab 选择下一件小零件 · Esc 保存并返回"));}
    Set(TimeValue,FString::Printf(TEXT("%.1f / %.1f 秒"),System->Job().CalibrationSeconds,System->Job().CalibrationDuration));
    Set(HitsValue,FString::Printf(TEXT("%d / %d"),System->InstalledCount(),System->Recipe().Parts.Num()));
    Set(QualityValue,bFinished?FString::Printf(TEXT("%.0f 分"),System->Score()):TEXT("待完成"));
    QualityValue->SetColorAndOpacity(bFinished?ColdSteelUI::Success:ColdSteelUI::TextPrimary);
    const float Cal=System->Job().CalibrationSeconds/FMath::Max(.01f,System->Job().CalibrationDuration);
    Timer->SetPercent(bFinished?1.f:(System->InstalledCount()+Cal)/FMath::Max(1,System->Recipe().Parts.Num()+1));
}
int32 UGunAssemblyActionWidget::NativePaint(const FPaintArgs& Args,const FGeometry& G,const FSlateRect& Clip,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool Enabled) const
{
    Layer=Super::NativePaint(Args,G,Clip,Out,Layer,Style,Enabled)+1;
    const FVector2D Size=G.GetLocalSize();const float S=ColdSteelUI::PixelScale(this);
    auto Circle=[&](FVector2D P,float R,FLinearColor Color){TArray<FVector2D> V;for(int I=0;I<=48;++I){const double A=2*PI*I/48;V.Add(P+FVector2D(FMath::Cos(A),FMath::Sin(A))*R);}FSlateDrawElement::MakeLines(Out,Layer,G.ToPaintGeometry(),V,ESlateDrawEffect::None,Color,true,1.5f/S);};
    if(!bFinished)
    {
        const FVector2D Pointer=Aim*Size;Circle(Pointer,5/S,ColdSteelUI::TextPrimary);
        if(bCalibration)Circle(Target*Size,FMath::Min(Size.X,Size.Y)*.047f,bInside?ColdSteelUI::Success:ColdSteelUI::TextPrimary);
        else for(int32 I=0;I<Markers.Num();++I)if(!Done[I]&&Names.IsValidIndex(I))
        {
            const FVector2D P=Markers[I]*Size;const FLinearColor Color=I==Highlight?ColdSteelUI::TextPrimary:ColdSteelUI::TextSecondary;
            Circle(P,9/S,Color);
            FSlateDrawElement::MakeText(Out,Layer,G.ToPaintGeometry(FVector2D(130/S,26/S),FSlateLayoutTransform(P+FVector2D(12/S,-10/S))),Names[I],GunsmithUI::TextFont(12/S),ESlateDrawEffect::None,Color);
        }
    }
    return Layer;
}
