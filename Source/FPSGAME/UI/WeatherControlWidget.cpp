#include "WeatherControlWidget.h"
#include "ColdSteelUIStyle.h"
#include "../FPSWeatherManager.h"
#include "../FPSGAMEPlayerController.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/ScaleBox.h"
#include "Components/SizeBox.h"
#include "Components/ScrollBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "EngineUtils.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"

namespace
{
    const TCHAR* PresetNames[] = {TEXT("晴天"), TEXT("阴天"), TEXT("小雨"), TEXT("中雨"), TEXT("暴风雨")};
}

void UWeatherControlWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(true);
    auto* Root = WidgetTree->ConstructWidget<UCanvasPanel>();
    WidgetTree->RootWidget = Root;
    auto* HintStack = WidgetTree->ConstructWidget<UVerticalBox>();
    auto* Hint = AddButton(HintStack, TEXT("F6  天气控制"), TEXT("WeatherOpen"));
    Hint->OnClicked.AddDynamic(this, &ThisClass::OpenClicked);
    auto* HintSlot = Root->AddChildToCanvas(HintStack);
    HintSlot->SetAnchors(FAnchors(0.0f, 1.0f));
    HintSlot->SetAlignment(FVector2D(0.0f, 1.0f));
    HintSlot->SetPosition(FVector2D(16.0f, -90.0f));
    HintSlot->SetAutoSize(true);

    auto* Fit = WidgetTree->ConstructWidget<UScaleBox>();
    Fit->SetStretch(EStretch::ScaleToFit);
    Fit->SetStretchDirection(EStretchDirection::DownOnly);
    Panel = Fit;
    auto* FitSlot = Root->AddChildToCanvas(Fit);
    FitSlot->SetAnchors(FAnchors(0.0f, 0.0f, 1.0f, 1.0f));
    FitSlot->SetOffsets(FMargin(20.0f));
    auto* Size = WidgetTree->ConstructWidget<USizeBox>();
    const float PixelScale = ColdSteelUI::PixelScale(this);
    Size->SetWidthOverride(450.0f / PixelScale);
    const float ViewportHeight = UWidgetLayoutLibrary::GetViewportSize(this).Y;
    Size->SetHeightOverride((ViewportHeight >= 100 ? FMath::Min(640.0f, ViewportHeight - 40) : 480.0f) / PixelScale);
    Fit->AddChild(Size);
    auto* Surface = WidgetTree->ConstructWidget<UBorder>();
    Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint, 24.0f / PixelScale));
    Surface->SetPadding(FMargin(24.0f / PixelScale));
    Size->AddChild(Surface);
    auto* Stack = WidgetTree->ConstructWidget<UVerticalBox>();
    Surface->SetContent(Stack);
    auto* Title = WidgetTree->ConstructWidget<UTextBlock>();
    Title->SetText(FText::FromString(TEXT("天气控制")));
    Title->SetFont(ColdSteelUI::TextFont(18 / PixelScale));
    Title->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    Stack->AddChildToVerticalBox(Title)->SetPadding(FMargin(0, 0, 0, 12));
    Status = WidgetTree->ConstructWidget<UTextBlock>();
    Status->SetFont(ColdSteelUI::TextFont(10.5f / PixelScale));
    Status->SetColorAndOpacity(ColdSteelUI::Accent);
    Status->SetAutoWrapText(true);
    Stack->AddChildToVerticalBox(Status)->SetPadding(FMargin(0, 0, 0, 14));
    auto* Scroll = WidgetTree->ConstructWidget<UScrollBox>();
    Scroll->SetScrollbarThickness(FVector2D(4, 4));
    Stack->AddChildToVerticalBox(Scroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* Presets = WidgetTree->ConstructWidget<UVerticalBox>();
    Scroll->AddChild(Presets);
    const TCHAR* Captions[] = {TEXT("晴天 · 停雨"), TEXT("阴天 · 无降雨"), TEXT("小雨 · 35% · 轻柔雨声"),
        TEXT("中雨 · 68% · 密集雨滴"), TEXT("暴风雨 · 100% · 闪电与雷声"), TEXT("恢复自动天气")};
    for (int32 Index = 0; Index < 6; ++Index)
        PresetButtons.Add(AddButton(Presets, Captions[Index], *FString::Printf(TEXT("WeatherPreset%d"), Index)));
    PresetButtons[0]->OnClicked.AddDynamic(this, &ThisClass::ClearClicked);
    PresetButtons[1]->OnClicked.AddDynamic(this, &ThisClass::CloudyClicked);
    PresetButtons[2]->OnClicked.AddDynamic(this, &ThisClass::LightClicked);
    PresetButtons[3]->OnClicked.AddDynamic(this, &ThisClass::RainClicked);
    PresetButtons[4]->OnClicked.AddDynamic(this, &ThisClass::StormClicked);
    PresetButtons[5]->OnClicked.AddDynamic(this, &ThisClass::AutoClicked);
    auto* Help = WidgetTree->ConstructWidget<UTextBlock>();
    Help->SetText(FText::FromString(TEXT("雨量约 8 秒渐变；手动选择会暂停自动天气。\n昼夜继续运行，进入遮蔽物后雨滴与雨声减弱。")));
    Help->SetFont(ColdSteelUI::TextFont(9 / PixelScale));
    Help->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Help->SetAutoWrapText(true);
    Presets->AddChildToVerticalBox(Help)->SetPadding(FMargin(0, 10, 0, 10));
    CloseButton = AddButton(Stack, TEXT("返回游戏  ·  F6 / Esc"), TEXT("WeatherClose"));
    CloseButton->OnClicked.AddDynamic(this, &ThisClass::CloseClicked);
    Panel->SetVisibility(ESlateVisibility::Collapsed);
}

UButton* UWeatherControlWidget::AddButton(UVerticalBox* Stack, const FString& Caption, const FName Name)
{
    auto* Button = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass(), Name);
    FButtonStyle Style;
    Style.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonNormal, 12));
    Style.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, 12, ColdSteelUI::Accent));
    Style.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed, 12, ColdSteelUI::Accent));
    Style.SetNormalPadding(FMargin(12, 9));
    Style.SetPressedPadding(FMargin(12, 9));
    Button->SetStyle(Style);
    auto* Text = WidgetTree->ConstructWidget<UTextBlock>();
    Text->SetText(FText::FromString(Caption));
    Text->SetFont(ColdSteelUI::TextFont(12 / ColdSteelUI::PixelScale(this)));
    Text->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    Button->AddChild(Text);
    Stack->AddChildToVerticalBox(Button)->SetPadding(FMargin(0, 3));
    return Button;
}

AFPSWeatherManager* UWeatherControlWidget::ResolveWeather()
{
    if (!Weather.IsValid())
        for (TActorIterator<AFPSWeatherManager> It(GetWorld()); It; ++It) { Weather = *It; break; }
    return Weather.Get();
}

void UWeatherControlWidget::SetPanelOpen(bool bOpen)
{
    if (bPanelOpen == bOpen) return;
    bPanelOpen = bOpen;
    Panel->SetVisibility(bOpen ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    if (auto* PC = GetOwningPlayer())
    {
        PC->SetIgnoreMoveInput(bOpen);
        PC->SetIgnoreLookInput(bOpen);
        PC->bShowMouseCursor = bOpen;
        if (bOpen)
        {
            FInputModeGameAndUI Mode;
            Mode.SetWidgetToFocus(TakeWidget());
            Mode.SetHideCursorDuringCapture(false);
            Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
            PC->SetInputMode(Mode);
            CloseButton->SetKeyboardFocus();
        }
        else PC->SetInputMode(FInputModeGameOnly());
    }
    GetWorld()->GetTimerManager().ClearTimer(RefreshTimer);
    if (bOpen)
    {
        RefreshStatus();
        GetWorld()->GetTimerManager().SetTimer(RefreshTimer, this, &ThisClass::RefreshStatus, 0.2f, true);
    }
}

void UWeatherControlWidget::RefreshStatus()
{
    auto* Manager = ResolveWeather();
    for (UButton* Button : PresetButtons) Button->SetIsEnabled(Manager != nullptr);
    if (!Manager) { Status->SetText(FText::FromString(TEXT("当前场景未找到天气系统"))); return; }
    const int32 Minutes = FMath::FloorToInt(Manager->NormalizedDayTime * 1440.0f) % 1440;
    const FString Map = UGameplayStatics::GetCurrentLevelName(this, true);
    const FString Scene = Map == TEXT("L_Normandy_FPS_Test") ? TEXT("村庄") : Map == TEXT("L_MilitaryTrench_FPS_Test") ? TEXT("战壕") : Map;
    Status->SetText(FText::FromString(FString::Printf(TEXT("%s  ·  %02d:%02d\n%s · %s  |  当前雨量 %.0f%%\n昼夜：%s"),
        *Scene, Minutes / 60, Minutes % 60, Manager->bAutomaticSchedule ? TEXT("自动天气") : TEXT("手动天气"),
        PresetNames[FMath::Clamp(static_cast<int32>(Manager->CurrentState), 0, 4)], Manager->GetEffectiveRainIntensity() * 100,
        Manager->IsSkyClockConnected() ? TEXT("已连接天空时钟") : Manager->IsSceneDayNightActive() ? TEXT("已连接场景光照") : TEXT("未连接场景光照"))));
    for (int32 Index = 0; Index < PresetButtons.Num(); ++Index)
        PresetButtons[Index]->SetBackgroundColor((Index == 5 ? Manager->bAutomaticSchedule :
            static_cast<int32>(Manager->CurrentState) == Index) ? ColdSteelUI::Accent : FLinearColor::White);
}

void UWeatherControlWidget::SelectPreset(int32 State)
{
    if (State >= 0 && State <= 4)
        if (auto* Manager = ResolveWeather()) Manager->SetWeatherState(static_cast<EFPSWeatherState>(State));
    RefreshStatus();
}
void UWeatherControlWidget::SelectAutomatic() { if (auto* Manager = ResolveWeather()) Manager->ResumeAutomaticSchedule(); RefreshStatus(); }
void UWeatherControlWidget::OpenClicked() { if (auto* PC = GetOwningPlayer<AFPSGAMEPlayerController>()) PC->ToggleWeatherPanel(); }
void UWeatherControlWidget::CloseClicked() { SetPanelOpen(false); }
void UWeatherControlWidget::ClearClicked() { SelectPreset(0); }
void UWeatherControlWidget::CloudyClicked() { SelectPreset(1); }
void UWeatherControlWidget::LightClicked() { SelectPreset(2); }
void UWeatherControlWidget::RainClicked() { SelectPreset(3); }
void UWeatherControlWidget::StormClicked() { SelectPreset(4); }
void UWeatherControlWidget::AutoClicked() { SelectAutomatic(); }
FReply UWeatherControlWidget::NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (bPanelOpen)
    {
        if (Event.GetKey() == EKeys::F6 || Event.GetKey() == EKeys::Escape) SetPanelOpen(false);
        return FReply::Handled();
    }
    return Super::NativeOnKeyDown(Geometry, Event);
}
void UWeatherControlWidget::NativeDestruct()
{
    SetPanelOpen(false);
    if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(RefreshTimer);
    Weather.Reset();
    Super::NativeDestruct();
}
