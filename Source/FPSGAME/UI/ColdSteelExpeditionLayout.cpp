#include "ColdSteelExpeditionWidget.h"
#include "ColdSteelTextToolTip.h"
#include "ColdSteelUIStyle.h"
#include "SExpeditionButton.h"
#include "../FPSGAMEPlayerController.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "ImageUtils.h"
#include "Engine/Texture2D.h"
#include "Misc/Paths.h"
#include "Rendering/DrawElements.h"
#include "Widgets/SLeafWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SNullWidget.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/Images/SImage.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SComboButton.h"
#include "Widgets/Input/SEditableTextBox.h"

namespace
{
    // Decorative portal engraving, deliberately not presented as a dungeon map or screenshot.
    class SExpeditionPortal : public SLeafWidget
    {
    public:
        SLATE_BEGIN_ARGS(SExpeditionPortal) : _Artwork(nullptr) {}
            SLATE_ARGUMENT(const FSlateBrush*, Artwork)
        SLATE_END_ARGS()
        const FSlateBrush* Artwork=nullptr;
        void Construct(const FArguments& Args) { Artwork=Args._Artwork;SetVisibility(EVisibility::HitTestInvisible); }
        virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(280, 130); }
        virtual int32 OnPaint(const FPaintArgs&, const FGeometry& Geometry, const FSlateRect&,
            FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle&, bool) const override
        {
            const FVector2D Size = Geometry.GetLocalSize();
            if(Artwork && Artwork->GetResourceObject() && Size.X>0 && Size.Y>0)
            {
                FSlateBrush Brush=*Artwork;
                const float SourceAspect=Brush.ImageSize.X/Brush.ImageSize.Y;
                const float TargetAspect=Size.X/Size.Y;
                const FVector2D UVSize=TargetAspect>SourceAspect?FVector2D(1,SourceAspect/TargetAspect):FVector2D(TargetAspect/SourceAspect,1);
                const FVector2D UVMin=(FVector2D(1,1)-UVSize)*.5;
                Brush.SetUVRegion(FBox2f(FVector2f(UVMin),FVector2f(UVMin+UVSize)));
                FSlateDrawElement::MakeBox(Elements,Layer,Geometry.ToPaintGeometry(),&Brush,ESlateDrawEffect::None,FLinearColor::White);
                return Layer;
            }
            const float Center = Size.X * .79f, Top = 12.f, Bottom = Size.Y - 12.f;
            const float HalfWidth = FMath::Min(Size.X * .17f, 100.f);
            for (int32 Index = 0; Index < 5; ++Index)
            {
                const float Inset = Index * 8.f;
                TArray<FVector2D> Points = {
                    FVector2D(Center - HalfWidth + Inset, Bottom), FVector2D(Center - HalfWidth + Inset, Top + Inset),
                    FVector2D(Center + HalfWidth - Inset, Top + Inset), FVector2D(Center + HalfWidth - Inset, Bottom)};
                FSlateDrawElement::MakeLines(Elements, Layer, Geometry.ToPaintGeometry(), Points,
                    ESlateDrawEffect::None, ColdSteelUI::Gray(184, 42 - Index * 5), true, 1.f);
            }
            return Layer;
        }
    };
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::Label(const FString& Text, int32 Size, FLinearColor Color, bool Numeric, bool Wrap) const
{
    return SNew(STextBlock).Text(FText::FromString(Text))
        .Font(Numeric ? ColdSteelUI::NumberFont(Size * .75f) : ColdSteelUI::TextFont(Size * .75f, Size >= 16))
        .ColorAndOpacity(Color).AutoWrapText(Wrap);
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::Card(TSharedRef<SWidget> Content, float Inset)
{
    return SNew(SBorder).BorderImage(&CardBrush).Padding(Inset)[Content];
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::Divider(EOrientation Orientation) const
{
    auto Line = SNew(SBox).Visibility(EVisibility::HitTestInvisible)
        [SNew(SImage).Image(FCoreStyle::Get().GetBrush("WhiteBrush")).ColorAndOpacity(ColdSteelUI::Border)];
    if (Orientation == Orient_Vertical) Line->SetWidthOverride(1.f);
    else Line->SetHeightOverride(1.f);
    return Line;
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::Row(const FString& Name, const FString& Value, bool Numeric) const
{
    return SNew(SHorizontalBox)
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 7, 12, 7)
            [SNew(SBox).MinDesiredWidth(84)[SNew(STextBlock).Text(FText::FromString(Name))
                .Font(ColdSteelUI::TextFont(14*.75f)).ColorAndOpacity(ColdSteelUI::TextPrimary).AutoWrapText(false)]]
        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0, 7)
            [SNew(STextBlock).Text(FText::FromString(Value))
                .Font(Numeric?ColdSteelUI::NumberFont(14*.75f):ColdSteelUI::TextFont(14*.75f))
                .ColorAndOpacity(ColdSteelUI::TextPrimary).Justification(ETextJustify::Right).AutoWrapText(false).OverflowPolicy(ETextOverflowPolicy::Ellipsis).ToolTip(ColdSteelToolTip::Make(FText::FromString(Value)))];
}

TSharedRef<SButton> UColdSteelExpeditionWidget::Action(const FString& Text, TFunction<void()> Callback, EActionRole Role)
{
    const bool Primary = Role == EActionRole::Primary;
    const FButtonStyle& Style = Primary ? PrimaryStyle : (Role == EActionRole::Secondary ? MutedStyle : QuietStyle);
    auto Button = SNew(SExpeditionButton).ButtonStyle(&Style)
        .ContentPadding(FMargin(12, 0)).HAlign(HAlign_Fill).VAlign(VAlign_Center)
        .OnClicked_Lambda([Callback]() { Callback(); return FReply::Handled(); })
        [SNew(SBox).MinDesiredHeight(ColdSteelUI::ActionHeight).VAlign(VAlign_Center)
            [SNew(STextBlock).Text(FText::FromString(Text)).Font(ColdSteelUI::TextFont(10.5f, true))
                .ColorAndOpacity(Primary ? ColdSteelUI::Gray(22) : ColdSteelUI::TextPrimary).Justification(ETextJustify::Center)]];
    if (Primary) Button->UseDarkFocus();
    return Button;
}

TSharedRef<SButton> UColdSteelExpeditionWidget::NavigationTab(const FString& Text, TAttribute<bool> Current, FOnClicked OnClicked)
{
    const FSlateFontInfo Regular = ColdSteelUI::TextFont(10.5f);
    const FSlateFontInfo Medium = ColdSteelUI::TextFont(10.5f, true);
    return SNew(SExpeditionButton).ButtonStyle(&QuietStyle).OnClicked(OnClicked)
        .HAlign(HAlign_Center).VAlign(VAlign_Center).ContentPadding(FMargin(12, 0))
        [SNew(SBox).MinDesiredHeight(ColdSteelUI::ActionHeight)
            [SNew(SOverlay)
                +SOverlay::Slot().VAlign(VAlign_Center)
                    [SNew(STextBlock).Text(FText::FromString(Text)).AutoWrapText(false)
                        .Font_Lambda([Current, Regular, Medium]() { return Current.Get() ? Medium : Regular; })
                        .ColorAndOpacity_Lambda([Current]() { return Current.Get() ? ColdSteelUI::TextPrimary : ColdSteelUI::TextSecondary; })]
                +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(0, 0, 0, 2)
                    [SNew(SBox).WidthOverride(20).HeightOverride(2)
                        .Visibility_Lambda([Current]() { return Current.Get() ? EVisibility::HitTestInvisible : EVisibility::Hidden; })
                        [SNew(SImage).Image(FCoreStyle::Get().GetBrush("WhiteBrush")).ColorAndOpacity(ColdSteelUI::Accent)]]]];
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::BuildCatalog()
{
    FilterButtons.Reset();Search.Reset();
    auto Filters = SNew(SHorizontalBox).Visibility_Lambda([this]() { return Destinations.Num()>1 ? EVisibility::Visible : EVisibility::Collapsed; });
    for (int32 Index = 0; Index < 2; ++Index)
    {
        TSharedPtr<SButton> Button;
        Filters->AddSlot().FillWidth(1).Padding(Index ? 2 : 0, 0, Index ? 0 : 2, 0)
            [SAssignNew(Button, SExpeditionButton).ButtonStyle(&QuietStyle)
                .ContentPadding(FMargin(8, 0)).HAlign(HAlign_Center).VAlign(VAlign_Center)
                .OnClicked_Lambda([this, Index]() { bAvailableOnly = Index == 1; RefreshList(); return FReply::Handled(); })
                [SNew(SBox).MinDesiredHeight(36).VAlign(VAlign_Center)[Label(Index ? TEXT("可出征") : TEXT("全部"), 14, ColdSteelUI::TextPrimary, false, false)]]];
        FilterButtons.Add(Button);
    }
    return Card(SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("目的地"), 16, ColdSteelUI::HUDGold)]
                +SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Text_Lambda([this]() { return FText::AsNumber(VisibleIds.Num()); })
                    .Font(ColdSteelUI::NumberFont(10.5f)).ColorAndOpacity(ColdSteelUI::TextTertiary)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
            [SNew(SBox).MinDesiredHeight(36).Visibility_Lambda([this]() { return Destinations.Num()>1 ? EVisibility::Visible : EVisibility::Collapsed; })
                [SAssignNew(Search, SEditableTextBox).Style(&SearchStyle).Text(FText::FromString(Query))
                    .HintText(FText::FromString(TEXT("搜索目的地 / 类型")))
                    .OnTextChanged_Lambda([this](const FText& Text) { Query = Text.ToString().TrimStartAndEnd(); RefreshList(); })]]
        +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)[Filters]
        +SVerticalBox::Slot().FillHeight(1)
            [SNew(SScrollBox).ScrollBarThickness(FVector2D(6, 6)).ScrollBarVisibility(EVisibility::Visible).AllowOverscroll(EAllowOverscroll::No)
                +SScrollBox::Slot()[SAssignNew(CatalogRows, SVerticalBox)]]);
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::BuildDestinationSelector()
{
    return SNew(SHorizontalBox)
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,14,0)
            [Label(TEXT("目的地"),16,ColdSteelUI::HUDGold,false,false)]
        +SHorizontalBox::Slot().FillWidth(1)
            [SAssignNew(DestinationPicker,SComboButton).ComboButtonStyle(&DestinationStyle).ButtonStyle(&NormalStyle)
                .ForegroundColor(ColdSteelUI::TextPrimary).ContentPadding(FMargin(14,6))
                .OnGetMenuContent_Lambda([this]() -> TSharedRef<SWidget> {
                    const float Width=BodyHost?BodyHost->GetCachedGeometry().GetLocalSize().X:340.f;
                    auto Menu=SNew(SBox).WidthOverride(FMath::Clamp(Width*.4f,240.f,420.f))
                        .HeightOverride(FMath::Clamp(100.f+Destinations.Num()*108.f,200.f,440.f))[BuildCatalog()];
                    RefreshList();
                    return Menu;
                })
                .ButtonContent()
                [SNew(SBox).MinDesiredHeight(28)
                    [SNew(SHorizontalBox)
                        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                            [SNew(STextBlock).Font(ColdSteelUI::TextFont(12,true)).ColorAndOpacity(ColdSteelUI::TextPrimary)
                                .Text_Lambda([this](){return FText::FromString(Selection()?Selection()->Name:TEXT("选择地牢"));})
                                .AutoWrapText(false).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(16,0,12,0)
                            [SNew(STextBlock).Font(ColdSteelUI::TextFont(9)).ColorAndOpacity(ColdSteelUI::TextSecondary)
                                .Text_Lambda([this](){return FText::FromString(Selection()?(Selection()->bCanDepart?TEXT("可出征"):TEXT("暂未开放")):TEXT("暂无目的地"));})]]]];
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::BuildDetail()
{
    auto Tabs=SNew(SHorizontalBox);
    const TCHAR* Titles[]={TEXT("概览"),TEXT("奖励"),TEXT("规则")};
    for(int32 Index=0;Index<3;++Index)
        Tabs->AddSlot().AutoWidth().Padding(0,0,8,0)
            [NavigationTab(Titles[Index],TAttribute<bool>::CreateLambda([this,Index](){return DetailTab==Index;}),
                FOnClicked::CreateLambda([this,Index](){
                    if(DetailTab!=Index){DetailTab=Index;RefreshDetail();if(DetailScroll)DetailScroll->ScrollToStart();}
                    return FReply::Handled();
                }))];

    auto DetailContent=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[Tabs]
        +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,16)[Divider()]
        +SVerticalBox::Slot().FillHeight(1)
            [SAssignNew(DetailScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6)).AllowOverscroll(EAllowOverscroll::No)
                +SScrollBox::Slot()
                    [SNew(SBox).MinDesiredHeight_Lambda([this](){
                        return !bStackOverview&&DetailScroll?FMath::Max(0.f,DetailScroll->GetCachedGeometry().GetLocalSize().Y-2.f):0.f;
                    })[SAssignNew(DetailRows,SVerticalBox)]]];
    TSharedRef<SWidget> Body=SNullWidget::NullWidget;
    if(bStackOverview)
    {
        // One content scroll in narrow windows; preparation is part of the same flow.
        Body=Card(DetailContent,16);
    }
    else
        Body=SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(.63f).Padding(0,0,12,0)[Card(DetailContent,18)]
            +SHorizontalBox::Slot().FillWidth(.37f)[BuildPreparation()];

    return SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)
            [SNew(SBorder).BorderImage(&HeroBrush).Padding(0)
                [SNew(SBox).HeightOverride_Lambda([this](){
                    const float Height=BodyHost?BodyHost->GetCachedGeometry().GetLocalSize().Y:0.f;
                    return FMath::Clamp(Height*.22f,64.f,210.f);
                })
                    [SNew(SOverlay)
                        +SOverlay::Slot()[SNew(SExpeditionPortal).Artwork(&DestinationArtBrush)]
                        +SOverlay::Slot().Padding(20,12).VAlign(VAlign_Bottom)
                            [SNew(SVerticalBox)
                                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock)
                                    .Text_Lambda([this](){return FText::FromString(Selection()?Selection()->Name:TEXT("等待选择"));})
                                    .Font(ColdSteelUI::TextFont(18,true)).ColorAndOpacity(ColdSteelUI::HUDGold).AutoWrapText(true)]
                                +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[SNew(STextBlock)
                                    .Text_Lambda([this](){return FText::FromString(Selection()?Selection()->Category:TEXT("目的地档案"));})
                                    .Font(ColdSteelUI::TextFont(9)).ColorAndOpacity(ColdSteelUI::TextSecondary).AutoWrapText(true)]]]]]
        +SVerticalBox::Slot().FillHeight(1)[Body];
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::BuildPreparation()
{
    auto Content=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Label(TEXT("行前准备"),20,ColdSteelUI::HUDGold,false,false)]
                +SHorizontalBox::Slot().AutoWidth()[Action(TEXT("调整装备"),[this](){
                    if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))PC->PrepareExpeditionEquipment();
                },EActionRole::Secondary)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,12)
            [Label(TEXT("携带物资与当前武器备弹"),12,ColdSteelUI::TextTertiary)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[Divider()];
    if(bStackOverview)
        Content->AddSlot().AutoHeight()[SAssignNew(PreparationRows,SVerticalBox)];
    else
        Content->AddSlot().FillHeight(1)
            [SAssignNew(PreparationScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6)).AllowOverscroll(EAllowOverscroll::No)
                +SScrollBox::Slot()[SNew(SBox).MinDesiredHeight_Lambda([this](){
                    return PreparationScroll?FMath::Max(0.f,PreparationScroll->GetCachedGeometry().GetLocalSize().Y-2.f):0.f;
                })[SAssignNew(PreparationRows,SVerticalBox)]]];
    return Card(Content,18);
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::RebuildWidget()
{
    SetIsFocusable(true);
    LayoutMode = -1;
    DestinationArtBrush=ColdSteelUI::RoundedBrush(FLinearColor::White,ColdSteelUI::CardRadius,ColdSteelUI::Border,1);
    RefreshDestinationArtwork();
    PanelBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint, ColdSteelUI::PanelRadius);
    FallbackBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback, ColdSteelUI::PanelRadius);
    CardBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::Content, ColdSteelUI::CardRadius);
    HeroBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard, ColdSteelUI::CardRadius);
    RewardTooltipBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::ItemTooltipSurface, ColdSteelUI::CardRadius, ColdSteelUI::ItemTooltipBorder, 1);
    NormalStyle = ColdSteelUI::ButtonStyle();
    NormalStyle.SetNormalPadding(FMargin(0)).SetPressedPadding(FMargin(0));
    const FSlateBrush Clear = *FCoreStyle::Get().GetBrush("NoBrush");
    const FSlateBrush Hover = ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, ColdSteelUI::ButtonRadius, FLinearColor::Transparent, 0);
    const FSlateBrush Pressed = ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed, ColdSteelUI::ButtonRadius, FLinearColor::Transparent, 0);
    QuietStyle = NormalStyle;
    QuietStyle.SetNormal(Clear).SetHovered(Hover).SetPressed(Pressed).SetDisabled(Clear);
    MutedStyle = QuietStyle;
    MutedStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonNormal, ColdSteelUI::ButtonRadius, FLinearColor::Transparent, 0));
    SelectedStyle = NormalStyle;
    SelectedStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, ColdSteelUI::ButtonRadius));
    PrimaryStyle = NormalStyle;
    PrimaryStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::Accent, 6));
    PrimaryStyle.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::TextPrimary, 6));
    PrimaryStyle.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(174), 6));
    PrimaryStyle.SetDisabled(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(100), 6));
    DestinationStyle=FCoreStyle::Get().GetWidgetStyle<FComboButtonStyle>("ComboButton");
    DestinationStyle.SetButtonStyle(NormalStyle).SetMenuBorderBrush(CardBrush).SetMenuBorderPadding(FMargin(1));
    SearchStyle = FEditableTextBoxStyle()
        .SetFont(ColdSteelUI::TextFont(10.5f)).SetForegroundColor(ColdSteelUI::TextPrimary)
        .SetBackgroundImageNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::Content, 6))
        .SetBackgroundImageHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonNormal, 6))
        .SetBackgroundImageFocused(ColdSteelUI::RoundedBrush(ColdSteelUI::Content, 6, ColdSteelUI::Accent))
        .SetBackgroundImageReadOnly(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonDisabled, 6))
        .SetPadding(FMargin(10, 7));

    auto Confirm = Action(TEXT("确认出征"), [this]() { ConfirmDeparture(); }, EActionRole::Primary);
    Confirm->SetEnabled(TAttribute<bool>::CreateLambda([this]() { return CanConfirm(); }));
    ColdSteelToolTip::Set(*Confirm, TAttribute<FText>::CreateLambda([this]() { return BlockMessage(); }));

    auto Content = SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Label(TEXT("出征"), 20, ColdSteelUI::HUDGold)]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Action(TEXT("Esc  返回"), [this]() { Close(); })]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)[BuildDestinationSelector()]
        +SVerticalBox::Slot().FillHeight(1)[SAssignNew(BodyHost, SBox).Clipping(EWidgetClipping::ClipToBounds)]
        +SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 8)[Divider()]
        +SVerticalBox::Slot().AutoHeight()
            [SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(8, 4))
                +SWrapBox::Slot().FillLineWhenSizeLessThan(510.f).VAlign(VAlign_Center)
                    [SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock)
                            .Text_Lambda([this]() { const auto* Entry = Selection(); return FText::FromString(Entry ? (Entry->EntryCost.IsEmpty() ? TEXT("消耗待公布") : Entry->EntryCost) : TEXT("尚未选择目的地")); })
                            .Font(ColdSteelUI::TextFont(10.5f, true)).ColorAndOpacity(ColdSteelUI::TextPrimary).AutoWrapText(true)]
                        +SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)[SNew(STextBlock)
                            .Text_Lambda([this]() { return BlockMessage(); }).Font(ColdSteelUI::TextFont(9))
                            .ColorAndOpacity_Lambda([this]() { return CanConfirm() && Feedback.IsEmpty() ? ColdSteelUI::Success : ColdSteelUI::TextSecondary; }).AutoWrapText(true)]]
                +SWrapBox::Slot().FillEmptySpace(true).HAlign(HAlign_Right).VAlign(VAlign_Center)
                    [SNew(SHorizontalBox)
                        +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).MinDesiredWidth(112.f)[Confirm]]]];
    UpdateLayout();
    // Cancel UMG's canvas DPI; thresholds and typography use actual available pixels, as the other workbenches do.
    return SNew(SDPIScaler).DPIScale_Lambda([this]() { return 1.f / ColdSteelUI::PixelScale(this); })
        [SNew(SBorder).BorderBackgroundColor(ColdSteelUI::Gray(10, 225)).Padding(12).HAlign(HAlign_Center)
            [SNew(SBox).WidthOverride_Lambda([this]()
                { const float ViewWidth=UWidgetLayoutLibrary::GetViewportSize(this).X;return ViewWidth>0?FMath::Max(0.f,FMath::Min(1800.f,ViewWidth-24.f)):1800.f; })
            [SNew(SBackgroundBlur).BlurStrength(ColdSteelUI::GlassBlurStrength).BlurRadius(ColdSteelUI::GlassBlurRadius).CornerRadius(FVector4(ColdSteelUI::PanelRadius))
                .LowQualityFallbackBrush(&FallbackBrush).Padding(0)
                [SNew(SBorder).BorderImage(&PanelBrush).Padding(16)[Content]]]]];
}

void UColdSteelExpeditionWidget::RefreshDestinationArtwork()
{
    const FString File=Selection()?Selection()->ArtworkFile:FString();
    if(LoadedArtworkFile!=File)
    {
        LoadedArtworkFile=File;
        DestinationArtwork=File.IsEmpty()?nullptr:FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/File);
    }
    DestinationArtBrush.SetResourceObject(DestinationArtwork);
    if(DestinationArtwork)DestinationArtBrush.ImageSize=FVector2D(DestinationArtwork->GetSizeX(),DestinationArtwork->GetSizeY());
}

void UColdSteelExpeditionWidget::UpdateLayout()
{
    if(!BodyHost)return;
    const float Width=BodyHost->GetCachedGeometry().GetLocalSize().X;
    if(Width<100.f&&LayoutMode>=0)return;
    const bool Stack=Width>0.f&&Width<1000.f;
    const float DetailWidth=(Stack?Width:(Width-12.f)*.63f)-36.f;
    const int32 Mode=Stack?1:0;
    const int32 Columns=FMath::Clamp(FMath::FloorToInt(DetailWidth/270.f),1,3);
    const bool SingleColumn=DetailWidth<540.f;
    if(LayoutMode==Mode)
    {
        if(bSingleColumnFacts!=SingleColumn||CardColumns!=Columns)
        {bSingleColumnFacts=SingleColumn;CardColumns=Columns;RefreshDetail();}
        return;
    }
    bSingleColumnFacts=SingleColumn;bStackOverview=Stack;CardColumns=Columns;LayoutMode=Mode;
    BodyHost->SetContent(SNullWidget::NullWidget);
    DetailRows.Reset();PreparationRows.Reset();DetailScroll.Reset();PreparationScroll.Reset();
    BodyHost->SetContent(BuildDetail());
    RefreshDetail();RefreshPreparation();
}
