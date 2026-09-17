#include "WeatherControlWidget.h"
#include "ColdSteelUIStyle.h"
#include "../FPSWeatherManager.h"
#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
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
    const TCHAR* PresetNames[] = {TEXT("晴天"), TEXT("多云"), TEXT("小雨"), TEXT("中雨"), TEXT("暴风雨")};
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
    auto* Scroll = WidgetTree->ConstructWidget<UScrollBox>();
    Scroll->SetScrollbarThickness(FVector2D(4, 4));
    Stack->AddChildToVerticalBox(Scroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* Presets = WidgetTree->ConstructWidget<UVerticalBox>();
    Scroll->AddChild(Presets);
    BuildWeatherContent(Presets);
    CloseButton = AddButton(Stack, TEXT("返回游戏  ·  F6 / Esc"), TEXT("WeatherClose"));
    CloseButton->OnClicked.AddDynamic(this, &ThisClass::CloseClicked);
    Panel->SetVisibility(ESlateVisibility::Collapsed);
}

void UWeatherControlWidget::BuildWeatherContent(UVerticalBox* Presets)
{
    Status = CreatePanelText(TEXT("正在读取天气"), 14, ColdSteelUI::TextSecondary);
    Presets->AddChildToVerticalBox(Status)->SetPadding(FMargin(0, 0, 0, 14));
    const TCHAR* Captions[] = {TEXT("晴天 · 疏云"), TEXT("多云 · 无降雨"), TEXT("小雨 · 35% · 轻柔雨声"),
        TEXT("中雨 · 68% · 密集雨滴"), TEXT("暴风雨 · 100% · 闪电与雷声"), TEXT("恢复自动天气")};
    for (int32 Index = 0; Index < 6; ++Index)
        PresetButtons.Add(AddButton(Presets, Captions[Index], *FString::Printf(TEXT("WeatherPreset%d"), Index)));
    PresetButtons[0]->OnClicked.AddDynamic(this, &ThisClass::ClearClicked);
    PresetButtons[1]->OnClicked.AddDynamic(this, &ThisClass::CloudyClicked);
    PresetButtons[2]->OnClicked.AddDynamic(this, &ThisClass::LightClicked);
    PresetButtons[3]->OnClicked.AddDynamic(this, &ThisClass::RainClicked);
    PresetButtons[4]->OnClicked.AddDynamic(this, &ThisClass::StormClicked);
    PresetButtons[5]->OnClicked.AddDynamic(this, &ThisClass::AutoClicked);
    auto* Help = CreatePanelText(TEXT("降雨前先转多云，再渐增雨量；手动选择会暂停自动天气。\n昼夜继续运行，进入遮蔽物后雨滴与雨声减弱。"), 12, ColdSteelUI::TextSecondary);
    Presets->AddChildToVerticalBox(Help)->SetPadding(FMargin(0, 10, 0, 10));
}

UTextBlock* UWeatherControlWidget::CreatePanelText(const FString& Caption, float Pixels, FLinearColor Color)
{
    auto* Text = WidgetTree->ConstructWidget<UTextBlock>();
    Text->SetText(FText::FromString(Caption));
    Text->SetFont(ColdSteelUI::TextFont(Pixels * .75f / ColdSteelUI::PixelScale(this)));
    Text->SetColorAndOpacity(Color); Text->SetAutoWrapText(true);
    TextSizes.Emplace(Text, Pixels);
    return Text;
}

UButton* UWeatherControlWidget::CreatePanelButton(const FString& Caption, FName Name)
{
    auto* Button = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass(), Name);
    Button->SetStyle(ColdSteelUI::ButtonStyle(1.f / ColdSteelUI::PixelScale(this)));
    auto* Text = CreatePanelText(Caption, 14, ColdSteelUI::TextPrimary);
    Text->SetJustification(ETextJustify::Center);
    Button->AddChild(Text);
    return Button;
}

UButton* UWeatherControlWidget::AddButton(UVerticalBox* Stack, const FString& Caption, const FName Name)
{
    auto* Button = CreatePanelButton(Caption, Name);
    Stack->AddChildToVerticalBox(Button)->SetPadding(FMargin(0, 3));
    return Button;
}

void UWeatherControlWidget::RefreshPanelTypography()
{
    const float Scale = ColdSteelUI::PixelScale(this);
    for (const auto& Item : TextSizes) if (Item.Key.IsValid()) Item.Key->SetFont(ColdSteelUI::TextFont(Item.Value * .75f / Scale));
    TArray<UWidget*> Widgets; WidgetTree->GetAllWidgets(Widgets);
    for (auto* Widget : Widgets) if (auto* Button = Cast<UButton>(Widget)) Button->SetStyle(ColdSteelUI::ButtonStyle(1.f / Scale));
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
            UWidgetBlueprintLibrary::CancelDragDrop();
            if (auto* Character = Cast<AFPSGAMECharacter>(PC->GetPawn())) Character->SuspendWeaponForMenu();
            // 与背包装备同一打开规则：UIOnly 接管输入，鼠标可见并锁定移动／视角。
            FInputModeUIOnly Mode;
            Mode.SetWidgetToFocus(TakeWidget());
            Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
            PC->SetInputMode(Mode);
            CloseButton->SetKeyboardFocus();
        }
        else PC->SetInputMode(FInputModeGameOnly());
    }
    if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(RefreshTimer);
    if (bOpen && GetWorld())
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
    FString StatusText = FString::Printf(TEXT("%s  ·  %02d:%02d\n%s · %s  |  当前雨量 %.0f%%\n昼夜：%s"),
        *Scene, Minutes / 60, Minutes % 60, Manager->bAutomaticSchedule ? TEXT("自动天气") : TEXT("手动天气"),
        PresetNames[FMath::Clamp(static_cast<int32>(Manager->CurrentState), 0, 4)], Manager->GetEffectiveRainIntensity() * 100,
        Manager->IsSkyClockConnected() ? TEXT("已连接天空时钟") : Manager->IsSceneDayNightActive() ? TEXT("已连接场景光照") : TEXT("未连接场景光照"));
    if (Manager->IsRainPending())
        StatusText += FString::Printf(TEXT("\n云层正在聚集，约 %d 秒后开始%s"), FMath::CeilToInt(Manager->GetRainLeadInRemaining()),
            PresetNames[FMath::Clamp(static_cast<int32>(Manager->GetPendingRainState()), 0, 4)]);
    Status->SetText(FText::FromString(StatusText));
    for (int32 Index = 0; Index < PresetButtons.Num(); ++Index)
    {
        const bool Selected = Index == 5 ? Manager->bAutomaticSchedule : !Manager->bAutomaticSchedule &&
            static_cast<int32>(Manager->IsRainPending() ? Manager->GetPendingRainState() : Manager->CurrentState) == Index;
        auto Style = ColdSteelUI::ButtonStyle(1.f / ColdSteelUI::PixelScale(this));
        if (Selected) Style.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, ColdSteelUI::ButtonRadius / ColdSteelUI::PixelScale(this), ColdSteelUI::Accent));
        PresetButtons[Index]->SetStyle(Style);
    }
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
