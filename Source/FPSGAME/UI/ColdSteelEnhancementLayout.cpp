#include "ColdSteelEnhancementWidget.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "M4GunsmithWidget.h"
#include "SM4PreviewSurface.h"
#include "../FPSGAMEPlayerController.h"
#include "Engine/Texture2D.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Colors/SSimpleGradient.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SNullWidget.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Styling/CoreStyle.h"

TSharedRef<SWidget> UColdSteelEnhancementWidget::Label(const FString& Text,int32 Size,FLinearColor Color,bool Numeric)const
{
    return SNew(STextBlock).Text(FText::FromString(Text))
        .Font(Numeric?GunsmithUI::NumberFont(Size):GunsmithUI::TextFont(Size,Size>=16))
        .ColorAndOpacity(Color).AutoWrapText(true).Justification(Numeric?ETextJustify::Right:ETextJustify::Left);
}

TSharedRef<SButton> UColdSteelEnhancementWidget::Button(const FString& Text,TFunction<void()> Action,bool Primary,bool Selected,bool Enabled)
{
    return SNew(SButton).ButtonStyle(Primary?&PrimaryStyle:Selected?&SelectedStyle:&Normal)
        .ContentPadding(FMargin(12,0)).HAlign(HAlign_Fill).VAlign(VAlign_Center).IsEnabled(Enabled)
        .ToolTipText(FText::FromString(Text)).OnClicked_Lambda([Action](){Action();return FReply::Handled();})
        [SNew(SBox).MinDesiredHeight(ColdSteelUI::ActionHeight).VAlign(VAlign_Center)
            [SNew(STextBlock).Text(FText::FromString(Text)).Font(GunsmithUI::TextFont(14,true))
                .ColorAndOpacity(Primary?ColdSteelUI::Gray(22):ColdSteelUI::TextPrimary).Justification(ETextJustify::Center)]];
}

TSharedRef<SWidget> UColdSteelEnhancementWidget::TableRow(const FString& Name,const FString& Before,const FString& After,const FString& Delta,int32 Benefit)const
{
    const auto Tone=Benefit>0?ColdSteelUI::Success:Benefit<0?ColdSteelUI::Danger:ColdSteelUI::TextSecondary;
    auto Cells=SNew(SHorizontalBox);
    const FString Values[]={Name,Before,After,Delta};
    const float Widths[]={1.55f,.94f,.94f,.83f};
    for(int32 N=0;N<4;++N)
        Cells->AddSlot().FillWidth(Widths[N]).Padding(4,7).VAlign(VAlign_Center)
            [Label(Values[N],14,N>=2?Tone:ColdSteelUI::TextSecondary,N>0)];
    return SNew(SBorder).BorderImage(&RowBrush).Padding(0).ToolTipText(FText::FromString(Name))[Cells];
}

TSharedRef<SWidget> UColdSteelEnhancementWidget::GlassPanel(TSharedRef<SWidget> Content)
{
    return SNew(SOverlay)
        +SOverlay::Slot()[SNew(SBackgroundBlur).BlurStrength(5.f).BlurRadius(13).Padding(0)
            .CornerRadius(FVector4(10,10,10,10)).LowQualityFallbackBrush(&GlassFallback)
            [SNew(SBorder).BorderImage(&PanelBrush).Padding(14)[Content]]]
        +SOverlay::Slot().VAlign(VAlign_Top).Padding(12,0)
            [SNew(SBox).HeightOverride(1)[SNew(SImage).Image(FCoreStyle::Get().GetBrush("WhiteBrush"))
                .ColorAndOpacity(ColdSteelUI::Gray(255,42)).Visibility(EVisibility::HitTestInvisible)]];
}

TSharedRef<SWidget> UColdSteelEnhancementWidget::RebuildWidget()
{
    SetIsFocusable(true);LayoutMode=-1;
    PanelBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius);
    GlassFallback=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius);
    RowBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::AttributeRow,4,ColdSteelUI::Border,.5f);
    Normal=ColdSteelUI::ButtonStyle();
    Normal.SetNormalPadding(FMargin(0));Normal.SetPressedPadding(FMargin(0));
    SelectedStyle=Normal;SelectedStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius,ColdSteelUI::Accent));
    PrimaryStyle=Normal;PrimaryStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::Accent,ColdSteelUI::ButtonRadius));
    PrimaryStyle.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::TextPrimary,ColdSteelUI::ButtonRadius));
    PrimaryStyle.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(174),ColdSteelUI::ButtonRadius));
    PrimaryStyle.SetDisabled(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(85),ColdSteelUI::ButtonRadius));
    BackgroundTexture=LoadObject<UTexture2D>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_WorkshopBackground.T_WorkshopBackground"));
    Background.SetResourceObject(BackgroundTexture);Background.ImageSize=FVector2D(1672,941);Background.DrawAs=ESlateBrushDrawType::Image;

    auto Header=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,12,0)
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[Label(TEXT("装备加工 / 强化与附魔"),20,ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[Label(TEXT("选择装备 · 预览变化 · 确认并保存"),12,ColdSteelUI::TextSecondary)]]
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [SNew(SBox).WidthOverride(112)[Button(TEXT("Esc  返回"),[this](){CastChecked<AFPSGAMEPlayerController>(GetOwningPlayer())->CloseEnhancement();})]];

    RailContent=GlassPanel(SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,6)[Label(TEXT("可加工装备"),16,ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)[Label(TEXT("装备与背包 · 仅切换预览"),12,ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().FillHeight(1)[SAssignNew(RailScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6))
            .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
            +SScrollBox::Slot()[SAssignNew(Rail,SVerticalBox)]]);

    if(!WorkbenchPreview)WorkbenchPreview=CreateWidget<UM4GunsmithWidget>(GetOwningPlayer());
    ResetViewControl=Button(TEXT("水平复位"),[this](){WorkbenchPreview->SetSidePreview(true);});
    AimViewControl=Button(TEXT("瞄准预览"),[this](){WorkbenchPreview->SetAimPreview(true);});
    auto Stage=SNew(SOverlay)
        +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill)[SNew(SImage).Image(&Background)]]
        +SOverlay::Slot().Padding(8,70,8,54)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SImage).Image(WorkbenchPreview->StandaloneBrush())
            .Visibility_Lambda([this](){return WorkbenchPreview->HasWorkbenchCapture()?EVisibility::HitTestInvisible:EVisibility::Collapsed;})]]
        +SOverlay::Slot().Padding(48,88,48,64)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SImage)
            .Image_Lambda([this](){return &WeaponBrush;})
            .Visibility_Lambda([this](){return WorkbenchPreview->HasWorkbenchCapture()?EVisibility::Collapsed:EVisibility::HitTestInvisible;})]]
        +SOverlay::Slot().VAlign(VAlign_Top).Padding(16)
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SAssignNew(ItemTitle,STextBlock).Font(GunsmithUI::TextFont(20,true))
                    .ColorAndOpacity(ColdSteelUI::TextPrimary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[SAssignNew(ItemLevel,STextBlock).Font(GunsmithUI::TextFont(12))
                    .ColorAndOpacity(ColdSteelUI::TextSecondary).AutoWrapText(true)]]
        +SOverlay::Slot().VAlign(VAlign_Bottom).Padding(14)
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,8,0)
                    [Label(TEXT("拖动旋转 · 滚轮缩放 · 双击复位"),12,ColdSteelUI::TextSecondary)]
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,4,0)[SNew(SBox).WidthOverride(104)[ResetViewControl.ToSharedRef()]]
                +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(104)[AimViewControl.ToSharedRef()]]];
    PreviewSurface=SNew(SM4PreviewSurface).CanRotate_Lambda([this](){return WorkbenchPreview->HasWorkbenchCapture();})
        .OnOrbit_Lambda([this](FVector2D Delta){WorkbenchPreview->RotatePreview(Delta);})
        .OnZoom_Lambda([this](float Delta){WorkbenchPreview->ZoomPreview(Delta);})
        .OnReset_Lambda([this](){WorkbenchPreview->SetSidePreview(true);})[Stage];

    EnhanceControl=Button(TEXT("主属性强化"),[this](){SelectTab(false);});
    EnchantControl=Button(TEXT("附魔"),[this](){SelectTab(true);});
    auto OptionHeader=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,2,0)[EnhanceControl.ToSharedRef()]
        +SHorizontalBox::Slot().FillWidth(1).Padding(2,0,0,0)[EnchantControl.ToSharedRef()];
    CenterContent=SNew(SVerticalBox)
        +SVerticalBox::Slot().FillHeight(1)[SNew(SBorder).BorderImage(&PanelBrush).Padding(1).Clipping(EWidgetClipping::ClipToBounds)[PreviewSurface.ToSharedRef()]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,0)
            [GlassPanel(SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[OptionHeader]
                +SVerticalBox::Slot().AutoHeight()[SNew(SBox).HeightOverride(158)
                    [SAssignNew(OptionScroll,SScrollBox).Orientation(Orient_Horizontal).ScrollBarThickness(FVector2D(6,6))
                        .ScrollBarAlwaysVisible(true).AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::Always)
                        .WheelScrollMultiplier(2.f).AnimateWheelScrolling(false)+SScrollBox::Slot()[SAssignNew(Options,SHorizontalBox)]]])];

    CurrentCompare=Button(TEXT("对比当前"),[this](){bCompareBase=false;Refresh();});
    BaseCompare=Button(TEXT("对比基础"),[this](){bCompareBase=true;Refresh();});
    auto TableHeader=SNew(SHorizontalBox);
    const float Widths[]={1.55f,.94f,.94f,.83f};
    for(int32 N=0;N<4;++N)
        TableHeader->AddSlot().FillWidth(Widths[N]).Padding(4,5)
            [SNew(STextBlock).Text_Lambda([this,N](){return FText::FromString(N==0?TEXT("项目"):N==1?(bCompareBase?TEXT("基础"):TEXT("当前")):N==2?(bEnchant?TEXT("附魔后"):TEXT("强化后")):TEXT("变化"));})
                .Font(GunsmithUI::TextFont(12,true)).ColorAndOpacity(ColdSteelUI::TextSecondary).Justification(N?ETextJustify::Right:ETextJustify::Left)];
    InspectorContent=GlassPanel(SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)
            [SNew(STextBlock).Text_Lambda([this](){return FText::FromString(bEnchant?TEXT("附魔项目"):TEXT("强化项目"));})
                .Font(GunsmithUI::TextFont(16,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight()[SNew(SBox).HeightOverride_Lambda([this](){return bEnchant?76.f:46.f;})
            [SNew(SScrollBox).ScrollBarThickness(FVector2D(6,6)).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
                +SScrollBox::Slot()[SAssignNew(ProjectSummary,SVerticalBox)]]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,8)[Label(TEXT("装备数值总览"),20,ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,2,0)[CurrentCompare.ToSharedRef()]
            +SHorizontalBox::Slot().FillWidth(1).Padding(2,0,0,0)[BaseCompare.ToSharedRef()]]
        +SVerticalBox::Slot().AutoHeight()[TableHeader]
        +SVerticalBox::Slot().FillHeight(1)[SAssignNew(OverviewScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6))
            .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
            +SScrollBox::Slot()[SAssignNew(Inspector,SVerticalBox)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[Label(TEXT("绿色 增强 / 红色 削弱 / 灰色 不变"),12,ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,14,0,6)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("消耗汇总"),16,ColdSteelUI::TextPrimary)]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Label(TEXT("需要 / 持有"),12,ColdSteelUI::TextTertiary)]]
        +SVerticalBox::Slot().AutoHeight()[SNew(SBox).MaxDesiredHeight(104)
            [SNew(SScrollBox).ScrollBarThickness(FVector2D(6,6)).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
                +SScrollBox::Slot()[SAssignNew(Costs,SVerticalBox)]]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,0)[SNew(STextBlock)
            .Text_Lambda([this](){return FText::FromString(bEnchant?TEXT("卷轴仅计背包 · 粉尘计入背包与仓库"):TEXT("材料计入背包与仓库"));})
            .Font(GunsmithUI::TextFont(12)).ColorAndOpacity(ColdSteelUI::TextTertiary).AutoWrapText(true)]);

    ConfirmControl=Button(TEXT("确认强化"),[this](){Confirm();},true);
    ConfirmControl->SetContent(SNew(SBox).MinDesiredHeight(ColdSteelUI::ActionHeight).VAlign(VAlign_Center)
        [SAssignNew(ConfirmText,STextBlock).Font(GunsmithUI::TextFont(14,true)).ColorAndOpacity(ColdSteelUI::Gray(22)).Justification(ETextJustify::Center)]);
    auto FooterContent=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,12,0)
            [SAssignNew(Footer,STextBlock).Font(GunsmithUI::TextFont(14)).ColorAndOpacity(ColdSteelUI::TextSecondary).AutoWrapText(true)]
        +SHorizontalBox::Slot().AutoWidth().Padding(0,0,4,0)[SNew(SBox).WidthOverride(112)
            [Button(TEXT("取消"),[this](){CastChecked<AFPSGAMEPlayerController>(GetOwningPlayer())->CloseEnhancement();})]]
        +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(112)[ConfirmControl.ToSharedRef()]];
    auto Content=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(22,18,22,16)[Header]
        +SVerticalBox::Slot().FillHeight(1).Padding(18,0)[SAssignNew(BodyHost,SBox)]
        +SVerticalBox::Slot().AutoHeight().Padding(22,14,22,18)[FooterContent];
    UpdateResponsiveLayout();
    return SNew(SDPIScaler).DPIScale_Lambda([this](){return 1.f/ColdSteelUI::PixelScale(this);})
        [SNew(SOverlay)
            +SOverlay::Slot()[SNew(SSimpleGradient).StartColor(FLinearColor(.075f,.075f,.075f)).EndColor(FLinearColor(.24f,.24f,.24f)).Orientation(Orient_Vertical)]
            +SOverlay::Slot()[SNew(SSimpleGradient).StartColor(FLinearColor(1,1,1,.025f)).EndColor(FLinearColor(0,0,0,.25f)).Orientation(Orient_Horizontal)]
            +SOverlay::Slot()[Content]];
}

void UColdSteelEnhancementWidget::UpdateResponsiveLayout()
{
    if(!BodyHost||!RailContent||!CenterContent||!InspectorContent)return;
    FVector2D Size=BodyHost->GetCachedGeometry().GetLocalSize();if(Size.X<100)Size=FVector2D(1500,740);
    const int32 Mode=Size.X<740?3:(Size.X<1100||Size.Y<520)?2:Size.X<1450?1:0;
    if(LayoutMode==Mode)return;
    LayoutMode=Mode;const float RailWidth=Mode==0?208.f:184.f,InspectorWidth=Mode==0?438.f:394.f;
    BodyHost->SetContent(SNullWidget::NullWidget);BodyScroll.Reset();
    if(Mode<2)
        BodyHost->SetContent(SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().Padding(0,0,12,0)[SNew(SBox).WidthOverride(RailWidth)[RailContent.ToSharedRef()]]
            +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,12,0)[CenterContent.ToSharedRef()]
            +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(InspectorWidth)[InspectorContent.ToSharedRef()]]);
    else
    {
        auto Flow=SNew(SVerticalBox);
        if(Mode==2)
            Flow->AddSlot().AutoHeight()[SNew(SBox).HeightOverride(610)[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,12,0)[SNew(SBox).WidthOverride(RailWidth)[RailContent.ToSharedRef()]]
                +SHorizontalBox::Slot().FillWidth(1)[CenterContent.ToSharedRef()]]];
        else
        {
            Flow->AddSlot().AutoHeight()[SNew(SBox).HeightOverride(240)[RailContent.ToSharedRef()]];
            Flow->AddSlot().AutoHeight().Padding(0,12,0,0)[SNew(SBox).HeightOverride(530)[CenterContent.ToSharedRef()]];
        }
        Flow->AddSlot().AutoHeight().Padding(0,12,0,0)
            [SNew(SBox).HeightOverride_Lambda([this](){return FMath::Max(600.f,float(BodyHost->GetCachedGeometry().GetLocalSize().Y));})[InspectorContent.ToSharedRef()]];
        BodyHost->SetContent(SAssignNew(BodyScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6))
            .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)+SScrollBox::Slot()[Flow]);
    }
}
