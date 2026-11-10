#include "ColdSteelEnhancementWidget.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelEnhancementLayoutMetrics.h"
#include "GunsmithUIStyle.h"
#include "M4GunsmithWidget.h"
#include "SM4PreviewSurface.h"
#include "SColdSteelArcaneSeal.h"
#include "../FPSGAMEPlayerController.h"
#include "Engine/Texture2D.h"
#include "Blueprint/WidgetLayoutLibrary.h"
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
#include "Widgets/Input/SSearchBox.h"
#include "Widgets/Images/SImage.h"
#include "Styling/CoreStyle.h"

TSharedRef<SWidget> UColdSteelEnhancementWidget::Label(const FString& Text,int32 Size,FLinearColor Color,bool Numeric)const
{
    return SNew(STextBlock).Text(FText::FromString(Text))
        .Font(Numeric?GunsmithUI::NumberFont(Size):GunsmithUI::TextFont(Size,Size>=16))
        .ColorAndOpacity(Color).AutoWrapText(false).OverflowPolicy(ETextOverflowPolicy::Ellipsis)
        .ToolTipText(FText::FromString(Text)).Justification(Numeric?ETextJustify::Right:ETextJustify::Left);
}

TSharedRef<SButton> UColdSteelEnhancementWidget::Button(const FString& Text,TFunction<void()> Action,bool Primary,bool Selected,bool Enabled)
{
    return SNew(SButton).ButtonStyle(Primary?&PrimaryStyle:Selected?&SelectedStyle:&Normal)
        .ContentPadding(FMargin(12,0)).HAlign(HAlign_Fill).VAlign(VAlign_Center).IsEnabled(Enabled)
        .OnClicked_Lambda([Action](){Action();return FReply::Handled();})
        [SNew(SBox).MinDesiredHeight(ColdSteelUI::ActionHeight).VAlign(VAlign_Center)
            [SNew(STextBlock).Text(FText::FromString(Text)).Font(GunsmithUI::TextFont(14,true))
                .ColorAndOpacity(Primary?ColdSteelUI::Gray(22):ColdSteelUI::TextPrimary).AutoWrapText(false)
                .OverflowPolicy(ETextOverflowPolicy::Ellipsis).Justification(ETextJustify::Center)]];
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
    SetIsFocusable(true);LayoutMode=-1;bClosing=false;
    PanelBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius);
    GlassFallback=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius);
    RowBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::AttributeRow,4,ColdSteelUI::Border,.5f);
    TrackDone=ColdSteelUI::RoundedBrush(ColdSteelUI::Enhanced,2,FLinearColor::Transparent,0);
    TrackNext=ColdSteelUI::RoundedBrush(ColdSteelUI::Accent,2,FLinearColor::Transparent,0);
    TrackIdle=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(64),2,FLinearColor::Transparent,0);
    FlashBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(255,30),ColdSteelUI::PanelRadius,ColdSteelUI::Accent,1.5f);
    Normal=ColdSteelUI::ButtonStyle();
    Normal.SetNormalPadding(FMargin(0));Normal.SetPressedPadding(FMargin(0));
    SelectedStyle=Normal;SelectedStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius,ColdSteelUI::Accent));
    PrimaryStyle=Normal;PrimaryStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::Accent,ColdSteelUI::ButtonRadius));
    PrimaryStyle.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::TextPrimary,ColdSteelUI::ButtonRadius));
    PrimaryStyle.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(174),ColdSteelUI::ButtonRadius));
    PrimaryStyle.SetDisabled(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(85),ColdSteelUI::ButtonRadius));
    EquipmentSearchStyle=FCoreStyle::Get().GetWidgetStyle<FSearchBoxStyle>("SearchBox");
    EquipmentSearchStyle.TextBoxStyle.SetFont(GunsmithUI::TextFont(14));
    EquipmentSearchStyle.TextBoxStyle.SetForegroundColor(ColdSteelUI::TextPrimary);
    EquipmentSearchStyle.TextBoxStyle.SetBackgroundImageNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,6,ColdSteelUI::Border));
    EquipmentSearchStyle.TextBoxStyle.SetBackgroundImageHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,6,ColdSteelUI::Border));
    EquipmentSearchStyle.TextBoxStyle.SetBackgroundImageFocused(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,6,ColdSteelUI::Accent));
    EquipmentSearchStyle.SetActiveFont(GunsmithUI::TextFont(14));
    Background.SetResourceObject(BackgroundTexture);Background.ImageSize=FVector2D(1672,941);
    Background.DrawAs=BackgroundTexture?ESlateBrushDrawType::Image:ESlateBrushDrawType::NoDrawType;
    if(!bWorldMode)LoadArcaneBackground();

    auto ResourceChip=[&](const FString& Definition,const FString& Mark,TSharedPtr<STextBlock>& Text)->TSharedRef<SWidget>
    {
        const FSlateBrush* Brush=MaterialIcon(Definition);const bool bPending=!MaterialBrushes.Contains(Definition);
        auto Img=SNew(SImage).Image(Brush);
        auto Tile=SNew(SBorder).BorderImage(&RowBrush).HAlign(HAlign_Center).VAlign(VAlign_Center)[Label(Mark,10,ColdSteelUI::TextSecondary)];
        const bool HasImage=Brush&&Brush->DrawAs==ESlateBrushDrawType::Image;
        Img->SetVisibility(HasImage?EVisibility::HitTestInvisible:EVisibility::Collapsed);
        Tile->SetVisibility(HasImage?EVisibility::Collapsed:EVisibility::HitTestInvisible);
        if(bPending){PendingIconImages.FindOrAdd(Definition).Add(Img);PendingIconTiles.FindOrAdd(Definition).Add(Tile);}
        return SNew(SBorder).BorderImage(&RowBrush).Padding(7,2)
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBox).WidthOverride(18).HeightOverride(18)
                    [SNew(SOverlay)+SOverlay::Slot()[Tile]+SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[Img]]]]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6,0,0,0)[SAssignNew(Text,STextBlock)
                    .Font(GunsmithUI::NumberFont(12)).ColorAndOpacity(ColdSteelUI::TextSecondary)]];
    };
    auto Header=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,12,0)
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[Label(TEXT("秘法工坊"),20,ColdSteelUI::TextPrimary)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[Label(TEXT("灵魂淬炼 · 符文铭刻"),12,ColdSteelUI::TextSecondary)]]
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,14,0)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().Padding(0,0,6,0)[ResourceChip(TEXT("souls"),TEXT("魂"),SoulChip)]
            +SHorizontalBox::Slot().AutoWidth().Padding(0,0,6,0)[ResourceChip(TEXT("enhancement_stone"),TEXT("石"),StoneChip)]
            +SHorizontalBox::Slot().AutoWidth()[ResourceChip(TEXT("magic_dust"),TEXT("尘"),DustChip)]]
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [SNew(SBox).WidthOverride(112)[Button(TEXT("Esc  返回"),[this](){CastChecked<AFPSGAMEPlayerController>(GetOwningPlayer())->CloseEnhancement();})]];

    RailContent=GlassPanel(SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,6)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("选择装备"),16,ColdSteelUI::TextPrimary)]
            +SHorizontalBox::Slot().AutoWidth()[SAssignNew(DirectoryCount,STextBlock).Font(GunsmithUI::NumberFont(12)).ColorAndOpacity(ColdSteelUI::TextTertiary)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[Label(TEXT("装备与背包"),12,ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)[SNew(SBox).HeightOverride(32)
            [SNew(SSearchBox).Style(&EquipmentSearchStyle).HintText(FText::FromString(TEXT("搜索装备")))
                .InitialText(FText::FromString(EquipmentSearch))
                .OnTextChanged_Lambda([this](const FText& Value){EquipmentSearch=Value.ToString();Refresh();})]]
        +SVerticalBox::Slot().FillHeight(1)[SAssignNew(RailScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6))
            .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
            +SScrollBox::Slot()[SAssignNew(Rail,SVerticalBox)]]);

    if(!WorkbenchPreview)WorkbenchPreview=CreateWidget<UM4GunsmithWidget>(GetOwningPlayer());
    ResetViewControl=Button(TEXT("水平复位"),[this](){WorkbenchPreview->SetSidePreview(true);});
    AimViewControl=Button(TEXT("瞄准预览"),[this](){WorkbenchPreview->SetAimPreview(true);});
    auto StageHeader=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[SAssignNew(OperationBadge,STextBlock)
            .Font(GunsmithUI::TextFont(12,true)).ColorAndOpacity(ColdSteelUI::Enhanced)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,12,0)[SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SAssignNew(ItemTitle,STextBlock).Font(GunsmithUI::TextFont(20,true))
                    .ColorAndOpacity(ColdSteelUI::TextPrimary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                +SVerticalBox::Slot().AutoHeight().Padding(0,5,0,0)[SAssignNew(ItemLevel,STextBlock).Font(GunsmithUI::TextFont(12))
                    .ColorAndOpacity(ColdSteelUI::TextSecondary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)[SAssignNew(LevelBadge,STextBlock).Font(GunsmithUI::NumberFont(24,true))
                    .ColorAndOpacity(ColdSteelUI::Enhanced)]
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)[SAssignNew(LevelMax,STextBlock)
                    .Font(GunsmithUI::TextFont(12)).ColorAndOpacity(ColdSteelUI::TextTertiary)]]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[SAssignNew(LevelTrack,SHorizontalBox)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[SAssignNew(AffixRow,SHorizontalBox)];
    auto Stage=SNew(SOverlay)
        +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill)[SNew(SImage).Image(&Background)]]
        +SOverlay::Slot()[SNew(SSimpleGradient).StartColor(ColdSteelUI::Gray(8,126)).EndColor(FLinearColor::Transparent).Orientation(Orient_Vertical)]
        +SOverlay::Slot().Padding(12,0)[SAssignNew(RitualSeal,SColdSteelArcaneSeal)]
        +SOverlay::Slot().Padding(16,0)[SNew(SVerticalBox)
            +SVerticalBox::Slot().FillHeight(.36f)[SNullWidget::NullWidget]
            +SVerticalBox::Slot().FillHeight(.48f)[SNew(SOverlay)
                +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SImage).Image(WorkbenchPreview->StandaloneBrush())
                    .Visibility_Lambda([this](){return WorkbenchPreview->HasWorkbenchCapture()?EVisibility::HitTestInvisible:EVisibility::Collapsed;})]]
                +SOverlay::Slot().Padding(26,0)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SImage)
                    .Image_Lambda([this](){return &WeaponBrush;})
                    .Visibility_Lambda([this](){return WorkbenchPreview->HasWorkbenchCapture()?EVisibility::Collapsed:EVisibility::HitTestInvisible;})]]]
            +SVerticalBox::Slot().FillHeight(.16f)[SNullWidget::NullWidget]]
        +SOverlay::Slot().VAlign(VAlign_Top).Padding(18)[StageHeader]
        +SOverlay::Slot().VAlign(VAlign_Bottom).Padding(14)[SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[SAssignNew(OutcomeText,STextBlock)
                .Font(GunsmithUI::TextFont(14,true)).ColorAndOpacity(ColdSteelUI::TextPrimary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
            +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,8,0)
                    [Label(TEXT("拖动旋转 · 滚轮缩放"),12,ColdSteelUI::TextSecondary)]
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,4,0)[SNew(SBox).WidthOverride(80)[ResetViewControl.ToSharedRef()]]
                +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(80)[AimViewControl.ToSharedRef()]]]]
        +SOverlay::Slot()[SAssignNew(FlashOverlay,SBorder).BorderImage(&FlashBrush)
            .Visibility(EVisibility::Collapsed)];
    PreviewSurface=SNew(SM4PreviewSurface).CanRotate_Lambda([this](){return WorkbenchPreview->HasWorkbenchCapture();})
        .OnOrbit_Lambda([this](FVector2D Delta){WorkbenchPreview->RotatePreview(Delta);})
        .OnZoom_Lambda([this](float Delta){WorkbenchPreview->ZoomPreview(Delta);})
        .OnReset_Lambda([this](){WorkbenchPreview->SetSidePreview(true);})[Stage];

    EnhanceControl=Button(TEXT("灵魂强化"),[this](){SelectTab(false);});
    EnchantControl=Button(TEXT("符文附魔"),[this](){SelectTab(true);});
    auto OptionHeader=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,2,0)[EnhanceControl.ToSharedRef()]
        +SHorizontalBox::Slot().FillWidth(1).Padding(2,0,0,0)[EnchantControl.ToSharedRef()];
    ScrollFilters=SNew(SHorizontalBox);
    const TCHAR* FilterNames[]={TEXT("全部"),TEXT("前缀"),TEXT("后缀")};
    for(int32 N=0;N<3;++N)
    {
        ScrollFilterControls[N]=Button(FilterNames[N],[this,N](){SetScrollFilter(N);});
        ScrollFilters->AddSlot().FillWidth(1).Padding(N?2:0,0,N<2?2:0,0)[ScrollFilterControls[N].ToSharedRef()];
    }
    // Required materials are compact text rows. Only the selectable scroll catalog scrolls.
    auto MaterialsBody=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,6)[SNew(STextBlock)
            .Text_Lambda([this](){return FText::FromString(bEnchant?TEXT("选择卷轴"):TEXT("所需材料"));})
            .Font(GunsmithUI::TextFont(16,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[SNew(STextBlock)
            .Text(FText::FromString(TEXT("仅显示背包持有的卷轴 · 横向滚动选择")))
            .Font(GunsmithUI::TextFont(12)).ColorAndOpacity(ColdSteelUI::TextTertiary).AutoWrapText(false)
            .OverflowPolicy(ETextOverflowPolicy::Ellipsis)
            .Visibility_Lambda([this](){return bEnchant?EVisibility::Visible:EVisibility::Collapsed;})]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,6)[ScrollFilters.ToSharedRef()]
        +SVerticalBox::Slot().AutoHeight()[SNew(SBox).HeightOverride(170)
            .Visibility_Lambda([this](){return bEnchant?EVisibility::Visible:EVisibility::Collapsed;})
            [SAssignNew(OptionScroll,SScrollBox).Orientation(Orient_Horizontal).ScrollBarThickness(FVector2D(6,6))
                .ScrollBarAlwaysVisible(false).AllowOverscroll(EAllowOverscroll::No)
                .ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
                .WheelScrollMultiplier(2.f).AnimateWheelScrolling(false)
                +SScrollBox::Slot()[SAssignNew(Options,SHorizontalBox)]]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,6)[SNew(STextBlock)
            .Text(FText::FromString(TEXT("本次消耗"))).Font(GunsmithUI::TextFont(14,true))
            .ColorAndOpacity(ColdSteelUI::TextPrimary).AutoWrapText(false)
            .Visibility_Lambda([this](){return bEnchant?EVisibility::Visible:EVisibility::Collapsed;})]
        +SVerticalBox::Slot().AutoHeight()[SAssignNew(Costs,SVerticalBox)];
    auto MaterialChoices=GlassPanel(MaterialsBody);
    if(!bWorldMode)CenterContent=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[OptionHeader]
        +SVerticalBox::Slot().FillHeight(1)[SNew(SBorder).BorderImage(&PanelBrush).Padding(1).Clipping(EWidgetClipping::ClipToBounds)[PreviewSurface.ToSharedRef()]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,0)[MaterialChoices];

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
        +SVerticalBox::Slot().AutoHeight()[SNew(SBox).HeightOverride_Lambda([this](){return bEnchant?144.f:76.f;})
            [SNew(SScrollBox).ScrollBarThickness(FVector2D(6,6)).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
                +SScrollBox::Slot()[SAssignNew(ProjectSummary,SVerticalBox)]]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,8)[SNew(STextBlock).Text_Lambda([this](){return FText::FromString(bEnchant?TEXT("附魔后数值"):TEXT("强化后数值"));}).Font(GunsmithUI::TextFont(16,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,2,0)[CurrentCompare.ToSharedRef()]
            +SHorizontalBox::Slot().FillWidth(1).Padding(2,0,0,0)[BaseCompare.ToSharedRef()]]
        +SVerticalBox::Slot().AutoHeight()[TableHeader]
        +SVerticalBox::Slot().FillHeight(1)[SAssignNew(OverviewScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6))
            .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
            +SScrollBox::Slot()[SAssignNew(Inspector,SVerticalBox)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[Label(TEXT("绿色 增强 / 红色 削弱 / 灰色 不变"),12,ColdSteelUI::TextTertiary)]);

    ConfirmControl=Button(TEXT("确认强化"),[this](){Confirm();},true);
    ConfirmControl->SetContent(SNew(SBox).MinDesiredHeight(ColdSteelUI::ActionHeight).VAlign(VAlign_Center)
        [SAssignNew(ConfirmText,STextBlock).Font(GunsmithUI::TextFont(14,true)).ColorAndOpacity(ColdSteelUI::Gray(22)).Justification(ETextJustify::Center)]);
    if(bWorldMode)
    {
        // Real tabletop remains visible. One outer blur owns the entire panel;
        // internal sections use the shared neutral row surface, never another blur.
        Stage->ClearChildren();PreviewSurface.Reset();
        MaterialChoices=SNullWidget::NullWidget;InspectorContent.Reset();RailContent.Reset();
        auto Section=[&](TSharedRef<SWidget> Content)->TSharedRef<SWidget>
        {return SNew(SBorder).BorderImage(&RowBrush).Padding(12)[Content];};
        auto WorldMaterials=Section(MaterialsBody);
        WorldMaterials->SetVisibility(TAttribute<EVisibility>::CreateLambda([this]()
            {return bEnchant||!ItemId.IsEmpty()?EVisibility::Visible:EVisibility::Collapsed;}));

        auto WorldDetails=Section(SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[SNew(STextBlock)
                .Text_Lambda([this](){return FText::FromString(bEnchant?TEXT("附魔项目"):TEXT("强化项目"));})
                .Font(GunsmithUI::TextFont(16,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
            +SVerticalBox::Slot().AutoHeight()[ProjectSummary.ToSharedRef()]
            +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,8)[SNew(STextBlock).Text_Lambda([this](){return FText::FromString(bEnchant?TEXT("附魔后数值"):TEXT("强化后数值"));}).Font(GunsmithUI::TextFont(16,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)]
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,2,0)[CurrentCompare.ToSharedRef()]
                +SHorizontalBox::Slot().FillWidth(1).Padding(2,0,0,0)[BaseCompare.ToSharedRef()]]
            +SVerticalBox::Slot().AutoHeight()[TableHeader]
            +SVerticalBox::Slot().AutoHeight()[Inspector.ToSharedRef()]
            +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[Label(TEXT("绿色 增强 / 红色 削弱 / 灰色 不变"),12,ColdSteelUI::TextTertiary)]);
        WorldDetails->SetVisibility(TAttribute<EVisibility>::CreateLambda([this]()
            {return ItemId.IsEmpty()?EVisibility::Collapsed:EVisibility::Visible;}));
        // Old fullscreen containers are not attached in world mode.
        InspectorContent.Reset();RailContent.Reset();
        auto EscrowCard=Section(SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)
                [Label(TEXT("工作台暂存"),16,ColdSteelUI::TextPrimary)]
            +SVerticalBox::Slot().AutoHeight()[StageHeader]
            +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[SNew(STextBlock)
                .Text_Lambda([this](){return FText::FromString(ItemId.IsEmpty()
                    ?TEXT("从背包或装备栏放入武器，开始强化或附魔。")
                    :TEXT("靠近台上装备即可选中；右键取回，或按住拖回背包。"));})
                .Font(GunsmithUI::TextFont(12)).ColorAndOpacity(ColdSteelUI::TextSecondary).AutoWrapText(true)]);
        auto RetrieveControl=Button(TEXT("取回背包"),[this](){SelectItem(TEXT(""));});
        RetrieveControl->SetEnabled(TAttribute<bool>::CreateLambda([this](){return !ItemId.IsEmpty();}));
        RetrieveControl->SetToolTipText(FText::FromString(TEXT("将暂存武器取回背包；空间不足时仍保留在工作台。")));
        auto WorldBody=SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight()[EscrowCard]
            +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,0)[WorldMaterials]
            +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,0)[WorldDetails];
        auto Controls=SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Label(TEXT("秘法工作台"),20,ColdSteelUI::TextPrimary)]
                +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("Esc 返回"),[this](){CastChecked<AFPSGAMEPlayerController>(GetOwningPlayer())->CloseEnhancement();})]]
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)[OptionHeader]
            +SVerticalBox::Slot().FillHeight(1)[SAssignNew(BodyScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6))
                .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
                +SScrollBox::Slot()[WorldBody]]
            +SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[SNew(STextBlock)
                .Text_Lambda([this](){return FText::FromString(ItemId.IsEmpty()
                    ?TEXT("工作台为空 · 放入后可操作")
                    :TEXT("武器已暂存 · 关闭面板不会自动取回"));})
                .Font(GunsmithUI::TextFont(12)).ColorAndOpacity(ColdSteelUI::TextSecondary)
                .AutoWrapText(false).OverflowPolicy(ETextOverflowPolicy::Ellipsis)
                .ToolTipText(FText::FromString(TEXT("暂存武器不占用背包或装备槽。关闭面板后仍保留，重新打开可继续操作或取回。")))]
            +SVerticalBox::Slot().AutoHeight().Padding(0,6,0,8)[SAssignNew(Footer,STextBlock)
                .Font(GunsmithUI::TextFont(12)).ColorAndOpacity(ColdSteelUI::TextSecondary)
                .AutoWrapText(false).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
            +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,2,0)[RetrieveControl]
                +SHorizontalBox::Slot().FillWidth(1).Padding(2,0,0,0)[ConfirmControl.ToSharedRef()]];
        ManagementSurface=GlassPanel(Controls);
        // Keep a readable 410 px content width at very narrow sizes and scroll
        // horizontally rather than reducing glyph size or the inventory geometry.
        return SNew(SDPIScaler).DPIScale_Lambda([this](){return 1.f/ColdSteelUI::PixelScale(this);})
            [SNew(SOverlay).Visibility(EVisibility::SelfHitTestInvisible)
                // Only the unobstructed scene receives world-item input; never cover the backpack.
                +SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top)
                .Padding(TAttribute<FMargin>::CreateLambda([this](){const auto L=FColdSteelEnhancementLayoutMetrics::ForViewport(UWidgetLayoutLibrary::GetViewportSize(this));
                    return FMargin(L.ScenePosition.X,L.ScenePosition.Y,0,0);}))
                [SNew(SBox)
                    .WidthOverride_Lambda([this](){return FColdSteelEnhancementLayoutMetrics::ForViewport(UWidgetLayoutLibrary::GetViewportSize(this)).SceneSize.X;})
                    .HeightOverride_Lambda([this](){return FColdSteelEnhancementLayoutMetrics::ForViewport(UWidgetLayoutLibrary::GetViewportSize(this)).SceneSize.Y;})
                    [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("NoBrush")).Padding(0)]]
                +SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top)
                .Padding(TAttribute<FMargin>::CreateLambda([this](){const auto L=FColdSteelEnhancementLayoutMetrics::ForViewport(UWidgetLayoutLibrary::GetViewportSize(this));
                    return FMargin(L.PanelPosition.X,L.PanelPosition.Y,0,0);}))
                [SNew(SBox)
                    .WidthOverride_Lambda([this](){return FColdSteelEnhancementLayoutMetrics::ForViewport(UWidgetLayoutLibrary::GetViewportSize(this)).PanelSize.X;})
                    .HeightOverride_Lambda([this](){return FColdSteelEnhancementLayoutMetrics::ForViewport(UWidgetLayoutLibrary::GetViewportSize(this)).PanelSize.Y;})
                    .Clipping(EWidgetClipping::ClipToBounds)
                    [SNew(SScrollBox).Orientation(Orient_Horizontal).ScrollBarThickness(FVector2D(6,6))
                        .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
                        +SScrollBox::Slot()[SNew(SBox)
                            .WidthOverride_Lambda([this](){return FMath::Max(410.f,float(FColdSteelEnhancementLayoutMetrics::ForViewport(UWidgetLayoutLibrary::GetViewportSize(this)).PanelSize.X));})
                            .HeightOverride_Lambda([this](){return FMath::Max(1.f,float(FColdSteelEnhancementLayoutMetrics::ForViewport(UWidgetLayoutLibrary::GetViewportSize(this)).PanelSize.Y)-6.f);})
                            [ManagementSurface.ToSharedRef()]]]]];
    }
    auto FooterContent=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,12,0)
            [SAssignNew(Footer,STextBlock).Font(GunsmithUI::TextFont(14)).ColorAndOpacity(ColdSteelUI::TextSecondary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
        +SHorizontalBox::Slot().AutoWidth().Padding(0,0,4,0)[SNew(SBox).WidthOverride(112)
            [Button(TEXT("取消"),[this](){CastChecked<AFPSGAMEPlayerController>(GetOwningPlayer())->CloseEnhancement();})]]
        +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(152)[ConfirmControl.ToSharedRef()]];
    auto Content=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(22,18,22,16)[SNew(SScrollBox).Orientation(Orient_Horizontal)
            .ScrollBarThickness(FVector2D(4,4)).AllowOverscroll(EAllowOverscroll::No)
            +SScrollBox::Slot()[SNew(SBox).MinDesiredWidth_Lambda([this](){return FMath::Max(640.f,float(BodyHost?BodyHost->GetCachedGeometry().GetLocalSize().X:0.f)-8.f);})[Header]]]
        +SVerticalBox::Slot().FillHeight(1).Padding(18,0)[SAssignNew(BodyHost,SBox)]
        +SVerticalBox::Slot().AutoHeight().Padding(22,14,22,18)[FooterContent];
    UpdateResponsiveLayout();
    return SNew(SDPIScaler).DPIScale_Lambda([this](){return 1.f/ColdSteelUI::PixelScale(this);})
        [SNew(SOverlay)
            +SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(ColdSteelUI::Gray(12))]
            +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill)[SNew(SImage).Image(&Background).ColorAndOpacity(FLinearColor(.78f,.78f,.78f,1))]]
            +SOverlay::Slot()[SNew(SSimpleGradient).StartColor(ColdSteelUI::Gray(8,80)).EndColor(ColdSteelUI::Gray(8,120)).Orientation(Orient_Vertical)]
            +SOverlay::Slot()[Content]];
}

void UColdSteelEnhancementWidget::UpdateResponsiveLayout()
{
    if(bWorldMode||!BodyHost||!RailContent||!CenterContent||!InspectorContent)return;
    FVector2D Size=BodyHost->GetCachedGeometry().GetLocalSize();if(Size.X<100)Size=FVector2D(1500,740);
    const int32 Mode=Size.X<760?3:(Size.X<1240||Size.Y<650)?2:Size.X<1450?1:0;
    if(LayoutMode==Mode)return;
    LayoutMode=Mode;const float RailWidth=Mode==0?220.f:196.f,InspectorWidth=Mode==0?440.f:410.f;
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
            Flow->AddSlot().AutoHeight()[SNew(SBox).HeightOverride(720)[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,12,0)[SNew(SBox).WidthOverride(RailWidth)[RailContent.ToSharedRef()]]
                +SHorizontalBox::Slot().FillWidth(1)[CenterContent.ToSharedRef()]]];
        else
        {
            Flow->AddSlot().AutoHeight()[SNew(SBox).HeightOverride(240)[RailContent.ToSharedRef()]];
            Flow->AddSlot().AutoHeight().Padding(0,12,0,0)[SNew(SBox).HeightOverride(720)[CenterContent.ToSharedRef()]];
        }
        Flow->AddSlot().AutoHeight().Padding(0,12,0,0)
            [SNew(SBox).HeightOverride_Lambda([this](){return FMath::Max(700.f,float(BodyHost->GetCachedGeometry().GetLocalSize().Y));})[InspectorContent.ToSharedRef()]];
        BodyHost->SetContent(SAssignNew(BodyScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6))
            .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)+SScrollBox::Slot()[Flow]);
    }
}
