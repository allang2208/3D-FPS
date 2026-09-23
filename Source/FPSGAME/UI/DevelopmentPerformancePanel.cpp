// F6 performance UI: measured observations, instrumented counts and resource inventory are distinct.
#include "DevelopmentPanelWidget.h"
#include "PerformanceTextUpdate.h"
#include "Components/BackgroundBlur.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/ProgressBar.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/WrapBox.h"
#include "Engine/World.h"
#include "Misc/ScopeExit.h"

namespace
{
FLinearColor BudgetColor(float Ms, float TargetFps)
{
    if (Ms <= 0.f) return ColdSteelUI::TextSecondary;
    const float Budget = 1000.f / FMath::Max(1.f, TargetFps);
    return Ms <= Budget ? ColdSteelUI::Success : (Ms <= Budget * 2.f ? ColdSteelUI::Warning : ColdSteelUI::Danger);
}
FString FormatCount(int64 Value)
{
    if (Value >= 1000000) return FString::Printf(TEXT("%.1fM"), Value / 1000000.0);
    if (Value >= 1000) return FString::Printf(TEXT("%.1fK"), Value / 1000.0);
    return FString::Printf(TEXT("%lld"), Value);
}
FString TimingLine(const TCHAR* Name, const FFPSMetricDistribution& Data)
{
    if (Data.Count == 0) return FString::Printf(TEXT("%s：—（无有效计时；未就绪或该线程/计时不可用）"), Name);
    return FString::Printf(TEXT("%s  均 %.2f · P50 %.2f · P95 %.2f · P99 %.2f · 峰 %.2f ms  [n=%d]"),
        Name, Data.Average, Data.P50, Data.P95, Data.P99, Data.Peak, Data.Count);
}
void ButtonText(UButton* Button, const TCHAR* Text)
{
    if (Button)
        if (auto* Label = Cast<UTextBlock>(Button->GetContent()))
        {
            Label->SetAutoWrapText(false);
            SetPerformanceText(Label, FText::FromString(Text));
        }
}
}

void UDevelopmentPanelWidget::BuildPerformancePage(UVerticalBox* Page)
{
    const float Scale = ColdSteelUI::PixelScale(this);
    const auto Section = [this, Page, Scale](const TCHAR* Title)
    {
        Page->AddChildToVerticalBox(CreatePanelText(Title, 16, ColdSteelUI::TextPrimary))
            ->SetPadding(FMargin(0, 12.f / Scale, 0, 6.f / Scale));
    };
    const auto Body = [this, Page, Scale](const TCHAR* Text)
    {
        auto* Label = CreatePanelText(Text, 12, ColdSteelUI::TextSecondary);
        Page->AddChildToVerticalBox(Label)->SetPadding(FMargin(0, 0, 0, 6.f / Scale));
        return Label;
    };
    Section(TEXT("性能记录"));
    auto* Controls = WidgetTree->ConstructWidget<UWrapBox>();
    Controls->SetInnerSlotPadding(FVector2D(6.f / Scale, 6.f / Scale));
    Page->AddChildToVerticalBox(Controls)->SetPadding(FMargin(0, 0, 0, 8.f / Scale));
    const auto AddControl = [this, Controls](UWidget* Widget, float Pixels)
    {
        auto* Box = WidgetTree->ConstructWidget<USizeBox>();
        Box->SetContent(Widget);
        Controls->AddChildToWrapBox(Box);
        PerformanceControlBoxes.Emplace(Box, Pixels);
    };
    PerformancePauseButton = CreatePanelButton(TEXT("冻结显示"), TEXT("DevelopmentPerformancePause"));
    PerformancePauseButton->OnClicked.AddDynamic(this, &ThisClass::PerformancePauseClicked);
    AddControl(PerformancePauseButton, 88.f);
    PerformanceRecordingButton = CreatePanelButton(TEXT("停止采集"), TEXT("DevelopmentPerformanceRecording"));
    PerformanceRecordingButton->OnClicked.AddDynamic(this, &ThisClass::PerformanceRecordingClicked);
    AddControl(PerformanceRecordingButton, 104.f);
    PerformanceResetButton = CreatePanelButton(TEXT("清空采样"), TEXT("DevelopmentPerformanceReset"));
    PerformanceResetButton->OnClicked.AddDynamic(this, &ThisClass::PerformanceResetClicked);
    AddControl(PerformanceResetButton, 88.f);
    PerformanceExportButton = CreatePanelButton(TEXT("导出 JSON"), TEXT("DevelopmentPerformanceExport"));
    PerformanceExportButton->OnClicked.AddDynamic(this, &ThisClass::PerformanceExportClicked);
    AddControl(PerformanceExportButton, 100.f);

    PerformanceInterval = WidgetTree->ConstructWidget<UComboBoxString>();
    for (const TCHAR* Option : {TEXT("0.25 秒"), TEXT("0.5 秒"), TEXT("1 秒"), TEXT("2 秒")})
        PerformanceInterval->AddOption(Option);
    PerformanceInterval->OnGenerateWidgetEvent.BindDynamic(this, &ThisClass::GenerateListOption);
    PerformanceInterval->SetSelectedOption(TEXT("0.5 秒"));
    PerformanceInterval->OnSelectionChanged.AddDynamic(this, &ThisClass::PerformanceIntervalChanged);
    AddControl(PerformanceInterval, 104.f);
    PerformanceRowCount = WidgetTree->ConstructWidget<UComboBoxString>();
    for (const TCHAR* Option : {TEXT("前 10"), TEXT("前 20"), TEXT("前 40"), TEXT("前 80")})
        PerformanceRowCount->AddOption(Option);
    PerformanceRowCount->OnGenerateWidgetEvent.BindDynamic(this, &ThisClass::GenerateListOption);
    PerformanceRowCount->SetSelectedOption(TEXT("前 20"));
    PerformanceRowCount->OnSelectionChanged.AddDynamic(this, &ThisClass::PerformanceRowsChanged);
    AddControl(PerformanceRowCount, 88.f);
    PerformanceLiveState = Body(TEXT("等待首个引擎帧；关闭面板后轻量采集继续。"));
    PerformanceMessage = Body(TEXT("重新开始/清空采样会清除长帧历史；图标失败状态保留。导出保存当前显示快照。"));

    Section(TEXT("帧预算 · 引擎帧边界墙钟"));
    PerformanceBudget = CreatePanelText(TEXT("采样中…"), 14, ColdSteelUI::TextPrimary);
    Page->AddChildToVerticalBox(PerformanceBudget)->SetPadding(FMargin(0, 0, 0, 6.f / Scale));
    PerformanceStats = Body(TEXT(""));
    Body(TEXT("线程/GPU 为进程级原始观察值，异步发布且可能延迟，不能逐行当作同一帧或相加；GPU 取 GPU0。零计时显示未知。"
        "百分位使用 nearest-rank；未过滤暂停、后台或加载长帧。"));

    Section(TEXT("长帧事件 · 可追溯帧号"));
    PerformanceHitches = Body(TEXT("等待帧窗口…"));
    Section(TEXT("图标任务与已采集分段"));
    PerformanceIconTasks = Body(TEXT("等待图标子系统状态…"));
    Body(TEXT("分段为主线程墙钟耗时，包含内部等待；World Tick 包含内部项目工作，图标 Prepare 包含预热，各项不能相加。"
        "队列年龄是跨帧等待时间；GPU Capture 这里只计提交，GPU 执行耗时未采集。"));

    Section(TEXT("项目动作 · 已埋点路径"));
    PerformanceCounters = Body(TEXT("等待采样…"));
    Body(TEXT("字段变化不是实际渲染重建次数；主/世界可见性刷新分别统计。这里只覆盖玩家身体已埋点路径，不代表全部 CPU 开销。"));

    Section(TEXT("资源覆盖 · 配置与数量"));
    PerformanceCoverage = Body(TEXT("等待场景扫描…"));
    Body(TEXT("骨骼配置、启用 Tick 与实际求值不同；手动求值/并行求值耗时未采集。隐藏阴影仅为当前视图资格，遮挡和实际 shadow pass 未采集。"));
    PerformanceEnvironment = Body(TEXT(""));

    Section(TEXT("灯光 · 配置与视野估算"));
    PerformanceLights = Body(TEXT("等待灯光快照…"));
    Body(TEXT("候选数只按组件状态、距离与球形影响范围/视锥筛选，未计入墙体遮挡、聚光锥精确裁剪、屏幕尺寸裁剪及渲染器实际提交。"
        "它不是实际渲染灯数，也不是 GPU 毫秒；天空光不计入局部/方向光源列表。"));

    Section(TEXT("网格资源复杂度 · 经验权重"));
    Body(TEXT("权重 =（源三角数 + 0.1 × 顶点数 + 2500 × 材质槽）× 实例总数。百分比以全部有几何数据的已注册网格为分母，条形图相对榜首。"
        "这些不是耗时占比，也不是本帧绘制量；不按距离或可见性推测开销。"));
    PerformanceStatus = Body(TEXT("等待扫描…"));
    PerformanceList = WidgetTree->ConstructWidget<UVerticalBox>();
    Page->AddChildToVerticalBox(PerformanceList);
    Body(TEXT("当前实际 LOD、Nanite 渲染路径、可见实例、材质复杂度和遮挡未采集。GPU 分阶段、已列分段之外的 CPU/等待归因、内存及 GC/加载事件尚未接入。"));
    UpdatePerformanceLayout(Scale);
}

void UDevelopmentPanelWidget::UpdatePerformanceLayout(float Scale)
{
    for (const auto& Entry : PerformanceControlBoxes)
        if (auto* Box = Entry.Key.Get())
        {
            Box->SetWidthOverride(Entry.Value / Scale);
            Box->SetHeightOverride(ColdSteelUI::ActionHeight / Scale);
        }
    for (auto* Button : {PerformancePauseButton.Get(), PerformanceRecordingButton.Get(),
        PerformanceResetButton.Get(), PerformanceExportButton.Get()})
    {
        if (!Button) continue;
        Button->SetStyle(ColdSteelUI::ButtonStyle(1.f / Scale));
        if (auto* Label = Cast<UTextBlock>(Button->GetContent())) Label->SetAutoWrapText(false);
    }
    StyleChoice(PerformanceInterval, Scale);
    StyleChoice(PerformanceRowCount, Scale);
    for (FPerformanceRow& Row : PerformanceEntries)
        if (auto* Card = Row.Card.Get())
        {
            Card->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard, ColdSteelUI::CardRadius / Scale));
            Card->SetPadding(FMargin(10.f / Scale, 8.f / Scale));
        }
}

void UDevelopmentPanelWidget::PerformanceClicked() { SetPage(3); }

void UDevelopmentPanelWidget::SetPerformancePaused(bool bPaused)
{
    bPerformancePaused = bPaused;
    PerformanceNextStatus = 0.0;
    if (!bPaused) PerformanceNextUpdate = 0.0;
    ButtonText(PerformancePauseButton, bPaused ? TEXT("恢复显示") : TEXT("冻结显示"));
}
void UDevelopmentPanelWidget::PerformancePauseClicked() { SetPerformancePaused(!bPerformancePaused); }

void UDevelopmentPanelWidget::PerformanceRecordingClicked()
{
    if (UWorld* World = GetWorld())
        if (auto* Metrics = World->GetSubsystem<UFPSPerformanceMetricsSubsystem>())
        {
            Metrics->SetRecording(!Metrics->IsRecording());
            SetPerformancePaused(false);
            if (PerformanceMessage) SetPerformanceText(PerformanceMessage, FText::FromString(
                Metrics->IsRecording() ? TEXT("已开始新采集，旧窗口与长帧历史已清空；图标失败状态保留。") : TEXT("采集已停止，保留最后窗口与长帧历史；未收齐的前后帧不会补录。")));
        }
}
void UDevelopmentPanelWidget::PerformanceResetClicked()
{
    if (UWorld* World = GetWorld())
        if (auto* Metrics = World->GetSubsystem<UFPSPerformanceMetricsSubsystem>())
        {
            Metrics->ClearSamples();
            SetPerformancePaused(false);
            if (PerformanceMessage) SetPerformanceText(PerformanceMessage, FText::FromString(TEXT("窗口、长帧历史、观察开销和事件基线已清空；图标失败状态保留。")));
        }
}
void UDevelopmentPanelWidget::PerformanceExportClicked()
{
    if (bPerformanceExporting) return;
    if (PerformanceCache.CapturedAtUtc.IsEmpty())
    {
        if (PerformanceMessage) SetPerformanceText(PerformanceMessage, FText::FromString(TEXT("尚无快照可导出。")));
        return;
    }
    bPerformanceExporting = true;
    const uint64 ExportGeneration = ++PerformanceExportGeneration;
    if (PerformanceExportButton) PerformanceExportButton->SetIsEnabled(false);
    if (PerformanceMessage) {
        SetPerformanceText(PerformanceMessage, FText::FromString(TEXT("正在后台导出提交时的显示快照…")));
        PerformanceMessage->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    }
    const FString Source = FString::Printf(TEXT("session=%s generation=%llu"),*PerformanceCache.SessionId,PerformanceCache.CaptureGeneration);
    FFPSPerformanceScope ExportScope(this,TEXT("Panel.ExportSubmit"),Source);
    const TWeakObjectPtr<UDevelopmentPanelWidget> WeakThis(this);
    const TWeakObjectPtr<UWorld> WeakWorld(GetWorld());
    FFPSPerformanceSnapshot ExportCopy = PerformanceCache;
    ExportCopy.ObserverAtExport = {true, IsPanelOpen(), bPerformancePaused, ActivePage, PerformanceIntervalMs,
        Blur ? Blur->GetBlurStrength() : 0.f, Blur ? Blur->GetBlurRadius() : 0};
    UFPSPerformanceMetricsSubsystem::ExportSnapshotAsync(ExportCopy,
        [WeakThis,WeakWorld,ExportGeneration,Source](bool bSaved,const FString& Path,double ElapsedMs)
        {
            UFPSPerformanceMetricsSubsystem::RecordMarker(WeakWorld.Get(),TEXT("Panel.ExportFinished"),
                FString::Printf(TEXT("%s success=%d async_total_wall_ms=%.3f path=%s"),*Source,bSaved,ElapsedMs,*Path));
            auto* Widget = WeakThis.Get();
            if (!Widget || Widget->PerformanceExportGeneration != ExportGeneration) return;
            Widget->bPerformanceExporting = false;
            if (Widget->PerformanceExportButton) Widget->PerformanceExportButton->SetIsEnabled(true);
            if (Widget->PerformanceMessage) {
                SetPerformanceText(Widget->PerformanceMessage, FText::FromString(bSaved
                    ? FString::Printf(TEXT("已导出提交时的快照（复制/排队/写入历时 %.1f ms，非主线程耗时）：\n%s"),ElapsedMs,*Path)
                    : TEXT("导出失败：无法写入 Saved/PerformanceReports。")));
                Widget->PerformanceMessage->SetColorAndOpacity(bSaved?ColdSteelUI::Success:ColdSteelUI::Warning);
            }
        });
}
void UDevelopmentPanelWidget::PerformanceIntervalChanged(FString Selected, ESelectInfo::Type)
{
    if (Selected.StartsWith(TEXT("0.25"))) PerformanceIntervalMs = 250.f;
    else if (Selected.StartsWith(TEXT("1"))) PerformanceIntervalMs = 1000.f;
    else if (Selected.StartsWith(TEXT("2"))) PerformanceIntervalMs = 2000.f;
    else PerformanceIntervalMs = 500.f;
    PerformanceNextUpdate = 0.0;
}
void UDevelopmentPanelWidget::PerformanceRowsChanged(FString Selected, ESelectInfo::Type)
{
    if (Selected.Contains(TEXT("10"))) PerformanceRowLimit = 10;
    else if (Selected.Contains(TEXT("40"))) PerformanceRowLimit = 40;
    else if (Selected.Contains(TEXT("80"))) PerformanceRowLimit = 80;
    else PerformanceRowLimit = 20;
    PerformanceNextUpdate = 0.0;
}

void UDevelopmentPanelWidget::RefreshPerformance(float)
{
    UWorld* World = GetWorld();
    if (!World) return;
    auto* Metrics = World->GetSubsystem<UFPSPerformanceMetricsSubsystem>();
    if (!Metrics) return;
    const double Now = FPlatformTime::Seconds();
    if (Now >= PerformanceNextStatus)
    {
        PerformanceNextStatus = Now + .5;
        ButtonText(PerformanceRecordingButton, Metrics->IsRecording() ? TEXT("停止采集") : TEXT("开始新采集"));
        if (PerformanceLiveState)
        {
            SetPerformanceText(PerformanceLiveState, FText::FromString(FString::Printf(
                TEXT("%s · %s · 最近 %.0f 秒滚动窗口\n显示快照：%s · 快照年龄 %.1f 秒"),
                Metrics->IsRecording() ? TEXT("后台采集中") : TEXT("采集已停止"),
                bPerformancePaused ? TEXT("显示已冻结") : TEXT("显示刷新中"), Metrics->WindowSeconds,
                PerformanceCache.CapturedAtUtc.IsEmpty() ? TEXT("等待首次刷新") : *PerformanceCache.CapturedAtUtc,
                PerformanceLastRefresh > 0.0 ? Now - PerformanceLastRefresh : 0.0)));
        }
    }
    if (bPerformancePaused || Now < PerformanceNextUpdate) return;
    PerformanceNextUpdate = Now + PerformanceIntervalMs / 1000.0;
    PerformanceLastRefresh = Now;
    PerformanceCache = Metrics->BuildSnapshot(PerformanceRowLimit, GetOwningPlayer());
    PerformanceCache.ObserverAtSnapshot = {true, IsPanelOpen(), bPerformancePaused, ActivePage, PerformanceIntervalMs,
        Blur ? Blur->GetBlurStrength() : 0.f, Blur ? Blur->GetBlurRadius() : 0};
    // Measure only UI update work here. The snapshot records the scan separately.
    const double UiStart = FPlatformTime::Seconds();
    FFPSPerformanceScope UiScope(this,TEXT("Panel.UiUpdate"));
    ON_SCOPE_EXIT { Metrics->RecordUiUpdate(static_cast<float>((FPlatformTime::Seconds() - UiStart) * 1000.0)); };
    const FFPSFrameBudget& B = PerformanceCache.Budget;
    RefreshPerformanceDiagnostics();
    const float Scale = ColdSteelUI::PixelScale(this);
    if (PerformanceBudget)
    {
        FString Text = B.Frame.Count > 0
            ? FString::Printf(TEXT("%.1f FPS（同窗） · 最新帧 %.2f ms\n平均 %.2f · P50 %.2f · P95 %.2f · P99 %.2f · 峰值 %.2f ms\n%d 帧 / %.2f 秒 · 目标 %.0f FPS / %.2f ms · 超预算 %.1f%% · >%.2f ms 慢帧 %.1f%%"),
                B.Fps, B.LatestFrameMs, B.Frame.Average, B.Frame.P50, B.Frame.P95, B.Frame.P99, B.Frame.Peak,
                B.Frame.Count, B.DurationSeconds, PerformanceCache.TargetFps, 1000.f / PerformanceCache.TargetFps,
                B.OverBudgetFraction * 100.f, PerformanceCache.SlowFrameThresholdMs, B.SlowFrameFraction * 100.f)
            : FString(B.bRecording ? TEXT("等待两个引擎帧边界建立窗口…") : TEXT("采集已停止，当前窗口无样本。"));
        if (B.Frame.Count > 0 && B.Frame.Count < 100) Text += TEXT("\n样本少于 100，尾部百分位仅供参考。");
        if (B.bCapacityLimited) Text += TEXT("\n已达 8192 帧容量，实际窗口短于设定时间。");
        Text += FString::Printf(TEXT("\n窗口内：暂停 %d 帧 · 后台 %d 帧 · 最新样本距快照 %.2f 秒"),
            B.PausedFrames, B.BackgroundFrames, B.SampleAgeSeconds);
        SetPerformanceText(PerformanceBudget, FText::FromString(Text));
        PerformanceBudget->SetColorAndOpacity(BudgetColor(B.Frame.P95, PerformanceCache.TargetFps));
    }
    if (PerformanceStats)
    {
        FString Text = TEXT("线程来源帧号/发布时间未知：下列为独立发布读数，不与上方长帧逐行对齐。\n")
            + TimingLine(TEXT("Game"), B.Game) + TEXT("\n") + TimingLine(TEXT("Draw"), B.Draw)
            + TEXT("\n") + TimingLine(TEXT("RHI"), B.Rhi) + TEXT("\n") + TimingLine(TEXT("GPU0"), B.Gpu)
            + TEXT("\n") + TimingLine(TEXT("Game 等待"), B.GameWait)
            + TEXT("\n") + TimingLine(TEXT("Draw 等待"), B.DrawWait)
            + TEXT("\n") + TimingLine(TEXT("Game 关键路径"), B.GameCritical)
            + TEXT("\n") + TimingLine(TEXT("Draw 关键路径"), B.DrawCritical);
        Text += FString::Printf(TEXT("\n场景/窗口构建：本次 %.3f ms · 平均 %.3f · 峰值 %.3f [n=%d]"),
            PerformanceCache.ScanMs, B.Scan.Average, B.Scan.Peak, B.Scan.Count);
        Text += B.UiUpdate.Count > 0
            ? FString::Printf(TEXT("\nUI 更新：平均 %.3f · 峰值 %.3f ms [n=%d；截至上次刷新]"),
                B.UiUpdate.Average, B.UiUpdate.Peak, B.UiUpdate.Count)
            : TEXT("\nUI 更新：—（等待一次完整刷新）");
        Text += TEXT("\n上述观察开销不包含 Slate 布局/绘制与 GPU 模糊，不能代表整个面板成本。");
        SetPerformanceText(PerformanceStats, FText::FromString(Text));
    }
    if (PerformanceCounters)
    {
        const FFPSPerformanceActions& A = PerformanceCache.Actions;
        const auto Event = [&B](const TCHAR* Label, uint64 Count)
        {
            return B.Frame.Count > 0 && B.DurationSeconds > 0
                ? FString::Printf(TEXT("%s %llu 次 · %.2f/s · %.3f/帧"), Label, Count,
                    Count / B.DurationSeconds, static_cast<double>(Count) / B.Frame.Count)
                : FString::Printf(TEXT("%s —（无采样窗口）"), Label);
        };
        SetPerformanceText(PerformanceCounters, FText::FromString(
            Event(TEXT("可见性/阴影字段变化"), A.VisibilityFlagChanges)
            + TEXT("\n") + Event(TEXT("玩家身体路径武器重建"), A.EquipmentRebuilds)
            + TEXT("\n") + Event(TEXT("服装重建"), A.OutfitRebuilds)
            + TEXT("\n") + Event(TEXT("装备采集"), A.EquipmentCaptures)
            + TEXT("\n") + Event(TEXT("主可见性刷新"), A.VisibilityUpdates)
            + TEXT("\n") + Event(TEXT("世界可见性刷新"), A.WorldVisibilityUpdates)));
    }
    if (PerformanceCoverage)
    {
        const FFPSPerformanceCoverage& C = PerformanceCache.Coverage;
        FString Text = FString::Printf(
            TEXT("骨骼组件 %d · 有网格 %d · 资产骨骼合计 %d\n已注册且启用 Tick %d · Leader Pose 跟随 %d\n")
            TEXT("AlwaysRefresh 配置 %d（其中已注册/有网格/启用 Tick %d）· AlwaysPose 配置 %d\n")
            TEXT("ISM/HISM 组件 %d · 实例总数 %lld · DynamicMesh %d\n")
            TEXT("光源 %d（已注册且可见标志 %d / 其中投影标志 %d）· 音源 %d（播放中 %d）\n")
            TEXT("Niagara %d（激活 %d；粒子量和耗时未知）· Cascade %d（活动粒子 %lld）\n")
            TEXT("其它图元 %d · 网格几何不可读 %d"),
            C.SkeletalComponents, C.SkeletalWithAsset, C.TotalAssetBones, C.SkeletalTickEnabled,
            C.SkeletalLeaderFollowers, C.AlwaysRefreshConfigured, C.TickEnabledAlwaysRefresh,
            C.AlwaysPoseConfigured, C.InstancedComponents, C.Instances, C.DynamicMeshes,
            C.Lights, C.VisibleLights, C.ShadowLights, C.AudioComponents, C.PlayingAudio,
            C.NiagaraComponents, C.ActiveNiagara, C.CascadeComponents, C.CascadeParticles,
            C.OtherPrimitives, C.GeometryUnavailable);
        Text += PerformanceCache.bHasView
            ? FString::Printf(TEXT("\n隐藏投影资格 %d（所有图元；不代表实际渲染次数）"), C.HiddenShadowEligible)
            : TEXT("\n隐藏投影资格：—（无当前视图）");
        SetPerformanceText(PerformanceCoverage, FText::FromString(Text));
    }
    if (PerformanceEnvironment)
    {
        FString Text=PerformanceCache.Environment;
        for(const FString& Json:PerformanceCache.DungeonGenerationReports)
        {
            TSharedPtr<FJsonObject> Report;
            if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Report)||!Report)continue;
            const FString GenerationStatus=Report->GetStringField(TEXT("status"));
            Text+=FString::Printf(TEXT("\n地牢种子 %d · %s · 创建任务 %d / %d"),int32(Report->GetNumberField(TEXT("seed"))),
                GenerationStatus==TEXT("ready")?TEXT("已就绪"):GenerationStatus==TEXT("planning")?TEXT("规划中"):GenerationStatus==TEXT("failed")?TEXT("生成失败"):TEXT("构建中"),
                int32(Report->GetNumberField(TEXT("jobs_completed"))),int32(Report->GetNumberField(TEXT("jobs_total"))));
            double Modules=0;
            if(Report->TryGetNumberField(TEXT("modules"),Modules))
            {
                Text+=FString::Printf(TEXT(" · %d 模块\n实例化 %d 构件 / %d 组 · 独立刚性构件 %d · 最慢创建批次 %.2f ms"),int32(Modules),
                    int32(Report->GetNumberField(TEXT("instanced_parts"))),int32(Report->GetNumberField(TEXT("instance_components"))),
                    int32(Report->GetNumberField(TEXT("individual_rigid_parts"))),Report->GetNumberField(TEXT("peak_slice_ms")));
            }
            Text+=TEXT("\n以上为本次生成累计记录，独立于帧窗口；不是 GPU 耗时或帧数收益。");
        }
        SetPerformanceText(PerformanceEnvironment, FText::FromString(Text));
    }
    RefreshPerformanceLighting();
    if (PerformanceStatus)
    {
        const double Fraction = PerformanceCache.AllRankTotal > 0
            ? PerformanceCache.DisplayedRankTotal / PerformanceCache.AllRankTotal : 0.0;
        SetPerformanceText(PerformanceStatus, FText::FromString(FString::Printf(
            TEXT("扫描 %d Actor / %d 组件；可排名网格 %d；显示 %d 项，占全部网格权重 %.1f%%"),
            PerformanceCache.ActorCount, PerformanceCache.ComponentCount, PerformanceCache.RankedMeshCount,
            PerformanceCache.Costs.Num(), Fraction * 100.0)));
    }
    if (!PerformanceList) return;
    const int32 Wanted = PerformanceCache.Costs.Num();
    if (PerformanceEntries.Num() < Wanted)
    {
        const int32 Target = FMath::Min(FMath::DivideAndRoundUp(Wanted, 8) * 8, FMath::Max(PerformanceRowLimit, 8));
        for (int32 Index = PerformanceEntries.Num(); Index < Target; ++Index)
        {
            FPerformanceRow Row;
            auto* Card = WidgetTree->ConstructWidget<UBorder>();
            PerformanceList->AddChildToVerticalBox(Card)->SetPadding(FMargin(0, 0, 0, 6.f / Scale));
            Card->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard, ColdSteelUI::CardRadius / Scale));
            Card->SetPadding(FMargin(10.f / Scale, 8.f / Scale));
            auto* Stack = WidgetTree->ConstructWidget<UVerticalBox>(); Card->SetContent(Stack);
            Row.Card = Card;
            auto* BarBox = WidgetTree->ConstructWidget<USizeBox>();
            BarBox->SetHeightOverride(3.f / Scale);
            Stack->AddChildToVerticalBox(BarBox)->SetPadding(FMargin(0, 0, 0, 6.f / Scale));
            auto* Bar = WidgetTree->ConstructWidget<UProgressBar>(); BarBox->SetContent(Bar);
            Bar->SetFillColorAndOpacity(ColdSteelUI::Accent);
            FProgressBarStyle BarStyle;
            BarStyle.SetBackgroundImage(ColdSteelUI::RoundedBrush(ColdSteelUI::Content, 1.f, FLinearColor::Transparent, 0.f));
            BarStyle.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White, 1.f, FLinearColor::Transparent, 0.f));
            Bar->SetWidgetStyle(BarStyle); Row.Bar = Bar;

            auto* Head = WidgetTree->ConstructWidget<UHorizontalBox>(); Stack->AddChildToVerticalBox(Head);
            auto* Rank = CreatePanelText(TEXT(""), 12, ColdSteelUI::TextSecondary); Rank->SetAutoWrapText(false);
            Head->AddChildToHorizontalBox(Rank)->SetPadding(FMargin(0, 0, 8.f / Scale, 0)); Row.Rank = Rank;
            auto* Label = CreatePanelText(TEXT(""), 14, ColdSteelUI::TextPrimary);
            Head->AddChildToHorizontalBox(Label)->SetSize(FSlateChildSize(ESlateSizeRule::Fill)); Row.Label = Label;
            auto* Share = CreatePanelText(TEXT(""), 12, ColdSteelUI::TextSecondary); Share->SetAutoWrapText(false);
            Head->AddChildToHorizontalBox(Share)->SetPadding(FMargin(8.f / Scale, 0, 0, 0)); Row.Share = Share;
            auto* Numbers = CreatePanelText(TEXT(""), 12, ColdSteelUI::TextSecondary);
            Stack->AddChildToVerticalBox(Numbers)->SetPadding(FMargin(0, 4.f / Scale, 0, 0)); Row.Numbers = Numbers;
            auto* Detail = CreatePanelText(TEXT(""), 12, ColdSteelUI::TextSecondary);
            Stack->AddChildToVerticalBox(Detail)->SetPadding(FMargin(0, 3.f / Scale, 0, 0)); Row.Detail = Detail;
            PerformanceEntries.Add(MoveTemp(Row));
        }
    }
    for (int32 Index = 0; Index < PerformanceEntries.Num(); ++Index)
    {
        FPerformanceRow& Row = PerformanceEntries[Index];
        const bool bUsed = Index < Wanted;
        if (auto* Card = Row.Card.Get()) Card->SetVisibility(bUsed ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
        if (!bUsed) continue;
        const FFPSComponentCost& Cost = PerformanceCache.Costs[Index];
        if (auto* Label = Row.Rank.Get()) SetPerformanceText(Label, FText::AsNumber(Index + 1));
        if (auto* Label = Row.Label.Get())
        {
            SetPerformanceText(Label, FText::FromString(Cost.Label));
            Label->SetToolTipText(FText::FromString(Cost.ObjectPath + TEXT("\n") + Cost.Detail));
        }
        if (auto* Label = Row.Share.Get())
            SetPerformanceText(Label, FText::FromString(FString::Printf(TEXT("%.1f%% 权重"), Cost.ShareOfAll * 100.f)));
        if (auto* Bar = Row.Bar.Get()) Bar->SetPercent(FMath::Clamp(Cost.ShareOfTop, 0.f, 1.f));
        if (auto* Label = Row.Numbers.Get())
        {
            FString Text = FString::Printf(TEXT("%s · %s %s tri · %d 材质槽"),
                *Cost.Kind, Cost.bDynamicGeometry ? TEXT("当前 CPU 源网格") : TEXT("资产 LOD0/回退"),
                *FormatCount(Cost.Triangles), Cost.MaterialSlots);
            if (Cost.bInstanced) Text += FString::Printf(TEXT(" · %d 实例（单份几何 × 实例总量排名）"), Cost.Instances);
            if (Cost.ForcedLodModel >= 0)
                Text += Cost.ForcedLodModel == 0 ? TEXT(" · LOD 自动（实际未采集）")
                    : FString::Printf(TEXT(" · 配置强制 LOD%d（参数 %d；实际未采集）"),Cost.ForcedLodModel-1,Cost.ForcedLodModel);
            if (Cost.bViewVisibilityKnown)
                Text += FString::Printf(TEXT("\n%.1f m · 视图可见性标志：%s"), Cost.DistanceMeters, Cost.bVisibleToView ? TEXT("允许") : TEXT("隐藏"));
            else Text += TEXT("\n当前视图可见性：未知");
            Text += Cost.bHasFrustum ? (Cost.bOnScreen ? TEXT(" · 包围盒与主视锥相交") : TEXT(" · 主视锥外")) : TEXT(" · 视锥未知");
            Text += Cost.bCastsShadow ? TEXT(" · CastShadow 开") : TEXT(" · CastShadow 关");
            if (Cost.bHiddenShadowEligible) Text += TEXT(" · 隐藏投影资格");
            SetPerformanceText(Label, FText::FromString(Text));
        }
        if (auto* Label = Row.Detail.Get())
        {
            FString Text;
            if (!Cost.LODTriangles.IsEmpty())
            {
                TArray<FString> Steps;
                for (int64 Count : Cost.LODTriangles) Steps.Add(FormatCount(Count));
                Text = FString::Printf(TEXT("%sLOD 链（%d 档）：%s；当前实际档位未采集"),
                    Cost.bHasNaniteData ? TEXT("回退网格 ") : TEXT("资产 "), Steps.Num(), *FString::Join(Steps, TEXT(" → ")));
            }
            if (Cost.bHasNaniteData) Text += TEXT("\nNanite 数据存在；不代表当前渲染路径。");
            if (!Cost.Detail.IsEmpty()) Text += TEXT("\n") + Cost.Detail;
            SetPerformanceText(Label, FText::FromString(Text));
        }
    }
}
