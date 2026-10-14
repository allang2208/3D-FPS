#include "FPSPerformanceMetrics.h"
#include "Async/Async.h"
#include "Dom/JsonObject.h"
#include "RHI.h"
#include "RenderingThread.h"
#include "RHICommandList.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace
{
struct FResourceGroup
{
    uint64 Bytes=0, NonTransientBytes=0, ResidentFlagBytes=0;
    int32 Count=0;
    void Add(const FRHIResourceStats& R)
    {
        Bytes+=R.SizeInBytes; ++Count;
        if(!R.bTransient)NonTransientBytes+=R.SizeInBytes;
        if(R.bResident)ResidentFlagBytes+=R.SizeInBytes;
    }
};

TUniquePtr<FJsonObject> BuildInventory(const TArray<TSharedPtr<FRHIResourceStats>>& Stats)
{
    auto Result=MakeUnique<FJsonObject>();
    TMap<FString,FResourceGroup> ByType, ByOwner;
    FResourceGroup Total;
    int32 UnknownOwner=0;
    uint64 UnknownOwnerBytes=0;
    TArray<TSharedPtr<FJsonValue>> Rows;
    constexpr int32 MaxRows=128, MaxOwners=64;
    // Engine returns resources sorted by allocation size. Aggregate all entries
    // before truncating the exported detail, on a worker after releasing its lock.
    for(const auto& Ptr:Stats)
    {
        if(!Ptr)continue;
        const auto& R=*Ptr;
        Total.Add(R); ByType.FindOrAdd(R.Type).Add(R);
        const FString Owner=R.OwnerName.IsNone()?TEXT("<untracked owner>"):R.OwnerName.ToString();
        ByOwner.FindOrAdd(Owner).Add(R);
        if(R.OwnerName.IsNone()){++UnknownOwner;UnknownOwnerBytes+=R.SizeInBytes;}
        if(Rows.Num()>=MaxRows)continue;
        auto Row=MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("name"),R.Name.ToString());
        if(R.OwnerName.IsNone())Row->SetField(TEXT("owner"),MakeShared<FJsonValueNull>());
        else Row->SetStringField(TEXT("owner"),Owner);
        Row->SetStringField(TEXT("type"),R.Type); Row->SetStringField(TEXT("flags"),R.Flags);
        Row->SetNumberField(TEXT("allocation_bytes"),double(R.SizeInBytes));
        Row->SetBoolField(TEXT("resident_flag"),R.bResident);
        Row->SetBoolField(TEXT("has_flags"),R.bHasFlags);
        Row->SetBoolField(TEXT("transient"),R.bTransient);
        Row->SetBoolField(TEXT("streamable"),R.bStreaming);
        Row->SetBoolField(TEXT("render_target"),R.bRenderTarget);
        Row->SetBoolField(TEXT("depth_stencil"),R.bDepthStencil);
        Row->SetBoolField(TEXT("uav"),R.bUnorderedAccessView);
        Row->SetBoolField(TEXT("ray_tracing_acceleration_structure"),R.bRayTracingAccelerationStructure);
        Row->SetBoolField(TEXT("marked_for_delete"),R.bMarkedForDelete);
        Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    auto GroupRows=[](const TMap<FString,FResourceGroup>& Groups,int32 Limit)
    {
        TArray<FString> Keys; Groups.GetKeys(Keys);
        Keys.Sort([&Groups](const FString& A,const FString& B){return Groups[A].Bytes>Groups[B].Bytes;});
        TArray<TSharedPtr<FJsonValue>> Out;
        for(int32 I=0;I<FMath::Min(Keys.Num(),Limit);++I)
        {
            const auto& G=Groups[Keys[I]];auto Row=MakeShared<FJsonObject>();
            Row->SetStringField(TEXT("key"),Keys[I]);Row->SetNumberField(TEXT("resource_count"),G.Count);
            Row->SetNumberField(TEXT("allocation_bytes"),double(G.Bytes));
            Row->SetNumberField(TEXT("non_transient_allocation_bytes"),double(G.NonTransientBytes));
            Row->SetNumberField(TEXT("resident_flag_allocation_bytes"),double(G.ResidentFlagBytes));
            Out.Add(MakeShared<FJsonValueObject>(Row));
        }
        return Out;
    };
    Result->SetStringField(TEXT("status"),Stats.IsEmpty()?TEXT("no_tracked_resources"):TEXT("captured"));
    Result->SetNumberField(TEXT("tracked_resource_count"),Total.Count);
    Result->SetNumberField(TEXT("allocation_bytes"),double(Total.Bytes));
    Result->SetNumberField(TEXT("non_transient_allocation_bytes"),double(Total.NonTransientBytes));
    Result->SetNumberField(TEXT("resident_flag_allocation_bytes"),double(Total.ResidentFlagBytes));
    Result->SetNumberField(TEXT("unknown_owner_count"),UnknownOwner);
    Result->SetNumberField(TEXT("unknown_owner_allocation_bytes"),double(UnknownOwnerBytes));
    Result->SetNumberField(TEXT("owner_group_count"),ByOwner.Num());
    Result->SetBoolField(TEXT("resource_details_truncated"),Total.Count>MaxRows);
    Result->SetBoolField(TEXT("owner_details_truncated"),ByOwner.Num()>MaxOwners);
    Result->SetArrayField(TEXT("top_resources"),Rows);
    Result->SetArrayField(TEXT("by_type"),GroupRows(ByType,64));
    Result->SetArrayField(TEXT("top_owners"),GroupRows(ByOwner,MaxOwners));
    return Result;
}
}

void UFPSPerformanceMetricsSubsystem::PumpGpuResourceInventory(double Now)
{
    if(!IsGpuInventoryEnabled()){GpuInventoryRequests.Reset();return;}
    if(bGpuInventoryPending || GpuInventoryRequests.IsEmpty() || Now<NextGpuInventorySeconds
        || Now<GpuInventoryRequests[0].Due)return;
    const auto Request=GpuInventoryRequests[0];GpuInventoryRequests.RemoveAt(0);
    bGpuInventoryPending=true;NextGpuInventorySeconds=Now+5.;
    const uint64 Generation=CaptureGeneration;
    const TWeakObjectPtr<UFPSPerformanceMetricsSubsystem> WeakThis(this);
    RecordMarker(this,TEXT("Observer.GpuInventoryQueued"),Request.Reason,true);
    ENQUEUE_RENDER_COMMAND(FPSGpuInventory)([WeakThis,Generation,Request](FRHICommandListImmediate&)
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Perf_GpuInventoryEnumeration);
        const double Begin=FPlatformTime::Seconds();
        const uint64 RenderFrame=GFrameNumberRenderThread;
        TArray<TSharedPtr<FRHIResourceStats>> Stats;
#if RHI_ENABLE_RESOURCE_INFO
        RHIGetTrackedResourceStats(Stats);
#endif
        const double End=FPlatformTime::Seconds();
        Async(EAsyncExecution::ThreadPool,[WeakThis,Generation,Request,Begin,End,RenderFrame,Stats=MoveTemp(Stats)]() mutable
        {
            const double AggregateBegin=FPlatformTime::Seconds();
            auto Row=BuildInventory(Stats);
#if !RHI_ENABLE_RESOURCE_INFO
            Row->SetStringField(TEXT("status"),TEXT("resource_tracking_not_compiled"));
#endif
            Row->SetStringField(TEXT("reason"),Request.Reason);
            Row->SetStringField(TEXT("requested_engine_frame"),LexToString(Request.RequestedFrame));
            Row->SetStringField(TEXT("collection_render_frame"),LexToString(RenderFrame));
            Row->SetNumberField(TEXT("requested_seconds"),Request.RequestedSeconds);
            Row->SetNumberField(TEXT("scheduled_seconds"),Request.Due);
            Row->SetNumberField(TEXT("enumeration_start_seconds"),Begin);
            Row->SetNumberField(TEXT("enumeration_end_seconds"),End);
            Row->SetNumberField(TEXT("enumeration_ms"),(End-Begin)*1000.);
            Row->SetNumberField(TEXT("worker_aggregation_ms"),(FPlatformTime::Seconds()-AggregateBegin)*1000.);
            AsyncTask(ENamedThreads::GameThread,[WeakThis,Generation,Row=MoveTemp(Row)]() mutable
            {
                auto* Self=WeakThis.Get();
                if(!Self || Self->CaptureGeneration!=Generation)return;
                Self->bGpuInventoryPending=false;
                if(!Self->bRecording)return;
                Row->SetNumberField(TEXT("published_seconds"),FPlatformTime::Seconds());
                if(Self->GpuResourceInventories.Num()>=MaxGpuInventories)
                {Self->GpuResourceInventories.RemoveAt(0);++Self->GpuInventoriesOverwritten;}
                Self->GpuResourceInventories.Add(MakeShareable(Row.Release()));
            });
        });
    });
}
