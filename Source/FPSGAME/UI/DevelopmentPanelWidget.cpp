#include "DevelopmentPanelWidget.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelHUDWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Development/DevelopmentSpawnComponent.h"
#include "Engine/GameInstance.h"
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
    // 与背包装备同一抽屉：全屏压暗底在面板之下，随送出／收回进度淡入淡出。
    DrawerBackdrop = WidgetTree->ConstructWidget<UBorder>();
    DrawerBackdrop->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor(0.f, 0.f, 0.f, .40f), 0.f, FLinearColor::Transparent, 0.f));
    DrawerBackdrop->SetVisibility(ESlateVisibility::Collapsed);
    auto* BackdropSlot = Root->AddChildToCanvas(DrawerBackdrop);
    BackdropSlot->SetAnchors(FAnchors(0.f, 0.f, 1.f, 1.f));
    BackdropSlot->SetOffsets(FMargin(0.f));
    BackdropSlot->SetZOrder(0);
    Shortcut = CreatePanelButton(TEXT("F6  开发面板"), TEXT("DevelopmentOpen"));
    Shortcut->OnClicked.AddDynamic(this, &ThisClass::OpenDeveloper);
    ShortcutSlot = Root->AddChildToCanvas(Shortcut);
    ShortcutSlot->SetAnchors(FAnchors(0, 1));
    ShortcutSlot->SetAlignment(FVector2D(0, 1));
    ShortcutSlot->SetAutoSize(true);
    ShortcutSlot->SetZOrder(2);

    auto* Shell = WidgetTree->ConstructWidget<UOverlay>();
    Panel = Shell;
    PanelSlot = Root->AddChildToCanvas(Shell);
    // 与背包同源：贴右边缘、上下各 12px 的右侧抽屉。
    PanelSlot->SetAnchors(FAnchors(1, 0, 1, 1));
    PanelSlot->SetAlignment(FVector2D(1, 0));
    PanelSlot->SetZOrder(1);
    Blur = WidgetTree->ConstructWidget<UBackgroundBlur>();
    Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);
    Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);
    Blur->SetOverrideAutoRadiusCalculation(true);
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
    PopulateMonsters(); PopulateItems(); PopulateSkills();
    SetPage(2); UpdateLayout(); RefreshFeatures();
    Panel->SetVisibility(ESlateVisibility::Collapsed);
}

UWidget* UDevelopmentPanelWidget::GenerateMonsterOption(FString Item)
{
    return CreatePanelText(Item, 10.5f, ColdSteelUI::TextPrimary);
}

UWidget* UDevelopmentPanelWidget::GenerateListOption(FString Item)
{
    // 物品与技能下拉的条目可长可短，固定不换行，避免行高被折行撑开。
    auto* Text = CreatePanelText(Item, 12, ColdSteelUI::TextPrimary);
    Text->SetAutoWrapText(false);
    return Text;
}

UDevelopmentSpawnComponent* UDevelopmentPanelWidget::ResolveSpawner() const
{
    const auto* Player = GetOwningPlayer<AFPSGAMEPlayerController>();
    return Player ? Player->GetDevelopmentSpawner() : nullptr;
}

UColdSteelStatusModel* UDevelopmentPanelWidget::ResolveModel() const
{
    if (const auto* Player = GetOwningPlayer()) if (auto* Instance = Player->GetGameInstance())
        return Instance->GetSubsystem<UColdSteelStatusModel>();
    return nullptr;
}

UColdSteelHUDWidget* UDevelopmentPanelWidget::ResolveHUD() const
{
    const auto* Player = GetOwningPlayer<AFPSGAMEPlayerController>();
    return Player ? Player->GetColdSteelHUD() : nullptr;
}

const FColdSteelCatalogEntry* UDevelopmentPanelWidget::SelectedItem() const
{
    return ItemOptions.FindByPredicate([this](const FColdSteelCatalogEntry& Entry)
        { return Entry.Definition == SelectedItemDefinition; });
}

void UDevelopmentPanelWidget::PopulateItems()
{
    if (!ItemChoice) return;
    const FString Previous = SelectedItemDefinition;
    ItemOptions.Reset(); ItemChoice->ClearOptions();
    if (const auto* Model = ResolveModel())
    {
        for (const auto& Entry : Model->ItemCatalog())
        {
            ItemOptions.Add(Entry);
            ItemChoice->AddOption(FString::Printf(TEXT("%s · %s"), *Entry.Group, *Entry.Name));
        }
    }
    int32 Index = INDEX_NONE;
    if (!Previous.IsEmpty())
        for (int32 N = 0; N < ItemOptions.Num(); ++N) if (ItemOptions[N].Definition == Previous) { Index = N; break; }
    ItemChoice->SetIsEnabled(!ItemOptions.IsEmpty());
    if (ItemOptions.IsEmpty()) { SelectedItemDefinition.Reset(); return; }
    const int32 Pick = Index == INDEX_NONE ? 0 : Index;
    ItemChoice->SetSelectedIndex(Pick);
    SelectedItemDefinition = ItemOptions[Pick].Definition;
}

void UDevelopmentPanelWidget::PopulateSkills()
{
    if (!SkillChoice) return;
    const FName Previous = SelectedSkill;
    SkillIds.Reset(); SkillChoice->ClearOptions();
    if (const auto* Model = ResolveModel())
    {
        SkillIds = Model->SkillCatalog();
        for (const FName Id : SkillIds) SkillChoice->AddOption(Model->DevelopmentSkillDefinition(Id).Name);
    }
    const int32 Index = SkillIds.IndexOfByKey(Previous);
    SkillChoice->SetIsEnabled(!SkillIds.IsEmpty());
    if (SkillIds.IsEmpty()) { SelectedSkill = NAME_None; return; }
    const int32 Pick = Index == INDEX_NONE ? 0 : Index;
    SkillChoice->SetSelectedIndex(Pick);
    SelectedSkill = SkillIds[Pick];
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
    // 基础实现直接折叠面板；抽屉收回顾动画由 TickDrawer 驱动，动画期间保持可见。
    if (bOpen || DrawerProgress > KINDA_SMALL_NUMBER)
    {
        if (Panel) Panel->SetVisibility(ESlateVisibility::Visible);
        if (DrawerBackdrop) DrawerBackdrop->SetVisibility(ESlateVisibility::Visible);
    }
    if (bOpen)
    {
        // 让位在收回动画播完后由 TickDrawer 复位，与背包装备的恢复时机一致。
        if (auto* HUD = ResolveHUD()) { HUD->SetExternalDrawerOpen(true); bHudYielded = true; }
        PopulateMonsters(); PopulateItems(); PopulateSkills();
        UpdateLayout(); RefreshStatus(); RefreshTuning(); RefreshFeatures();
    }
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
    RefreshFeatures();
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

void UDevelopmentPanelWidget::ItemSelected(FString Name, ESelectInfo::Type Type)
{
    const int32 Index = ItemChoice->GetSelectedIndex();
    SelectedItemDefinition = ItemOptions.IsValidIndex(Index) ? ItemOptions[Index].Definition : FString();
    if (GenerateItemButton) RefreshFeatures();
}

void UDevelopmentPanelWidget::SkillSelected(FString Name, ESelectInfo::Type Type)
{
    const int32 Index = SkillChoice->GetSelectedIndex();
    SelectedSkill = SkillIds.IsValidIndex(Index) ? SkillIds[Index] : NAME_None;
    RefreshFeatures();
}

void UDevelopmentPanelWidget::SetFeatureMessage(const FString& Text, const FLinearColor& Color)
{
    if (!FeatureStatus) return;
    FeatureStatus->SetText(FText::FromString(Text));
    FeatureStatus->SetColorAndOpacity(Color);
}

void UDevelopmentPanelWidget::RefreshFeatures()
{
    const auto* Model = ResolveModel();
    const auto* Player = GetOwningPlayer();
    const bool bUsable = Model && Player && Player->HasAuthority() && Player->IsLocalController() &&
        Cast<AFPSGAMECharacter>(Player->GetPawn()) != nullptr;
    if (LevelHelp)
    {
        LevelHelp->SetText(FText::FromString(Model
            ? FString::Printf(TEXT("当前 Lv.%d · 属性点 %d · 经验 %lld / %lld · 每级 +3 点"),
                Model->Level, Model->AttributePoints, Model->Experience(), Model->MaxExperience())
            : TEXT("未读取到玩家档案")));
        LevelHelp->SetColorAndOpacity(Model ? ColdSteelUI::TextSecondary : ColdSteelUI::Warning);
    }
    if (SkillHelp)
    {
        FString Text = TEXT("未读取到技能进度");
        if (Model && !SelectedSkill.IsNone())
        {
            const auto& Definition = Model->DevelopmentSkillDefinition(SelectedSkill);
            const auto Progress = Model->MasteryProgress(SelectedSkill);
            Text = FString::Printf(TEXT("当前：%s Lv.%d / %d · 修炼值 %d"),
                *Definition.Name, Progress.Level, Definition.MaxLevel, Progress.Experience);
        }
        SkillHelp->SetText(FText::FromString(Text));
        SkillHelp->SetColorAndOpacity(Model ? ColdSteelUI::TextSecondary : ColdSteelUI::Warning);
    }
    if (GenerateItemButton) GenerateItemButton->SetIsEnabled(bUsable && !SelectedItemDefinition.IsEmpty() && !ItemOptions.IsEmpty());
    if (GrantLevelButton) GrantLevelButton->SetIsEnabled(bUsable);
    const bool bSkillReady = bUsable && !SelectedSkill.IsNone() && Model &&
        Model->MasteryProgress(SelectedSkill).Level < Model->DevelopmentSkillDefinition(SelectedSkill).MaxLevel;
    if (RaiseSkillButton) RaiseSkillButton->SetIsEnabled(bSkillReady);
    if (MaxSkillButton) MaxSkillButton->SetIsEnabled(bSkillReady);
}

void UDevelopmentPanelWidget::GenerateItemClicked()
{
    auto* Model = ResolveModel();
    const int32 Count = ItemCountBox ? FMath::Clamp(FMath::RoundToInt(ItemCountBox->GetValue()), 1, 9999) : 1;
    const FColdSteelCatalogEntry* Entry = SelectedItem();
    if (!Model || !Entry) { SetFeatureMessage(TEXT("请选择要生成的物品"), ColdSteelUI::Warning); return; }
    const FString Name = Entry->Name;
    if (Model->AddItem(SelectedItemDefinition, Count))
        SetFeatureMessage(FString::Printf(TEXT("已生成 %s ×%d → 背包"), *Name, Count), ColdSteelUI::Success);
    else
        SetFeatureMessage(FString::Printf(TEXT("生成失败：%s"), *Model->ResultMessage()), ColdSteelUI::Warning);
    RefreshFeatures();
}

void UDevelopmentPanelWidget::GrantLevelClicked()
{
    auto* Model = ResolveModel();
    if (!Model) { SetFeatureMessage(TEXT("未读取到玩家档案"), ColdSteelUI::Warning); return; }
    if (Model->GrantLevel(1))
        SetFeatureMessage(FString::Printf(TEXT("角色等级提升 → Lv.%d · 属性点 %d"), Model->Level, Model->AttributePoints), ColdSteelUI::Success);
    else
        SetFeatureMessage(FString::Printf(TEXT("等级提升失败：%s"), *Model->ResultMessage()), ColdSteelUI::Warning);
    RefreshFeatures();
}

void UDevelopmentPanelWidget::RaiseSkillClicked()
{
    auto* Model = ResolveModel();
    if (!Model || SelectedSkill.IsNone()) { SetFeatureMessage(TEXT("请选择要提升的技能"), ColdSteelUI::Warning); return; }
    const FString Name = Model->DevelopmentSkillDefinition(SelectedSkill).Name;
    if (Model->RaiseSkillLevel(SelectedSkill, 1))
        SetFeatureMessage(FString::Printf(TEXT("%s → Lv.%d"), *Name, Model->MasteryProgress(SelectedSkill).Level), ColdSteelUI::Success);
    else
        SetFeatureMessage(FString::Printf(TEXT("%s 已是满级或无法提升"), *Name), ColdSteelUI::Warning);
    RefreshFeatures();
}

void UDevelopmentPanelWidget::MaxSkillClicked()
{
    auto* Model = ResolveModel();
    if (!Model || SelectedSkill.IsNone()) { SetFeatureMessage(TEXT("请选择要提升的技能"), ColdSteelUI::Warning); return; }
    const FString Name = Model->DevelopmentSkillDefinition(SelectedSkill).Name;
    const int32 Max = Model->DevelopmentSkillDefinition(SelectedSkill).MaxLevel;
    if (Model->MaxSkillLevel(SelectedSkill))
        SetFeatureMessage(FString::Printf(TEXT("%s 已提升至满级 Lv.%d"), *Name, Max), ColdSteelUI::Success);
    else
        SetFeatureMessage(FString::Printf(TEXT("%s 已是满级"), *Name), ColdSteelUI::Warning);
    RefreshFeatures();
}

void UDevelopmentPanelWidget::UpdateLayout()
{
    const FVector2D View = UWidgetLayoutLibrary::GetViewportSize(this);
    const float Scale = ColdSteelUI::PixelScale(this);
    if (View.X < 1 || View.Y < 1 || (LastViewport.Equals(View) && FMath::IsNearlyEqual(LastPixelScale, Scale))) return;
    LastViewport = View; LastPixelScale = Scale;
    // 与背包装备同一抽屉规格：贴右边缘、上下各 12px，宽度 = min(视口-12, clamp(48%, 720, 1040))。
    const float RightInset = ColdSteelUI::NavigationDrawerInset;
    const float Width = FMath::Min(View.X - RightInset - 12.f, FMath::Clamp(View.X * .48f, 720.f, 1040.f));
    DrawerSlide = FMath::Max(1.f, Width);
    PanelSlot->SetOffsets(FMargin(-RightInset / Scale, 12.f / Scale, DrawerSlide / Scale, 12.f / Scale));
    ShortcutSlot->SetPosition(FVector2D(16.f,-90.f) / Scale);
    Surface->SetPadding(FMargin(18.f / Scale));
    Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint, ColdSteelUI::PanelRadius / Scale));
    Blur->SetCornerRadius(FVector4(ColdSteelUI::PanelRadius / Scale));
    Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback, ColdSteelUI::PanelRadius / Scale));
    RefreshPanelTypography();
    UpdateTuningLayout(FMath::Max(1.f, Width - 36.f), Scale);
    UpdateFeatureLayout(FMath::Max(1.f, Width - 36.f), Scale);
    StyleChoice(MonsterChoice, Scale);
    StyleChoice(ItemChoice, Scale);
    StyleChoice(SkillChoice, Scale);
    for (auto* Spin : {CountBox.Get(), DistanceBox.Get(), ItemCountBox.Get()}) StyleCount(Spin, Scale);
    SetPage(ActivePage);
}

void UDevelopmentPanelWidget::StyleChoice(UComboBoxString* Combo, float Scale)
{
    if (!Combo) return;
    auto ComboStyle = Combo->GetWidgetStyle();
    ComboStyle.ComboButtonStyle.ButtonStyle = ColdSteelUI::ButtonStyle(1.f / Scale);
    ComboStyle.ComboButtonStyle.DownArrowImage.TintColor = ColdSteelUI::TextSecondary;
    ComboStyle.ComboButtonStyle.MenuBorderBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback, ColdSteelUI::ButtonRadius / Scale);
    Combo->SetWidgetStyle(ComboStyle);
}

void UDevelopmentPanelWidget::StyleCount(USpinBox* Spin, float Scale)
{
    if (!Spin) return;
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

void UDevelopmentPanelWidget::TickDrawer(float Delta)
{
    const bool bOpen = IsPanelOpen();
    DrawerProgress = FMath::FInterpConstantTo(DrawerProgress, bOpen ? 1.f : 0.f, Delta, 4.f);
    const float Scale = ColdSteelUI::PixelScale(this);
    const bool bOut = bOpen || DrawerProgress > KINDA_SMALL_NUMBER;
    if (Panel)
    {
        Panel->SetRenderTranslation(FVector2D((1.f - DrawerProgress) * DrawerSlide / Scale, 0.f));
        Panel->SetVisibility(bOut ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    }
    if (DrawerBackdrop)
    {
        DrawerBackdrop->SetRenderOpacity(DrawerProgress);
        DrawerBackdrop->SetVisibility(bOut ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    }
    if (Blur) Blur->SetRenderOpacity(DrawerProgress);
    // 入口按钮与 HUD 的右侧栏目一样，在抽屉出现期间（含收回动画）让位。
    if (Shortcut) Shortcut->SetVisibility(bOut ? ESlateVisibility::Collapsed : ESlateVisibility::Visible);
    if (!bOpen && !bOut && bHudYielded)
    {
        bHudYielded = false;
        if (auto* HUD = ResolveHUD()) HUD->SetExternalDrawerOpen(false);
    }
}

void UDevelopmentPanelWidget::NativeTick(const FGeometry& Geometry, float DeltaSeconds)
{
    Super::NativeTick(Geometry, DeltaSeconds);
    UpdateLayout();
    TickDrawer(DeltaSeconds);
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
