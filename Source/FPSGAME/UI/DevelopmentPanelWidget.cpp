#include "DevelopmentPanelWidget.h"
#include "ColdSteelUIStyle.h"
#include "../FPSGAMEPlayerController.h"
#include "../Development/DevelopmentSpawnComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScrollBox.h"
#include "Components/SpinBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/WidgetSwitcher.h"
#include "InputCoreTypes.h"

void UDevelopmentPanelWidget::NativeOnInitialized()
{
    // The shared base contributes weather content/input, while this owns its shell.
    UUserWidget::NativeOnInitialized();
    SetIsFocusable(true);
    auto* Root = WidgetTree->ConstructWidget<UCanvasPanel>();
    Root->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    WidgetTree->RootWidget = Root;
    auto* Shortcut = CreatePanelButton(TEXT("F6  开发面板"), TEXT("DevelopmentOpen"));
    Shortcut->OnClicked.AddDynamic(this, &ThisClass::OpenDeveloper);
    ShortcutSlot = Root->AddChildToCanvas(Shortcut);
    ShortcutSlot->SetAnchors(FAnchors(0, 1));
    ShortcutSlot->SetAlignment(FVector2D(0, 1));
    ShortcutSlot->SetAutoSize(true);

    auto* Shell = WidgetTree->ConstructWidget<UOverlay>();
    Panel = Shell;
    PanelSlot = Root->AddChildToCanvas(Shell);
    PanelSlot->SetAnchors(FAnchors(1, 0));
    PanelSlot->SetAlignment(FVector2D(1, 0));
    Blur = WidgetTree->ConstructWidget<UBackgroundBlur>();
    Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);
    Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);
    Blur->SetApplyAlphaToBlur(false);
    auto* BlurSlot = Shell->AddChildToOverlay(Blur);
    BlurSlot->SetHorizontalAlignment(HAlign_Fill); BlurSlot->SetVerticalAlignment(VAlign_Fill);
    Surface = WidgetTree->ConstructWidget<UBorder>();
    auto* SurfaceSlot = Shell->AddChildToOverlay(Surface);
    SurfaceSlot->SetHorizontalAlignment(HAlign_Fill); SurfaceSlot->SetVerticalAlignment(VAlign_Fill);
    auto* Stack = WidgetTree->ConstructWidget<UVerticalBox>(); Surface->SetContent(Stack);
    Stack->AddChildToVerticalBox(CreatePanelText(TEXT("交互开发面板"), 20, ColdSteelUI::TextPrimary))->SetPadding(FMargin(0,0,0,10));
    auto* Tabs = WidgetTree->ConstructWidget<UHorizontalBox>();
    Stack->AddChildToVerticalBox(Tabs)->SetPadding(FMargin(0,0,0,14));
    WeatherTab = CreatePanelButton(TEXT("天气环境"), TEXT("DevelopmentWeatherTab"));
    MonsterTab = CreatePanelButton(TEXT("怪物生成"), TEXT("DevelopmentMonsterTab"));
    TuningTab = CreatePanelButton(TEXT("基本调参"), TEXT("DevelopmentTuningTab"));
    for (auto* Button : {TuningTab.Get(), WeatherTab.Get(), MonsterTab.Get()})
    {
        auto* TabSlot = Tabs->AddChildToHorizontalBox(Button); TabSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill)); TabSlot->SetPadding(FMargin(2,0));
    }
    WeatherTab->OnClicked.AddDynamic(this, &ThisClass::WeatherClicked);
    MonsterTab->OnClicked.AddDynamic(this, &ThisClass::MonstersClicked);
    TuningTab->OnClicked.AddDynamic(this, &ThisClass::TuningClicked);
    auto* Scroll = WidgetTree->ConstructWidget<UScrollBox>();
    Scroll->SetScrollbarThickness(FVector2D(6,6));
    Stack->AddChildToVerticalBox(Scroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Pages = WidgetTree->ConstructWidget<UWidgetSwitcher>(); Scroll->AddChild(Pages);
    auto* WeatherPage = WidgetTree->ConstructWidget<UVerticalBox>(); Pages->AddChild(WeatherPage);
    BuildWeatherContent(WeatherPage);

    auto* MonsterPage = WidgetTree->ConstructWidget<UVerticalBox>(); Pages->AddChild(MonsterPage);
    auto Label = [this, MonsterPage](const TCHAR* Caption)
    {
        MonsterPage->AddChildToVerticalBox(CreatePanelText(Caption, 16, ColdSteelUI::TextPrimary))->SetPadding(FMargin(0,12,0,6));
    };
    Label(TEXT("怪物类型"));
    MonsterChoice = WidgetTree->ConstructWidget<UComboBoxString>();
    MonsterChoice->OnGenerateWidgetEvent.BindDynamic(this, &ThisClass::GenerateMonsterOption);
    MonsterChoice->OnSelectionChanged.AddDynamic(this, &ThisClass::MonsterSelected);
    MonsterPage->AddChildToVerticalBox(MonsterChoice);
    Label(TEXT("生成数量"));
    CountBox = WidgetTree->ConstructWidget<USpinBox>();
    CountBox->SetMinValue(1); CountBox->SetMaxValue(10); CountBox->SetMinSliderValue(1); CountBox->SetMaxSliderValue(10);
    CountBox->SetDelta(1); CountBox->SetMinFractionalDigits(0); CountBox->SetMaxFractionalDigits(0); CountBox->SetValue(1);
    MonsterPage->AddChildToVerticalBox(CountBox);
    Label(TEXT("前方距离 · 米"));
    DistanceBox = WidgetTree->ConstructWidget<USpinBox>();
    DistanceBox->SetMinValue(3); DistanceBox->SetMaxValue(15); DistanceBox->SetMinSliderValue(3); DistanceBox->SetMaxSliderValue(15);
    DistanceBox->SetDelta(.5f); DistanceBox->SetMinFractionalDigits(1); DistanceBox->SetMaxFractionalDigits(1); DistanceBox->SetValue(5);
    MonsterPage->AddChildToVerticalBox(DistanceBox);
    SpawnCount = CreatePanelText(TEXT("本面板生成的怪物：0"), 14, ColdSteelUI::TextSecondary);
    MonsterPage->AddChildToVerticalBox(SpawnCount)->SetPadding(FMargin(0,16,0,10));
    SpawnStatus = CreatePanelText(TEXT("选择怪物后点击生成。怪物出现在玩家朝向的前方，并面向玩家。"), 14, ColdSteelUI::TextPrimary);
    MonsterPage->AddChildToVerticalBox(SpawnStatus)->SetPadding(FMargin(0,0,0,14));
    MonsterPage->AddChildToVerticalBox(CreatePanelText(TEXT("场景持续运行，怪物按原有行为活动。空间不足时只生成能放下的数量；清除按钮只影响本面板生成的怪物。"), 12, ColdSteelUI::TextSecondary));

    auto* TuningPage = WidgetTree->ConstructWidget<UVerticalBox>(); Pages->AddChild(TuningPage);
    BuildTuningPage(TuningPage);
    auto* TuningFooter = WidgetTree->ConstructWidget<UVerticalBox>(); TuningActions = TuningFooter;
    Stack->AddChildToVerticalBox(TuningFooter)->SetPadding(FMargin(0,12,0,0));
    DisableTuningButton = AddButton(TuningFooter, TEXT("全部关闭"), TEXT("DevelopmentDisableTuning"));
    DisableTuningButton->OnClicked.AddDynamic(this, &ThisClass::DisableTuningClicked);

    auto* Actions = WidgetTree->ConstructWidget<UVerticalBox>(); SpawnActions = Actions;
    Stack->AddChildToVerticalBox(Actions)->SetPadding(FMargin(0,12,0,0));
    SpawnButton = AddButton(Actions, TEXT("在玩家前方生成"), TEXT("DevelopmentSpawn"));
    ClearButton = AddButton(Actions, TEXT("清除本面板生成的怪物"), TEXT("DevelopmentClear"));
    SpawnButton->OnClicked.AddDynamic(this, &ThisClass::SpawnClicked);
    ClearButton->OnClicked.AddDynamic(this, &ThisClass::ClearMonstersClicked);
    CloseButton = AddButton(Stack, TEXT("返回游戏  ·  F6 / Esc"), TEXT("DevelopmentClose"));
    CloseButton->OnClicked.AddDynamic(this, &ThisClass::CloseDeveloper);
    PopulateMonsters(); SetPage(2); UpdateLayout();
    Panel->SetVisibility(ESlateVisibility::Collapsed);
}

UWidget* UDevelopmentPanelWidget::GenerateMonsterOption(FString Item)
{
    return CreatePanelText(Item, 10.5f, ColdSteelUI::TextPrimary);
}

UDevelopmentSpawnComponent* UDevelopmentPanelWidget::ResolveSpawner() const
{
    const auto* Player = GetOwningPlayer<AFPSGAMEPlayerController>();
    return Player ? Player->GetDevelopmentSpawner() : nullptr;
}

void UDevelopmentPanelWidget::PopulateMonsters()
{
    const FName Previous = SelectedMonster;
    MonsterIds.Reset(); MonsterChoice->ClearOptions();
    if (const auto* Spawner = ResolveSpawner())
        for (const auto& Entry : Spawner->GetMonsters())
        { MonsterIds.Add(Entry.Id); MonsterChoice->AddOption(Entry.Name.ToString()); }
    const int32 Index = MonsterIds.IndexOfByKey(Previous);
    if (!MonsterIds.IsEmpty()) MonsterChoice->SetSelectedIndex(Index == INDEX_NONE ? 0 : Index);
    else SelectedMonster = NAME_None;
    MonsterChoice->SetIsEnabled(!MonsterIds.IsEmpty());
}

void UDevelopmentPanelWidget::SetPanelOpen(bool bOpen)
{
    Super::SetPanelOpen(bOpen);
    if (bOpen) { PopulateMonsters(); UpdateLayout(); RefreshStatus(); RefreshTuning(); }
}

void UDevelopmentPanelWidget::SetPage(int32 Index)
{
    ActivePage = Index;
    Pages->SetActiveWidgetIndex(Index);
    SpawnActions->SetVisibility(Index == 1 ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    TuningActions->SetVisibility(Index == 2 ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    const float Scale = ColdSteelUI::PixelScale(this);
    auto Selected = ColdSteelUI::ButtonStyle(1.f / Scale);
    Selected.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, ColdSteelUI::ButtonRadius / Scale, ColdSteelUI::Accent));
    WeatherTab->SetStyle(Index == 0 ? Selected : ColdSteelUI::ButtonStyle(1.f / Scale));
    MonsterTab->SetStyle(Index == 1 ? Selected : ColdSteelUI::ButtonStyle(1.f / Scale));
    TuningTab->SetStyle(Index == 2 ? Selected : ColdSteelUI::ButtonStyle(1.f / Scale));
    RefreshStatus();
    RefreshTuning();
}

void UDevelopmentPanelWidget::RefreshStatus()
{
    Super::RefreshStatus();
    const auto* Tuning = UDevelopmentTuningSubsystem::Find(this);
    if (bTuningAvailable != (Tuning && Tuning->CanEdit(GetOwningPlayer()))) RefreshTuning();
    if (!SpawnCount) return;
    const auto* Spawner = ResolveSpawner();
    const int32 Live = Spawner ? Spawner->GetSpawnedCount() : 0;
    SpawnCount->SetText(FText::FromString(FString::Printf(TEXT("本面板生成的怪物：%d"), Live)));
    const auto* Player = GetOwningPlayer();
    SpawnButton->SetIsEnabled(Spawner && Player && Player->GetPawn() && Player->HasAuthority() && !SelectedMonster.IsNone());
    ClearButton->SetIsEnabled(Live > 0);
}

void UDevelopmentPanelWidget::SpawnClicked()
{
    if (auto* Spawner = ResolveSpawner())
    {
        FText Result;
        const int32 Created = Spawner->SpawnInFront(SelectedMonster, FMath::RoundToInt(CountBox->GetValue()), DistanceBox->GetValue(), Result);
        SpawnStatus->SetText(Result);
        SpawnStatus->SetColorAndOpacity(Created > 0 ? ColdSteelUI::Success : ColdSteelUI::Warning);
    }
    RefreshStatus();
}

void UDevelopmentPanelWidget::ClearMonstersClicked()
{
    if (auto* Spawner = ResolveSpawner())
    {
        const int32 Count = Spawner->ClearSpawned();
        SpawnStatus->SetText(FText::FromString(FString::Printf(TEXT("已清除本面板生成的 %d 只怪物"), Count)));
        SpawnStatus->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    }
    RefreshStatus();
}

void UDevelopmentPanelWidget::MonsterSelected(FString Name, ESelectInfo::Type Type)
{
    const int32 Index = MonsterChoice->GetSelectedIndex();
    SelectedMonster = MonsterIds.IsValidIndex(Index) ? MonsterIds[Index] : NAME_None;
    if (SpawnButton) RefreshStatus();
}

void UDevelopmentPanelWidget::UpdateLayout()
{
    const FVector2D View = UWidgetLayoutLibrary::GetViewportSize(this);
    const float Scale = ColdSteelUI::PixelScale(this);
    if (View.X < 1 || View.Y < 1 || (LastViewport.Equals(View) && FMath::IsNearlyEqual(LastPixelScale, Scale))) return;
    LastViewport = View; LastPixelScale = Scale;
    const float Width = View.X < 720.f ? View.X - 24.f : FMath::Min(520.f, View.X - 24.f);
    PanelSlot->SetPosition(FVector2D(-12.f,12.f) / Scale);
    PanelSlot->SetSize(FVector2D(FMath::Max(1.f, Width), FMath::Max(1.f, FMath::Min(820.f, View.Y - 24.f))) / Scale);
    ShortcutSlot->SetPosition(FVector2D(16.f,-90.f) / Scale);
    Surface->SetPadding(FMargin(18.f / Scale));
    Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint, ColdSteelUI::PanelRadius / Scale));
    Blur->SetCornerRadius(FVector4(ColdSteelUI::PanelRadius / Scale));
    RefreshPanelTypography();
    UpdateTuningLayout(FMath::Max(1.f, Width - 36.f), Scale);
    auto ComboStyle = MonsterChoice->GetWidgetStyle();
    ComboStyle.ComboButtonStyle.ButtonStyle = ColdSteelUI::ButtonStyle(1.f / Scale);
    ComboStyle.ComboButtonStyle.DownArrowImage.TintColor = ColdSteelUI::TextSecondary;
    ComboStyle.ComboButtonStyle.MenuBorderBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback, ColdSteelUI::ButtonRadius / Scale);
    MonsterChoice->SetWidgetStyle(ComboStyle);
    for (auto* Spin : {CountBox.Get(), DistanceBox.Get()})
    {
        Spin->SetFont(ColdSteelUI::NumberFont(10.5f / Scale));
        Spin->SetForegroundColor(ColdSteelUI::TextPrimary);
        auto Style = Spin->GetWidgetStyle();
        Style.SetBackgroundBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content, ColdSteelUI::ButtonRadius / Scale));
        Style.SetHoveredBackgroundBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, ColdSteelUI::ButtonRadius / Scale));
        Style.SetActiveBackgroundBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content, ColdSteelUI::ButtonRadius / Scale, ColdSteelUI::Accent));
        Style.SetActiveFillBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, ColdSteelUI::ButtonRadius / Scale));
        Style.SetInactiveFillBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content, ColdSteelUI::ButtonRadius / Scale));
        Spin->SetWidgetStyle(Style);
    }
    SetPage(ActivePage);
}

void UDevelopmentPanelWidget::NativeTick(const FGeometry& Geometry, float DeltaSeconds)
{
    Super::NativeTick(Geometry, DeltaSeconds);
    UpdateLayout();
}

void UDevelopmentPanelWidget::OpenDeveloper() { if (auto* Player = GetOwningPlayer<AFPSGAMEPlayerController>()) Player->ToggleDevelopmentPanel(); }
void UDevelopmentPanelWidget::CloseDeveloper() { SetPanelOpen(false); }
void UDevelopmentPanelWidget::WeatherClicked() { SetPage(0); }
void UDevelopmentPanelWidget::MonstersClicked() { SetPage(1); }
void UDevelopmentPanelWidget::TuningClicked() { SetPage(2); }
FReply UDevelopmentPanelWidget::NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (IsPanelOpen() && (Event.GetKey() == EKeys::F6 || Event.GetKey() == EKeys::Escape))
    { SetPanelOpen(false); return FReply::Handled(); }
    return UUserWidget::NativeOnKeyDown(Geometry, Event);
}
