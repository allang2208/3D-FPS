#include "DevelopmentItemPicker.h"
#include "ColdSteelTextToolTip.h"
#include "ColdSteelScrollBar.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SComboButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

void UDevelopmentItemPicker::SetOptions(const TArray<FColdSteelCatalogEntry>& Entries, const FString& Selected, bool bCenterCaption)
{
    CloseMenu();
    Options = Entries;
    SelectedDefinition = Selected;
    bCenteredCaption = bCenterCaption;
    SetPixelScale(PixelScale);
    RefreshCaption();
}

void UDevelopmentItemPicker::SetSelectedOption(const FString& Selected)
{
    if (SelectedDefinition == Selected) return;
    CloseMenu();
    SelectedDefinition = Selected;
    RefreshCaption();
}

FSlateFontInfo UDevelopmentItemPicker::OptionFont(float Size,bool bMedium) const
{return bPhysicalFontSizes?GunsmithUI::TextFont(Size/PixelScale,bMedium):ColdSteelUI::TextFont(Size/PixelScale,bMedium);}

void UDevelopmentItemPicker::SetPixelScale(float Scale)
{
    // 视口／DPI 改变时收起旧几何的菜单，下次展开使用当前尺寸和字号。
    CloseMenu();
    PixelScale = FMath::Max(.01f, Scale);
    const float StyleScale=bPhysicalFontSizes?PixelScale:1.f/PixelScale;
    ComboStyle = FCoreStyle::Get().GetWidgetStyle<FComboButtonStyle>(TEXT("ComboButton"));
    ComboStyle.ButtonStyle = ColdSteelUI::ButtonStyle(StyleScale);
    ComboStyle.DownArrowImage.TintColor = ColdSteelUI::TextSecondary;
    ComboStyle.MenuBorderBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback, ColdSteelUI::ButtonRadius / PixelScale);
    ComboStyle.MenuBorderPadding = FMargin(4.f / PixelScale);
    if (bCenteredCaption)
    {
        ComboStyle.DownArrowImage.ImageSize = FVector2D(8.f, 8.f) / PixelScale;
        ComboStyle.DownArrowPadding = FMargin(4.f / PixelScale, 0.f, 0.f, 0.f);
    }
    RowStyle = ColdSteelUI::ButtonStyle(StyleScale);
    RowStyle.SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent, ColdSteelUI::ButtonRadius / PixelScale, FLinearColor::Transparent, 0.f));
    SelectedRowStyle = RowStyle;
    SelectedRowStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, ColdSteelUI::ButtonRadius / PixelScale, ColdSteelUI::Accent));
    if (Choice) Choice->SetButtonContentPadding(FMargin(bCenteredCaption ? 22.f : 10.f, 4.f, 10.f, 4.f) * (1.f / PixelScale));
    if (Caption)
    {
        Caption->SetFont(OptionFont(14.f));
        Caption->SetJustification(bCenteredCaption ? ETextJustify::Center : ETextJustify::Left);
    }
}

TSharedRef<SWidget> UDevelopmentItemPicker::RebuildWidget()
{
    SetPixelScale(ColdSteelUI::PixelScale(this));
    SAssignNew(Choice, SComboButton)
        .ComboButtonStyle(&ComboStyle)
        .Method(EPopupMethod::UseCurrentWindow)
        .ContentPadding(FMargin(bCenteredCaption ? 22.f : 10.f, 4.f, 10.f, 4.f) * (1.f / PixelScale))
        .HAlign(HAlign_Fill)
        .OnGetMenuContent_UObject(this, &ThisClass::BuildMenu)
        .ButtonContent()
        [
            SAssignNew(Caption, STextBlock)
                .Font(OptionFont(14.f))
                .ColorAndOpacity(ColdSteelUI::TextPrimary)
                .Justification(bCenteredCaption ? ETextJustify::Center : ETextJustify::Left)
                .AutoWrapText(false)
                .OverflowPolicy(ETextOverflowPolicy::Ellipsis)
        ];
    RefreshCaption();
    return Choice.ToSharedRef();
}

void UDevelopmentItemPicker::RefreshCaption()
{
    if (!Caption) return;
    const auto* Selected = Options.FindByPredicate([this](const auto& Entry) { return Entry.Definition == SelectedDefinition; });
    const FString Text = Selected ? FString::Printf(TEXT("%s · %s"), *Selected->Group, *Selected->Name) : TEXT("暂无可选物品");
    Caption->SetText(FText::FromString(Text));
    ColdSteelToolTip::Set(*Choice, FText::FromString(Text));
}

TSharedRef<SWidget> UDevelopmentItemPicker::BuildMenu()
{
    // 只在展开时构造菜单，不在 NativeTick 解析目录或重建全部物品控件。
    const FVector2D View = UWidgetLayoutLibrary::GetViewportSize(this);
    const float Width = FMath::Min(FMath::Max(Choice->GetCachedGeometry().GetLocalSize().X, 360.f / PixelScale),
        FMath::Max(1.f, View.X - 24.f) / PixelScale);
    const float Height = FMath::Min(480.f, FMath::Max(1.f, View.Y * .5f - 48.f)) / PixelScale;
    const float InverseScale = 1.f / PixelScale;
    TSharedRef<SVerticalBox> Rows = SNew(SVerticalBox);
    TSharedPtr<SWidget> FocusItem;
    FString LastGroup, LastSubgroup;
    for (const auto& Entry : Options)
    {
        const bool bNewGroup = Entry.Group != LastGroup;
        if (bNewGroup)
        {
            Rows->AddSlot().AutoHeight().Padding(FMargin(6.f, LastGroup.IsEmpty() ? 4.f : 18.f, 6.f, 0.f) * InverseScale)
            [
                SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")))
                    .BorderBackgroundColor(ColdSteelUI::HeaderTint).Padding(FMargin(8.f, 6.f) * InverseScale)
                [
                    SNew(STextBlock).Text(FText::FromString(Entry.Group))
                        .Font(OptionFont(16.f,true))
                        .ColorAndOpacity(ColdSteelUI::TextPrimary)
                ]
            ];
            Rows->AddSlot().AutoHeight().Padding(FMargin(6.f, 5.f, 6.f, 6.f) * InverseScale)
            [
                SNew(SBox).HeightOverride(1.f / PixelScale)
                [
                    SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")))
                        .BorderBackgroundColor(ColdSteelUI::Border).Padding(0.f)
                ]
            ];
            LastGroup = Entry.Group;
            LastSubgroup.Reset();
        }
        if (!Entry.Subgroup.IsEmpty() && (bNewGroup || Entry.Subgroup != LastSubgroup))
        {
            Rows->AddSlot().AutoHeight().Padding(FMargin(18.f, 8.f, 8.f, 4.f) * InverseScale)
            [
                SNew(STextBlock).Text(FText::FromString(Entry.Subgroup))
                    .Font(OptionFont(14.f,true))
                    .ColorAndOpacity(ColdSteelUI::TextSecondary)
            ];
            LastSubgroup = Entry.Subgroup;
        }
        TSharedRef<SButton> Item = SNew(SButton)
            .ButtonStyle(Entry.Definition == SelectedDefinition ? &SelectedRowStyle : &RowStyle)
            .HAlign(HAlign_Fill).ContentPadding(FMargin(10.f, 7.f) * InverseScale)
            .ToolTip(ColdSteelToolTip::Make(FText::FromString(Entry.Name)))
            .OnClicked_UObject(this, &ThisClass::ChooseItem, Entry.Definition)
        [
            SNew(SBox).MinDesiredHeight((ColdSteelUI::ActionHeight - 14.f) / PixelScale).VAlign(VAlign_Center)
            [
                SNew(STextBlock).Text(FText::FromString(Entry.Name))
                    .Font(OptionFont(14.f))
                    .ColorAndOpacity(ColdSteelUI::TextPrimary).AutoWrapText(false).OverflowPolicy(ETextOverflowPolicy::Ellipsis)
            ]
        ];
        Rows->AddSlot().AutoHeight().Padding(FMargin(Entry.Subgroup.IsEmpty() ? 18.f : 28.f, 0.f, 6.f, 2.f) * InverseScale)[Item];
        if (!FocusItem || Entry.Definition == SelectedDefinition) FocusItem = Item;
    }
    TSharedRef<SScrollBox> Scroll = ColdSteelUI::ApplyGoldScroll(SNew(SScrollBox)
        .ScrollWhenFocusChanges(EScrollWhenFocusChanges::InstantScroll)
        .NavigationDestination(EDescendantScrollDestination::IntoView)
        + SScrollBox::Slot()[Rows], FVector2D(6.f, 6.f) / PixelScale, FMargin(4.f / PixelScale, 0.f, 0.f, 0.f), true);
    Choice->SetMenuContentWidgetToFocus(FocusItem);
    if (FocusItem) Scroll->ScrollDescendantIntoView(FocusItem, false);
    return SNew(SBox).WidthOverride(Width).MaxDesiredHeight(Height)[Scroll];
}

FReply UDevelopmentItemPicker::ChooseItem(FString Definition)
{
    SelectedDefinition = MoveTemp(Definition);
    RefreshCaption();
    CloseMenu();
    OnSelectionChanged.Broadcast(SelectedDefinition);
    return FReply::Handled();
}

void UDevelopmentItemPicker::CloseMenu()
{
    if (Choice) Choice->SetIsOpen(false);
}

void UDevelopmentItemPicker::ReleaseSlateResources(bool bReleaseChildren)
{
    CloseMenu();
    Super::ReleaseSlateResources(bReleaseChildren);
    Choice.Reset();
    Caption.Reset();
}
