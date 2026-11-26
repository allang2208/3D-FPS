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
#include "Styling/CoreStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Rendering/SlateRenderer.h"

UTextBlock* UGunAssemblyActionWidget::Text(const FString& Caption,float Pixels,bool bNumeric)
{
    auto* Label=WidgetTree->ConstructWidget<UTextBlock>();
    Label->SetText(FText::FromString(Caption));Label->SetAutoWrapText(false);
    Label->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    Labels.Add({Label,Pixels,bNumeric});return Label;
}

void UGunAssemblyActionWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* Root=WidgetTree->ConstructWidget<UCanvasPanel>();WidgetTree->RootWidget=Root;
    FollowNoticeSize=WidgetTree->ConstructWidget<USizeBox>();
    auto* NoticeSlot=Root->AddChildToCanvas(FollowNoticeSize);
    NoticeSlot->SetAnchors(FAnchors(.5f,0.f));NoticeSlot->SetAlignment(FVector2D(.5f,0.f));NoticeSlot->SetAutoSize(true);
    FollowNotice=WidgetTree->ConstructWidget<UBorder>();FollowNoticeSize->SetContent(FollowNotice);
    FollowHint=Text(TEXT("长按鼠标左键，将准星放入圆圈内并持续跟随"),16);
    FollowHint->SetJustification(ETextJustify::Center);FollowHint->SetAutoWrapText(true);FollowNotice->SetContent(FollowHint);
    FollowNoticeSize->SetVisibility(ESlateVisibility::Collapsed);
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
    Details=Text(TEXT(""),14);Details->SetAutoWrapText(true);Details->SetColorAndOpacity(ColdSteelUI::TextSecondary);DetailsSlot=Stack->AddChildToVerticalBox(Details);
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
    HitsValue=Metric(TEXT("组件装配"),Label);HitsLabel=Label;QualityValue=Metric(TEXT("伤害加成"),Label);
    BonusBreakdown=Text(TEXT(""),14);BonusBreakdown->SetAutoWrapText(true);Stack->AddChildToVerticalBox(BonusBreakdown);
    TimerSize=WidgetTree->ConstructWidget<USizeBox>();Timer=WidgetTree->ConstructWidget<UProgressBar>();TimerSize->SetContent(Timer);
    Timer->SetFillColorAndOpacity(ColdSteelUI::Accent);TimerSlot=Stack->AddChildToVerticalBox(TimerSize);
    Hint=Text(TEXT("左键拖放 · 长按 Q / E 旋转 · 滚轮微调 · 右键放回 · Esc 返回"),12);Hint->SetAutoWrapText(true);
    Hint->SetColorAndOpacity(ColdSteelUI::TextSecondary);HintSlot=Stack->AddChildToVerticalBox(Hint);
    UpdateLayout();
}

void UGunAssemblyActionWidget::UpdateLayout()
{
    const float NewScale=FMath::Max(.1f,ColdSteelUI::PixelScale(this));
    const float NewWidth=FMath::Min(600.f,FMath::Max(1.f,float(UWidgetLayoutLibrary::GetViewportSize(this).X)-24.f));
    if(FMath::IsNearlyEqual(Scale,NewScale,.001f)&&FMath::IsNearlyEqual(Width,NewWidth,.5f))return;
    Scale=NewScale;Width=NewWidth;PanelSize->SetWidthOverride(Width/Scale);
    FollowNoticeSize->SetWidthOverride(Width/Scale);
    if(auto* Position=Cast<UCanvasPanelSlot>(FollowNoticeSize->Slot))Position->SetPosition(FVector2D(0,48/Scale));
    FollowNotice->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor(.008f,.012f,.018f,.94f),ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));
    FollowNotice->SetPadding(FMargin(16/Scale,10/Scale));
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
    FollowNoticeSize->SetVisibility(bCalibration&&!GunAssemblyCalibration::Complete(CalibrationTime)?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    auto Set=[](UTextBlock* T,const FString& V){if(T->GetText().ToString()!=V)T->SetText(FText::FromString(V));};
    if(bFinished)
    {Set(Heading,FString::Printf(TEXT("%s 拼装完成 · %s · %.0f 分"),*System->ProductName(),*System->QualityName(System->Score()),System->Score()));Set(Details,System->BenefitText(System->Score(),System->MaterialBonus()));Set(Hint,TEXT("成品已保存 · Enter 返回领取 · Esc 暂离"));}
    else if(bCalibration)
    {
        const int32 Round=GunAssemblyCalibration::Round(CalibrationTime);
        const float Remaining=FMath::CeilToInt(GunAssemblyCalibration::PhaseRemaining(CalibrationTime)*10.f)/10.f;
        const bool Following=GunAssemblyCalibration::Following(CalibrationTime);
        if(GunAssemblyCalibration::Complete(CalibrationTime))Set(Heading,TEXT("五组校准结束 · 正在保存成品"));
        else if(Following)Set(Heading,FString::Printf(TEXT("第 %d / %d 组 · 跟随剩余 %.1f 秒"),Round+1,GunAssemblyCalibration::RoundCount,Remaining));
        else Set(Heading,FString::Printf(TEXT("%s · 第 %d / %d 组 · %.1f 秒"),Round==0?TEXT("准备"):TEXT("组间休息"),Round+1,GunAssemblyCalibration::RoundCount,Remaining));
        Set(Details,Message.IsEmpty()?(Following?TEXT("绿色：判定成功 · 红色：未命中或未按住左键"):TEXT("黄色：准备或休息 · 此阶段不计分")):Message);
        Set(Hint,TEXT("出圈或松开仍计时 · 5 组完成后自动进入交付 · Esc 保存并返回"));
    }
    else
    {Set(Heading,FString::Printf(TEXT("%s 散件拼装 · %d / %d"),*System->ProductName(),System->InstalledCount(),System->Recipe().Parts.Num()));Set(Details,Message.IsEmpty()?(Selected>=0?System->Recipe().Parts[Selected].Name+TEXT(" · 圆心对准明亮安装圈，旋转至 0°"):TEXT("选择散件，将零件圆心拖到明亮安装圈")):Message);Set(Hint,Held?TEXT("长按 Q / E 连续旋转 · 滚轮微调 · 松开左键安装 · 右键放回"):TEXT("按住左键拿取 · 按 Tab 选择下一件小零件 · Esc 保存并返回"));}
    Set(TimeLabel,bCalibration?TEXT("总剩余时间"):TEXT("校准时长"));
    Set(TimeValue,FString::Printf(TEXT("%.1f 秒"),bCalibration?FMath::Max(0.f,GunAssemblyCalibration::Duration-CalibrationTime):GunAssemblyCalibration::Duration));
    Set(HitsLabel,bCalibration?TEXT("有效跟随"):TEXT("组件装配"));
    Set(HitsValue,bCalibration?FString::Printf(TEXT("%.1f / %.0f 秒"),System->Job().CalibrationSeconds,GunAssemblyCalibration::ScoringSeconds):FString::Printf(TEXT("%d / %d"),System->InstalledCount(),System->Recipe().Parts.Num()));
    const double Base=System->MaterialBonus(),Skill=ColdSteelAssemblyQuality::SkillBonus(System->Score());
    Set(QualityValue,FString::Printf(TEXT("+%.2f%%"),(Base+Skill)*100));
    Set(BonusBreakdown,FString::Printf(TEXT("材质 +%.2f%% ＋ 工艺 +%.2f%% · 本材质最高 +%.2f%%"),Base*100,Skill*100,(Base+ColdSteelAssemblyQuality::MaxSkillBonus)*100));
    QualityValue->SetColorAndOpacity(Base+Skill>0?ColdSteelUI::Success:ColdSteelUI::TextPrimary);
    Timer->SetPercent(bFinished?1.f:bCalibration?CalibrationTime/GunAssemblyCalibration::Duration:float(System->InstalledCount())/FMath::Max(1,System->Recipe().Parts.Num()));
}
float UGunAssemblyActionWidget::CalibrationTop(int32 ViewportHeight) const
{
    return FMath::Max(.08f,(48.f+FollowNoticeSize->GetDesiredSize().Y*Scale+12.f)/FMath::Max(1,ViewportHeight));
}
float UGunAssemblyActionWidget::WorkspaceBottom(int32 ViewportHeight)
{
    UpdateLayout();ForceLayoutPrepass();
    // Keep the workspace above the footer, with room for a two-line feedback message.
    const float Reserved=124.f+PanelSize->GetDesiredSize().Y*Scale+48.f;
    return FMath::Clamp(1.f-Reserved/FMath::Max(1,ViewportHeight),.25f,.70f);
}
int32 UGunAssemblyActionWidget::NativePaint(const FPaintArgs& Args,const FGeometry& G,const FSlateRect& Clip,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool Enabled) const
{
    Layer=Super::NativePaint(Args,G,Clip,Out,Layer,Style,Enabled)+1;
    const FVector2D Size=G.GetLocalSize();const float S=ColdSteelUI::PixelScale(this);
    auto Circle=[&](FVector2D P,float R,FLinearColor Color,float Thickness=1.5f){TArray<FVector2D> V;for(int I=0;I<=48;++I){const double A=2*PI*I/48;V.Add(P+FVector2D(FMath::Cos(A),FMath::Sin(A))*R);}FSlateDrawElement::MakeLines(Out,Layer,G.ToPaintGeometry(),V,ESlateDrawEffect::None,Color,true,Thickness/S);};
    if(!bFinished)
    {
        const FVector2D Pointer=Aim*Size;
        Circle(Pointer,5/S,FLinearColor::Black,5);Circle(Pointer,5/S,FLinearColor::White,2);
        if(bCalibration)
        {
            const float Radius=FMath::Min(Size.X,Size.Y)*CalibrationRadius;
            const bool Following=GunAssemblyCalibration::Following(CalibrationTime);
            const bool Preparing=!Following&&!GunAssemblyCalibration::Complete(CalibrationTime);
            FLinearColor Color=Following?(bInside?FLinearColor(.2f,1.f,.35f):FLinearColor(1.f,.12f,.08f)):FLinearColor(1.f,.78f,.05f);
            if(Preparing)
            {
                const float Phase=GunAssemblyCalibration::RoundTime(CalibrationTime);
                Color.A=.35f+.65f*(.5f+.5f*FMath::Cos(Phase*4.f*PI));
            }
            Circle(Target*Size,Radius,FLinearColor(.005f,.008f,.012f,.96f),7);
            Circle(Target*Size,Radius,Color,2.5f);
            ++Layer;Circle(Pointer,5/S,FLinearColor::Black,5);Circle(Pointer,5/S,FLinearColor::White,2);
            if(Preparing)
            {
                // Keep the countdown steady while the ring pulses; share the gameplay phase clock.
                const float Remaining=FMath::CeilToInt(GunAssemblyCalibration::PhaseRemaining(CalibrationTime)*10.f)/10.f;
                const FString Countdown=FString::Printf(TEXT("%.1f"),Remaining);
                const int32 Pixels=FMath::Clamp(FMath::FloorToInt(Radius*S*.8f),8,18);
                auto Font=GunsmithUI::NumberFont(Pixels/S,true);
                Font.OutlineSettings.OutlineSize=FMath::Max(1,FMath::RoundToInt(2/S));
                Font.OutlineSettings.OutlineColor=FLinearColor::Black;
                const FVector2D TextSize=FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(Countdown,Font);
                FSlateDrawElement::MakeText(Out,++Layer,G.ToPaintGeometry(TextSize,FSlateLayoutTransform(Target*Size-TextSize*.5f)),Countdown,Font,ESlateDrawEffect::None,FLinearColor(1.f,.9f,.45f));
            }
        }
        else for(int32 I=0;I<Markers.Num();++I)if(!Done[I]&&Names.IsValidIndex(I))
        {
            const FVector2D P=Markers[I]*Size;const FLinearColor Color=I==Highlight?ColdSteelUI::TextPrimary:ColdSteelUI::TextSecondary;
            Circle(P,9/S,Color);
            FSlateDrawElement::MakeText(Out,Layer,G.ToPaintGeometry(FVector2D(130/S,26/S),FSlateLayoutTransform(P+FVector2D(12/S,-10/S))),Names[I],GunsmithUI::TextFont(12/S),ESlateDrawEffect::None,Color);
        }
        if(!bCalibration&&bInstallGuide)
        {
            const FVector2D P=InstallTarget*Size,Part=InstallPart*Size;
            const FLinearColor Ink(.005f,.008f,.012f,.96f),Color=bInstallReady?FLinearColor(.2f,1.f,.35f):FLinearColor(.15f,.9f,1.f);
            const TArray<FVector2D> Leader={Part,P};
            FSlateDrawElement::MakeLines(Out,Layer,G.ToPaintGeometry(),Leader,ESlateDrawEffect::None,Ink,true,5/S);
            FSlateDrawElement::MakeLines(Out,++Layer,G.ToPaintGeometry(),Leader,ESlateDrawEffect::None,Color,true,1.5f/S);
            Circle(P,15/S,Ink,8);Circle(P,15/S,Color,3);Circle(P,7/S,Ink,6);Circle(P,7/S,FLinearColor::White,2);
            const TArray<FVector2D> Horizontal={P-FVector2D(22/S,0),P+FVector2D(22/S,0)};
            const TArray<FVector2D> Vertical={P-FVector2D(0,22/S),P+FVector2D(0,22/S)};
            for(const auto& Line:{Horizontal,Vertical})
            {
                FSlateDrawElement::MakeLines(Out,Layer,G.ToPaintGeometry(),Line,ESlateDrawEffect::None,Ink,true,5/S);
                FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Line,ESlateDrawEffect::None,Color,true,1.5f/S);
            }
            Layer+=2;
            // Project the exact scoring target in the HUD, so receiver/hand depth cannot hide it.
            const FVector2D LabelSize(258/S,46/S);
            const FVector2D Label(FMath::Clamp(P.X+26/S,8./S,FMath::Max(8./S,Size.X-LabelSize.X-8/S)),FMath::Max(8./S,P.Y-58/S));
            FSlateDrawElement::MakeBox(Out,Layer,G.ToPaintGeometry(LabelSize,FSlateLayoutTransform(Label)),FCoreStyle::Get().GetBrush("WhiteBrush"),ESlateDrawEffect::None,Ink);
            FSlateDrawElement::MakeText(Out,Layer+1,G.ToPaintGeometry(LabelSize,FSlateLayoutTransform(Label+FVector2D(8/S,3/S))),TEXT("安装位 · ")+InstallName,GunsmithUI::TextFont(14/S),ESlateDrawEffect::None,Color);
            const FString Detail=FString::Printf(TEXT("距离 %.1f cm · 角度 %+.0f°%s"),InstallDistance,InstallAngle,bInstallReady?TEXT(" · 可安装"):TEXT(""));
            FSlateDrawElement::MakeText(Out,Layer+1,G.ToPaintGeometry(LabelSize,FSlateLayoutTransform(Label+FVector2D(8/S,24/S))),Detail,GunsmithUI::TextFont(12/S),ESlateDrawEffect::None,FLinearColor::White);
            Layer+=2;Circle(Pointer,5/S,FLinearColor::Black,5);Circle(Pointer,5/S,FLinearColor::White,2);
        }
    }
    return Layer;
}
