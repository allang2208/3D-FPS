#include "ColdSteelHUDWidget.h"
#include "ColdSteelAmmoReadout.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelStatusModel.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Engine/GameInstance.h"

#include "../FPSGAMECharacter.h"
#include "../FPSWeatherManager.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "ColdSteelUIStyle.h"

#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ProgressBar.h"
#include "Components/ScaleBox.h"
#include "Components/ScaleBoxSlot.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/Spacer.h"
#include "Components/TextBlock.h"
#include "Components/UniformGridPanel.h"
#include "Components/UniformGridSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/Texture2D.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "Input/Reply.h"
#include "InputCoreTypes.h"
#include "Misc/Paths.h"
#include "Styling/SlateTypes.h"
#include "UObject/UnrealType.h"

namespace
{
    // Layout contract: Godot reference drawer at 45% width, 3x5 gear and 18x4 storage.
    constexpr float HotbarSlotSize = 48.0f;
    constexpr float HotbarGap = 8.0f;
    constexpr int32 InventoryColumns = 18;
    constexpr int32 InventoryRows = 4;
    constexpr float TimelineCompactWidth = 360.0f;
    constexpr float TimelineExpandedWidth = 560.0f;
    constexpr int32 WeatherSegmentsPerDay = AFPSWeatherManager::ScheduleSegmentsPerDay;
    constexpr float TimelineHorizonDays = 5.0f;

    const FLinearColor DrawerHeader = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("29323AFF")));
    const FLinearColor DrawerDeep = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("0A0E11F8")));
    const FLinearColor SlotDark = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("10151AE8")));
    const FLinearColor SlotEquipped = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("283139F2")));
    const FLinearColor GridLine = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("71828B42")));
    const FLinearColor TimelineTrackColor = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("101419FF")));
    const FLinearColor TimelineLineColor = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("B5CDD92E")));
    const FLinearColor TimelineWeatherColor = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("45BFFFFF")));
    const FLinearColor TimelineCriticalColor = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("FF665CFF")));
    const FLinearColor StatusCard = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("172028D9")));
    const FLinearColor AttributeRow = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("2730397A")));
    const FLinearColor TooltipSurface = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("0B1116FA")));

    FProgressBarStyle StatusBarStyle()
    {
        FProgressBarStyle Style;
        Style.SetBackgroundImage(ColdSteelUI::RoundedBrush(
            FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("0D1419FF"))), 4.0f,
            FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("8DA5AFB0"))), 1.0f));
        Style.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White, 3.0f, FLinearColor::Transparent, 0.0f));
        return Style;
    }

    void FillSlot(UCanvasPanelSlot* Slot, const FAnchors& Anchors, const FMargin& Offsets = FMargin(0.0f), int32 ZOrder = 0)
    {
        Slot->SetAnchors(Anchors);
        Slot->SetOffsets(Offsets);
        Slot->SetZOrder(ZOrder);
    }

    bool IsWetWeather(EFPSWeatherState State)
    {
        return State == EFPSWeatherState::LightRain || State == EFPSWeatherState::Rain || State == EFPSWeatherState::Storm;
    }

    FString WeatherRegionName(const UWorld* World)
    {
        const FString Map = World ? World->GetMapName() : FString();
        if (Map.Contains(TEXT("DayNight_Lighting"))) return TEXT("天空基地");
        if (Map.Contains(TEXT("L_Normandy_FPS_Test"))) return TEXT("诺曼底村庄");
        if (Map.Contains(TEXT("L_MilitaryTrench_FPS_Test"))) return TEXT("战壕");
        if (Map.Contains(TEXT("L_TemperateHills_Initial"))) return TEXT("温带丘陵");
        return TEXT("当前区域");
    }

    FString WeatherName(EFPSWeatherState State)
    {
        switch (State)
        {
        case EFPSWeatherState::LightRain: return TEXT("小雨");
        case EFPSWeatherState::Rain: return TEXT("中雨");
        case EFPSWeatherState::Storm: return TEXT("暴风雨");
        case EFPSWeatherState::Cloudy: return TEXT("阴天");
        default: return TEXT("晴天");
        }
    }

    FString WeatherIconFile(EFPSWeatherState State)
    {
        switch (State)
        {
        case EFPSWeatherState::LightRain: return TEXT("rain-light.png");
        case EFPSWeatherState::Rain: return TEXT("rain-moderate.png");
        case EFPSWeatherState::Storm: return TEXT("rain-storm.png");
        default: return TEXT("rain-light.png");
        }
    }

    FString FormatTimelineAbsolute(float AbsoluteSeconds, float DaySeconds)
    {
        const int32 Day = FMath::Max(0, FMath::FloorToInt(AbsoluteSeconds / DaySeconds));
        const float WithinDay = FMath::Fmod(FMath::Max(0.0f, AbsoluteSeconds), DaySeconds);
        const int32 Minutes = FMath::FloorToInt((WithinDay / DaySeconds) * 24.0f * 60.0f + 0.001f) % (24 * 60);
        return FString::Printf(TEXT("第%d日 %02d:%02d"), Day + 1, Minutes / 60, Minutes % 60);
    }
}

void UColdSteelHUDWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(false);
    BuildInterface();
}

void UColdSteelHUDWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
    Super::NativeTick(MyGeometry, InDeltaTime);
    TickWarehouse(MyGeometry,InDeltaTime);
    AmmoRefreshAccumulator += InDeltaTime;
    if (AmmoRefreshAccumulator >= 0.05f)
    {
        AmmoRefreshAccumulator = 0.0f;
        RefreshAmmo();
        RefreshTopVitals();
    }
    StatusRefreshAccumulator += InDeltaTime;
    if (StatusRefreshAccumulator >= 0.10f && bInventoryOpen)
    {
        StatusRefreshAccumulator = 0.0f;
        RefreshStatus();
    }
    if (StatusTooltip && StatusTooltip->IsVisible()) UpdateStatusTooltipPlacement();

    TimelineRefreshAccumulator += InDeltaTime;
    TimelinePulse += InDeltaTime;
    if (TimelineRefreshAccumulator >= 0.25f)
    {
        TimelineRefreshAccumulator = 0.0f;
        RefreshEventTimeline();
    }
    if (TimelineEventLine && TimelineMarkerImage && bTimelineHasEvent)
    {
        const float Period = bTimelineEventActive ? 0.8f : (bTimelineContainsStorm ? 1.15f : 2.0f);
        const float Wave = FMath::Sin(TimelinePulse * 2.0f * PI / Period) * 0.5f + 0.5f;
        TimelineEventLine->SetRenderOpacity(0.68f + 0.28f * Wave);
        TimelineMarkerImage->SetRenderOpacity(0.82f + 0.18f * Wave);
    }

    const float Target = bInventoryOpen ? 1.0f : 0.0f;
    DrawerProgress = FMath::FInterpConstantTo(DrawerProgress, Target, InDeltaTime, 4.0f);
    if (InventoryPanel)
    {
        const float DrawerWidth = FMath::Max(1.0f, MyGeometry.GetLocalSize().X * 0.45f);
        InventoryPanel->SetRenderTranslation(FVector2D((1.0f - DrawerProgress) * DrawerWidth, 0.0f));
    }
    if (InventoryBackdrop)
    {
        InventoryBackdrop->SetRenderOpacity(DrawerProgress);
    }
    if (InventoryBlur)
    {
        InventoryBlur->SetRenderOpacity(DrawerProgress);
    }
    if (EquipmentTooltip && EquipmentTooltip->IsVisible() && !bEquipmentTooltipPinned)
    {
        UpdateEquipmentTooltipPlacement();
    }
    if (!bInventoryOpen && DrawerProgress <= KINDA_SMALL_NUMBER)
    {
        InventoryPanel->SetVisibility(ESlateVisibility::Collapsed);
        InventoryBackdrop->SetVisibility(ESlateVisibility::Collapsed);
        InventoryBlur->SetVisibility(ESlateVisibility::Collapsed);
    }
}

FReply UColdSteelHUDWidget::NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent)
{
    if (HandlePanelShortcut(InKeyEvent.GetKey(), InKeyEvent.IsRepeat())) return FReply::Handled();
    if (InKeyEvent.GetKey() == EKeys::Escape && TimelinePopover && TimelinePopover->IsVisible())
    {
        TimelinePopover->SetVisibility(ESlateVisibility::Collapsed);
        return FReply::Handled();
    }
    if (bInventoryOpen)
    {
        const FKey Key = InKeyEvent.GetKey();
        if (Key == EKeys::Escape)
        {
            SetInventoryOpen(false);
            return FReply::Handled();
        }
    }
    return Super::NativeOnKeyDown(InGeometry, InKeyEvent);
}

UWidget* UColdSteelHUDWidget::NativeGetDesiredFocusTarget() const
{
    return bInventoryOpen && CloseButton ? static_cast<UWidget*>(CloseButton.Get()) : nullptr;
}

void UColdSteelHUDWidget::ToggleInventory()
{
    SetInventoryOpen(!bInventoryOpen);
}

bool UColdSteelHUDWidget::HandlePanelShortcut(const FKey& Key, bool bRepeat)
{
    if (Key != EKeys::Tab && Key != EKeys::CapsLock) return false;
    if (bRepeat) return true;
    const bool bStatus = Key == EKeys::CapsLock;
    if (bInventoryOpen && (Key == EKeys::Tab || bStatusTabActive == bStatus))
    {
        SetInventoryOpen(false);
        return true;
    }
    UWidgetBlueprintLibrary::CancelDragDrop();
    if (auto* Scroll = Cast<UScrollBox>(EquipmentPage))
        if (auto* Board = Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0))) Board->CancelInteraction();
    if (bStatus) CloseWarehouse();
    SetInventoryTab(bStatus);
    SetInventoryOpen(true);
    if (CloseButton) CloseButton->SetKeyboardFocus();
    return true;
}

void UColdSteelHUDWidget::BuildInterface()
{
    UCanvasPanel* Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("ColdSteelRoot"));
    WidgetTree->RootWidget = Root;
    BuildAmmoReadout(Root);
    BuildHotbar(Root);
    BuildEventTimeline(Root);
    BuildInventory(Root);
    BuildCharacterSummary(Root);
    BuildWarehouse(Root);
    RefreshAmmo();
    RefreshEventTimeline(true);
}

void UColdSteelHUDWidget::BuildAmmoReadout(UCanvasPanel* Root)
{
    AmmoReadout=CreateWidget<UColdSteelAmmoReadout>(GetOwningPlayer());
    UCanvasPanelSlot* CanvasSlot = Root->AddChildToCanvas(AmmoReadout);
    CanvasSlot->SetAnchors(FAnchors(1.0f, 1.0f));
    CanvasSlot->SetAlignment(FVector2D(1.0f, 1.0f));
    CanvasSlot->SetPosition(FVector2D(-ReferenceUnits(20), -ReferenceUnits(20)));
    CanvasSlot->SetSize(FVector2D(ReferenceUnits(184), ReferenceUnits(38)));
    CanvasSlot->SetZOrder(10);
}

void UColdSteelHUDWidget::BuildHotbar(UCanvasPanel* Root)
{
    UBorder* Surface = MakeSurface(FLinearColor(0.063f, 0.082f, 0.102f, 0.90f), 10.0f, ColdSteelUI::Border);
    Surface->SetPadding(FMargin(ReferenceUnits(9)));
    UHorizontalBox* Row = WidgetTree->ConstructWidget<UHorizontalBox>();
    Surface->SetContent(Row);

    const TArray<TPair<FString, FString>> Slots = {
        {TEXT("Q"), TEXT("")}, {TEXT("E"), TEXT("")}, {TEXT("X"), TEXT("")},
        {TEXT("1"), TEXT("")}, {TEXT("2"), TEXT("")}, {TEXT("3"), TEXT("")}, {TEXT("4"), TEXT("")}
    };
    for (int32 Index = 0; Index < Slots.Num(); ++Index)
    {
        if (Index == 0 || Index == 3)
        {
            UBorder* Divider = MakeSurface(ColdSteelUI::Border, 0.0f, FLinearColor::Transparent, 0.0f);
            USizeBox* DividerSize = WidgetTree->ConstructWidget<USizeBox>();
            DividerSize->SetWidthOverride(ReferenceUnits(1));
            DividerSize->SetHeightOverride(ReferenceUnits(HotbarSlotSize - 16));
            Divider->SetContent(DividerSize);
            Row->AddChildToHorizontalBox(Divider)->SetPadding(FMargin(ReferenceUnits(4), ReferenceUnits(8)));
        }
        Row->AddChildToHorizontalBox(MakeHotbarSlot(Slots[Index].Key, Slots[Index].Value))
            ->SetPadding(FMargin(Index == 0 ? 0.0f : ReferenceUnits(HotbarGap * .5f), 0, ReferenceUnits(HotbarGap * .5f), 0));
    }

    UCanvasPanelSlot* CanvasSlot = Root->AddChildToCanvas(Surface);
    CanvasSlot->SetAnchors(FAnchors(0.5f, 1.0f));
    CanvasSlot->SetAlignment(FVector2D(0.5f, 1.0f));
    CanvasSlot->SetPosition(FVector2D(0, -ReferenceUnits(12)));
    CanvasSlot->SetAutoSize(true);
    CanvasSlot->SetZOrder(30);
}

void UColdSteelHUDWidget::BuildEventTimeline(UCanvasPanel* Root)
{
    auto MakeTimelineButton = [this](const FString& Text, int32 FontSize, bool bSelected = false)
    {
        UButton* Button = WidgetTree->ConstructWidget<UButton>();
        const FLinearColor NormalFill = bSelected
            ? FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("263038F0")))
            : TimelineTrackColor;
        Button->SetStyle(FButtonStyle()
            .SetNormal(ColdSteelUI::RoundedBrush(NormalFill, 6.0f, bSelected ? ColdSteelUI::Accent : TimelineLineColor, 1.0f))
            .SetHovered(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("232B33FF"))), 6.0f, ColdSteelUI::Accent, 1.0f))
            .SetPressed(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("1B242CFF"))), 6.0f, ColdSteelUI::Accent, 1.0f)));
        Button->SetContent(MakeText(Text, FontSize, bSelected ? ColdSteelUI::TextPrimary : ColdSteelUI::TextSecondary));
        return Button;
    };

    TimelineWidthBox = WidgetTree->ConstructWidget<USizeBox>();
    TimelineWidthBox->SetWidthOverride(TimelineCompactWidth);
    UCanvasPanelSlot* TimelineRootSlot = Root->AddChildToCanvas(TimelineWidthBox);
    TimelineRootSlot->SetAnchors(FAnchors(0.5f, 0.0f));
    TimelineRootSlot->SetAlignment(FVector2D(0.5f, 0.0f));
    TimelineRootSlot->SetPosition(FVector2D(0.0f, 76.0f));
    TimelineRootSlot->SetAutoSize(true);
    TimelineRootSlot->SetZOrder(28);

    TimelinePanel = MakeSurface(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("171D23F2"))), 8.0f,
        FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("A2BCC88F"))), 1.0f);
    TimelinePanel->SetPadding(FMargin(8.0f, 3.0f, 8.0f, 2.0f));
    TimelineWidthBox->SetContent(TimelinePanel);
    UVerticalBox* TimelineColumn = WidgetTree->ConstructWidget<UVerticalBox>();
    TimelinePanel->SetContent(TimelineColumn);

    TimelineExpandedContent = WidgetTree->ConstructWidget<UVerticalBox>();
    TimelineExpandedContent->SetVisibility(ESlateVisibility::Collapsed);
    TimelineExpandedContent->SetRenderOpacity(1.0f);
    TimelineColumn->AddChildToVerticalBox(TimelineExpandedContent);

    UHorizontalBox* Heading = WidgetTree->ConstructWidget<UHorizontalBox>();
    TimelineExpandedContent->AddChildToVerticalBox(Heading);
    UHorizontalBoxSlot* TitleSlot = Heading->AddChildToHorizontalBox(MakeText(TEXT("时间进度栏"), 12, ColdSteelUI::TextPrimary, false, true));
    TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    TimelineWindowText = MakeText(TEXT("未来5日 · 1个事件"), 11, ColdSteelUI::TextSecondary);
    Heading->AddChildToHorizontalBox(TimelineWindowText)->SetVerticalAlignment(VAlign_Center);

    UBorder* Divider = MakeSurface(TimelineLineColor, 0.0f, FLinearColor::Transparent, 0.0f);
    USizeBox* DividerHeight = WidgetTree->ConstructWidget<USizeBox>();
    DividerHeight->SetHeightOverride(1.0f);
    Divider->SetContent(DividerHeight);
    TimelineExpandedContent->AddChildToVerticalBox(Divider)->SetPadding(FMargin(0.0f, 3.0f, 0.0f, 4.0f));

    UHorizontalBox* Filters = WidgetTree->ConstructWidget<UHorizontalBox>();
    TimelineExpandedContent->AddChildToVerticalBox(Filters)->SetHorizontalAlignment(HAlign_Center);
    TimelineAllFilterButton = MakeTimelineButton(TEXT("全部 1"), 10, true);
    TimelineAllFilterText = MakeText(TEXT("全部 1"), 10, ColdSteelUI::TextPrimary);
    TimelineAllFilterButton->SetContent(TimelineAllFilterText);
    TimelineAllFilterButton->OnClicked.AddDynamic(this, &UColdSteelHUDWidget::HandleTimelineFilterAllClicked);
    Filters->AddChildToHorizontalBox(TimelineAllFilterButton)->SetPadding(FMargin(0.0f, 0.0f, 2.0f, 2.0f));
    TimelineWeatherFilterButton = MakeTimelineButton(TEXT("天气 1"), 10, false);
    TimelineWeatherFilterText = MakeText(TEXT("天气 1"), 10, ColdSteelUI::TextSecondary);
    TimelineWeatherFilterButton->SetContent(TimelineWeatherFilterText);
    TimelineWeatherFilterButton->OnClicked.AddDynamic(this, &UColdSteelHUDWidget::HandleTimelineFilterWeatherClicked);
    Filters->AddChildToHorizontalBox(TimelineWeatherFilterButton)->SetPadding(FMargin(2.0f, 0.0f, 0.0f, 2.0f));

    UHorizontalBox* InvasionRow = WidgetTree->ConstructWidget<UHorizontalBox>();
    TimelineExpandedContent->AddChildToVerticalBox(InvasionRow)->SetHorizontalAlignment(HAlign_Center);
    UTextBlock* InvasionGlyph = MakeText(TEXT("⚔"), 12, ColdSteelUI::TextPrimary);
PRAGMA_DISABLE_DEPRECATION_WARNINGS
    InvasionGlyph->SetFont(FSlateFontInfo(TEXT("C:/Windows/Fonts/seguisym.ttf"), 12));
PRAGMA_ENABLE_DEPRECATION_WARNINGS
    InvasionRow->AddChildToHorizontalBox(InvasionGlyph)->SetPadding(FMargin(0.0f, 0.0f, 4.0f, 0.0f));
    TimelineInvasionText = MakeText(TEXT("暂无入侵情报"), 12, ColdSteelUI::TextPrimary);
    InvasionRow->AddChildToHorizontalBox(TimelineInvasionText);

    TimelineTrackSize = WidgetTree->ConstructWidget<USizeBox>();
    TimelineTrackSize->SetHeightOverride(30.0f);
    TimelineColumn->AddChildToVerticalBox(TimelineTrackSize)->SetPadding(FMargin(0.0f, 1.0f, 0.0f, 0.0f));
    TimelineTrack = WidgetTree->ConstructWidget<UCanvasPanel>();
    TimelineTrackSize->SetContent(TimelineTrack);

    UBorder* TrackBackground = MakeSurface(TimelineTrackColor, 3.0f, TimelineLineColor, 1.0f);
    FillSlot(TimelineTrack->AddChildToCanvas(TrackBackground), FAnchors(0.0f, 0.0f, 1.0f, 1.0f));

    TimelineGradientTexture = UTexture2D::CreateTransient(256, 1, PF_B8G8R8A8);
    if (TimelineGradientTexture && TimelineGradientTexture->GetPlatformData())
    {
        static const FLinearColor Stops[] = {
            FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("E5413EFF"))),
            FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("F1C13FFF"))),
            FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("418BE7FF"))),
            FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("3DC45BFF")))
        };
        FColor* Pixels = static_cast<FColor*>(TimelineGradientTexture->GetPlatformData()->Mips[0].BulkData.Lock(LOCK_READ_WRITE));
        for (int32 X = 0; X < 256; ++X)
        {
            const float Position = static_cast<float>(X) / 255.0f;
            const float Scaled = Position * 3.0f;
            const int32 Segment = FMath::Clamp(FMath::FloorToInt(Scaled), 0, 2);
            Pixels[X] = FMath::Lerp(Stops[Segment], Stops[Segment + 1], Scaled - Segment).ToFColor(true);
        }
        TimelineGradientTexture->GetPlatformData()->Mips[0].BulkData.Unlock();
        TimelineGradientTexture->UpdateResource();
        LoadedTextures.Add(TimelineGradientTexture);
    }
    TimelineGradient = WidgetTree->ConstructWidget<UImage>();
    TimelineGradient->SetBrushFromTexture(TimelineGradientTexture, false);
    FillSlot(TimelineTrack->AddChildToCanvas(TimelineGradient), FAnchors(0.0f, 1.0f, 1.0f, 1.0f), FMargin(0.0f, -3.0f, 0.0f, 3.0f), 1);

    TimelineCursorLine = MakeSurface(ColdSteelUI::TextPrimary, 0.0f, FLinearColor::Transparent, 0.0f);
    FillSlot(TimelineTrack->AddChildToCanvas(TimelineCursorLine), FAnchors(0.04f, 0.0f, 0.04f, 1.0f), FMargin(-1.0f, -3.0f, 2.0f, 5.0f), 3);

    TimelineEventLine = MakeSurface(TimelineWeatherColor, 0.0f, FLinearColor::Transparent, 0.0f);
    FillSlot(TimelineTrack->AddChildToCanvas(TimelineEventLine), FAnchors(0.064f, 0.0f, 0.064f, 1.0f), FMargin(-1.0f, -1.0f, 2.0f, 2.0f), 2);

    TimelineMarkerButton = WidgetTree->ConstructWidget<UButton>();
    TimelineMarkerButton->SetStyle(FButtonStyle()
        .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent, 0.0f, FLinearColor::Transparent, 0.0f))
        .SetHovered(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("232B3388"))), 4.0f, ColdSteelUI::Accent, 1.0f))
        .SetPressed(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("1B242CCC"))), 4.0f, ColdSteelUI::Accent, 1.0f)));
    TimelineMarkerButton->OnClicked.AddDynamic(this, &UColdSteelHUDWidget::HandleTimelineMarkerClicked);
    UHorizontalBox* MarkerRow = WidgetTree->ConstructWidget<UHorizontalBox>();
    TimelineMarkerButton->SetContent(MarkerRow);
    TimelineMarkerImage = WidgetTree->ConstructWidget<UImage>();
    if (UTexture2D* RainTexture = LoadUiTexture(TEXT("rain-light.png"))) TimelineMarkerImage->SetBrushFromTexture(RainTexture, true);
    USizeBox* MarkerIconSize = WidgetTree->ConstructWidget<USizeBox>();
    MarkerIconSize->SetWidthOverride(18.0f);
    MarkerIconSize->SetHeightOverride(18.0f);
    MarkerIconSize->SetContent(TimelineMarkerImage);
    MarkerRow->AddChildToHorizontalBox(MarkerIconSize);
    TimelineMarkerTimeText = MakeText(TEXT("3 小时后"), 9, ColdSteelUI::TextPrimary);
    MarkerRow->AddChildToHorizontalBox(TimelineMarkerTimeText)->SetPadding(FMargin(3.0f, 1.0f, 0.0f, 0.0f));
    UCanvasPanelSlot* MarkerSlot = TimelineTrack->AddChildToCanvas(TimelineMarkerButton);
    MarkerSlot->SetAnchors(FAnchors(0.064f, 0.0f));
    MarkerSlot->SetAlignment(FVector2D(0.15f, 0.0f));
    MarkerSlot->SetPosition(FVector2D(0.0f, 2.0f));
    MarkerSlot->SetAutoSize(true);
    MarkerSlot->SetZOrder(4);

    TimelineNowText = MakeText(TEXT("现在"), 9, ColdSteelUI::TextPrimary);
    UCanvasPanelSlot* NowSlot = TimelineTrack->AddChildToCanvas(TimelineNowText);
    NowSlot->SetAnchors(FAnchors(0.04f, 1.0f));
    NowSlot->SetAlignment(FVector2D(0.5f, 0.0f));
    NowSlot->SetPosition(FVector2D(0.0f, -5.0f));
    NowSlot->SetAutoSize(true);
    NowSlot->SetZOrder(4);

    UHorizontalBox* ToggleRow = WidgetTree->ConstructWidget<UHorizontalBox>();
    TimelineColumn->AddChildToVerticalBox(ToggleRow)->SetHorizontalAlignment(HAlign_Fill);
    USpacer* ToggleLeft = WidgetTree->ConstructWidget<USpacer>();
    ToggleRow->AddChildToHorizontalBox(ToggleLeft)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    USizeBox* ToggleSize = WidgetTree->ConstructWidget<USizeBox>();
    ToggleSize->SetWidthOverride(46.0f);
    ToggleSize->SetHeightOverride(16.0f);
    TimelineToggleButton = MakeTimelineButton(TEXT("⌄"), 12, false);
    if (UTextBlock* ToggleGlyph = Cast<UTextBlock>(TimelineToggleButton->GetContent()))
    {
PRAGMA_DISABLE_DEPRECATION_WARNINGS
        ToggleGlyph->SetFont(FSlateFontInfo(TEXT("C:/Windows/Fonts/seguisym.ttf"), 12));
PRAGMA_ENABLE_DEPRECATION_WARNINGS
    }
    TimelineToggleButton->OnClicked.AddDynamic(this, &UColdSteelHUDWidget::HandleTimelineToggleClicked);
    TimelineToggleButton->SetToolTipText(FText::FromString(TEXT("展开详细时间进度栏")));
    ToggleSize->SetContent(TimelineToggleButton);
    ToggleRow->AddChildToHorizontalBox(ToggleSize);
    USpacer* ToggleRight = WidgetTree->ConstructWidget<USpacer>();
    ToggleRow->AddChildToHorizontalBox(ToggleRight)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));

    TimelinePopover = MakeSurface(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("171D23F5"))), 9.0f,
        FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("A2BCC88F"))), 1.0f);
    TimelinePopover->SetPadding(FMargin(8.0f, 7.0f));
    TimelinePopover->SetVisibility(ESlateVisibility::Collapsed);
    UCanvasPanelSlot* PopoverSlot = Root->AddChildToCanvas(TimelinePopover);
    PopoverSlot->SetAnchors(FAnchors(0.5f, 0.0f));
    PopoverSlot->SetAlignment(FVector2D(0.5f, 0.0f));
    PopoverSlot->SetPosition(FVector2D(0.0f, 246.0f));
    PopoverSlot->SetSize(FVector2D(410.0f, 291.0f));
    PopoverSlot->SetZOrder(29);

    UVerticalBox* PopoverColumn = WidgetTree->ConstructWidget<UVerticalBox>();
    TimelinePopover->SetContent(PopoverColumn);
    UHorizontalBox* PopoverHeading = WidgetTree->ConstructWidget<UHorizontalBox>();
    PopoverColumn->AddChildToVerticalBox(PopoverHeading);
    TimelinePopoverTitle = MakeText(TEXT("天气预报详情"), 12, ColdSteelUI::TextPrimary, false, true);
    PopoverHeading->AddChildToHorizontalBox(TimelinePopoverTitle)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    UButton* PopoverClose = MakeTimelineButton(TEXT("×"), 18, false);
    PopoverClose->OnClicked.AddDynamic(this, &UColdSteelHUDWidget::HandleTimelineDetailsCloseClicked);
    USizeBox* PopoverCloseSize = WidgetTree->ConstructWidget<USizeBox>();
    PopoverCloseSize->SetWidthOverride(24.0f);
    PopoverCloseSize->SetHeightOverride(24.0f);
    PopoverCloseSize->SetContent(PopoverClose);
    PopoverHeading->AddChildToHorizontalBox(PopoverCloseSize);
    UBorder* PopoverDivider = MakeSurface(TimelineLineColor, 0.0f, FLinearColor::Transparent, 0.0f);
    USizeBox* PopoverDividerHeight = WidgetTree->ConstructWidget<USizeBox>();
    PopoverDividerHeight->SetHeightOverride(1.0f);
    PopoverDivider->SetContent(PopoverDividerHeight);
    PopoverColumn->AddChildToVerticalBox(PopoverDivider)->SetPadding(FMargin(0.0f, 3.0f, 0.0f, 5.0f));
    TimelineDetailContent = WidgetTree->ConstructWidget<UVerticalBox>();
    TimelineDetailContent->SetClipping(EWidgetClipping::ClipToBounds);
    PopoverColumn->AddChildToVerticalBox(TimelineDetailContent)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));

    SetEventTimelineCompact(true);
}

void UColdSteelHUDWidget::BuildInventory(UCanvasPanel* Root)
{
    InventoryBlur = WidgetTree->ConstructWidget<UBackgroundBlur>();
    InventoryBlur->SetBlurStrength(4.0f);
    InventoryBlur->SetApplyAlphaToBlur(true);
    InventoryBlur->SetVisibility(ESlateVisibility::Collapsed);
    FillSlot(Root->AddChildToCanvas(InventoryBlur), FAnchors(0.0f, 0.0f, 1.0f, 1.0f), FMargin(0.0f), 39);

    InventoryBackdrop = MakeSurface(FLinearColor(0.0f, 0.0f, 0.0f, 0.65f), 0.0f, FLinearColor::Transparent, 0.0f);
    InventoryBackdrop->SetVisibility(ESlateVisibility::Collapsed);
    FillSlot(Root->AddChildToCanvas(InventoryBackdrop), FAnchors(0.0f, 0.0f, 1.0f, 1.0f), FMargin(0.0f), 40);

    InventoryPanel = MakeSurface(ColdSteelUI::GlassTint, ReferenceUnits(18), ColdSteelUI::Border, 1.0f);
    InventoryPanel->SetPadding(FMargin(3.0f, 0.0f, 0.0f, 0.0f));
    InventoryPanel->SetVisibility(ESlateVisibility::Collapsed);
    FillSlot(Root->AddChildToCanvas(InventoryPanel), FAnchors(0.55f, 0.0f, 1.0f, 1.0f), FMargin(0.0f), 41);

    UVerticalBox* Body = WidgetTree->ConstructWidget<UVerticalBox>();
    InventoryPanel->SetContent(Body);

    UBorder* HeaderSurface = MakeSurface(DrawerHeader, 0.0f, FLinearColor::Transparent, 0.0f);
    HeaderSurface->SetPadding(FMargin(ReferenceUnits(18), ReferenceUnits(10)));
    USizeBox* HeaderHeight = WidgetTree->ConstructWidget<USizeBox>();
    HeaderHeight->SetHeightOverride(ReferenceUnits(36));
    HeaderSurface->SetContent(HeaderHeight);
    Body->AddChildToVerticalBox(HeaderSurface)->SetSize(FSlateChildSize(ESlateSizeRule::Automatic));
    UHorizontalBox* Header = WidgetTree->ConstructWidget<UHorizontalBox>();
    HeaderHeight->SetContent(Header);
    InventoryTitleText = MakeReferenceText(TEXT("装备与背包"), 20, ColdSteelUI::TextPrimary, false, true);
    UHorizontalBoxSlot* TitleSlot = Header->AddChildToHorizontalBox(InventoryTitleText);
    TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    TitleSlot->SetVerticalAlignment(VAlign_Center);

    CloseButton = WidgetTree->ConstructWidget<UButton>();
    CloseButton->SetStyle(FButtonStyle()
        .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor(0.16f, 0.20f, 0.23f, 0.7f), 5.0f, ColdSteelUI::Border, 1.0f))
        .SetHovered(ColdSteelUI::RoundedBrush(FLinearColor(0.22f, 0.27f, 0.31f, 0.95f), 5.0f, ColdSteelUI::Accent, 1.0f))
        .SetPressed(ColdSteelUI::RoundedBrush(FLinearColor(0.10f, 0.13f, 0.16f, 1.0f), 5.0f)));
    CloseButton->SetContent(MakeText(TEXT("×"), 24, ColdSteelUI::TextSecondary));
    CloseButton->OnClicked.AddDynamic(this, &UColdSteelHUDWidget::HandleCloseClicked);
    Header->AddChildToHorizontalBox(CloseButton)->SetVerticalAlignment(VAlign_Center);

    UHorizontalBox* Tabs = WidgetTree->ConstructWidget<UHorizontalBox>();
    auto AddTab = [this, Tabs](const FString& Caption, bool bActive, TObjectPtr<UBorder>& OutSurface, TObjectPtr<UTextBlock>& OutText, TObjectPtr<UBorder>& OutUnderline, bool bEnabled)
    {
        UButton* Button = WidgetTree->ConstructWidget<UButton>();
        Button->SetStyle(FButtonStyle()
            .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent, 0.0f, FLinearColor::Transparent, 0.0f))
            .SetHovered(ColdSteelUI::RoundedBrush(FLinearColor(0.18f, 0.22f, 0.25f, 0.45f), 0.0f, FLinearColor::Transparent, 0.0f))
            .SetPressed(ColdSteelUI::RoundedBrush(FLinearColor(0.10f, 0.13f, 0.16f, 0.75f), 0.0f, FLinearColor::Transparent, 0.0f)));
        OutSurface = MakeTab(Caption, bActive);
        UOverlay* Layer = Cast<UOverlay>(Cast<USizeBox>(OutSurface->GetContent())->GetContent());
        OutText = Layer ? Cast<UTextBlock>(Layer->GetChildAt(0)) : nullptr;
        OutUnderline = Layer && Layer->GetChildrenCount() > 1 ? Cast<UBorder>(Layer->GetChildAt(1)) : nullptr;
        Button->SetContent(OutSurface);
        if (auto* ContentSlot = Cast<UButtonSlot>(OutSurface->Slot))
        {
            ContentSlot->SetHorizontalAlignment(HAlign_Fill);
            ContentSlot->SetVerticalAlignment(VAlign_Fill);
            ContentSlot->SetPadding(FMargin(0));
        }
        Button->SetIsEnabled(bEnabled);
        UHorizontalBoxSlot* TabSlot = Tabs->AddChildToHorizontalBox(Button);
        TabSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        return Button;
    };
    UButton* StatusButton = AddTab(TEXT("状态"), false, StatusTabSurface, StatusTabText, StatusTabUnderline, true);
    UButton* EquipmentButton = AddTab(TEXT("装备"), true, EquipmentTabSurface, EquipmentTabText, EquipmentTabUnderline, true);
    TObjectPtr<UBorder> DummySurface = nullptr;
    TObjectPtr<UTextBlock> DummyText = nullptr;
    TObjectPtr<UBorder> DummyUnderline = nullptr;
    AddTab(TEXT("技能"), false, DummySurface, DummyText, DummyUnderline, false);
    AddTab(TEXT("图鉴"), false, DummySurface, DummyText, DummyUnderline, false);
    StatusButton->OnClicked.AddDynamic(this, &UColdSteelHUDWidget::HandleStatusTabClicked);
    EquipmentButton->OnClicked.AddDynamic(this, &UColdSteelHUDWidget::HandleEquipmentTabClicked);
    Body->AddChildToVerticalBox(Tabs)->SetSize(FSlateChildSize(ESlateSizeRule::Automatic));

    StatusPage = BuildStatusPage();
    EquipmentPage = BuildEquipmentPage();
    Body->AddChildToVerticalBox(StatusPage)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Body->AddChildToVerticalBox(EquipmentPage)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    BuildStatusTooltip(Root);
    BuildEquipmentTooltip(Root);
    SetInventoryTab(false);
}


UWidget* UColdSteelHUDWidget::BuildEquipmentPage()
{
    auto* Scroll = WidgetTree->ConstructWidget<UScrollBox>();
    Scroll->SetConsumeMouseWheel(EConsumeMouseWheel::Always);
    auto* Board = CreateWidget<UColdSteelInventoryWidget>(GetOwningPlayer());
    Scroll->AddChild(Board);
    return Scroll;
}

UWidget* UColdSteelHUDWidget::MakeAttributeRow(const FString& Label, const FString& Key, UTextBlock*& OutValue)
{
    UButton* Button = WidgetTree->ConstructWidget<UButton>();
    Button->SetStyle(FButtonStyle()
        .SetNormal(ColdSteelUI::RoundedBrush(AttributeRow, 4.0f, FLinearColor::Transparent, 0.0f))
        .SetHovered(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("3A4652A8"))), 4.0f, FLinearColor::Transparent, 0.0f))
        .SetPressed(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("222B33D0"))), 4.0f, ColdSteelUI::Accent, 1.0f)));
    UHorizontalBox* Row = WidgetTree->ConstructWidget<UHorizontalBox>();
    UButtonSlot* ContentSlot = Cast<UButtonSlot>(Button->SetContent(Row));
    if (ContentSlot) ContentSlot->SetPadding(FMargin(9.0f, 4.0f));
    Row->AddChildToHorizontalBox(MakeReferenceText(Label, 12, ColdSteelUI::TextSecondary))->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    OutValue = MakeReferenceText(TEXT("10"), 14, ColdSteelUI::TextPrimary, true, true);
    OutValue->SetJustification(ETextJustify::Right);
    Row->AddChildToHorizontalBox(OutValue);
    if (Key == TEXT("str")) Button->OnHovered.AddDynamic(this, &UColdSteelHUDWidget::HandleStrengthHovered);
    else if (Key == TEXT("dex")) Button->OnHovered.AddDynamic(this, &UColdSteelHUDWidget::HandleDexterityHovered);
    else if (Key == TEXT("intt")) Button->OnHovered.AddDynamic(this, &UColdSteelHUDWidget::HandleIntelligenceHovered);
    else if (Key == TEXT("con")) Button->OnHovered.AddDynamic(this, &UColdSteelHUDWidget::HandleConstitutionHovered);
    else if (Key == TEXT("wis")) Button->OnHovered.AddDynamic(this, &UColdSteelHUDWidget::HandleWisdomHovered);
    else Button->OnHovered.AddDynamic(this, &UColdSteelHUDWidget::HandleLuckHovered);
    Button->OnUnhovered.AddDynamic(this, &UColdSteelHUDWidget::HandleAttributeUnhovered);
    return Button;
}

void UColdSteelHUDWidget::BuildStatusTooltip(UCanvasPanel* Root)
{
    StatusTooltip = MakeSurface(TooltipSurface, ReferenceUnits(16.0f), FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("7187928A"))), 1.0f);
    StatusTooltip->SetPadding(FMargin(ReferenceUnits(16.0f), ReferenceUnits(12.0f)));
    StatusTooltip->SetVisibility(ESlateVisibility::Collapsed);
    StatusTooltipCanvasSlot = Root->AddChildToCanvas(StatusTooltip);
    StatusTooltipCanvasSlot->SetAnchors(FAnchors(0.56f, 0.51f));
    StatusTooltipCanvasSlot->SetPosition(FVector2D(0.0f, 0.0f));
    StatusTooltipCanvasSlot->SetSize(FVector2D(ReferenceUnits(260.0f), ReferenceUnits(142.0f)));
    StatusTooltipCanvasSlot->SetZOrder(60);
    UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>();
    StatusTooltip->SetContent(Column);
    StatusTooltipTitle = MakeReferenceText(TEXT("力量"), 16, FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("E4E9EBFF"))), false, true);
    Column->AddChildToVerticalBox(StatusTooltipTitle);
    UBorder* Divider = MakeSurface(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("B8D6DF50"))), 0.0f, FLinearColor::Transparent, 0.0f);
    USizeBox* DividerHeight = WidgetTree->ConstructWidget<USizeBox>();
    DividerHeight->SetHeightOverride(ReferenceUnits(1.0f)); Divider->SetContent(DividerHeight);
    Column->AddChildToVerticalBox(Divider)->SetPadding(FMargin(0, ReferenceUnits(4), 0, ReferenceUnits(6)));
    StatusTooltipDescription = MakeReferenceText(TEXT("提升物理攻击与少量物理防御。"), 14, ColdSteelUI::TextPrimary);
    StatusTooltipDescription->SetAutoWrapText(true);
    Column->AddChildToVerticalBox(StatusTooltipDescription);
    StatusTooltipRowsBox = WidgetTree->ConstructWidget<UVerticalBox>();
    Column->AddChildToVerticalBox(StatusTooltipRowsBox)->SetPadding(FMargin(0, ReferenceUnits(4), 0, 0));
    StatusTooltipNote = MakeReferenceText(TEXT("每点力量 ≈ +0.05 物理攻击"), 12, ColdSteelUI::TextSecondary);
    StatusTooltipNote->SetAutoWrapText(true);
    Column->AddChildToVerticalBox(StatusTooltipNote)->SetPadding(FMargin(0, ReferenceUnits(4), 0, 0));
}

void UColdSteelHUDWidget::BuildEquipmentTooltip(UCanvasPanel* Root)
{
    EquipmentTooltip = MakeSurface(FLinearColor::Transparent, 0.0f, FLinearColor::Transparent, 0.0f);
    EquipmentTooltip->SetClipping(EWidgetClipping::ClipToBounds);
    EquipmentTooltip->SetVisibility(ESlateVisibility::Collapsed);
    EquipmentTooltipCanvasSlot = Root->AddChildToCanvas(EquipmentTooltip);
    EquipmentTooltipCanvasSlot->SetAnchors(FAnchors(0.008f, 0.56f, 0.992f, 0.90f));
    EquipmentTooltipCanvasSlot->SetOffsets(FMargin(0.0f));
    EquipmentTooltipCanvasSlot->SetZOrder(50);
    EquipmentTooltipScroll = WidgetTree->ConstructWidget<UScrollBox>();
    EquipmentTooltipScroll->SetOrientation(EOrientation::Orient_Horizontal);
    EquipmentTooltipScroll->SetScrollbarThickness(FVector2D(ReferenceUnits(12), ReferenceUnits(12)));
    EquipmentTooltipScroll->SetAlwaysShowScrollbar(false);
    EquipmentTooltipScroll->SetAnimateWheelScrolling(false);
    EquipmentTooltip->SetContent(EquipmentTooltipScroll);
    UHorizontalBox* Cards = WidgetTree->ConstructWidget<UHorizontalBox>();
    EquipmentTooltipScroll->AddChild(Cards);
    auto AddCard = [this, Cards](float Width, float PadX, float PadY)
    {
        UBorder* Card = MakeSurface(TooltipSurface, ReferenceUnits(16.0f), FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("7187928A"))), 1.0f);
        Card->SetPadding(FMargin(ReferenceUnits(PadX + 2.0f), ReferenceUnits(PadY + 2.0f)));
        USizeBox* CardSize = WidgetTree->ConstructWidget<USizeBox>();
        CardSize->SetWidthOverride(ReferenceUnits(Width));
        CardSize->SetContent(Card);
        Cards->AddChildToHorizontalBox(CardSize)->SetPadding(FMargin(0, 0, ReferenceUnits(18), 0));
        UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>();
        Card->SetContent(Column);
        return Column;
    };

    UVerticalBox* Main = AddCard(460.0f, 20.0f, 16.0f);
    UHorizontalBox* Header = WidgetTree->ConstructWidget<UHorizontalBox>();
    Main->AddChildToVerticalBox(Header)->SetPadding(FMargin(0, 0, 0, ReferenceUnits(8)));
    UVerticalBox* TitleBox = WidgetTree->ConstructWidget<UVerticalBox>();
    Header->AddChildToHorizontalBox(TitleBox)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    UHorizontalBox* NameRow = WidgetTree->ConstructWidget<UHorizontalBox>();
    TitleBox->AddChildToVerticalBox(NameRow);
    WeaponNameText = MakeReferenceText(TEXT("当前武器"), 16, ColdSteelUI::TextPrimary, false, true);
    NameRow->AddChildToHorizontalBox(WeaponNameText)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    TitleBox->AddChildToVerticalBox(MakeReferenceText(TEXT("武器  |  普通"), 12, ColdSteelUI::TextSecondary));
    UHorizontalBox* Meta = WidgetTree->ConstructWidget<UHorizontalBox>();
    Header->AddChildToHorizontalBox(Meta);
    UButton* Close = WidgetTree->ConstructWidget<UButton>();
    Close->SetStyle(FButtonStyle()
        .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("C83232CC"))), ReferenceUnits(12), FLinearColor::Transparent, 0.0f))
        .SetHovered(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("DC4646FF"))), ReferenceUnits(12), FLinearColor::Transparent, 0.0f)));
    Close->SetContent(MakeReferenceText(TEXT("×"), 14, ColdSteelUI::TextPrimary));
    Close->OnClicked.AddDynamic(this, &UColdSteelHUDWidget::HandleEquipmentTooltipCloseClicked);
    USizeBox* CloseSize = WidgetTree->ConstructWidget<USizeBox>(); CloseSize->SetWidthOverride(ReferenceUnits(24)); CloseSize->SetHeightOverride(ReferenceUnits(24)); CloseSize->SetContent(Close);
    Meta->AddChildToHorizontalBox(CloseSize);
    EquipmentDamageValue = AddTooltipRow(Main, TEXT("物理攻击"), TEXT("30"), ColdSteelUI::TextPrimary, true);
    EquipmentCapacityValue = AddTooltipRow(Main, TEXT("弹匣容量"), TEXT("30 发"), ColdSteelUI::TextPrimary);
    AddTooltipRow(Main, TEXT("分类"), TEXT("武器"), ColdSteelUI::TextPrimary);
    AddTooltipRow(Main, TEXT("武器类型"), TEXT("步枪"), ColdSteelUI::TextPrimary);
    AddTooltipRow(Main, TEXT("装备槽位"), TEXT("主手武器"), ColdSteelUI::TextPrimary);
    AddTooltipSection(Main, TEXT("攻击参数"));
    EquipmentIntervalValue = AddTooltipRow(Main, TEXT("攻击间隔"), TEXT("120ms"), ColdSteelUI::TextPrimary, true);
    EquipmentReloadValue = AddTooltipRow(Main, TEXT("换弹时间"), TEXT("2700ms"), ColdSteelUI::TextPrimary, true);
    EquipmentAmmoValue = AddTooltipRow(Main, TEXT("当前弹药"), TEXT("30 / 90"), ColdSteelUI::TextPrimary, true);
}

UTextBlock* UColdSteelHUDWidget::AddTooltipRow(UVerticalBox* Parent, const FString& Label, const FString& Value, const FLinearColor& ValueColor, bool bNumericValue)
{
    UHorizontalBox* Row = WidgetTree->ConstructWidget<UHorizontalBox>();
    Parent->AddChildToVerticalBox(Row)->SetPadding(FMargin(0, ReferenceUnits(2), 0, ReferenceUnits(2)));
    UTextBlock* Name = MakeReferenceText(Label, 14, ColdSteelUI::TextSecondary);
    FSlateChildSize NameSize(ESlateSizeRule::Fill);
    NameSize.Value = 0.4f;
    Row->AddChildToHorizontalBox(Name)->SetSize(NameSize);
    UTextBlock* Result = MakeReferenceText(Value, 14, ValueColor, bNumericValue);
    Result->SetJustification(ETextJustify::Right);
    FSlateChildSize ValueSize(ESlateSizeRule::Fill);
    ValueSize.Value = 0.6f;
    Row->AddChildToHorizontalBox(Result)->SetSize(ValueSize);
    return Result;
}

void UColdSteelHUDWidget::AddTooltipSection(UVerticalBox* Parent, const FString& Title)
{
    Parent->AddChildToVerticalBox(MakeReferenceText(Title, 16, ColdSteelUI::TextPrimary, false, true));
    UBorder* Divider = MakeSurface(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("B8D6DF3D"))), 0.0f, FLinearColor::Transparent, 0.0f);
    USizeBox* Height = WidgetTree->ConstructWidget<USizeBox>();
    Height->SetHeightOverride(ReferenceUnits(1));
    Divider->SetContent(Height);
    Parent->AddChildToVerticalBox(Divider)->SetPadding(FMargin(0, ReferenceUnits(3), 0, ReferenceUnits(4)));
}

UWidget* UColdSteelHUDWidget::MakeInventoryGrid()
{
    USizeBox* DesignSize = WidgetTree->ConstructWidget<USizeBox>();
    DesignSize->SetWidthOverride(720.0f);
    DesignSize->SetHeightOverride(160.0f);
    UCanvasPanel* Grid = WidgetTree->ConstructWidget<UCanvasPanel>();
    DesignSize->SetContent(Grid);

    for (int32 Row = 0; Row < InventoryRows; ++Row)
    {
        for (int32 Column = 0; Column < InventoryColumns; ++Column)
        {
            const float L = static_cast<float>(Column) / InventoryColumns;
            const float T = static_cast<float>(Row) / InventoryRows;
            const float R = static_cast<float>(Column + 1) / InventoryColumns;
            const float B = static_cast<float>(Row + 1) / InventoryRows;
            UBorder* Cell = MakeSurface(SlotDark, 0.0f, GridLine, 1.0f);
            FillSlot(Grid->AddChildToCanvas(Cell), FAnchors(L, T, R, B));
        }
    }

    auto AddItem = [this, Grid](const FAnchors& Anchors, const FString& Name, const FString& File, const FString& Count, const FLinearColor& Rail)
    {
        UBorder* Card = MakeSurface(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("20282FF6"))), 2.0f, ColdSteelUI::Border, 1.0f);
        FillSlot(Grid->AddChildToCanvas(Card), Anchors, FMargin(1.0f), 3);
        UOverlay* Layer = WidgetTree->ConstructWidget<UOverlay>();
        Card->SetContent(Layer);
        if (!Name.IsEmpty())
        {
            UOverlaySlot* LabelSlot = Layer->AddChildToOverlay(MakeText(Name, 12, ColdSteelUI::TextPrimary));
            LabelSlot->SetHorizontalAlignment(HAlign_Left);
            LabelSlot->SetVerticalAlignment(VAlign_Top);
            LabelSlot->SetPadding(FMargin(6.0f, 3.0f));
        }
        if (UTexture2D* Texture = LoadUiTexture(File))
        {
            UImage* Image = WidgetTree->ConstructWidget<UImage>();
            Image->SetBrushFromTexture(Texture, true);
            UOverlaySlot* ImageSlot = Layer->AddChildToOverlay(Image);
            ImageSlot->SetHorizontalAlignment(HAlign_Fill);
            ImageSlot->SetVerticalAlignment(VAlign_Fill);
            ImageSlot->SetPadding(FMargin(8.0f, Name.IsEmpty() ? 4.0f : 17.0f, 8.0f, 4.0f));
        }
        UBorder* Badge = MakeSurface(Rail, 3.0f, FLinearColor::Transparent, 0.0f);
        UOverlaySlot* BadgeSlot = Layer->AddChildToOverlay(Badge);
        BadgeSlot->SetHorizontalAlignment(HAlign_Left);
        BadgeSlot->SetVerticalAlignment(VAlign_Fill);
        BadgeSlot->SetPadding(FMargin(3.0f));
        USizeBox* BadgeWidth = WidgetTree->ConstructWidget<USizeBox>();
        BadgeWidth->SetWidthOverride(6.0f);
        Badge->SetContent(BadgeWidth);
        if (!Count.IsEmpty())
        {
            UOverlaySlot* CountSlot = Layer->AddChildToOverlay(MakeText(Count, 10, ColdSteelUI::TextPrimary, true, true));
            CountSlot->SetHorizontalAlignment(HAlign_Center);
            CountSlot->SetVerticalAlignment(VAlign_Center);
        }
    };

    AddItem(FAnchors(0.0f, 0.0f, 5.0f / 18.0f, 0.5f), TEXT("M4A1"), TEXT("ue_m4a1.png"), TEXT(""), FLinearColor(0.72f, 0.76f, 0.84f, 0.9f));
    AddItem(FAnchors(5.0f / 18.0f, 0.0f, 6.0f / 18.0f, 0.25f), TEXT(""), TEXT("health_potion.png"), TEXT("5"), FLinearColor(0.91f, 0.55f, 0.62f, 0.9f));
    AddItem(FAnchors(6.0f / 18.0f, 0.0f, 7.0f / 18.0f, 0.25f), TEXT(""), TEXT("mana_potion.png"), TEXT("3"), FLinearColor(0.52f, 0.70f, 0.91f, 0.9f));
    AddItem(FAnchors(7.0f / 18.0f, 0.0f, 8.0f / 18.0f, 0.25f), TEXT(""), TEXT("gold.png"), TEXT("200"), FLinearColor(0.89f, 0.70f, 0.47f, 0.9f));

    UScaleBox* Scale = WidgetTree->ConstructWidget<UScaleBox>();
    Scale->SetStretch(EStretch::ScaleToFit);
    Scale->SetStretchDirection(EStretchDirection::DownOnly);
    if (UScaleBoxSlot* ScaleSlot = Cast<UScaleBoxSlot>(Scale->SetContent(DesignSize)))
    {
        ScaleSlot->SetHorizontalAlignment(HAlign_Fill);
        ScaleSlot->SetVerticalAlignment(VAlign_Top);
    }
    return Scale;
}

void UColdSteelHUDWidget::RefreshEventTimeline(bool bForce)
{
    if (FParse::Param(FCommandLine::Get(), TEXT("EventTimelineUIAudit")))
    {
        ApplyEventTimelineAuditFixture();
        return;
    }

    AFPSWeatherManager* Weather = nullptr;
    if (UWorld* World = GetWorld())
    {
        for (TActorIterator<AFPSWeatherManager> It(World); It; ++It)
        {
            Weather = *It;
            break;
        }
    }

    bTimelineHasEvent = false;
    bTimelineEventActive = false;
    bTimelineManual = Weather && !Weather->bAutomaticSchedule;
    TimelineStageStates.Reset();
    TimelineStageStarts.Reset();
    TimelineStageEnds.Reset();

    if (Weather)
    {
        const float DaySeconds = FMath::Max(60.0f, Weather->RealSecondsPerGameDay);
        TimelineDaySeconds = DaySeconds;
        const float DayFraction = FMath::Clamp(Weather->NormalizedDayTime, 0.0f, 0.999999f);
        TimelineDaySerial = Weather->GetScheduleDay();
        const float Now = TimelineDaySerial * DaySeconds + DayFraction * DaySeconds;
        const float SegmentSeconds = DaySeconds / WeatherSegmentsPerDay;
        const int32 CurrentGlobalSegment = TimelineDaySerial * WeatherSegmentsPerDay
            + FMath::Clamp(FMath::FloorToInt(DayFraction * WeatherSegmentsPerDay), 0, WeatherSegmentsPerDay - 1);

        int32 FirstWetSegment = INDEX_NONE;
        int32 EndWetSegment = INDEX_NONE;
        const int32 HorizonSegments = FMath::CeilToInt(TimelineHorizonDays * WeatherSegmentsPerDay);

        if (!Weather->bAutomaticSchedule)
        {
            if (IsWetWeather(Weather->CurrentState))
            {
                FirstWetSegment = CurrentGlobalSegment;
                EndWetSegment = CurrentGlobalSegment + 1;
                bTimelineManual = true;
            }
        }
        else
        {
            bTimelineManual = false;
            for (int32 Offset = 0; Offset <= HorizonSegments; ++Offset)
            {
                const int32 GlobalSegment = CurrentGlobalSegment + Offset;
                const int32 Day = FMath::FloorToInt(static_cast<float>(GlobalSegment) / WeatherSegmentsPerDay);
                const int32 Segment = FMath::FloorToInt(FMath::Fmod(static_cast<float>(GlobalSegment), static_cast<float>(WeatherSegmentsPerDay)) + WeatherSegmentsPerDay) % WeatherSegmentsPerDay;
                const EFPSWeatherState State = Offset == 0 ? Weather->CurrentState : Weather->GetScheduledStateAt(Day, Segment);
                if (IsWetWeather(State))
                {
                    FirstWetSegment = GlobalSegment;
                    break;
                }
            }
            if (FirstWetSegment != INDEX_NONE)
            {
                while (FirstWetSegment > 0)
                {
                    const int32 Previous = FirstWetSegment - 1;
                    const int32 PreviousDay = Previous / WeatherSegmentsPerDay;
                    const int32 PreviousSegment = Previous % WeatherSegmentsPerDay;
                    if (!IsWetWeather(Weather->GetScheduledStateAt(PreviousDay, PreviousSegment))) break;
                    --FirstWetSegment;
                }
                EndWetSegment = FirstWetSegment;
                while (EndWetSegment <= CurrentGlobalSegment + HorizonSegments + WeatherSegmentsPerDay)
                {
                    const int32 Day = EndWetSegment / WeatherSegmentsPerDay;
                    const int32 Segment = EndWetSegment % WeatherSegmentsPerDay;
                    if (!IsWetWeather(Weather->GetScheduledStateAt(Day, Segment))) break;
                    ++EndWetSegment;
                }
            }
        }

        if (FirstWetSegment != INDEX_NONE && EndWetSegment > FirstWetSegment)
        {
            bTimelineHasEvent = true;
            TimelineEventStart = bTimelineManual ? Now : FirstWetSegment * SegmentSeconds;
            TimelineEventEnd = bTimelineManual ? Now : EndWetSegment * SegmentSeconds;
            bTimelineEventActive = bTimelineManual || TimelineEventStart <= Now;
            bTimelineContainsStorm = false;

            if (bTimelineManual)
            {
                TimelineStageStates.Add(static_cast<int32>(Weather->CurrentState));
                TimelineStageStarts.Add(Now);
                TimelineStageEnds.Add(Now);
                bTimelineContainsStorm = Weather->CurrentState == EFPSWeatherState::Storm;
            }
            else
            {
                for (int32 GlobalSegment = FirstWetSegment; GlobalSegment < EndWetSegment; ++GlobalSegment)
                {
                    const int32 Day = GlobalSegment / WeatherSegmentsPerDay;
                    const int32 Segment = GlobalSegment % WeatherSegmentsPerDay;
                    const EFPSWeatherState State = Weather->GetScheduledStateAt(Day, Segment);
                    const float StageStart = GlobalSegment * SegmentSeconds;
                    const float StageEnd = (GlobalSegment + 1) * SegmentSeconds;
                    bTimelineContainsStorm |= State == EFPSWeatherState::Storm;
                    if (!TimelineStageStates.IsEmpty() && TimelineStageStates.Last() == static_cast<int32>(State))
                    {
                        TimelineStageEnds.Last() = StageEnd;
                    }
                    else
                    {
                        TimelineStageStates.Add(static_cast<int32>(State));
                        TimelineStageStarts.Add(StageStart);
                        TimelineStageEnds.Add(StageEnd);
                    }
                }
            }

            EFPSWeatherState DisplayState = static_cast<EFPSWeatherState>(TimelineStageStates[0]);
            if (bTimelineEventActive) DisplayState = Weather->CurrentState;
            else if (bTimelineContainsStorm) DisplayState = EFPSWeatherState::Storm;

            const FString RegionName = WeatherRegionName(GetWorld());
            TimelineEventLabel = RegionName + (bTimelineContainsStorm ? TEXT(" · 降雨 · 有雷暴") : TEXT(" · 降雨"));
            TimelineIntensityLabel = !bTimelineEventActive && TimelineStageStates.Num() > 1
                ? TEXT("雨势有变化") : WeatherName(DisplayState);
            TimelineStartLabel = FormatTimelineAbsolute(TimelineEventStart, DaySeconds);
            TimelineEndLabel = bTimelineManual ? TEXT("—") : FormatTimelineAbsolute(TimelineEventEnd, DaySeconds);
            TimelineDurationLabel = bTimelineManual
                ? TEXT("手动控制")
                : FString::Printf(TEXT("%.1f 小时"), (TimelineEventEnd - TimelineEventStart) / DaySeconds * 24.0f);
            TimelineWarningLabel = bTimelineManual
                ? TEXT("手动天气，自动预报暂停")
                : bTimelineContainsStorm ? TEXT("本轮降雨包含雷暴，请留意雨势变化")
                : TEXT("本轮降雨结束后转为") + WeatherName(Weather->GetScheduledStateAt(EndWetSegment / WeatherSegmentsPerDay, EndWetSegment % WeatherSegmentsPerDay));
            TimelineEventFraction = bTimelineEventActive
                ? 0.04f
                : 0.04f + FMath::Clamp((TimelineEventStart - Now) / (DaySeconds * TimelineHorizonDays), 0.0f, 1.0f) * 0.94f;

            FString TimeLabel;
            if (bTimelineEventActive)
            {
                TimeLabel = TEXT("进行中");
            }
            else
            {
                const float GameHours = (TimelineEventStart - Now) / DaySeconds * 24.0f;
                TimeLabel = GameHours < 1.0f ? TEXT("即将发生")
                    : GameHours < 24.0f ? FString::Printf(TEXT("%d 小时后"), FMath::CeilToInt(GameHours))
                    : FString::Printf(TEXT("%.1f 天后"), GameHours / 24.0f);
            }

            TimelineMarkerTimeText->SetText(FText::FromString(TimeLabel));
            TimelineMarkerButton->SetToolTipText(FText::FromString(FString::Printf(TEXT("%s\n%s · 持续 %s\n%s 至 %s\n%s · 点击查看完整预报"),
                *TimelineEventLabel, *TimelineIntensityLabel, *TimelineDurationLabel, *TimelineStartLabel, *TimelineEndLabel,
                bTimelineEventActive ? TEXT("正在发生") : TEXT("即将发生"))));
            if (UTexture2D* EventTexture = LoadUiTexture(WeatherIconFile(DisplayState)))
            {
                TimelineMarkerImage->SetBrushFromTexture(EventTexture, true);
            }
            TimelineEventLine->SetBrush(ColdSteelUI::RoundedBrush(bTimelineContainsStorm ? TimelineCriticalColor : TimelineWeatherColor, 0.0f, FLinearColor::Transparent, 0.0f));
        }
    }

    const int32 EventCount = bTimelineHasEvent ? 1 : 0;
    TimelineWindowText->SetText(FText::FromString(bTimelineWeatherFilter
        ? FString::Printf(TEXT("未来5日 · 显示%d/%d个事件"), EventCount, EventCount)
        : FString::Printf(TEXT("未来5日 · %d个事件"), EventCount)));
    TimelineAllFilterText->SetText(FText::FromString(FString::Printf(TEXT("全部 %d"), EventCount)));
    TimelineWeatherFilterText->SetText(FText::FromString(FString::Printf(TEXT("天气 %d"), EventCount)));
    UpdateEventTimelineFilterButtons();
    TimelineMarkerButton->SetVisibility(bTimelineHasEvent ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    TimelineEventLine->SetVisibility(bTimelineHasEvent ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    if (!bTimelineHasEvent && TimelinePopover) TimelinePopover->SetVisibility(ESlateVisibility::Collapsed);

    const FString NewSignature = FString::Printf(TEXT("%d|%d|%d|%s|%s|%s|%s|%s"), bTimelineHasEvent, bTimelineEventActive,
        bTimelineContainsStorm, *TimelineEventLabel, *TimelineStartLabel, *TimelineEndLabel, *TimelineWarningLabel, *TimelineIntensityLabel);
    if (bForce || NewSignature != TimelineDetailSignature)
    {
        TimelineDetailSignature = NewSignature;
        RebuildEventDetails();
    }
    UpdateEventTimelineLayout();
}

void UColdSteelHUDWidget::UpdateEventTimelineLayout()
{
    if (!TimelineWidthBox || !TimelineTrackSize) return;
    float VitalsOffset = 0.f;
    auto* TimelineRootSlot = Cast<UCanvasPanelSlot>(TimelineWidthBox->Slot);
    if (auto* LiveTimelineSlot = TimelineWidthBox ? Cast<UCanvasPanelSlot>(TimelineWidthBox->Slot) : nullptr; TopVitalsSurface && LiveTimelineSlot)
    {
        const auto& VitalsGeometry = TopVitalsSurface->GetCachedGeometry();
        if (VitalsGeometry.GetLocalSize().Y > 0)
        {
            const float Bottom = GetCachedGeometry().AbsoluteToLocal(VitalsGeometry.LocalToAbsolute(VitalsGeometry.GetLocalSize())).Y;
            VitalsOffset = FMath::Max(0.f, Bottom + ReferenceUnits(8) - 76.f);
            LiveTimelineSlot->SetPosition(FVector2D(0, 76.f + VitalsOffset));
        }
    }
    const float Width = bTimelineCompact ? TimelineCompactWidth : TimelineExpandedWidth;
    TimelineWidthBox->SetWidthOverride(Width);
    TimelineTrackSize->SetHeightOverride(bTimelineCompact ? 30.0f : 44.0f);
    if (UVerticalBoxSlot* TrackSlot = Cast<UVerticalBoxSlot>(TimelineTrackSize->Slot))
    {
        const float SideMargin = bTimelineCompact ? 3.0f : 5.0f;
        TrackSlot->SetPadding(FMargin(SideMargin, 1.0f, SideMargin, 0.0f));
    }
    TimelineExpandedContent->SetVisibility(bTimelineCompact ? ESlateVisibility::Collapsed : ESlateVisibility::SelfHitTestInvisible);
    TimelineNowText->SetVisibility(bTimelineCompact ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
    TimelineMarkerTimeText->SetVisibility(bTimelineCompact ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
    TimelineToggleButton->GetContent()->SetToolTipText(FText::GetEmpty());
    if (UTextBlock* ToggleText = Cast<UTextBlock>(TimelineToggleButton->GetContent()))
    {
        ToggleText->SetText(FText::FromString(bTimelineCompact ? TEXT("⌄") : TEXT("⌃")));
    }
    TimelineToggleButton->SetToolTipText(FText::FromString(bTimelineCompact ? TEXT("展开详细时间进度栏") : TEXT("收起为简化时间进度栏")));
    TimelinePanel->SetPadding(bTimelineCompact ? FMargin(8.0f, 3.0f, 8.0f, 7.0f) : FMargin(10.0f, 8.0f, 10.0f, 17.0f));
    if (UCanvasPanelSlot* PopoverSlot = Cast<UCanvasPanelSlot>(TimelinePopover->Slot))
    {
        PopoverSlot->SetPosition(FVector2D(0.0f, (bTimelineCompact ? 140.0f : 246.0f) + VitalsOffset));
    }

    if (UCanvasPanelSlot* GradientSlot = Cast<UCanvasPanelSlot>(TimelineGradient->Slot))
    {
        GradientSlot->SetOffsets(FMargin(0.0f, bTimelineCompact ? -3.0f : -5.0f, 0.0f, bTimelineCompact ? 3.0f : 5.0f));
    }
    if (UCanvasPanelSlot* EventLineSlot = Cast<UCanvasPanelSlot>(TimelineEventLine->Slot))
    {
        EventLineSlot->SetAnchors(FAnchors(TimelineEventFraction, 0.0f, TimelineEventFraction, 1.0f));
    }
    if (UCanvasPanelSlot* MarkerSlot = Cast<UCanvasPanelSlot>(TimelineMarkerButton->Slot))
    {
        MarkerSlot->SetAnchors(FAnchors(TimelineEventFraction, 0.0f));
        MarkerSlot->SetAlignment(FVector2D(TimelineEventFraction <= 0.08f ? 0.08f : TimelineEventFraction >= 0.92f ? 0.92f : 0.5f, 0.0f));
        MarkerSlot->SetPosition(FVector2D(0.0f, bTimelineCompact ? 1.0f : 2.0f));
    }
    TimelineMarkerImage->SetDesiredSizeOverride(FVector2D(bTimelineCompact ? 14.0f : 18.0f));
}

void UColdSteelHUDWidget::UpdateEventTimelineFilterButtons()
{
    if (!TimelineAllFilterButton || !TimelineWeatherFilterButton) return;
    auto ApplyStyle = [](UButton* Button, bool bSelected)
    {
        const FLinearColor Fill = bSelected
            ? FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("263038F0")))
            : TimelineTrackColor;
        Button->SetStyle(FButtonStyle()
            .SetNormal(ColdSteelUI::RoundedBrush(Fill, 6.0f, bSelected ? ColdSteelUI::Accent : TimelineLineColor, 1.0f))
            .SetHovered(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("232B33FF"))), 6.0f, ColdSteelUI::Accent, 1.0f))
            .SetPressed(ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("1B242CFF"))), 6.0f, ColdSteelUI::Accent, 1.0f)));
    };
    ApplyStyle(TimelineAllFilterButton, !bTimelineWeatherFilter);
    ApplyStyle(TimelineWeatherFilterButton, bTimelineWeatherFilter);
    TimelineAllFilterText->SetColorAndOpacity(!bTimelineWeatherFilter ? ColdSteelUI::TextPrimary : ColdSteelUI::TextSecondary);
    TimelineWeatherFilterText->SetColorAndOpacity(bTimelineWeatherFilter ? ColdSteelUI::TextPrimary : ColdSteelUI::TextSecondary);
}

void UColdSteelHUDWidget::RebuildEventDetails()
{
    if (!TimelineDetailContent) return;
    TimelineDetailContent->ClearChildren();
    if (!bTimelineHasEvent) return;

    UHorizontalBox* Summary = WidgetTree->ConstructWidget<UHorizontalBox>();
    TimelineDetailContent->AddChildToVerticalBox(Summary)->SetPadding(FMargin(0.0f, 0.0f, 0.0f, 4.0f));
    UImage* SummaryImage = WidgetTree->ConstructWidget<UImage>();
    const EFPSWeatherState SummaryState = bTimelineContainsStorm ? EFPSWeatherState::Storm
        : static_cast<EFPSWeatherState>(TimelineStageStates[0]);
    if (UTexture2D* Texture = LoadUiTexture(WeatherIconFile(SummaryState))) SummaryImage->SetBrushFromTexture(Texture, true);
    USizeBox* SummaryIconSize = WidgetTree->ConstructWidget<USizeBox>();
    SummaryIconSize->SetWidthOverride(28.0f);
    SummaryIconSize->SetHeightOverride(28.0f);
    SummaryIconSize->SetContent(SummaryImage);
    Summary->AddChildToHorizontalBox(SummaryIconSize)->SetPadding(FMargin(0.0f, 0.0f, 7.0f, 0.0f));
    UTextBlock* SummaryName = MakeText(TimelineEventLabel, 12, ColdSteelUI::TextPrimary, false, true);
    SummaryName->SetAutoWrapText(true);
    Summary->AddChildToHorizontalBox(SummaryName)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));

    if (TimelineStageStates.Num() > 1)
    {
        FString Sequence = TEXT("依次变化：");
        for (int32 Index = 0; Index < TimelineStageStates.Num(); ++Index)
        {
            if (Index > 0) Sequence += TEXT(" → ");
            Sequence += WeatherName(static_cast<EFPSWeatherState>(TimelineStageStates[Index]));
        }
        UTextBlock* SequenceText = MakeText(Sequence, 12, ColdSteelUI::TextPrimary);
        SequenceText->SetAutoWrapText(true);
        TimelineDetailContent->AddChildToVerticalBox(SequenceText)->SetPadding(FMargin(0.0f, 0.0f, 0.0f, 4.0f));
    }

    UUniformGridPanel* DetailGrid = WidgetTree->ConstructWidget<UUniformGridPanel>();
    DetailGrid->SetSlotPadding(FMargin(2.5f));
    TimelineDetailContent->AddChildToVerticalBox(DetailGrid);
    const TArray<TPair<FString, FString>> DetailPairs = {
        {TEXT("位面"), WeatherRegionName(GetWorld())}, {TEXT("强度"), TimelineIntensityLabel},
        {TEXT("开始"), TimelineStartLabel}, {TEXT("结束"), TimelineEndLabel},
        {TEXT("持续"), TimelineDurationLabel}, {TEXT("强度提示"), TimelineWarningLabel},
        {TEXT("状态"), bTimelineEventActive ? TEXT("正在发生") : TEXT("预测中")}
    };
    for (int32 Index = 0; Index < DetailPairs.Num(); ++Index)
    {
        UBorder* Cell = MakeSurface(TimelineTrackColor, 4.0f, TimelineLineColor, 1.0f);
        Cell->SetPadding(FMargin(5.0f, 2.0f));
        UHorizontalBox* Row = WidgetTree->ConstructWidget<UHorizontalBox>();
        Cell->SetContent(Row);
        Row->AddChildToHorizontalBox(MakeText(DetailPairs[Index].Key, 11, ColdSteelUI::TextTertiary));
        UTextBlock* Value = MakeText(DetailPairs[Index].Value, 11, ColdSteelUI::TextPrimary);
        Value->SetAutoWrapText(true);
        Value->SetJustification(ETextJustify::Right);
        Value->SetToolTipText(FText::FromString(DetailPairs[Index].Value));
        Row->AddChildToHorizontalBox(Value)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        UUniformGridSlot* GridSlot = DetailGrid->AddChildToUniformGrid(Cell, Index / 2, Index % 2);
        GridSlot->SetHorizontalAlignment(HAlign_Fill);
        GridSlot->SetVerticalAlignment(VAlign_Fill);
    }

    if (TimelineStageStates.Num() > 1)
    {
        TimelineDetailContent->AddChildToVerticalBox(MakeText(TEXT("本轮雨势变化（依次发生）"), 12, ColdSteelUI::TextPrimary, false, true))
            ->SetPadding(FMargin(0.0f, 4.0f, 0.0f, 1.0f));
        for (int32 Index = 0; Index < TimelineStageStates.Num(); ++Index)
        {
            const FString Phase = FString::Printf(TEXT("%s  %s — %s"),
                *WeatherName(static_cast<EFPSWeatherState>(TimelineStageStates[Index])),
                *FormatTimelineAbsolute(TimelineStageStarts[Index], TimelineDaySeconds),
                *FormatTimelineAbsolute(TimelineStageEnds[Index], TimelineDaySeconds));
            TimelineDetailContent->AddChildToVerticalBox(MakeText(Phase, 11, ColdSteelUI::TextPrimary));
        }
    }
}

void UColdSteelHUDWidget::SetEventTimelineCompact(bool bCompact)
{
    bTimelineCompact = bCompact;
    if (bTimelineCompact && TimelinePopover) TimelinePopover->SetVisibility(ESlateVisibility::Collapsed);
    UpdateEventTimelineLayout();
}

void UColdSteelHUDWidget::ApplyEventTimelineAuditFixture()
{
    bTimelineHasEvent = true;
    bTimelineEventActive = false;
    bTimelineManual = false;
    bTimelineContainsStorm = false;
    TimelineDaySeconds = 1440.0f;
    TimelineEventStart = 844.0f;
    TimelineEventEnd = 1032.0f;
    TimelineEventFraction = 0.064f;
    TimelineEventLabel = TEXT("天空基地 · 降雨");
    TimelineIntensityLabel = TEXT("雨势有变化");
    TimelineStartLabel = TEXT("第1日 14:04");
    TimelineEndLabel = TEXT("第1日 17:12");
    TimelineDurationLabel = TEXT("3.1 小时");
    TimelineWarningLabel = TEXT("本轮降雨结束后转为阴天");
    TimelineStageStates = {
        static_cast<int32>(EFPSWeatherState::LightRain),
        static_cast<int32>(EFPSWeatherState::Rain),
        static_cast<int32>(EFPSWeatherState::LightRain)
    };
    TimelineStageStarts = {844.0f, 943.0f, 999.0f};
    TimelineStageEnds = {943.0f, 999.0f, 1032.0f};
    TimelineMarkerTimeText->SetText(FText::FromString(TEXT("3 小时后")));
    TimelineWindowText->SetText(FText::FromString(bTimelineWeatherFilter
        ? TEXT("未来5日 · 显示1/1个事件") : TEXT("未来5日 · 1个事件")));
    TimelineAllFilterText->SetText(FText::FromString(TEXT("全部 1")));
    TimelineWeatherFilterText->SetText(FText::FromString(TEXT("天气 1")));
    UpdateEventTimelineFilterButtons();
    TimelineMarkerButton->SetVisibility(ESlateVisibility::Visible);
    TimelineEventLine->SetVisibility(ESlateVisibility::HitTestInvisible);
    if (UTexture2D* EventTexture = LoadUiTexture(TEXT("rain-light.png")))
    {
        TimelineMarkerImage->SetBrushFromTexture(EventTexture, true);
    }
    TimelineEventLine->SetBrush(ColdSteelUI::RoundedBrush(TimelineWeatherColor, 0.0f, FLinearColor::Transparent, 0.0f));
    TimelineMarkerButton->SetToolTipText(FText::FromString(TEXT("天空基地 · 降雨\n雨势有变化 · 持续 3.1 小时\n第1日 14:04 至 第1日 17:12\n即将发生 · 点击查看完整预报")));
    TimelineDetailSignature = TEXT("audit-weather-fixture");
    RebuildEventDetails();
    UpdateEventTimelineLayout();
}

void UColdSteelHUDWidget::SetEventTimelineAuditState(int32 State)
{
    RefreshEventTimeline(true);
    SetEventTimelineCompact(State <= 0);
    if (State >= 2 && bTimelineHasEvent)
    {
        RebuildEventDetails();
        TimelinePopover->SetVisibility(ESlateVisibility::Visible);
    }
}

void UColdSteelHUDWidget::HandleTimelineToggleClicked()
{
    SetEventTimelineCompact(!bTimelineCompact);
}

void UColdSteelHUDWidget::HandleTimelineMarkerClicked()
{
    if (!bTimelineHasEvent) return;
    RebuildEventDetails();
    TimelinePopover->SetVisibility(TimelinePopover->IsVisible() ? ESlateVisibility::Collapsed : ESlateVisibility::Visible);
}

void UColdSteelHUDWidget::HandleTimelineDetailsCloseClicked()
{
    TimelinePopover->SetVisibility(ESlateVisibility::Collapsed);
}

void UColdSteelHUDWidget::HandleTimelineFilterAllClicked()
{
    bTimelineWeatherFilter = false;
    RefreshEventTimeline(true);
    if (TimelinePopover) TimelinePopover->SetVisibility(ESlateVisibility::Collapsed);
}

void UColdSteelHUDWidget::HandleTimelineFilterWeatherClicked()
{
    bTimelineWeatherFilter = true;
    RefreshEventTimeline(true);
    if (TimelinePopover) TimelinePopover->SetVisibility(ESlateVisibility::Collapsed);
}

void UColdSteelHUDWidget::SetInventoryOpen(bool bOpen)
{
    if(!bOpen)HideItemTooltip(true);
    if(!bOpen)CloseWarehouse();
    if (bInventoryOpen == bOpen) return;
    bInventoryOpen = bOpen;
    SetVisibility(bOpen?ESlateVisibility::Visible:ESlateVisibility::SelfHitTestInvisible);
    if(auto* Scroll=Cast<UScrollBox>(EquipmentPage))if(auto* Board=Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0)))Board->CancelInteraction();
    if(bOpen){if(auto* Pawn=GetOwningPlayerPawn<AFPSGAMECharacter>())Pawn->SuspendWeaponForMenu();}
    else UWidgetBlueprintLibrary::CancelDragDrop();
    if (!bOpen)
    {
        HideStatusTooltip();
        bEquipmentTooltipPinned = false;
        HideEquipmentTooltip();
    }
    SetIsFocusable(bOpen);
    if (bOpen)
    {
        RefreshStatus();
        InventoryBlur->SetVisibility(ESlateVisibility::HitTestInvisible);
        InventoryBackdrop->SetVisibility(ESlateVisibility::Visible);
        InventoryPanel->SetVisibility(ESlateVisibility::Visible);
    }
    if (APlayerController* PC = GetOwningPlayer())
    {
        PC->SetIgnoreMoveInput(bOpen);
        PC->SetIgnoreLookInput(bOpen);
        PC->bShowMouseCursor = bOpen;
        if (bOpen)
        {
            FInputModeUIOnly InputMode;
            InputMode.SetWidgetToFocus(TakeWidget());
            InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
            PC->SetInputMode(InputMode);
            CloseButton->SetKeyboardFocus();
        }
        else
        {
            PC->SetInputMode(FInputModeGameOnly());
        }
    }
}

void UColdSteelHUDWidget::SetInventoryTab(bool bStatusTab)
{
    HideItemTooltip(true);
    bStatusTabActive = bStatusTab;
    if (StatusPage) StatusPage->SetVisibility(bStatusTab ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    if (EquipmentPage) EquipmentPage->SetVisibility(bStatusTab ? ESlateVisibility::Collapsed : ESlateVisibility::Visible);
    if (InventoryTitleText) InventoryTitleText->SetText(FText::FromString(bStatusTab ? TEXT("角色状态") : TEXT("装备与背包")));
    if (StatusTabSurface) StatusTabSurface->SetBrush(ColdSteelUI::RoundedBrush(
        bStatusTab ? FLinearColor(0.12f, 0.16f, 0.19f, 0.88f) : FLinearColor(0.08f, 0.10f, 0.12f, 0.5f),
        0.0f, FLinearColor::Transparent, 0.0f));
    if (EquipmentTabSurface) EquipmentTabSurface->SetBrush(ColdSteelUI::RoundedBrush(
        bStatusTab ? FLinearColor(0.08f, 0.10f, 0.12f, 0.5f) : FLinearColor(0.12f, 0.16f, 0.19f, 0.88f),
        0.0f, FLinearColor::Transparent, 0.0f));
    if (StatusTabText) StatusTabText->SetColorAndOpacity(bStatusTab ? ColdSteelUI::TextPrimary : ColdSteelUI::TextTertiary);
    if (EquipmentTabText) EquipmentTabText->SetColorAndOpacity(bStatusTab ? ColdSteelUI::TextTertiary : ColdSteelUI::TextPrimary);
    if (StatusTabUnderline) StatusTabUnderline->SetVisibility(bStatusTab ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    if (EquipmentTabUnderline) EquipmentTabUnderline->SetVisibility(bStatusTab ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
    HideStatusTooltip();
    if (bStatusTab)
    {
        bEquipmentTooltipPinned = false;
        HideEquipmentTooltip();
    }
    RefreshStatus();
}

void UColdSteelHUDWidget::RefreshAmmo()
{
    if(StatusModel)for(int32 N=0;N<HotbarCounts.Num();++N)
    {
        const auto* Item=StatusModel->ResolveHotbar(N);
        HotbarCounts[N]->SetText(FText::FromString(Item?FString::Printf(TEXT("%lld"),Item->Count):TEXT("")));
        if(HotbarImages.IsValidIndex(N)){
            UTexture2D* Texture=nullptr;const FString Icon=Item?ColdSteelInventory::Text(*Item,TEXT("ue_icon")):TEXT("");
            if(!Icon.IsEmpty())Texture=LoadUiTexture(TEXT("../../ColdSteelData/")+Icon);
            HotbarImages[N]->SetVisibility(Texture?ESlateVisibility::HitTestInvisible:ESlateVisibility::Hidden);
            if(Texture)HotbarImages[N]->SetBrushFromTexture(Texture);
        }
    }

    const AFPSGAMECharacter* Character = GetOwningPlayerPawn<AFPSGAMECharacter>();
    if(AmmoReadout)AmmoReadout->Refresh(Character,StatusModel,bInventoryOpen);
}

void UColdSteelHUDWidget::RefreshStatus()
{
    RefreshCharacterSheet();
    const AFPSGAMECharacter* Character = GetOwningPlayerPawn<AFPSGAMECharacter>();
    if (!Character) return;
    const UFPSCombatHealthComponent* Health = Character->FindComponentByClass<UFPSCombatHealthComponent>();
    if (Health && HealthBar && HealthValueText)
    {
        const float MaxHealth = FMath::Max(1.0f, Health->MaxHealth);
        HealthBar->SetPercent(FMath::Clamp(Health->Health / MaxHealth, 0.0f, 1.0f));
        HealthValueText->SetText(FText::FromString(FString::Printf(TEXT("%.0f/%.0f"), Health->Health, MaxHealth)));
    }
    if (AmmoStatusValueText)
    {
        AmmoStatusValueText->SetText(FText::FromString(FString::Printf(TEXT("%d/%d"), Character->GetMagazineAmmo(), Character->GetReserveAmmo())));
    }
    if (MoveSpeedValueText && Character->GetCharacterMovement())
    {
        MoveSpeedValueText->SetText(FText::FromString(FString::Printf(TEXT("%.1f m/s"), Character->GetCharacterMovement()->MaxWalkSpeed / 100.0f)));
    }
    if (EquipmentDamageValue && EquipmentCapacityValue && EquipmentIntervalValue && EquipmentReloadValue && EquipmentAmmoValue)
    {
        float Damage = 0.0f;
        float Interval = 0.0f;
        float Reload = 0.0f;
        int32 Capacity = Character->GetMagazineAmmo();
        if (const FFloatProperty* Property = FindFProperty<FFloatProperty>(Character->GetClass(), TEXT("DamagePerShot"))) Damage = Property->GetPropertyValue_InContainer(Character);
        if (const FFloatProperty* Property = FindFProperty<FFloatProperty>(Character->GetClass(), TEXT("FireInterval"))) Interval = Property->GetPropertyValue_InContainer(Character);
        if (const FFloatProperty* Property = FindFProperty<FFloatProperty>(Character->GetClass(), TEXT("ReloadDuration"))) Reload = Property->GetPropertyValue_InContainer(Character);
        if (const FIntProperty* Property = FindFProperty<FIntProperty>(Character->GetClass(), TEXT("MagazineCapacity"))) Capacity = Property->GetPropertyValue_InContainer(Character);
        EquipmentDamageValue->SetText(FText::FromString(FString::Printf(TEXT("%.0f"), Damage)));
        EquipmentCapacityValue->SetText(FText::FromString(FString::Printf(TEXT("%d 发"), Capacity)));
        EquipmentIntervalValue->SetText(FText::FromString(FString::Printf(TEXT("%.0fms"), Interval * 1000.0f)));
        EquipmentReloadValue->SetText(FText::FromString(FString::Printf(TEXT("%.0fms"), Reload * 1000.0f)));
        EquipmentAmmoValue->SetText(FText::FromString(FString::Printf(TEXT("%d / %d"), Character->GetMagazineAmmo(), Character->GetReserveAmmo())));
    }
}



void UColdSteelHUDWidget::ShowEquipmentTooltip()
{
    if (!EquipmentTooltip || !bInventoryOpen || bStatusTabActive) return;
    RefreshStatus();
    EquipmentTooltip->SetVisibility(ESlateVisibility::Visible);
    EquipmentTooltipScroll->ScrollToEnd();
    if (!bEquipmentTooltipPinned) UpdateEquipmentTooltipPlacement();
}

void UColdSteelHUDWidget::HideEquipmentTooltip()
{
    if (EquipmentTooltip) EquipmentTooltip->SetVisibility(ESlateVisibility::Collapsed);
}

void UColdSteelHUDWidget::UpdateEquipmentTooltipPlacement()
{
    if (!EquipmentTooltipCanvasSlot) return;
    APlayerController* PC = GetOwningPlayer();
    if (!PC) return;
    FVector2D ViewportPixels = UWidgetLayoutLibrary::GetViewportSize(this);
    const float Scale = ColdSteelUI::PixelScale(this);
    const FVector2D ViewportUnits = ViewportPixels / Scale;
    float MouseX = 0.0f;
    float MouseY = 0.0f;
    const bool bMouse = UWidgetLayoutLibrary::GetMousePositionScaledByDPI(PC, MouseX, MouseY);
    if ((!bMouse || (EquippedItemButton && EquippedItemButton->HasKeyboardFocus())) && EquippedItemButton)
    {
        const auto& Geometry = EquippedItemButton->GetCachedGeometry();
        const FVector2D Anchor = GetCachedGeometry().AbsoluteToLocal(Geometry.LocalToAbsolute(FVector2D::ZeroVector));
        MouseX = Anchor.X; MouseY = Anchor.Y;
    }
    const FVector2D Extent(FMath::Min(ReferenceUnits(510), (ViewportPixels.X - 20.0f) / Scale), ReferenceUnits(360.0f));
    const float Gap = ReferenceUnits(10.0f);
    FVector2D Position(MouseX - Extent.X - Gap, MouseY + Gap);
    if (Position.X < Gap) Position.X = MouseX + Gap;
    if (Position.Y + Extent.Y > ViewportUnits.Y - Gap) Position.Y = MouseY - Extent.Y - Gap;
    Position.X = FMath::Clamp(Position.X, Gap, FMath::Max(Gap, ViewportUnits.X - Extent.X - Gap));
    Position.Y = FMath::Clamp(Position.Y, Gap, FMath::Max(Gap, ViewportUnits.Y - Extent.Y - Gap));
    EquipmentTooltipCanvasSlot->SetAnchors(FAnchors(0.0f));
    EquipmentTooltipCanvasSlot->SetPosition(Position);
    EquipmentTooltipCanvasSlot->SetSize(Extent);
}

void UColdSteelHUDWidget::SetInventoryAuditState(int32 State)
{
    SetInventoryOpen(true);
    DrawerProgress = 1.0f;
    if (InventoryPanel) InventoryPanel->SetRenderTranslation(FVector2D::ZeroVector);
    if (State <= 0)
    {
        SetInventoryTab(true);
        ShowStatusTooltip(TEXT("str"));
    }
    else
    {
        SetInventoryTab(false);
        bEquipmentTooltipPinned = true;
        ShowEquipmentTooltip();
    }
}

void UColdSteelHUDWidget::HandleStatusTabClicked() { OpenStatus(); }
void UColdSteelHUDWidget::HandleEquipmentTabClicked() { SetInventoryTab(false); }
void UColdSteelHUDWidget::HandleStrengthHovered() { ShowStatusTooltip(TEXT("str")); }
void UColdSteelHUDWidget::HandleDexterityHovered() { ShowStatusTooltip(TEXT("dex")); }
void UColdSteelHUDWidget::HandleIntelligenceHovered() { ShowStatusTooltip(TEXT("intt")); }
void UColdSteelHUDWidget::HandleConstitutionHovered() { ShowStatusTooltip(TEXT("con")); }
void UColdSteelHUDWidget::HandleWisdomHovered() { ShowStatusTooltip(TEXT("wis")); }
void UColdSteelHUDWidget::HandleLuckHovered() { ShowStatusTooltip(TEXT("luck")); }
void UColdSteelHUDWidget::HandleAttributeUnhovered() { HideStatusTooltip(); }
void UColdSteelHUDWidget::HandleEquipmentHovered() { ShowEquipmentTooltip(); }
void UColdSteelHUDWidget::HandleEquipmentUnhovered() { if (!bEquipmentTooltipPinned && (!EquippedItemButton || !EquippedItemButton->HasKeyboardFocus())) HideEquipmentTooltip(); }
void UColdSteelHUDWidget::HandleEquipmentClicked()
{
    bEquipmentTooltipPinned = !bEquipmentTooltipPinned;
    if (bEquipmentTooltipPinned) ShowEquipmentTooltip(); else HideEquipmentTooltip();
}
void UColdSteelHUDWidget::HandleEquipmentTooltipCloseClicked()
{
    bEquipmentTooltipPinned = false;
    HideEquipmentTooltip();
}

UTextBlock* UColdSteelHUDWidget::MakeText(const FString& Text, int32 Size, const FLinearColor& Color, bool bNumeric, bool bBold)
{
    UTextBlock* Label = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), *FString::Printf(TEXT("Text_%d"), WidgetSerial++));
    Label->SetText(FText::FromString(Text));
    Label->SetFont(bNumeric ? ColdSteelUI::NumberFont(Size, bBold) : ColdSteelUI::TextFont(Size));
    Label->SetColorAndOpacity(Color);
    Label->SetShadowOffset(FVector2D(0.0f, 1.0f));
    Label->SetShadowColorAndOpacity(FLinearColor(0.0f, 0.0f, 0.0f, 0.55f));
    return Label;
}

float UColdSteelHUDWidget::ReferenceUnits(float PixelSize) const
{
    const float ViewportScale = ColdSteelUI::PixelScale(this);
    return PixelSize / ViewportScale;
}

UTextBlock* UColdSteelHUDWidget::MakeReferenceText(const FString& Text, float PixelSize, const FLinearColor& Color, bool bNumeric, bool bBold)
{
    auto* Label = MakeText(Text, 12, Color, bNumeric, bBold);
    // Slate uses points at 96 DPI; the reference contract specifies physical pixels.
    const float Points = ReferenceUnits(PixelSize) * .75f;
    Label->SetFont(bNumeric ? ColdSteelUI::NumberFont(Points, bBold) : ColdSteelUI::TextFont(Points));
    return Label;
}

UBorder* UColdSteelHUDWidget::MakeSurface(const FLinearColor& Fill, float Radius, const FLinearColor& Outline, float OutlineWidth)
{
    UBorder* Surface = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), *FString::Printf(TEXT("Surface_%d"), WidgetSerial++));
    Surface->SetBrush(ColdSteelUI::RoundedBrush(Fill, Radius, Outline, OutlineWidth));
    return Surface;
}

UBorder* UColdSteelHUDWidget::MakeHotbarSlot(const FString& KeyHint, const FString& Caption)
{
    UBorder* SlotSurface = MakeSurface(ColdSteelUI::Content, 7.0f, ColdSteelUI::Border);
    USizeBox* Size = WidgetTree->ConstructWidget<USizeBox>();
    Size->SetWidthOverride(ReferenceUnits(HotbarSlotSize));
    Size->SetHeightOverride(ReferenceUnits(HotbarSlotSize));
    SlotSurface->SetContent(Size);
    UOverlay* Overlay = WidgetTree->ConstructWidget<UOverlay>();
    Size->SetContent(Overlay);
    if(KeyHint.IsNumeric())
    {
        auto* Icon=WidgetTree->ConstructWidget<UImage>();Icon->SetVisibility(ESlateVisibility::HitTestInvisible);
        auto* IconSlot=Overlay->AddChildToOverlay(Icon);IconSlot->SetPadding(FMargin(ReferenceUnits(6)));HotbarImages.Add(Icon);
        auto* Count=MakeReferenceText(TEXT(""),11,ColdSteelUI::TextPrimary,true);auto* CountSlot=Overlay->AddChildToOverlay(Count);
        CountSlot->SetHorizontalAlignment(HAlign_Right);CountSlot->SetVerticalAlignment(VAlign_Top);CountSlot->SetPadding(FMargin(ReferenceUnits(2)));HotbarCounts.Add(Count);
    }
    if (!Caption.IsEmpty())
    {
        UOverlaySlot* CaptionSlot = Overlay->AddChildToOverlay(MakeText(Caption, 11, ColdSteelUI::TextTertiary));
        CaptionSlot->SetHorizontalAlignment(HAlign_Center);
        CaptionSlot->SetVerticalAlignment(VAlign_Center);
    }
    UOverlaySlot* KeySlot = Overlay->AddChildToOverlay(MakeReferenceText(KeyHint, 12, ColdSteelUI::TextPrimary, true, true));
    KeySlot->SetHorizontalAlignment(HAlign_Right);
    KeySlot->SetVerticalAlignment(VAlign_Bottom);
    KeySlot->SetPadding(FMargin(0.0f, 0.0f, 4.0f, 2.0f));
    return SlotSurface;
}

UBorder* UColdSteelHUDWidget::MakeEquipmentSlot(const FString& Caption, bool bEquipped)
{
    UBorder* Surface = MakeSurface(bEquipped ? SlotEquipped : SlotDark, 7.0f, ColdSteelUI::Border);
    Surface->SetPadding(FMargin(4.0f));
    USizeBox* Height = WidgetTree->ConstructWidget<USizeBox>();
    Height->SetMinDesiredHeight(50.0f);
    Surface->SetContent(Height);
    UOverlay* Layer = WidgetTree->ConstructWidget<UOverlay>();
    Height->SetContent(Layer);
    if (bEquipped)
    {
        if (UTexture2D* Texture = LoadUiTexture(TEXT("ue_m4a1.png")))
        {
            UImage* Image = WidgetTree->ConstructWidget<UImage>();
            Image->SetBrushFromTexture(Texture, true);
            UOverlaySlot* ImageSlot = Layer->AddChildToOverlay(Image);
            ImageSlot->SetHorizontalAlignment(HAlign_Fill);
            ImageSlot->SetVerticalAlignment(VAlign_Fill);
            ImageSlot->SetPadding(FMargin(24.0f, 4.0f, 20.0f, 4.0f));
        }
        UBorder* Rail = MakeSurface(FLinearColor(0.72f, 0.76f, 0.84f, 0.9f), 3.0f, FLinearColor::Transparent, 0.0f);
        UOverlaySlot* RailSlot = Layer->AddChildToOverlay(Rail);
        RailSlot->SetHorizontalAlignment(HAlign_Left);
        RailSlot->SetVerticalAlignment(VAlign_Fill);
        RailSlot->SetPadding(FMargin(2.0f));
        USizeBox* RailWidth = WidgetTree->ConstructWidget<USizeBox>();
        RailWidth->SetWidthOverride(8.0f);
        Rail->SetContent(RailWidth);
    }
    else
    {
        UTextBlock* Label = MakeReferenceText(Caption, 16, Caption == TEXT("双手占用") ? FLinearColor(0.35f, 0.38f, 0.40f, 1.0f) : ColdSteelUI::TextSecondary);
        Label->SetJustification(ETextJustify::Center);
        UOverlaySlot* LabelSlot = Layer->AddChildToOverlay(Label);
        LabelSlot->SetHorizontalAlignment(HAlign_Fill);
        LabelSlot->SetVerticalAlignment(VAlign_Center);
    }
    return Surface;
}

UBorder* UColdSteelHUDWidget::MakeTab(const FString& Caption, bool bActive)
{
    UBorder* Surface = MakeSurface(bActive ? FLinearColor(0.12f, 0.16f, 0.19f, 0.88f) : FLinearColor(0.08f, 0.10f, 0.12f, 0.5f), 0.0f, FLinearColor::Transparent, 0.0f);
    USizeBox* Height = WidgetTree->ConstructWidget<USizeBox>();
    Height->SetHeightOverride(ReferenceUnits(50));
    Surface->SetContent(Height);
    UOverlay* Layer = WidgetTree->ConstructWidget<UOverlay>();
    Height->SetContent(Layer);
    UTextBlock* Label = MakeReferenceText(Caption, 16, bActive ? ColdSteelUI::TextPrimary : ColdSteelUI::TextTertiary);
    Label->SetJustification(ETextJustify::Center);
    UOverlaySlot* LabelSlot = Layer->AddChildToOverlay(Label);
    LabelSlot->SetHorizontalAlignment(HAlign_Fill);
    LabelSlot->SetVerticalAlignment(VAlign_Center);
    UBorder* Underline = MakeSurface(ColdSteelUI::Accent, 0.0f, FLinearColor::Transparent, 0.0f);
    Underline->SetVisibility(bActive ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    UOverlaySlot* UnderlineSlot = Layer->AddChildToOverlay(Underline);
    UnderlineSlot->SetHorizontalAlignment(HAlign_Fill);
    UnderlineSlot->SetVerticalAlignment(VAlign_Bottom);
    USizeBox* UnderlineHeight = WidgetTree->ConstructWidget<USizeBox>();
    UnderlineHeight->SetHeightOverride(3.0f);
    Underline->SetContent(UnderlineHeight);
    return Surface;
}

UTexture2D* UColdSteelHUDWidget::LoadUiTexture(const FString& Filename)
{
    if (const TObjectPtr<UTexture2D>* Existing = LoadedTextureCache.Find(Filename))
    {
        return Existing->Get();
    }
    const FString Path = FPaths::ProjectContentDir() / TEXT("ColdSteelUI/Icons") / Filename;
    UTexture2D* Texture = FImageUtils::ImportFileAsTexture2D(Path);
    if (Texture)
    {
        LoadedTextures.Add(Texture);
        LoadedTextureCache.Add(Filename, Texture);
    }
    return Texture;
}

void UColdSteelHUDWidget::HandleCloseClicked()
{
    SetInventoryOpen(false);
}
