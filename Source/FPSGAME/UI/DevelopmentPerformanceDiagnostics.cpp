#include "DevelopmentPanelWidget.h"
#include "PerformanceTextUpdate.h"
#include "Components/TextBlock.h"

namespace
{
struct FPerformanceStageLabel { const TCHAR* Stage; const TCHAR* Label; };
const FPerformanceStageLabel PerformanceStageLabels[] = {
    {TEXT("World.Tick"),TEXT("当前 World Tick")},
    {TEXT("Viewport.Draw"),TEXT("游戏视口绘制提交")},
    {TEXT("Slate.TickAndDrawWidgets"),TEXT("进程 Slate 更新/绘制")},
    {TEXT("Slate.WindowPaint"),TEXT("进程窗口 Paint（不含此前等待）")},
    {TEXT("Engine.GarbageCollection"),TEXT("进程垃圾回收（含嵌套工作）")},
    {TEXT("PlayerBody.EquipmentCapture"),TEXT("装备信息采集")},
    {TEXT("PlayerBody.OwnerVisibility"),TEXT("玩家可见性更新")},
    {TEXT("PlayerBody.WorldVisibility"),TEXT("世界身体可见性更新")},
    {TEXT("Panel.UiUpdate"),TEXT("性能页 UI 更新")},
    {TEXT("Icon.Tick"),TEXT("图标 Tick 总计")},
    {TEXT("Icon.Prepare"),TEXT("图标准备单片")},
    {TEXT("Icon.ResourceRequest"),TEXT("图标异步资源请求")},
    {TEXT("Icon.AttachmentSlice"),TEXT("图标单个配件装配")},
    {TEXT("Icon.InitializeVisuals"),TEXT("图标角色初始化")},
    {TEXT("Icon.AssemblyAndBounds"),TEXT("图标装配/包围盒/资源更新")},
    {TEXT("Icon.SkinnedBounds"),TEXT("图标/掉落物共享包围盒")},
    {TEXT("Icon.MaterialReadinessSubmit"),TEXT("材质就绪查询提交")},
    {TEXT("Icon.MeleeAssembly"),TEXT("近战图标准备")},
    {TEXT("Pickup.Warm"),TEXT("掉落物预热调用（含缓存检查）")},
    {TEXT("Pickup.BuildWeapon"),TEXT("掉落物模型构建")},
    {TEXT("Pickup.InitializeVisuals"),TEXT("掉落物角色初始化")},
    {TEXT("Icon.ReadbackSubmit"),TEXT("异步图标回读提交")},
    {TEXT("Icon.ReadbackPoll"),TEXT("异步回读查询/发布入口")},
    {TEXT("Icon.PublishTexture"),TEXT("图标纹理上传与缓存")},
    {TEXT("Icon.NotifyReady"),TEXT("图标完成通知")},
    {TEXT("Dungeon.RoomLighting"),TEXT("地牢房间灯光调度")},
    {TEXT("Dungeon.Catalog"),TEXT("地牢目录准备")},
    {TEXT("Dungeon.PrepareJobs"),TEXT("地牢任务与连接图")},
    {TEXT("Dungeon.AssemblySlice"),TEXT("地牢本帧创建批次（含子步骤）")},
    {TEXT("Dungeon.Resources"),TEXT("地牢资源解析")},
    {TEXT("Dungeon.Teardown"),TEXT("地牢旧预览清理")},
    {TEXT("Dungeon.Finalize"),TEXT("地牢提交与导航准备")},
    {TEXT("Dungeon.MeshCollision"),TEXT("地牢网格与碰撞注册")},
    {TEXT("Dungeon.Props"),TEXT("地牢宝箱姿态与碰撞")},
    {TEXT("Dungeon.Lights"),TEXT("地牢灯光创建")},
    {TEXT("Dungeon.Anchors"),TEXT("地牢定位点")},
    {TEXT("Dungeon.PusDamage"),TEXT("地牢积液伤害")},
    {TEXT("Dungeon.Ready"),TEXT("地牢准备完成")}
};
FString StageLabel(FName Stage)
{
    for (const auto& Entry : PerformanceStageLabels)
        if (Stage == FName(Entry.Stage)) return Entry.Label;
    return Stage.ToString();
}
}

void UDevelopmentPanelWidget::RefreshPerformanceDiagnostics()
{
    const auto& Snapshot = PerformanceCache;
    if (PerformanceHitches)
    {
        FString Text;
        if (Snapshot.Frames.IsEmpty()) Text = TEXT("暂无完整帧窗口；原始帧号将在 JSON 中保存。");
        else
        {
            Text = FString::Printf(TEXT("帧 %llu–%llu · 峰值帧 %llu\n超预算 %d · >%.2f ms %d · ≥50 ms %d · ≥100 ms %d（累计门槛，不相加）\n始终显示最慢 3 帧；相交分段不等于整帧原因。"),
                Snapshot.Budget.FirstFrameId,Snapshot.Budget.LastFrameId,Snapshot.Budget.PeakFrameId,
                Snapshot.OverBudgetFrames,Snapshot.SlowFrameThresholdMs,Snapshot.SlowFrames,Snapshot.FramesAtLeast50Ms,Snapshot.FramesAtLeast100Ms);
            for (const auto& Frame : Snapshot.SlowestFrames)
            {
                const FFPSPerformanceEvent* Candidate = nullptr;
                double LongestOverlap = 0.0;
                for (const auto& Event : Snapshot.Events)
                {
                    if (Event.bMarker || Event.Stage == FName(TEXT("Icon.Tick"))) continue;
                    const double Overlap = FMath::Min(Event.EndSeconds,Frame.Seconds)-FMath::Max(Event.StartSeconds,Frame.StartSeconds);
                    if (Overlap > LongestOverlap) { Candidate = &Event; LongestOverlap = Overlap; }
                }
                Text += FString::Printf(TEXT("\n#%llu · %.2f ms"),Frame.FrameId,Frame.FrameMs);
                if (Candidate)
                {
                    FString Item = Candidate->Key;
                    int32 Separator = INDEX_NONE;
                    if (Item.FindChar(TEXT('|'),Separator)) Item = Item.Left(Separator);
                    Text += FString::Printf(TEXT(" · 同段 %s %.2f ms · %s"),*StageLabel(Candidate->Stage),LongestOverlap*1000.0,*Item.Left(64));
                }
                else Text += TEXT(" · 无已采集分段相交，其他系统仍未知");
            }
        }
        Text += FString::Printf(TEXT("\n\n近期 ≥50 ms 历史：%d/%d 条 · 清空以来已覆盖 %llu 条（独立于滚动窗口）"),
            Snapshot.RecentHitches.Num(),Snapshot.HitchHistoryCapacity,Snapshot.HitchesOverwritten);
        for (int32 Index = Snapshot.RecentHitches.Num()-1; Index >= FMath::Max(0,Snapshot.RecentHitches.Num()-3); --Index)
        {
            const auto& Hitch = Snapshot.RecentHitches[Index];
            int32 Before = 0, After = 0;
            for (const auto& Frame : Hitch.Frames)
            {
                Before += Frame.FrameId < Hitch.PeakFrameId ? 1 : 0;
                After += Frame.FrameId > Hitch.PeakFrameId ? 1 : 0;
            }
            Text += FString::Printf(TEXT("\n#%llu · %.2f ms · 前 %d / 后 %d 帧 · %d 条相交事件%s"),
                Hitch.PeakFrameId,Hitch.PeakMs,Before,After,Hitch.Events.Num(),
                Hitch.bEventsCapacityLimited?TEXT("（事件已截断）"):TEXT(""));
            if (Before < 2 || After < 2) Text += TEXT(" · 前后文未收齐");
            if (Hitch.ActiveScopesAtContextEnd > 0) Text += TEXT(" · 边界时存在未结束分段");
        }
        Text += FString::Printf(TEXT("\n\n清空以来最严重 ≥50 ms：%d/%d 条（独立保留，与近期记录可能重合）"),
            Snapshot.WorstHitches.Num(),Snapshot.WorstHitchCapacity);
        for (const auto& Hitch : Snapshot.WorstHitches)
            Text += FString::Printf(TEXT("\n#%llu · %.2f ms · 上下文 %d 帧%s"),Hitch.PeakFrameId,Hitch.PeakMs,Hitch.Frames.Num(),
                Hitch.bEventsCapacityLimited?TEXT(" · 事件已截断"):TEXT(""));
        Text += TEXT("\nJSON 去重保留前后读数与事件；线程读数未对齐，不能固定平移一帧。\n历史仅属于当前 World；切图加载间隙尚未纳入统计。");
        if (Snapshot.bEventsCapacityLimited) Text += TEXT("\n事件缓冲已覆盖本窗口内记录，事件不完整。");
        if (Snapshot.EventsDiscardedAtBoundary > 0)
            Text += FString::Printf(TEXT("\n清空/停止边界中断了 %d 个事件，未拼接其耗时。"),Snapshot.EventsDiscardedAtBoundary);
        SetPerformanceText(PerformanceHitches, FText::FromString(Text));
    }
    if (PerformanceIconTasks)
    {
        FString Text;
        const auto& State = Snapshot.IconTask;
        FString FailureDetails;
        if (!State.bAvailable) Text = TEXT("图标子系统：未采集。");
        else
        {
            const TCHAR* StageNames[] = {TEXT("排队/准备"),TEXT("首次预热"),TEXT("查询就绪/最终捕获"),TEXT("异步回读/转换/发布"),TEXT("异步资源加载"),TEXT("分帧准备")};
            Text = FString::Printf(TEXT("快照时状态：队列 %d · 缓存 %d · 失败配方 %d · %s"),
                State.Queued,State.Cached,State.FailedRecipes,State.Queued?StageNames[FMath::Clamp(State.Stage,0,5)]:TEXT("空闲"));
            if (State.Queued)
            {
                Text += FString::Printf(TEXT("\n%s\n请求已等待 %.2f s · 本轮处理已历时 %.2f s（包含跨帧等待）"),*State.Key,State.RequestAgeSeconds,State.AttemptAgeSeconds);
                const TCHAR* WaitLabel = TEXT("无资源等待");
                if (State.WaitReason == FName(TEXT("Warmup"))) WaitLabel = TEXT("首次预热");
                else if (State.WaitReason == FName(TEXT("RenderReadiness"))) WaitLabel = TEXT("渲染线程尚未返回查询");
                else if (State.WaitReason == FName(TEXT("MaterialShader"))) WaitLabel = TEXT("材质着色器未就绪");
                else if (State.WaitReason == FName(TEXT("TextureStreaming"))) WaitLabel = TEXT("纹理正在初始化/流送");
                else if (State.WaitReason == FName(TEXT("TextureNotFullyResident"))) WaitLabel = TEXT("纹理未完全驻留，未见活动流送");
                else if (State.WaitReason == FName(TEXT("RetryCooldown"))) WaitLabel = TEXT("队列正在等待重试间隔");
                else if (State.WaitReason == FName(TEXT("GPUReadback"))) WaitLabel = TEXT("异步 GPU 回读中");
                else if (State.WaitReason == FName(TEXT("PixelConversion"))) WaitLabel = TEXT("后台像素转换中");
                else if (State.WaitReason == FName(TEXT("AsyncResources"))) WaitLabel = TEXT("展示资源异步加载中");
                else if (State.WaitReason == FName(TEXT("PreparationSlices"))) WaitLabel = TEXT("模型/配件/包围盒分帧准备中");
                Text += FString::Printf(TEXT("\n%s · %.2f s%s\n本轮就绪查询 %d · 捕获提交 %d · 此配方已延期 %d 次 · 包围盒缓存%s"),
                    WaitLabel,State.WaitAgeSeconds,State.bMaterialCheckPending?TEXT(" · 异步查询中"):TEXT(""),
                    State.ReadinessPolls,State.CaptureSubmissions,State.DeferredAttempts,State.bBoundsCacheHit?TEXT("命中"):TEXT("未命中"));
                if (!State.WaitResource.IsEmpty()) Text += TEXT("\n首个等待资源：") + State.WaitResource;
                Text += FString::Printf(TEXT("\n冷却配方 %d · 下次可调度 %.2f s"),State.CoolingDownRecipes,State.NextEligibleSeconds);
                if (State.Stage == 3)
                {
                    Text += FString::Printf(TEXT("\n回读流水线已历时 %.3f s（含 GPU 与调度等待）"),State.ReadbackAgeSeconds);
                    if (State.ReadbackCopyMs >= 0.0) Text += FString::Printf(TEXT(" · 后台拷贝 %.3f ms"),State.ReadbackCopyMs);
                    if (State.ReadbackConversionMs >= 0.0) Text += FString::Printf(TEXT(" · 转换 %.3f ms"),State.ReadbackConversionMs);
                }
            }
            if (State.FailedRecipes > 0)
            {
                Text += FString::Printf(TEXT("\n失败详情 %d/%d 条%s；仍使用目录图，清空采样不会重试图标。"),
                    State.RecentFailures.Num(),State.FailedRecipes,State.bFailureDetailsLimited?TEXT("（已达保留容量）"):TEXT(""));
                for (int32 Index = State.RecentFailures.Num()-1; Index >= FMath::Max(0,State.RecentFailures.Num()-3); --Index)
                {
                    const auto& Failure = State.RecentFailures[Index];
                    FString Item = Failure.Recipe;
                    int32 Separator = INDEX_NONE;
                    if (Item.FindChar(TEXT('|'),Separator)) Item = Item.Left(Separator);
                    TArray<FString> Lines;
                    Failure.Reason.ParseIntoArrayLines(Lines,true);
                    const FString Summary = (Lines.IsEmpty()?Failure.Reason:Lines.Last()).TrimStartAndEnd().Left(180);
                    Text += FString::Printf(TEXT("\n%s · %s · %s\n%s%s"),*Item,*Failure.Stage.ToString(),*Failure.OccurredAtUtc,*Summary,
                        Failure.bReasonTruncated?TEXT("（原因已截断）"):TEXT(""));
                    FailureDetails += FString::Printf(TEXT("%s\n阶段 %s · 帧 %llu · UTC %s\n资源 %s\n%s%s\n\n"),
                        *Failure.Recipe,*Failure.Stage.ToString(),Failure.FrameId,*Failure.OccurredAtUtc,
                        Failure.Resource.IsEmpty()?TEXT("未返回资源路径"):*Failure.Resource,*Failure.Reason,
                        Failure.bReasonTruncated?TEXT("\n原始原因超过 2048 字符；完整日志仍在编辑器日志中。"):TEXT(""));
                }
                Text += TEXT("\n显示最近 3 条；悬停查看配方与资源，JSON 保存全部保留详情。");
            }
        }
        if (!State.bAvailable) Text += TEXT("\n窗口动作：图标来源不可用，不按零次解释。");
        else if (Snapshot.Frames.IsEmpty()) Text += TEXT("\n窗口动作：尚无完整采样窗口。");
        else
        {
            const auto Count = [&Snapshot](EFPSIconAction Action) { return Snapshot.IconActions.Values[static_cast<int32>(Action)]; };
            Text += FString::Printf(TEXT("\n窗口动作：请求 %llu · 缓存命中 %llu · 已排队去重 %llu · 失败配方命中 %llu\n新入队 %llu · 完成 %llu · 失败 %llu · 延期 %llu"),
                Count(EFPSIconAction::Request),Count(EFPSIconAction::CacheHit),Count(EFPSIconAction::PendingHit),Count(EFPSIconAction::FailedHit),
                Count(EFPSIconAction::Queued),Count(EFPSIconAction::Completed),Count(EFPSIconAction::Failed),Count(EFPSIconAction::Deferred));
        }
        Text += TEXT("\n\n已采集分段（包含等待和嵌套工作，不相加）：");
        struct FStageTotals { int32 Count = 0; double Sum = 0.0, Peak = 0.0; };
        TMap<FName, FStageTotals> Totals;
        for (const auto& Event : Snapshot.Events)
        {
            if (Event.bMarker || Event.bCrossesWindowStart || Event.bCrossesWindowEnd) continue;
            auto& Total = Totals.FindOrAdd(Event.Stage);
            const double Ms = (Event.EndSeconds - Event.StartSeconds) * 1000.0;
            ++Total.Count; Total.Sum += Ms; Total.Peak = FMath::Max(Total.Peak, Ms);
        }
        for (const auto& Entry : PerformanceStageLabels)
        {
            if (const auto* Total = Totals.Find(FName(Entry.Stage)))
                Text += FString::Printf(TEXT("\n%s：均 %.3f · 峰 %.3f ms [n=%d]"),Entry.Label,Total->Sum/Total->Count,Total->Peak,Total->Count);
        }
        Text += TEXT("\n未列出的分段无完整事件样本；跨窗事件仅在 JSON 保留全长与边界标记。\nSlate 包含编辑器其他窗口；JSON 的 CoreTicker 时间点位于正常引擎循环的帧末同步之后，点前区间不等于纯等待耗时。");
        SetPerformanceText(PerformanceIconTasks, FText::FromString(Text));
        PerformanceIconTasks->SetToolTipText(FText::FromString(FailureDetails));
    }
}
