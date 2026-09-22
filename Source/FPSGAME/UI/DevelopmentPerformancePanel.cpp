// F6 开发面板「性能监测」页：帧预算 + 组件开销排行。
//
// 数据来源分两半，页面上也分开显示，避免把推导值和实测值混在一起：
//   - 帧预算：读引擎的线程计时（Game/Draw/RHI 周期数、GAverageMS/FPS），
//     与 `stat unit` 同源，是真实的耗时。
//   - 组件排行：遍历世界的图元/光源/粒子/音频组件，读真实的三角形、顶点、
//     材质槽与阴影开关，加权成 Rank 排序。Rank 是推导的排序分，**不是毫秒**。
#include "DevelopmentPanelWidget.h"
#include "FPSPerformanceMetrics.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/GridPanel.h"
#include "Components/GridSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/World.h"

namespace
{
/** 帧预算按 60 FPS / 30 FPS 两档着色，让一眼能看出当前是哪一档。 */
FLinearColor BudgetColor(float FrameMs)
{
    if (FrameMs <= 0.f) return ColdSteelUI::TextSecondary;
    if (FrameMs <= 16.7f) return FLinearColor(0.45f, 0.85f, 0.45f);
    if (FrameMs <= 33.3f) return FLinearColor(0.95f, 0.78f, 0.35f);
    return FLinearColor(0.95f, 0.45f, 0.40f);
}

/** 三角数按 K/M 缩写，避免长数字把行撑开。 */
FString FormatCount(int64 Value)
{
    if (Value >= 1000000) return FString::Printf(TEXT("%.1fM"), Value / 1000000.0);
    if (Value >= 1000) return FString::Printf(TEXT("%.1fK"), Value / 1000.0);
    return FString::FromInt(static_cast<int32>(Value));
}
}

void UDevelopmentPanelWidget::BuildPerformancePage(UVerticalBox* Page)
{
    const float Scale = ColdSteelUI::PixelScale(this);
    Page->AddChildToVerticalBox(CreatePanelText(TEXT("帧预算 · 实测"), 16, ColdSteelUI::TextPrimary))
        ->SetPadding(FMargin(0, 14.f / Scale, 0, 6.f / Scale));
    PerformanceBudget = CreatePanelText(TEXT("采样中…"), 13, ColdSteelUI::TextPrimary);
    Page->AddChildToVerticalBox(PerformanceBudget)->SetPadding(FMargin(0, 0, 0, 4.f / Scale));
    PerformanceStats = CreatePanelText(TEXT(""), 12, ColdSteelUI::TextSecondary);
    Page->AddChildToVerticalBox(PerformanceStats)->SetPadding(FMargin(0, 0, 0, 10.f / Scale));

    // 引擎动作计数：这是定位游戏线程耗时的主工具。
    Page->AddChildToVerticalBox(CreatePanelText(TEXT("每帧动作计数 · 实测"), 14, ColdSteelUI::TextPrimary))
        ->SetPadding(FMargin(0, 4.f / Scale, 0, 4.f / Scale));
    PerformanceCounters = CreatePanelText(TEXT("采样中…"), 12, ColdSteelUI::TextSecondary);
    Page->AddChildToVerticalBox(PerformanceCounters)->SetPadding(FMargin(0, 0, 0, 10.f / Scale));

    // 刷新控制：排行本身有开销，所以间隔可调、也能暂停。
    auto* Controls = WidgetTree->ConstructWidget<UHorizontalBox>();
    Page->AddChildToVerticalBox(Controls)->SetPadding(FMargin(0, 0, 0, 10.f / Scale));
    auto AddControlBox = [this, Controls](UWidget* Widget, float Pixels)
    {
        auto* Box = WidgetTree->ConstructWidget<USizeBox>();
        Box->SetContent(Widget); Box->SetWidthOverride(Pixels);
        Controls->AddChildToHorizontalBox(Box)->SetPadding(FMargin(0, 0, 6.f, 0));
    };
    PerformancePauseButton = CreatePanelButton(TEXT("暂停"), TEXT("DevelopmentPerformancePause"));
    AddControlBox(PerformancePauseButton, 76.f);
    PerformancePauseButton->OnClicked.AddDynamic(this, &ThisClass::PerformancePauseClicked);
    PerformanceInterval = WidgetTree->ConstructWidget<UComboBoxString>();
    PerformanceInterval->AddOption(TEXT("0.25 秒")); PerformanceInterval->AddOption(TEXT("0.5 秒"));
    PerformanceInterval->AddOption(TEXT("1 秒")); PerformanceInterval->AddOption(TEXT("2 秒"));
    PerformanceInterval->SetSelectedOption(TEXT("0.5 秒"));
    PerformanceInterval->OnSelectionChanged.AddDynamic(this, &ThisClass::PerformanceIntervalChanged);
    AddControlBox(PerformanceInterval, 104.f);
    PerformanceRowCount = WidgetTree->ConstructWidget<UComboBoxString>();
    PerformanceRowCount->AddOption(TEXT("前 10")); PerformanceRowCount->AddOption(TEXT("前 20"));
    PerformanceRowCount->AddOption(TEXT("前 40")); PerformanceRowCount->AddOption(TEXT("前 80"));
    PerformanceRowCount->SetSelectedOption(TEXT("前 20"));
    PerformanceRowCount->OnSelectionChanged.AddDynamic(this, &ThisClass::PerformanceRowsChanged);
    AddControlBox(PerformanceRowCount, 92.f);

    PerformanceStatus = CreatePanelText(TEXT("等待首次扫描…"), 12, ColdSteelUI::TextSecondary);
    Page->AddChildToVerticalBox(PerformanceStatus)->SetPadding(FMargin(0, 0, 0, 10.f / Scale));

    Page->AddChildToVerticalBox(CreatePanelText(TEXT("组件开销排行 · 推导"), 16, ColdSteelUI::TextPrimary))
        ->SetPadding(FMargin(0, 4.f / Scale, 0, 6.f / Scale));
    PerformanceList = WidgetTree->ConstructWidget<UVerticalBox>();
    Page->AddChildToVerticalBox(PerformanceList);

    Page->AddChildToVerticalBox(CreatePanelText(
        TEXT("排行按几何量、材质槽、阴影与粒子加权，是相对排序分，不是毫秒。"
             "引擎没有公开逐组件耗时接口，GPU 也不导出逐图元耗时，所以这里不给"
             "「某个组件花了多少毫秒」。要线程级拆解请用 stat unit / stat gpu。"),
        11, ColdSteelUI::TextSecondary))->SetPadding(FMargin(0, 10.f / Scale, 0, 0));
}

void UDevelopmentPanelWidget::PerformanceClicked() { SetPage(3); }

void UDevelopmentPanelWidget::SetPerformancePaused(bool bPaused)
{
    bPerformancePaused = bPaused;
    if (PerformancePauseButton)
    {
        if (auto* Label = Cast<UTextBlock>(PerformancePauseButton->GetContent()))
        {
            Label->SetText(FText::FromString(bPaused ? TEXT("继续") : TEXT("暂停")));
        }
    }
}

void UDevelopmentPanelWidget::PerformancePauseClicked() { SetPerformancePaused(!bPerformancePaused); }

void UDevelopmentPanelWidget::PerformanceIntervalChanged(FString Selected, ESelectInfo::Type Type)
{
    if (Selected.StartsWith(TEXT("0.25"))) PerformanceIntervalMs = 250.f;
    else if (Selected.StartsWith(TEXT("1"))) PerformanceIntervalMs = 1000.f;
    else if (Selected.StartsWith(TEXT("2"))) PerformanceIntervalMs = 2000.f;
    else PerformanceIntervalMs = 500.f;
    PerformanceCountdown = 0.f;
}

void UDevelopmentPanelWidget::PerformanceRowsChanged(FString Selected, ESelectInfo::Type Type)
{
    if (Selected.Contains(TEXT("10"))) PerformanceRowLimit = 10;
    else if (Selected.Contains(TEXT("40"))) PerformanceRowLimit = 40;
    else if (Selected.Contains(TEXT("80"))) PerformanceRowLimit = 80;
    else PerformanceRowLimit = 20;
    PerformanceCountdown = 0.f;
}

void UDevelopmentPanelWidget::RefreshPerformance(float Delta)
{
    if (bPerformancePaused) return;

    UWorld* World = GetWorld();
    if (!World) return;
    auto* Metrics = World->GetSubsystem<UFPSPerformanceMetricsSubsystem>();
    if (!Metrics) return;

    // 帧时间采样每帧都做，滚动统计才有足够样本；扫描按间隔做。
    Metrics->SampleFrame(Delta);
    PerformanceCountdown -= Delta;
    if (PerformanceCountdown > 0.f) return;
    PerformanceCountdown = PerformanceIntervalMs / 1000.f;

    const float SlowThresholdMs = Metrics->SlowFrameThresholdMs;
    PerformanceCache = Metrics->BuildSnapshot(PerformanceRowLimit);
    const FFPSFrameBudget& Budget = PerformanceCache.Budget;
    // 全部条目的 Rank 之和，用于算占比。作用域覆盖后面整个函数。
    float Total = 0.f;
    for (const FFPSComponentCost& Cost : PerformanceCache.Costs) Total += Cost.Rank;

    if (PerformanceBudget)
    {
        PerformanceBudget->SetText(FText::FromString(FString::Printf(
            TEXT("%.1f FPS   ·   帧 %.2f ms\n平均 %.2f · P50 %.2f · P95 %.2f · P99 %.2f · 峰值 %.2f ms"),
            Budget.Fps, Budget.FrameMs,
            Budget.AverageFrameMs, Budget.P50FrameMs, Budget.P95FrameMs,
            Budget.P99FrameMs, Budget.PeakFrameMs)));
        // 着色按 P95：体感由尾部决定，平均值会把尖峰抹平。
        PerformanceBudget->SetColorAndOpacity(FSlateColor(BudgetColor(
            Budget.P95FrameMs > 0.f ? Budget.P95FrameMs : Budget.FrameMs)));
    }
    if (PerformanceStats)
    {
        // Game 与 Draw 在时间轴上重叠，这里只并列显示，不做求和。
        FString Text = FString::Printf(
            TEXT("Game %.2f ms   Draw %.2f ms   RHI %.2f ms   Game 等待 %.2f ms"),
            Budget.GameMs, Budget.DrawMs, Budget.RhiMs, Budget.GameWaitMs);
        Text += FString::Printf(TEXT("\n关键路径  Game %.2f ms   Draw %.2f ms"),
            Budget.GameCriticalMs, Budget.DrawCriticalMs);
        Text += Budget.bHasGpu
            ? FString::Printf(TEXT("   GPU %.2f ms"), Budget.GpuMs)
            : FString(TEXT("   GPU 由 RHI 未报告"));
        Text += FString::Printf(TEXT("\n超目标预算 %.1f%%   超 %.1f ms 慢帧 %.1f%%   （%d 帧样本）"),
            Budget.Over60Pct * 100.f, SlowThresholdMs, Budget.Over30Pct * 100.f, Budget.SampleCount);
        // 采集器自己的开销也要报出来，否则「零成本观测」是假的。
        Text += FString::Printf(TEXT("\n面板自身扫描 平均 %.1f ms · 峰值 %.1f ms"),
            Budget.MonitorAverageMs, Budget.MonitorPeakMs);
        PerformanceStats->SetText(FText::FromString(Text));
    }
    if (PerformanceCounters)
    {
        const FFPSFrameCounters& C = PerformanceCache.Counters;
        // 计数解释：
        //   稳态下「标志改动」和「装备重建」都应当接近 0。若每秒几十次，
        //   说明当帧在持续置脏渲染状态 / 重建组件——那就是游戏线程的开销来源。
        //   「可见性刷新」本身每帧跑是设计如此，但它调用的 setter 受守卫保护，
        //   真正要看的是它引发的「标志改动」次数。
        FString Text = FString::Printf(
            TEXT("标志改动 %.1f/s（本周期 %d 次）   装备重建 %.1f/s（%d 次）\n")
            TEXT("可见性刷新 %.1f/s（%d 次）   装备采集 %d 次（0.2 s 节流）"),
            C.VisibilityFlagChangesPerSec, C.VisibilityFlagChanges,
            C.EquipmentRebuildsPerSec, C.EquipmentRebuilds,
            C.VisibilityUpdatesPerSec, C.VisibilityUpdates,
            C.EquipmentCaptures);
        Text += FString::Printf(
            TEXT("\n骨骼网格 %d 个 · 总骨骼 %d · 隐藏投影 %d"),
            C.SkeletalMeshComponents, C.TotalBones, C.HiddenShadowCasters);
        // 每帧强制刷新骨骼的网格数：这是「换任何武器都卡」的头号候选，
        // 因为它与装备无关，且每次刷新都要重算全部骨骼变换。
        Text += FString::Printf(
            TEXT("\n每帧强制刷骨骼 %d 个 · 仅求值 pose %d 个"),
            C.AlwaysRefreshBones, C.AlwaysTickPose);
        Text += FString::Printf(
            TEXT("\n线程  Game %.2f / 等待 %.2f   Draw %.2f / 等待 %.2f ms"),
            C.GameThreadMs, C.GameThreadWaitMs, C.RenderThreadMs, C.RenderThreadWaitMs);
        PerformanceCounters->SetText(FText::FromString(Text));
        // 标志改动或装备重建速率偏高就标黄——这两个是游戏线程的嫌疑项。
        const bool bSuspicious = C.VisibilityFlagChangesPerSec > 60.f || C.EquipmentRebuildsPerSec > 5.f;
        PerformanceCounters->SetColorAndOpacity(FSlateColor(
            bSuspicious ? FLinearColor(0.95f, 0.78f, 0.35f) : ColdSteelUI::TextSecondary));
    }
    if (PerformanceStatus)
    {
        PerformanceStatus->SetText(FText::FromString(FString::Printf(
            TEXT("扫描 %d 个 Actor / %d 个组件，用时 %.1f ms；下列 %d 项占统计总权重 %.0f%%"),
            PerformanceCache.ActorCount, PerformanceCache.ComponentCount, PerformanceCache.ScanMs,
            PerformanceCache.Costs.Num(),
            Total > 0.f ? PerformanceCache.Costs[0].Rank / Total * 100.f : 0.f)));
    }

    if (!PerformanceList) return;

    const int32 Wanted = PerformanceCache.Costs.Num();
    // 控件树只在「预留行数不够」时增长，多余的行隐藏而不销毁。
    // 扫描只返回 Rank > 0 的条目，实际条数会随场景在阈值附近浮动（例如 20 与 19 之间），
    // 若每次按实际条数重建整张列表，刷新时会持续闪烁。
    if (PerformanceEntries.Num() < Wanted)
    {
        const int32 Target = FMath::Min(FMath::DivideAndRoundUp(Wanted, 8) * 8,
                                        FMath::Max(PerformanceRowLimit, 8));
        for (int32 Index = PerformanceEntries.Num(); Index < Target; ++Index)
        {
            auto* Card = WidgetTree->ConstructWidget<UBorder>();
            PerformanceList->AddChildToVerticalBox(Card)->SetPadding(FMargin(0, 0, 0, 4.f));

            auto* Stack = WidgetTree->ConstructWidget<UVerticalBox>();
            Card->SetContent(Stack);

            FPerformanceRow Row;
            Row.Card = Card;
            // 占比条：宽度 = 该项 Rank / 榜首 Rank，对应原 game-dev 面板
            // barWidth = averageMs / topAverageMs 的核心视觉。
            // 用一个铺满的轨道 + 定宽前景条实现；前景宽度在刷新时按轨道实测宽度计算。
            auto* BarTrack = WidgetTree->ConstructWidget<UBorder>();
            Stack->AddChildToVerticalBox(BarTrack)->SetPadding(FMargin(26.f, 2.f, 0, 2.f));
            auto* BarFill = WidgetTree->ConstructWidget<USizeBox>();
            BarTrack->SetContent(BarFill);
            BarFill->SetHeightOverride(3.f);
            BarFill->SetWidthOverride(0.f);
            Row.BarFill = BarFill;

            // 首行：编号 + 名称 + 占比。名称放在权重格，随内容伸缩。
            auto* Head = WidgetTree->ConstructWidget<UHorizontalBox>();
            Stack->AddChildToVerticalBox(Head);
            auto* RankText = CreatePanelText(TEXT("—"), 12, ColdSteelUI::TextSecondary);
            RankText->SetAutoWrapText(false);
            auto* RankBox = WidgetTree->ConstructWidget<USizeBox>();
            RankBox->SetContent(RankText); RankBox->SetWidthOverride(26.f);
            Head->AddChildToHorizontalBox(RankBox);
            auto* LabelText = CreatePanelText(TEXT("—"), 12, ColdSteelUI::TextPrimary);
            LabelText->SetAutoWrapText(false);
            // 必须挂在 Fill 槽上：HBox 默认 Auto 会按内容定宽，把 WidthOverride 顶掉，
            // 长名字会被压成一条竖线。
            {
                auto* LabelBox = WidgetTree->ConstructWidget<USizeBox>();
                LabelBox->SetContent(LabelText);
                Head->AddChildToHorizontalBox(LabelBox)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
            }
            auto* ShareText = CreatePanelText(TEXT("—"), 12, ColdSteelUI::TextSecondary);
            ShareText->SetAutoWrapText(false);
            auto* ShareBox = WidgetTree->ConstructWidget<USizeBox>();
            ShareBox->SetContent(ShareText); ShareBox->SetWidthOverride(58.f);
            Head->AddChildToHorizontalBox(ShareBox);
            Row.Rank = RankText; Row.Label = LabelText; Row.Share = ShareText;

            auto* Numbers = CreatePanelText(TEXT(""), 11, ColdSteelUI::TextSecondary);
            Numbers->SetAutoWrapText(false);
            Stack->AddChildToVerticalBox(Numbers)->SetPadding(FMargin(26.f, 1.f, 0, 0));
            Row.Numbers = Numbers;
            auto* Detail = CreatePanelText(TEXT(""), 11, ColdSteelUI::TextSecondary);
            Detail->SetAutoWrapText(false);
            Stack->AddChildToVerticalBox(Detail)->SetPadding(FMargin(26.f, 1.f, 0, 0));
            Row.Detail = Detail;
            PerformanceEntries.Add(MoveTemp(Row));
        }
    }

    // 占比条的轨道宽度：读第一行前景条的父级（轨道 Border）实测宽度。
    float BarTrackWidth = 0.f;
    if (PerformanceEntries.Num() > 0)
    {
        if (auto* First = PerformanceEntries[0].BarFill.Get())
        {
            if (const UWidget* Track = First->GetParent())
            {
                BarTrackWidth = Track->GetCachedGeometry().GetLocalSize().X;
            }
        }
    }

    for (int32 Index = 0; Index < PerformanceEntries.Num(); ++Index)
    {
        FPerformanceRow& Row = PerformanceEntries[Index];
        // 超出本次结果的预留行隐藏，控件保留待下帧复用。
        const bool bUsed = Index < Wanted;
        if (auto* Card = Row.Card.Get())
        {
            Card->SetVisibility(bUsed ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
        }
        if (!bUsed) continue;

        const FFPSComponentCost& Cost = PerformanceCache.Costs[Index];
        if (auto* Text = Row.Rank.Get())
        {
            Text->SetText(FText::FromString(FString::Printf(TEXT("%d"), Index + 1)));
            Text->SetColorAndOpacity(FSlateColor(Index < 3 ? ColdSteelUI::TextPrimary : ColdSteelUI::TextSecondary));
        }
        if (auto* Text = Row.Label.Get())
        {
            Text->SetText(FText::FromString(Cost.Label));
        }
        if (auto* Text = Row.Share.Get())
        {
            Text->SetText(FText::FromString(FString::Printf(TEXT("%.1f%%"),
                Total > 0.f ? Cost.Rank / Total * 100.f : 0.f)));
        }
        if (auto* Text = Row.Numbers.Get())
        {
            FString Numbers = FString::Printf(TEXT("%s  ·  %.0f m  ·  %s"),
                *Cost.Kind, Cost.DistanceMeters, Cost.bOnScreen ? TEXT("视锥内") : TEXT("视锥外"));
            if (Cost.Triangles > 0) Numbers += FString::Printf(TEXT("  ·  %s tri"), *FormatCount(Cost.Triangles));
            if (Cost.MaterialSlots > 0) Numbers += FString::Printf(TEXT("  ·  %d 材质槽"), Cost.MaterialSlots);
            if (Cost.bCastsShadow) Numbers += TEXT("  ·  投射阴影");
            if (Cost.Particles > 0) Numbers += FString::Printf(TEXT("  ·  %d 粒子"), Cost.Particles);
            Text->SetText(FText::FromString(Numbers));
        }
        if (auto* Text = Row.Detail.Get())
        {
            // 展示 LOD 链：远端玩家能用多少面渲染，取决于这条链。
            // 链上只有一档，或末档仍然很重，意味着每个同类网格都在按最高细节跑。
            if (Cost.LODTriangles.Num() > 1)
            {
                TArray<FString> Steps;
                for (int64 Triangles : Cost.LODTriangles) Steps.Add(FormatCount(Triangles));
                FString Detail = FString::Printf(TEXT("%s tri · LOD %s"),
                    *FormatCount(Cost.Triangles), *FString::Join(Steps, TEXT(" → ")));
                if (!Cost.Detail.IsEmpty()) Detail += FString::Printf(TEXT(" · %s"), *Cost.Detail);
                Text->SetText(FText::FromString(Detail));
                Text->SetColorAndOpacity(FSlateColor(ColdSteelUI::TextSecondary));
            }
            else
            {
                FString Detail = Cost.Triangles > 0
                    ? FString::Printf(TEXT("%s tri · 仅 LOD0"), *FormatCount(Cost.Triangles))
                    : Cost.Detail;
                if (Cost.Triangles > 0 && !Cost.Detail.IsEmpty())
                    Detail += FString::Printf(TEXT(" · %s"), *Cost.Detail);
                Text->SetText(FText::FromString(Detail));
                // 只有一档 LOD 是联机时的隐患：远端玩家不会降面，标黄提示。
                Text->SetColorAndOpacity(FSlateColor(Cost.Triangles > 0 && Cost.LODTriangles.Num() <= 1
                    ? FLinearColor(0.95f, 0.78f, 0.35f) : ColdSteelUI::TextSecondary));
            }
        }
        if (auto* Bar = Row.BarFill.Get())
        {
            // 轨道宽度取上一帧的实测值；首帧还是 0，下一帧自然补上。
            // 最小 2% 保证榜首之外的项目也看得见。
            const float Track = BarTrackWidth > 1.f ? BarTrackWidth : 160.f;
            const float Share = FMath::Clamp(Cost.ShareOfTop, 0.02f, 1.f);
            Bar->SetWidthOverride(Track * Share);
        }
    }
}