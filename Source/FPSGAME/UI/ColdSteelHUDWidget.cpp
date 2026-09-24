#include "ColdSteelHUDWidget.h"
#include "ColdSteelSmeltingWidget.h"
#include "ColdSteelWorkbenchWidget.h"
#include "../Building/VoxelBuildWorld.h"
#include "Widgets/SWidget.h"
#include "ColdSteelSkillPage.h"
#include "ColdSteelCodexPage.h"
#include "ColdSteelProgressNotification.h"
#include "ColdSteelAmmoReadout.h"
#include "ColdSteelAmmoPouchWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelSmeltingWidget.h"
#include "ColdSteelWorkbenchWidget.h"
#include "../Building/VoxelBuildWorld.h"
#include "ColdSteelWorldClock.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Engine/GameInstance.h"

#include "../FPSGAMECharacter.h"
#include "../FPSWeatherManager.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelWorldInteraction.h"

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
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace
{
    // Preserve the 3x5 equipment and 18x4 storage contract while the drawer adapts.
    constexpr float HotbarSlotSize = 48.0f;
    constexpr float HotbarGap = 8.0f;
    constexpr int32 InventoryColumns = 18;
    constexpr int32 InventoryRows = 4;
    constexpr int32 WeatherSegmentsPerDay = AFPSWeatherManager::ScheduleSegmentsPerDay;
    constexpr float TimelineHorizonDays = 5.0f;

    const FLinearColor DrawerHeader = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("29323AFF")));
    const FLinearColor DrawerDeep = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("0A0E11F8")));
    const FLinearColor SlotDark = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("10151AE8")));
    const FLinearColor SlotEquipped = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("283139F2")));
    const FLinearColor GridLine = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("71828B42")));
    const FLinearColor TimelineWeatherColor = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("45BFFFFF")));
    const FLinearColor TimelineCriticalColor = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("FF665CFF")));
    const FLinearColor StatusCard = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("172028D9")));
    const FLinearColor AttributeRow = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("2730397A")));
    const FLinearColor TooltipSurface = ColdSteelUI::TooltipGlass;

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
        case EFPSWeatherState::Cloudy: return TEXT("多云");
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
    // NativePaint reads transient aim/hit data outside UMG property bindings.
    // Paint-only invalidation also removes the last frame when a hit expires.
    if (const auto Widget=GetCachedWidget()) Widget->Invalidate(EInvalidateWidgetReason::Paint);
    UpdateTopHUDLayout(MyGeometry);
    UpdateStaminaLayout(MyGeometry);
    UpdateInventoryLayout(MyGeometry);
    TickPanelNavigation(MyGeometry,InDeltaTime);
    UpdateInteractHint();
    TickWarehouse(MyGeometry,InDeltaTime);
    AmmoRefreshAccumulator += InDeltaTime;
    if (AmmoRefreshAccumulator >= 0.05f)
    {
        AmmoRefreshAccumulator = 0.0f;
        // RefreshAmmo already refreshes the quick bar for all of its callers.
        { TRACE_CPUPROFILER_EVENT_SCOPE(ColdSteelHUD_RefreshAmmo); RefreshAmmo(); }
        { TRACE_CPUPROFILER_EVENT_SCOPE(ColdSteelHUD_RefreshTopVitals); RefreshTopVitals(); }
        { TRACE_CPUPROFILER_EVENT_SCOPE(ColdSteelHUD_RefreshWorldClock); RefreshWorldClock(); }
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
    TickEventTimelinePresentation(InDeltaTime);
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
    // 缓动统一在渲染输出处做（进度本身保持线性＝时长恒定）；骑乘收回的面板共用这个值＝同曲线刚体。
    const float DrawerEase = ColdSteelUI::EaseSmooth(DrawerProgress);
    if (InventoryPanel)
    {
        // 整体骑乘收回时抽屉行程加长面板宽（多出的行程本就在屏幕外不可见），
        // 让面板与抽屉共用同一条位移曲线＝一个刚体向右缩回（2026-09-24 用户定稿口径）。
        const float DrawerWidth = FMath::Max(1.0f, (InventoryWidth+ColdSteelUI::NavigationDrawerInset+(bSmeltRiding?SmeltSlidePx:0.f)+(bWorkbenchRiding?WorkbenchSlidePx:0.f)) / ColdSteelUI::PixelScale(this));
        InventoryPanel->SetRenderTranslation(FVector2D((1.0f - DrawerEase) * DrawerWidth, 0.0f));
    }
    if (InventoryBackdrop)
    {
        InventoryBackdrop->SetRenderOpacity(bCloseAfterQuickDrag||(bInventoryDragOutside&&!bWarehouseOpen)?0.f:DrawerEase);
    }
    if (InventoryBlur)
    {
        InventoryBlur->SetRenderOpacity(bCloseAfterQuickDrag||(bInventoryDragOutside&&!bWarehouseOpen)?0.f:DrawerEase);
    }
    // 冶炼面板动画（2026-09-24 用户定稿）：
    // 弹出＝抽屉滑到位后，面板贴着背包左缘从抽屉背后向左滑出（SmeltMotion，运动中 Z 序 40、落位恢复 42）；
    // 关闭＝冶炼栏＋背包视为一个整体：立即关抽屉并让面板与抽屉同一位移曲线刚体骑乘向右缩回（bSmeltRiding）；
    //       背包本就已关时，面板单独向右滑出屏幕。
    // 本体/根画布均为 SelfHitTestInvisible：透明区放行世界点击，子控件照常命中
    //（HitTestInvisible 会连子树一起屏蔽命中——按钮全灭的根因，已入档）。
    if(SmeltingWidget)
    {
        if(bSmeltingOpen&&(!SmeltingWorld.IsValid()||!SmeltingWorld->HasPrefabAt(SmeltingCell)))CloseSmelting();
        const float S=ColdSteelUI::PixelScale(this);
        if(bSmeltRiding)
        {   SmeltMotion=FMath::FInterpConstantTo(SmeltMotion,0.f,InDeltaTime,4.0f);   // 复位进度，下次弹出重新起步
            SmeltingWidget->SetVisibility(DrawerProgress>KINDA_SMALL_NUMBER?ESlateVisibility::SelfHitTestInvisible:ESlateVisibility::Collapsed);
            if(SmeltingSlot)SmeltingSlot->SetZOrder(40);
            SmeltingWidget->SetRenderTranslation(FVector2D((1.f-DrawerEase)*(InventoryWidth+ColdSteelUI::NavigationDrawerInset+SmeltSlidePx)/S,0.f));
            if(DrawerProgress<=KINDA_SMALL_NUMBER){bSmeltRiding=false;SmeltingWidget->SetRenderTranslation(FVector2D::ZeroVector);}
        }
        else
        {
            if(bSmeltingOpen&&SmeltWidth>1.f)SmeltSlidePx=SmeltWidth+24.f;   // 开着时记住滑距（关闭瞬间 SmeltWidth 即被布局清零）
            const float SmeltTarget=bSmeltingOpen&&DrawerProgress>1.f-KINDA_SMALL_NUMBER&&SmeltWidth>1.f?1.f:0.f;
            SmeltMotion=FMath::FInterpConstantTo(SmeltMotion,SmeltTarget,InDeltaTime,4.0f);
            const float SmeltEase=ColdSteelUI::EaseSmooth(SmeltMotion);
            SmeltingWidget->SetVisibility(SmeltMotion>KINDA_SMALL_NUMBER?ESlateVisibility::SelfHitTestInvisible:ESlateVisibility::Collapsed);
            if(SmeltingSlot)SmeltingSlot->SetZOrder(SmeltMotion>1.f-KINDA_SMALL_NUMBER?42:40);
            if(SmeltMotion>KINDA_SMALL_NUMBER)
                SmeltingWidget->SetRenderTranslation(FVector2D((1.f-SmeltEase)*FMath::Max(SmeltSlidePx,24.f)/S,0.f));
            else SmeltingWidget->SetRenderTranslation(FVector2D::ZeroVector);
        }
    }
    // 工作台制作面板动画：与冶炼面板逐行同构（同贴位互斥，同一时刻至多一块在骑乘，
    // 抽屉行程加长项两旗标互斥相加即可；Docs/UI/workbench-panel-plan-20260924.md）。
    if(WorkbenchWidget)
    {
        if(bWorkbenchOpen&&(!WorkbenchWorld.IsValid()||!WorkbenchWorld->HasPrefabAt(WorkbenchCell)))CloseWorkbench();
        const float S=ColdSteelUI::PixelScale(this);
        if(bWorkbenchRiding)
        {   WorkbenchMotion=FMath::FInterpConstantTo(WorkbenchMotion,0.f,InDeltaTime,4.0f);   // 复位进度，下次弹出重新起步
            WorkbenchWidget->SetVisibility(DrawerProgress>KINDA_SMALL_NUMBER?ESlateVisibility::SelfHitTestInvisible:ESlateVisibility::Collapsed);
            if(WorkbenchSlot)WorkbenchSlot->SetZOrder(40);
            WorkbenchWidget->SetRenderTranslation(FVector2D((1.f-DrawerEase)*(InventoryWidth+ColdSteelUI::NavigationDrawerInset+WorkbenchSlidePx)/S,0.f));
            if(DrawerProgress<=KINDA_SMALL_NUMBER){bWorkbenchRiding=false;WorkbenchWidget->SetRenderTranslation(FVector2D::ZeroVector);}
        }
        else
        {
            if(bWorkbenchOpen&&WorkbenchWidth>1.f)WorkbenchSlidePx=WorkbenchWidth+24.f;   // 开着时记住滑距（关闭瞬间布局会把 WorkbenchWidth 清零）
            const float WorkbenchTarget=bWorkbenchOpen&&DrawerProgress>1.f-KINDA_SMALL_NUMBER&&WorkbenchWidth>1.f?1.f:0.f;
            WorkbenchMotion=FMath::FInterpConstantTo(WorkbenchMotion,WorkbenchTarget,InDeltaTime,4.0f);
            const float WorkbenchEase=ColdSteelUI::EaseSmooth(WorkbenchMotion);
            WorkbenchWidget->SetVisibility(WorkbenchMotion>KINDA_SMALL_NUMBER?ESlateVisibility::SelfHitTestInvisible:ESlateVisibility::Collapsed);
            if(WorkbenchSlot)WorkbenchSlot->SetZOrder(WorkbenchMotion>1.f-KINDA_SMALL_NUMBER?42:40);
            if(WorkbenchMotion>KINDA_SMALL_NUMBER)
                WorkbenchWidget->SetRenderTranslation(FVector2D((1.f-WorkbenchEase)*FMath::Max(WorkbenchSlidePx,24.f)/S,0.f));
            else WorkbenchWidget->SetRenderTranslation(FVector2D::ZeroVector);
        }
    }
    if (EquipmentTooltip && EquipmentTooltip->IsVisible() && !bEquipmentTooltipPinned)
    {
        UpdateEquipmentTooltipPlacement();
    }
    // 开发面板（外部抽屉）打开时同样按抽屉展开期处理，收起动画播完才恢复。
    const bool bDrawerOut=bInventoryOpen||DrawerProgress>KINDA_SMALL_NUMBER||bExternalDrawerOpen;
    if (!bInventoryOpen && !IsQuickDragging() && DrawerProgress <= KINDA_SMALL_NUMBER && !bExternalDrawerOpen)
    {
        InventoryPanel->SetVisibility(ESlateVisibility::Collapsed);
        InventoryBackdrop->SetVisibility(ESlateVisibility::Collapsed);
        InventoryBlur->SetVisibility(ESlateVisibility::Collapsed);
    }
    // The drawer hugs the right edge, so the world clock yields the corner while it is out.
    if (WorldClock) WorldClock->SetVisibility(bDrawerOut ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
}

FReply UColdSteelHUDWidget::NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent)
{
    if (HandlePanelShortcut(InKeyEvent.GetKey(), InKeyEvent.IsRepeat())) return FReply::Handled();
    // A drag in flight keeps its own keys: the drawer is hidden while the pointer is outside the panel,
    // so the board that started the drag may not be the widget receiving this event.
    if (InKeyEvent.GetKey() == EKeys::F && !InKeyEvent.IsRepeat() && InventoryDrag.IsValid())
    {
        if (auto* Board = InventoryDrag->SourceBoard.Get())
            if (Board->RotateDraggedItem(Board->GetCachedGeometry())) return FReply::Handled();
    }
    if (InKeyEvent.GetKey() == EKeys::Escape && TimelinePopover && TimelinePopover->IsVisible())
    {
        SetTimelineDetailsOpen(false);
        return FReply::Handled();
    }
    // 冶炼面板独立开合：Esc 先收面板，再轮到背包（面板打开时键盘焦点在它身上，事件冒泡到这里）。
    if (InKeyEvent.GetKey() == EKeys::Escape && !InKeyEvent.IsRepeat() && bSmeltingOpen)
    {
        CloseSmelting();
        return FReply::Handled();
    }
    // 工作台制作面板同款独立开合（与冶炼互斥，二者至多一个在开）。
    if (InKeyEvent.GetKey() == EKeys::Escape && !InKeyEvent.IsRepeat() && bWorkbenchOpen)
    {
        CloseWorkbench();
        return FReply::Handled();
    }
    if (bInventoryOpen)
    {
        const FKey Key = InKeyEvent.GetKey();
        if (Key == EKeys::Escape)
        {
            if(bSkillsTabActive && SkillPage && SkillPage->GoBack())return FReply::Handled();
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
    // 注意：K／J 属强化台与改造台（FPSGAMEPlayerController 先消费），C 是滑铲，图鉴用 N。
    if (Key != EKeys::Tab && Key != EKeys::CapsLock && Key != EKeys::P && Key != EKeys::N) return false;
    if (bRepeat) return true;
    if(IsQuickDragging()){CancelQuickDrag();return true;}
    const bool bStatus = Key == EKeys::CapsLock;
    const bool bCodex = Key == EKeys::N;
    const bool bSkills = Key == EKeys::P;
    // 已打开且按下的就是当前页 → 收起；Tab 关闭任意抽屉。
    if (bInventoryOpen && (Key == EKeys::Tab || (bSkills&&bSkillsTabActive) || (bStatus&&bStatusTabActive) || (bCodex&&bCodexTabActive)))
    {
        SetInventoryOpen(false);
        return true;
    }
    UWidgetBlueprintLibrary::CancelDragDrop();
    if (auto* Scroll = Cast<UScrollBox>(EquipmentPage))
        if (auto* Board = Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0))) Board->CancelInteraction();
    if (bStatus || bSkills || bCodex) CloseWarehouse();
    SetInventoryPage(bCodex?4:(bSkills?2:(bStatus?0:1)));
    SetInventoryOpen(true);
    if (CloseButton) CloseButton->SetKeyboardFocus();
    return true;
}

void UColdSteelHUDWidget::BuildInteractHint(UCanvasPanel* Root)
{
    // 统一 E 交互小浮窗（2026-09-24 用户指令）：准星下方居中的毛玻璃灰黑卡＋白字，
    // 取代高炉/工作台/宝箱/储物箱/拾取等一切挂在模型上方的世界空间名牌。
    auto* Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();
    Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);
    Blur->SetOverrideAutoRadiusCalculation(true);
    Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);
    Blur->SetCornerRadius(FVector4(ReferenceUnits(ColdSteelUI::CardRadius)));
    Blur->SetApplyAlphaToBlur(true);
    Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::CardRadius));
    Blur->SetVisibility(ESlateVisibility::Collapsed);
    auto* Surface=MakeSurface(ColdSteelUI::GlassTint,ReferenceUnits(ColdSteelUI::CardRadius),ColdSteelUI::Border,ReferenceUnits(1));
    Surface->SetPadding(FMargin(ReferenceUnits(12),ReferenceUnits(7)));
    Blur->SetContent(Surface);
    auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();
    Surface->SetContent(Row);
    InteractHintKey=MakeReferenceText(TEXT("E"),16,FLinearColor::White,true,true);
    auto* KeySlot=Row->AddChildToHorizontalBox(InteractHintKey);
    KeySlot->SetPadding(FMargin(0,0,ReferenceUnits(9),0));
    KeySlot->SetVerticalAlignment(VAlign_Center);
    InteractHintText=MakeReferenceText(FString(),15,FLinearColor::White);
    auto* TextSlot=Row->AddChildToHorizontalBox(InteractHintText);
    TextSlot->SetVerticalAlignment(VAlign_Center);
    auto* HintSlot=Root->AddChildToCanvas(Blur);
    HintSlot->SetAnchors(FAnchors(0.5f,0.5f));
    HintSlot->SetAlignment(FVector2D(0.5f,0.f));
    HintSlot->SetPosition(FVector2D(0,ReferenceUnits(56)));
    HintSlot->SetAutoSize(true);
    HintSlot->SetZOrder(38);
    InteractHintBlur=Blur;
}

void UColdSteelHUDWidget::UpdateInteractHint()
{
    if(!InteractHintBlur)return;
    APlayerController* PC=GetOwningPlayer();
    const auto* Character=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
    // 与旧准星提示同一出现条件：任一面板打开／光标显示／弹药轮／命中反馈 期间都不出浮窗。
    FString Text;bool bAction=true;
    if(Character&&!bInventoryOpen&&!bWarehouseOpen&&!PC->bShowMouseCursor&&!Character->IsAmmoWheelOpen())
    {
        FMonsterHitFeedback Feedback;
        if(!Character->GetMonsterHitFeedback(Feedback))
        {
            const auto Hint=ColdSteelWorldInteraction::ResolveInteractionHint(ColdSteelWorldInteraction::TraceTarget(PC));
            if(!Hint.Text.IsEmpty()){Text=Hint.Text;bAction=Hint.bAction;}
        }
    }
    if(Text.IsEmpty()){InteractHintBlur->SetVisibility(ESlateVisibility::Collapsed);LastInteractHintText.Reset();return;}
    InteractHintBlur->SetVisibility(ESlateVisibility::HitTestInvisible);
    if(Text!=LastInteractHintText){InteractHintText->SetText(FText::FromString(Text));LastInteractHintText=Text;}
    if(bAction!=bLastInteractHintAction){InteractHintKey->SetVisibility(bAction?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);bLastInteractHintAction=bAction;}
}

void UColdSteelHUDWidget::BuildInterface()
{
    UCanvasPanel* Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("ColdSteelRoot"));
    WidgetTree->RootWidget = Root;
    BuildAmmoReadout(Root);
    BuildHotbar(Root);
    BuildStamina(Root);
    BuildEventTimeline(Root);
    BuildInventory(Root);
    BuildCharacterSummary(Root);
    BuildWarehouse(Root);
    BuildSmelting(Root);
    BuildWorkbench(Root);
    BuildPanelNavigation(Root);
    BuildInteractHint(Root); // 统一 E 交互小浮窗（在面板 Z 之下：面板打开时本就不显示）
    ProgressNotification=CreateWidget<UColdSteelProgressNotification>(GetOwningPlayer());
    FillSlot(Root->AddChildToCanvas(ProgressNotification),FAnchors(0,0,1,1),FMargin(0),90);
    RefreshAmmo();
    RefreshEventTimeline(true);
    RefreshWorldClock();
}

void UColdSteelHUDWidget::BuildAmmoReadout(UCanvasPanel* Root)
{
    AmmoReadout=CreateWidget<UColdSteelAmmoReadout>(GetOwningPlayer());
    UCanvasPanelSlot* CanvasSlot = Root->AddChildToCanvas(AmmoReadout);
    CanvasSlot->SetAnchors(FAnchors(1.0f, 1.0f));
    CanvasSlot->SetAlignment(FVector2D(1.0f, 1.0f));
    CanvasSlot->SetPosition(FVector2D(-ReferenceUnits(20), -ReferenceUnits(20)));
    CanvasSlot->SetAutoSize(true);
    CanvasSlot->SetZOrder(10);
    AmmoReadout->UpdateLayout(UColdSteelAmmoReadout::PreferredWidth,20.f);
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
        auto* ItemSlot=MakeHotbarSlot(Slots[Index].Key, Slots[Index].Value);
        QuickSlotSurfaces.Add(ItemSlot);
        if(Index>=3)HotbarDropSlots.Add(ItemSlot);
        Row->AddChildToHorizontalBox(ItemSlot)
            ->SetPadding(FMargin(Index == 0 ? 0.0f : ReferenceUnits(HotbarGap * .5f), 0, ReferenceUnits(HotbarGap * .5f), 0));
    }

    // F 专属槽（快速进战）：与前三个分组一样用细分隔线隔开。不进 QuickSlotSurfaces
    // （QuickBarDropIndex/HighlightQuickBar 遍历它解析投放目标）也不进 HotbarDropSlots，
    // 拖动高亮与投放都不会落到它上面；槽位自身再挡一层拖放入口。
    {
        UBorder* Divider = MakeSurface(ColdSteelUI::Border, 0.0f, FLinearColor::Transparent, 0.0f);
        USizeBox* DividerSize = WidgetTree->ConstructWidget<USizeBox>();
        DividerSize->SetWidthOverride(ReferenceUnits(1));
        DividerSize->SetHeightOverride(ReferenceUnits(HotbarSlotSize - 16));
        Divider->SetContent(DividerSize);
        Row->AddChildToHorizontalBox(Divider)->SetPadding(FMargin(ReferenceUnits(4), ReferenceUnits(8)));
        auto* FixedSlot = MakeHotbarSlot(TEXT("F"), TEXT(""));
        Row->AddChildToHorizontalBox(FixedSlot)
            ->SetPadding(FMargin(ReferenceUnits(HotbarGap * .5f), 0, 0.0f, 0));
    }
    // G 专属槽（符文长剑·环绕飞剑）：与 F 槽同一口径，只读、不接拖放；
    // 整格与分隔线按装备状态显隐（RefreshQuickBar 驱动，收起时不占位）。
    {
        UBorder* Divider = MakeSurface(ColdSteelUI::Border, 0.0f, FLinearColor::Transparent, 0.0f);
        USizeBox* DividerSize = WidgetTree->ConstructWidget<USizeBox>();
        DividerSize->SetWidthOverride(ReferenceUnits(1));
        DividerSize->SetHeightOverride(ReferenceUnits(HotbarSlotSize - 16));
        Divider->SetContent(DividerSize);
        Row->AddChildToHorizontalBox(Divider)->SetPadding(FMargin(ReferenceUnits(4), ReferenceUnits(8)));
        auto* BladesSlot = MakeHotbarSlot(TEXT("G"), TEXT(""));
        Row->AddChildToHorizontalBox(BladesSlot)
            ->SetPadding(FMargin(ReferenceUnits(HotbarGap * .5f), 0, 0.0f, 0));
        BladesSlot->SetVisibility(ESlateVisibility::Collapsed);
        Divider->SetVisibility(ESlateVisibility::Collapsed);
        RuneBladesSlotSurface = BladesSlot;
        RuneBladesDivider = Divider;
    }

    UCanvasPanelSlot* CanvasSlot = Root->AddChildToCanvas(Surface);
    HotbarCanvasSlot=CanvasSlot;
    CanvasSlot->SetAnchors(FAnchors(0.5f, 1.0f));
    CanvasSlot->SetAlignment(FVector2D(0.5f, 1.0f));
    CanvasSlot->SetPosition(FVector2D(0, -ReferenceUnits(12)));
    CanvasSlot->SetAutoSize(true);
    CanvasSlot->SetZOrder(30);
}

void UColdSteelHUDWidget::BuildInventory(UCanvasPanel* Root)
{
    InventoryBackdrop = MakeSurface(FLinearColor(0.0f, 0.0f, 0.0f, 0.40f), 0.0f, FLinearColor::Transparent, 0.0f);
    InventoryBackdrop->SetVisibility(ESlateVisibility::Collapsed);
    FillSlot(Root->AddChildToCanvas(InventoryBackdrop), FAnchors(0.0f, 0.0f, 1.0f, 1.0f), FMargin(0.0f), 40);

    InventoryPanel = MakeSurface(FLinearColor::Transparent, ReferenceUnits(10), GunsmithUI::Edge, ReferenceUnits(1));
    InventoryPanel->SetPadding(FMargin(ReferenceUnits(1)));
    InventoryPanel->SetVisibility(ESlateVisibility::Collapsed);
    InventoryPanelSlot=Root->AddChildToCanvas(InventoryPanel);
    InventoryPanelSlot->SetAnchors(FAnchors(1,0,1,1));InventoryPanelSlot->SetAlignment(FVector2D(1,0));InventoryPanelSlot->SetZOrder(41);
    InventoryPanelSlot->SetOffsets(FMargin(-ReferenceUnits(ColdSteelUI::NavigationDrawerInset),ReferenceUnits(12),ReferenceUnits(720),ReferenceUnits(12)));
    InventoryBlur=WidgetTree->ConstructWidget<UBackgroundBlur>();InventoryBlur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);InventoryBlur->SetOverrideAutoRadiusCalculation(true);InventoryBlur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);
    InventoryBlur->SetCornerRadius(FVector4(10,10,10,10));InventoryBlur->SetApplyAlphaToBlur(true);
    InventoryBlur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius));
    InventoryPanel->SetContent(InventoryBlur);
    auto* Glass=MakeSurface(ColdSteelUI::GlassTint,ReferenceUnits(ColdSteelUI::PanelRadius),FLinearColor::Transparent,0);
    Glass->SetPadding(FMargin(0));InventoryBlur->SetContent(Glass);

    UVerticalBox* Body = WidgetTree->ConstructWidget<UVerticalBox>();
    Glass->SetContent(Body);

    UBorder* HeaderSurface = MakeSurface(ColdSteelUI::HeaderTint, ReferenceUnits(ColdSteelUI::PanelRadius), FLinearColor::Transparent, 0.0f);
    InventoryHeaderSurface=HeaderSurface;
    HeaderSurface->SetPadding(FMargin(ReferenceUnits(18), ReferenceUnits(12)));
    USizeBox* HeaderHeight = WidgetTree->ConstructWidget<USizeBox>();
    InventoryHeaderSize=HeaderHeight;
    HeaderHeight->SetHeightOverride(ReferenceUnits(36));
    HeaderSurface->SetContent(HeaderHeight);
    Body->AddChildToVerticalBox(HeaderSurface)->SetSize(FSlateChildSize(ESlateSizeRule::Automatic));
    UHorizontalBox* Header = WidgetTree->ConstructWidget<UHorizontalBox>();
    HeaderHeight->SetContent(Header);
    InventoryTitleText = MakeInventoryText(TEXT("装备与背包"),20,GunsmithUI::Text,false,true);
    UHorizontalBoxSlot* TitleSlot = Header->AddChildToHorizontalBox(InventoryTitleText);
    TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    TitleSlot->SetVerticalAlignment(VAlign_Center);

    CloseButton = WidgetTree->ConstructWidget<UButton>();
    CloseButton->SetStyle(ColdSteelUI::ButtonStyle(ColdSteelUI::PixelScale(this)));
    CloseButton->SetContent(MakeInventoryText(TEXT("Esc  返回"),14,GunsmithUI::Text));
    Cast<UButtonSlot>(CloseButton->GetContent()->Slot)->SetPadding(FMargin(ReferenceUnits(12),ReferenceUnits(8)));
    CloseButton->OnClicked.AddDynamic(this, &UColdSteelHUDWidget::HandleCloseClicked);
    Header->AddChildToHorizontalBox(CloseButton)->SetVerticalAlignment(VAlign_Center);

    UHorizontalBox* Tabs = WidgetTree->ConstructWidget<UHorizontalBox>();
    auto AddTab = [this, Tabs](const FString& Caption, bool bActive, TObjectPtr<UBorder>& OutSurface, TObjectPtr<UTextBlock>& OutText, TObjectPtr<UBorder>& OutUnderline, bool bEnabled)
    {
        UButton* Button = WidgetTree->ConstructWidget<UButton>();
        Button->SetStyle(FButtonStyle()
            .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent, 0.0f, FLinearColor::Transparent, 0.0f))
            .SetHovered(ColdSteelUI::RoundedBrush(GunsmithUI::Gray(110,45),7,FLinearColor::Transparent,0))
            .SetPressed(ColdSteelUI::RoundedBrush(GunsmithUI::Gray(24,180),7,FLinearColor::Transparent,0)));
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
    UButton* SkillButton=AddTab(TEXT("技能"), false, SkillTabSurface, SkillTabText, SkillTabUnderline, true);
    SkillButton->OnClicked.AddDynamic(this,&UColdSteelHUDWidget::OpenSkills);
    AddTab(TEXT("图鉴"), false, DummySurface, DummyText, DummyUnderline, false);
    StatusButton->OnClicked.AddDynamic(this, &UColdSteelHUDWidget::HandleStatusTabClicked);
    EquipmentButton->OnClicked.AddDynamic(this, &UColdSteelHUDWidget::HandleEquipmentTabClicked);
    Body->AddChildToVerticalBox(Tabs)->SetSize(FSlateChildSize(ESlateSizeRule::Automatic));
    // The persistent right rail now owns the three available panel destinations.
    Tabs->SetVisibility(ESlateVisibility::Collapsed);

    EquipmentAmmoTabs=WidgetTree->ConstructWidget<UHorizontalBox>();
    auto* GearTab=WidgetTree->ConstructWidget<UButton>();
    GearTab->SetStyle(ColdSteelUI::ButtonStyle(ColdSteelUI::PixelScale(this)));
    GearTab->SetContent(MakeInventoryText(TEXT("装备与背包"),14,ColdSteelUI::TextPrimary));
    GearTab->OnClicked.AddDynamic(this,&UColdSteelHUDWidget::HandleEquipmentTabClicked);
    EquipmentAmmoTabs->AddChildToHorizontalBox(GearTab)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* AmmoTab=WidgetTree->ConstructWidget<UButton>();
    AmmoTab->SetStyle(ColdSteelUI::ButtonStyle(ColdSteelUI::PixelScale(this)));
    AmmoTab->SetContent(MakeInventoryText(TEXT("弹药袋"),14,ColdSteelUI::TextPrimary));
    AmmoTab->OnClicked.AddDynamic(this,&UColdSteelHUDWidget::OpenAmmoPouch);
    EquipmentAmmoTabs->AddChildToHorizontalBox(AmmoTab)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Body->AddChildToVerticalBox(EquipmentAmmoTabs)->SetPadding(FMargin(ReferenceUnits(16),ReferenceUnits(6),ReferenceUnits(16),ReferenceUnits(8)));

    StatusPage = BuildStatusPage();
    EquipmentPage = BuildEquipmentPage();
    Body->AddChildToVerticalBox(StatusPage)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Body->AddChildToVerticalBox(EquipmentPage)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    AmmoPouchPage=CreateWidget<UColdSteelAmmoPouchWidget>(GetOwningPlayer());AmmoPouchPage->SetHUD(this);
    Body->AddChildToVerticalBox(AmmoPouchPage)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    SkillPage=CreateWidget<UColdSteelSkillPage>(GetOwningPlayer());
    SkillPage->SetHUD(this);
    auto* SkillSlot=Body->AddChildToVerticalBox(SkillPage);
    SkillSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));SkillSlot->SetHorizontalAlignment(HAlign_Fill);
    // 图鉴与技能页同为抽屉内的自包含 Slate 页，共用同一 Fill 槽位与生命周期。
    CodexPage=CreateWidget<UColdSteelCodexPage>(GetOwningPlayer());
    CodexPage->SetHUD(this);
    auto* CodexSlot=Body->AddChildToVerticalBox(CodexPage);
    CodexSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));CodexSlot->SetHorizontalAlignment(HAlign_Fill);
    auto* Footer=Body->AddChildToVerticalBox(MakeInventoryText(TEXT("Tab 收起  ·  Caps 状态  ·  P 技能  ·  右键物品操作"),12,GunsmithUI::Muted));
    InventoryFooterSlot=Footer;
    Footer->SetPadding(FMargin(ReferenceUnits(18),ReferenceUnits(8),ReferenceUnits(18),ReferenceUnits(10)));
    BuildStatusTooltip(Root);
    BuildEquipmentTooltip(Root);
    SetInventoryTab(false);
}


UWidget* UColdSteelHUDWidget::BuildEquipmentPage()
{
    auto* Scroll = WidgetTree->ConstructWidget<UScrollBox>();
    Scroll->SetConsumeMouseWheel(EConsumeMouseWheel::Always);
    Scroll->SetScrollbarThickness(FVector2D(ReferenceUnits(6),ReferenceUnits(6)));
    Scroll->SetAllowOverscroll(false);
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
    StatusTooltip = MakeSurface(FLinearColor::Transparent, ReferenceUnits(ColdSteelUI::PanelRadius), ColdSteelUI::Border, ReferenceUnits(1));
    StatusTooltip->SetPadding(FMargin(ReferenceUnits(1)));
    StatusTooltip->SetVisibility(ESlateVisibility::Collapsed);
    StatusTooltipCanvasSlot = Root->AddChildToCanvas(StatusTooltip);
    StatusTooltipCanvasSlot->SetAnchors(FAnchors(0.56f, 0.51f));
    StatusTooltipCanvasSlot->SetPosition(FVector2D(0.0f, 0.0f));
    StatusTooltipCanvasSlot->SetSize(FVector2D(ReferenceUnits(260.0f), ReferenceUnits(142.0f)));
    StatusTooltipCanvasSlot->SetZOrder(60);
    auto* Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);
    Blur->SetOverrideAutoRadiusCalculation(true);Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);
    Blur->SetCornerRadius(FVector4(10,10,10,10));Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius));
    StatusTooltip->SetContent(Blur);
    auto* Tint=MakeSurface(ColdSteelUI::Tooltip,ReferenceUnits(ColdSteelUI::PanelRadius),FLinearColor::Transparent,0);
    Tint->SetPadding(FMargin(ReferenceUnits(16),ReferenceUnits(12)));Blur->SetContent(Tint);
    UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>();
    Tint->SetContent(Column);
    StatusTooltipTitle = MakeInventoryText(TEXT("力量"), 16, ColdSteelUI::TextPrimary, false, true);
    Column->AddChildToVerticalBox(StatusTooltipTitle);
    UBorder* Divider = MakeSurface(ColdSteelUI::Border, 0.0f, FLinearColor::Transparent, 0.0f);
    USizeBox* DividerHeight = WidgetTree->ConstructWidget<USizeBox>();
    DividerHeight->SetHeightOverride(ReferenceUnits(1.0f)); Divider->SetContent(DividerHeight);
    Column->AddChildToVerticalBox(Divider)->SetPadding(FMargin(0, ReferenceUnits(4), 0, ReferenceUnits(6)));
    StatusTooltipDescription = MakeInventoryText(TEXT("提升物理攻击与少量物理防御。"), 14, ColdSteelUI::TextPrimary);
    StatusTooltipDescription->SetAutoWrapText(true);
    Column->AddChildToVerticalBox(StatusTooltipDescription);
    StatusTooltipRowsBox = WidgetTree->ConstructWidget<UVerticalBox>();
    Column->AddChildToVerticalBox(StatusTooltipRowsBox)->SetPadding(FMargin(0, ReferenceUnits(4), 0, 0));
    StatusTooltipNote = MakeInventoryText(TEXT("每点力量 ≈ +0.05 物理攻击"), 12, ColdSteelUI::TextSecondary);
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
    EquipmentDamageValue = AddTooltipRow(Main, TEXT("武器总伤害"), TEXT("30"), ColdSteelUI::TextPrimary, true);
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

    AFPSWeatherManager* Weather = HUDWeatherSource.Get();
    if (!Weather) if (UWorld* World = GetWorld())
    {
        for (TActorIterator<AFPSWeatherManager> It(World); It; ++It)
        {
            Weather = *It;
            HUDWeatherSource = Weather;
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
            if (IsWetWeather(Weather->CurrentState) || Weather->IsRainPending())
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
                const EFPSWeatherState State = Offset == 0
                    ? (Weather->IsRainPending() ? Weather->GetPendingRainState() : Weather->CurrentState)
                    : Weather->GetScheduledStateAt(Day, Segment);
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
            const bool bWaitingForClouds = Weather->IsRainPending() && FirstWetSegment <= CurrentGlobalSegment;
            if (bWaitingForClouds) TimelineEventStart = Now + Weather->GetRainLeadInRemaining();
            bTimelineEventActive = !bWaitingForClouds && (bTimelineManual || TimelineEventStart <= Now);
            bTimelineContainsStorm = false;

            if (bTimelineManual)
            {
                const EFPSWeatherState State = bWaitingForClouds ? Weather->GetPendingRainState() : Weather->CurrentState;
                TimelineStageStates.Add(static_cast<int32>(State));
                TimelineStageStarts.Add(TimelineEventStart);
                TimelineStageEnds.Add(TimelineEventStart);
                bTimelineContainsStorm = State == EFPSWeatherState::Storm;
            }
            else
            {
                for (int32 GlobalSegment = FirstWetSegment; GlobalSegment < EndWetSegment; ++GlobalSegment)
                {
                    const int32 Day = GlobalSegment / WeatherSegmentsPerDay;
                    const int32 Segment = GlobalSegment % WeatherSegmentsPerDay;
                    const EFPSWeatherState State = Weather->GetScheduledStateAt(Day, Segment);
                    const float StageStart = FMath::Max(GlobalSegment * SegmentSeconds, TimelineEventStart);
                    const float StageEnd = (GlobalSegment + 1) * SegmentSeconds;
                    if (StageEnd <= StageStart) continue;
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

            // A short automatic rain window can end before the cloud lead-in;
            // keep the pending forecast readable until the schedule cancels it.
            if (TimelineStageStates.IsEmpty())
            {
                TimelineStageStates.Add(static_cast<int32>(Weather->GetPendingRainState()));
                TimelineStageStarts.Add(TimelineEventStart);
                TimelineStageEnds.Add(TimelineEventStart);
            }
            TimelineEventEnd = FMath::Max(TimelineEventEnd, TimelineEventStart);
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
            if (bWaitingForClouds)
                TimelineWarningLabel = TEXT("云层正在聚集，随后开始") + WeatherName(Weather->GetPendingRainState());
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
    if (!bTimelineHasEvent) SetTimelineDetailsOpen(false);

    const FString NewSignature = FString::Printf(TEXT("%d|%d|%d|%s|%s|%s|%s|%s"), bTimelineHasEvent, bTimelineEventActive,
        bTimelineContainsStorm, *TimelineEventLabel, *TimelineStartLabel, *TimelineEndLabel, *TimelineWarningLabel, *TimelineIntensityLabel);
    if (bForce || NewSignature != TimelineDetailSignature)
    {
        TimelineDetailSignature = NewSignature;
        RebuildEventDetails();
    }
    UpdateEventTimelineLayout();
}

void UColdSteelHUDWidget::RebuildEventDetails()
{
    if(!TimelineDetailContent)return;
    const float S=ColdSteelUI::PixelScale(this);
    const float Scroll=TimelineDetailScroll?TimelineDetailScroll->GetScrollOffset():0;
    TimelineDetailContent->ClearChildren();
    if(!bTimelineHasEvent || TimelineStageStates.IsEmpty())return;
    auto* Summary=WidgetTree->ConstructWidget<UHorizontalBox>();
    TimelineDetailContent->AddChildToVerticalBox(Summary)->SetPadding(FMargin(0,0,0,12/S));
    auto* Icon=WidgetTree->ConstructWidget<UImage>();
    const auto State=bTimelineContainsStorm?EFPSWeatherState::Storm:static_cast<EFPSWeatherState>(TimelineStageStates[0]);
    if(auto* T=LoadUiTexture(WeatherIconFile(State)))Icon->SetBrushFromTexture(T,true);
    auto* IconSize=WidgetTree->ConstructWidget<USizeBox>();IconSize->SetWidthOverride(36/S);IconSize->SetHeightOverride(36/S);IconSize->SetContent(Icon);
    Summary->AddChildToHorizontalBox(IconSize)->SetPadding(FMargin(0,0,10/S,0));
    auto* Name=MakeTimelineText(TimelineEventLabel,16,ColdSteelUI::TextPrimary,false,true);Name->SetAutoWrapText(true);
    auto* NameSlot=Summary->AddChildToHorizontalBox(Name);NameSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));NameSlot->SetVerticalAlignment(VAlign_Center);
    const TArray<TPair<FString,FString>> Pairs={
        {TEXT("位面"),WeatherRegionName(GetWorld())},{TEXT("强度"),TimelineIntensityLabel},
        {TEXT("开始"),TimelineStartLabel},{TEXT("结束"),TimelineEndLabel},
        {TEXT("持续"),TimelineDurationLabel},{TEXT("状态"),bTimelineEventActive?TEXT("正在发生"):TEXT("预测中")}};
    auto* Grid=WidgetTree->ConstructWidget<UUniformGridPanel>();Grid->SetSlotPadding(FMargin(2/S));TimelineDetailContent->AddChildToVerticalBox(Grid);
    const int32 Columns=TimelineDetailWidth>0 && TimelineDetailWidth<440?1:2;
    for(int32 I=0;I<Pairs.Num();++I)
    {
        auto* Cell=MakeSurface(ColdSteelUI::StatusCard,8/S,ColdSteelUI::Border,1/S);Cell->SetPadding(FMargin(10/S,8/S));
        auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();Cell->SetContent(Row);
        auto* Key=MakeTimelineText(Pairs[I].Key,12,ColdSteelUI::TextSecondary);Row->AddChildToHorizontalBox(Key)->SetPadding(FMargin(0,0,8/S,0));
        bool Numeric=false;for(TCHAR C:Pairs[I].Value)Numeric|=FChar::IsDigit(C);
        auto* Value=MakeTimelineText(Pairs[I].Value,14,ColdSteelUI::TextPrimary,Numeric);Value->SetAutoWrapText(true);Value->SetJustification(ETextJustify::Right);
        Row->AddChildToHorizontalBox(Value)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        auto* CellSlot=Grid->AddChildToUniformGrid(Cell,I/Columns,I%Columns);CellSlot->SetHorizontalAlignment(HAlign_Fill);CellSlot->SetVerticalAlignment(VAlign_Fill);
    }
    auto* Note=MakeTimelineText(TimelineWarningLabel,14,bTimelineContainsStorm?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);Note->SetAutoWrapText(true);
    TimelineDetailContent->AddChildToVerticalBox(Note)->SetPadding(FMargin(2/S,10/S,2/S,8/S));
    if(TimelineStageStates.Num()>1)
    {
        TimelineDetailContent->AddChildToVerticalBox(MakeTimelineText(TEXT("雨势变化"),16,ColdSteelUI::TextPrimary,false,true))->SetPadding(FMargin(2/S,8/S,0,4/S));
        for(int32 I=0;I<TimelineStageStates.Num();++I)
        {
            auto* Phase=WidgetTree->ConstructWidget<UVerticalBox>();TimelineDetailContent->AddChildToVerticalBox(Phase)->SetPadding(FMargin(2/S,6/S));
            Phase->AddChildToVerticalBox(MakeTimelineText(WeatherName(static_cast<EFPSWeatherState>(TimelineStageStates[I])),14,ColdSteelUI::TextPrimary));
            auto* Time=MakeTimelineText(FormatTimelineAbsolute(TimelineStageStarts[I],TimelineDaySeconds)+TEXT(" — ")+FormatTimelineAbsolute(TimelineStageEnds[I],TimelineDaySeconds),12,ColdSteelUI::TextSecondary,true);
            Time->SetAutoWrapText(true);Phase->AddChildToVerticalBox(Time);
        }
    }
    if(TimelineDetailScroll)TimelineDetailScroll->SetScrollOffset(Scroll);
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
    TimelineWarningLabel = TEXT("本轮降雨结束后转为多云");
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
        SetTimelineDetailsOpen(true);
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
    SetTimelineDetailsOpen(!bTimelineDetailsOpen);
}

void UColdSteelHUDWidget::HandleTimelineDetailsCloseClicked()
{
    SetTimelineDetailsOpen(false);
}

void UColdSteelHUDWidget::HandleTimelineFilterAllClicked()
{
    bTimelineWeatherFilter = false;
    RefreshEventTimeline(true);
    SetTimelineDetailsOpen(false);
}

void UColdSteelHUDWidget::HandleTimelineFilterWeatherClicked()
{
    bTimelineWeatherFilter = true;
    RefreshEventTimeline(true);
    SetTimelineDetailsOpen(false);
}

void UColdSteelHUDWidget::SetExternalDrawerOpen(bool bOpen)
{
    if(bExternalDrawerOpen==bOpen)return;
    bExternalDrawerOpen=bOpen;
    // 入口列、世界时钟与武器详情都在逐帧 Tick 里读这个标记；这里再刷一次弹药栏，
    // 让面板弹出的同一帧就收起它（该面板的可见性由它自己的 Refresh 决定）。
    RefreshAmmo();
}

void UColdSteelHUDWidget::SetInventoryOpen(bool bOpen)
{
    if(!bOpen)CancelQuickDrag();
    if(!bOpen)HideItemTooltip(true);
    if(!bOpen)CloseWarehouse();
    if(!bOpen)CloseSmelting();   // 收背包连带收面板：保证"再打开背包"永远不会带出上次的面板
    if(!bOpen)CloseWorkbench();  // 工作台制作面板同一连带口径（同文件同规则）
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
        InventoryBlur->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
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
{ SetInventoryPage(bStatusTab?0:1); }

void UColdSteelHUDWidget::OpenSkills()
{
    UWidgetBlueprintLibrary::CancelDragDrop(); CloseWarehouse();
    SetInventoryPage(2); SetInventoryOpen(true);
    if(CloseButton)CloseButton->SetKeyboardFocus();
}

void UColdSteelHUDWidget::OpenCodex()
{
    UWidgetBlueprintLibrary::CancelDragDrop(); CloseWarehouse();
    SetInventoryPage(4); SetInventoryOpen(true);
    if(CloseButton)CloseButton->SetKeyboardFocus();
}

void UColdSteelHUDWidget::SetInventoryPage(int32 Page)
{
    HideItemTooltip(true);
    bStatusTabActive=Page==0; bSkillsTabActive=Page==2; bCodexTabActive=Page==4;
    if (StatusPage) StatusPage->SetVisibility(Page==0?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if (EquipmentPage) EquipmentPage->SetVisibility(Page==1?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if (EquipmentAmmoTabs) EquipmentAmmoTabs->SetVisibility(Page==1||Page==3?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if (AmmoPouchPage) AmmoPouchPage->SetVisibility(Page==3?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if (SkillPage) SkillPage->SetVisibility(Page==2?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if (CodexPage) CodexPage->SetVisibility(Page==4?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if (InventoryTitleText) InventoryTitleText->SetText(FText::FromString(Page==0?TEXT("角色状态"):(Page==1||Page==3)?TEXT("装备与背包"):Page==4?TEXT("图鉴"):TEXT("技能")));
    UBorder* Surfaces[]={StatusTabSurface,EquipmentTabSurface,SkillTabSurface};
    UBorder* Underlines[]={StatusTabUnderline,EquipmentTabUnderline,SkillTabUnderline};
    UTextBlock* Labels[]={StatusTabText,EquipmentTabText,SkillTabText};
    for(int32 I=0;I<3;++I)
    {
        if(Surfaces[I])Surfaces[I]->SetBrush(ColdSteelUI::RoundedBrush(I==Page?GunsmithUI::Gray(75,110):GunsmithUI::Gray(18,32),ReferenceUnits(7),FLinearColor::Transparent,0));
        if(Labels[I])Labels[I]->SetColorAndOpacity(I==Page?GunsmithUI::Text:GunsmithUI::Muted);
        if(Underlines[I])Underlines[I]->SetVisibility(I==Page?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    }
    HideStatusTooltip();
    if (Page!=1)
    {
        if(auto* Scroll=Cast<UScrollBox>(EquipmentPage))if(auto* Board=Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0)))Board->CancelInteraction();
        bEquipmentTooltipPinned = false;
        HideEquipmentTooltip();
    }
    RefreshStatus();
}

void UColdSteelHUDWidget::RefreshAmmo()
{
    RefreshQuickBar();

    const AFPSGAMECharacter* Character = GetOwningPlayerPawn<AFPSGAMECharacter>();
    if(AmmoReadout)
    {
        AmmoReadout->Refresh(Character,StatusModel,bInventoryOpen);
        // The bottom-right weapon readout and the drawer share the right edge; hide it during the slide too.
        if(bInventoryOpen||DrawerProgress>KINDA_SMALL_NUMBER||bExternalDrawerOpen)AmmoReadout->SetVisibility(ESlateVisibility::Collapsed);
        const float S=ColdSteelUI::PixelScale(this);
        FVector2D View=GetCachedGeometry().GetLocalSize();
        if(View.X<100)View=UWidgetLayoutLibrary::GetViewportSize(this)/S;
        if(View.X>0)
        {
            const float Width=FMath::Min(UColdSteelAmmoReadout::PreferredWidth,FMath::Max(1.f,float(View.X)*S-40.f));
            const FVector2D HotbarSize=HotbarCanvasSlot&&HotbarCanvasSlot->Content?HotbarCanvasSlot->Content->GetDesiredSize():FVector2D::ZeroVector;
            const float HotbarRight=View.X*.5f+FMath::Max(float(HotbarSize.X),424/S)*.5f;
            float Bottom=20/S;
            if(View.X-20/S-Width/S<HotbarRight+12/S)
            {
                const float HotbarBottom=HotbarCanvasSlot?-HotbarCanvasSlot->GetPosition().Y:12/S;
                const float HotbarTop=HotbarBottom+FMath::Max(float(HotbarSize.Y),66/S);
                const float StaminaTop=StaminaSlot?-StaminaSlot->GetPosition().Y+StaminaSlot->GetSize().Y:HotbarTop;
                Bottom=FMath::Max(HotbarTop,StaminaTop)+12/S;
            }
            AmmoReadout->UpdateLayout(Width,Bottom*S);
        }
    }
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
        const bool Sword=StatusModel&&StatusModel->Equipped()&&ColdSteelInventory::IsTwoHandedSword(*StatusModel->Equipped());
        AmmoStatusValueText->SetText(FText::FromString(Sword?TEXT("近战"):FString::Printf(TEXT("%d/%d"), Character->GetMagazineAmmo(), Character->GetReserveAmmo())));
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
        if(StatusModel&&StatusModel->Equipped()&&ColdSteelInventory::IsTwoHandedSword(*StatusModel->Equipped()))
            Damage=ColdSteelMelee::Evaluate(*StatusModel->Equipped(),StatusModel).Damage;
        EquipmentDamageValue->SetText(FText::FromString(FString::Printf(TEXT("%.2f"), Damage)));
        EquipmentCapacityValue->SetText(FText::FromString(FString::Printf(TEXT("%d 发"), Capacity)));
        EquipmentIntervalValue->SetText(FText::FromString(FString::Printf(TEXT("%.0fms"), Interval * 1000.0f)));
        EquipmentReloadValue->SetText(FText::FromString(FString::Printf(TEXT("%.0fms"), Reload * 1000.0f)));
        EquipmentAmmoValue->SetText(FText::FromString(FString::Printf(TEXT("%d / %d"), Character->GetMagazineAmmo(), Character->GetReserveAmmo())));
        if(StatusModel&&StatusModel->Equipped()&&ColdSteelInventory::IsTwoHandedSword(*StatusModel->Equipped()))
        {EquipmentCapacityValue->SetText(FText::FromString(TEXT("—")));EquipmentReloadValue->SetText(FText::FromString(TEXT("—")));EquipmentAmmoValue->SetText(FText::FromString(TEXT("近战")));}
    }
}



void UColdSteelHUDWidget::ShowEquipmentTooltip()
{
    if (!EquipmentTooltip || !bInventoryOpen || bStatusTabActive || bSkillsTabActive || bCodexTabActive) return;
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
    Label->SetFont(bNumeric ? ColdSteelUI::NumberFont(Size, bBold) : ColdSteelUI::TextFont(Size, bBold));
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
    Label->SetFont(bNumeric ? ColdSteelUI::NumberFont(Points, bBold) : ColdSteelUI::TextFont(Points, bBold));
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
    SlotSurface->SetPadding(FMargin(0));
    SlotSurface->SetHorizontalAlignment(HAlign_Fill);
    SlotSurface->SetVerticalAlignment(VAlign_Fill);
    USizeBox* Size = WidgetTree->ConstructWidget<USizeBox>();
    Size->SetWidthOverride(ReferenceUnits(HotbarSlotSize));
    Size->SetHeightOverride(ReferenceUnits(HotbarSlotSize));
    SlotSurface->SetContent(Size);
    UOverlay* Overlay = WidgetTree->ConstructWidget<UOverlay>();
    Size->SetContent(Overlay);
    // F/G 专属槽：快速进战与环绕飞剑的固定键位，只读显示，不占七槽混放绑定。
    if(KeyHint==TEXT("F")){BuildQuickSlot(Overlay,QuickSlots.Num(),TEXT("quickCombat"));return SlotSurface;}
    if(KeyHint==TEXT("G")){BuildQuickSlot(Overlay,QuickSlots.Num(),TEXT("runeBlades"));return SlotSurface;}
    const int32 Index=KeyHint.IsNumeric()?FCString::Atoi(*KeyHint)+2:KeyHint==TEXT("Q")?0:KeyHint==TEXT("E")?1:2;
    BuildQuickSlot(Overlay,Index);
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
    UBorder* Surface = MakeSurface(bActive?GunsmithUI::Gray(75,110):GunsmithUI::Gray(18,32),ReferenceUnits(7),FLinearColor::Transparent,0);
    USizeBox* Height = WidgetTree->ConstructWidget<USizeBox>();
    Height->SetHeightOverride(ReferenceUnits(40));
    InventoryTabSizes.Add(Height);
    Surface->SetContent(Height);
    UOverlay* Layer = WidgetTree->ConstructWidget<UOverlay>();
    Height->SetContent(Layer);
    UTextBlock* Label = MakeInventoryText(Caption,14,bActive?GunsmithUI::Text:GunsmithUI::Muted,false,bActive);
    Label->SetJustification(ETextJustify::Center);
    UOverlaySlot* LabelSlot = Layer->AddChildToOverlay(Label);
    LabelSlot->SetHorizontalAlignment(HAlign_Fill);
    LabelSlot->SetVerticalAlignment(VAlign_Center);
    UBorder* Underline = MakeSurface(GunsmithUI::Silver,0,FLinearColor::Transparent,0);
    Underline->SetVisibility(bActive ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    UOverlaySlot* UnderlineSlot = Layer->AddChildToOverlay(Underline);
    UnderlineSlot->SetHorizontalAlignment(HAlign_Fill);
    UnderlineSlot->SetVerticalAlignment(VAlign_Bottom);
    USizeBox* UnderlineHeight = WidgetTree->ConstructWidget<USizeBox>();
    UnderlineHeight->SetHeightOverride(ReferenceUnits(2));
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
