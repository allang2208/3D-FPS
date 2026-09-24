#include "VoxelBuildWorld.h"
#include "VoxelBuildRuntime.h"
#include "VoxelBuildPersistence.h"
#include "VoxelCollapseFragment.h"
#include "Async/Async.h"

namespace
{
    /**
     * 审计 P13 第 3 条（计划第 5 节决策 2，用户选 (b)：存档合并到 ≥2 s）。
     *
     * 原行为：第一次置脏把截止时间设为 +0.75 s，后续置脏不重置它，所以持续编辑时
     * 每 0.75 s 就做一次**完整快照**（game thread 拷约 450 KB + 一次 GC 跟踪 UObject 分配
     * + 一次 damage map rehash）。
     *
     * 现行为：截止时间取 `max(Now + 0.75, 上次存档开始 + SaveIntervalSeconds)`。
     * 因为「上次存档开始」在一次存档完成前是固定值，这个值不会随每次编辑往前跑；
     * 置脏又由 `if(!bSaveDirty)` 守着不重算，所以连续建造时存档稳定落在约 2 s 一次，
     * 而不是被无限推后（把崩溃丢失窗口从 0.75 s 放宽到约 2 s，换取快照次数降到约三分之一）。
     */
    constexpr double SaveIntervalSeconds=2.0;
    /** 上一次存档**开始**的时刻（用开始时刻，保证间隔是 开始→开始）。 */
    double LastSaveStartedSeconds=0.0;
}

void AVoxelBuildWorld::MarkSaveDirty()
{
    // 注意顺序：先判 bSaveDirty 再置位。本函数在持续编辑时会被**反复调用**，
    // 若每次都重算截止时间，就会一直把 SaveAt 推到 Now 之后 —— TickPersistence 的
    // `Now >= SaveAt` 永远不成立，存档彻底停摆（我第一版就是这样，靠一次调度模拟才发现）。
    // 原实现用 `if(!bSaveDirty)` 起到同样的作用，这里保留该保护，只把截止时间的计算换成
    // "不许早于 上次存档开始 + 最小间隔"。
    if(!Runtime->bSaveDirty)
    {
        const double Now=GetWorld()->GetTimeSeconds();
        // 降频：不早于「上次存档开始 + 最小间隔」，从而把相邻两次完整快照拉开到 2 s。
        Runtime->SaveAt=FMath::Max(Now+.75,LastSaveStartedSeconds+SaveIntervalSeconds);
    }
    Runtime->bSaveDirty=true;
}

bool AVoxelBuildWorld::Save()
{
    if(!bReady||GetNetMode()!=NM_Standalone)return false;
    MarkSaveDirty();Runtime->SaveAt=0;Message=TEXT("建筑保存已排队");return true;
}
bool AVoxelBuildWorld::FlushPersistenceNow()
{
    if(!bReady||GetNetMode()!=NM_Standalone)return false;
    TickPersistence(true);
    if(!Runtime->bSaveFailed)Runtime->bSaveDirty=false;
    return !Runtime->bSaveFailed;
}

UVoxelBuildSave* AVoxelBuildWorld::MakeSnapshot() const
{
    auto* Data=NewObject<UVoxelBuildSave>();Data->WorldKey=WorldKey;Data->Cells.Reserve(Cells.Num());
    for(const auto& E:Cells){auto& C=Data->Cells.AddDefaulted_GetRef();C.Position=E.Key;C.Material=E.Value;}
    for(const auto& E:FreeVolumes)if(!E.Value.Cells.IsEmpty())Data->FreeVolumes.Add(E.Value);
    Data->Prefabs=Prefabs;
    Data->Smelting=SmeltingJobs;
    Data->Fuel=Fuels;
    Data->Damage=CellDamage;Data->LegacyProtected=LegacyProtected;
    for(const auto& B:SupportGraph->Broken)if(!VolumeMaterialAt(B.A.Volume,B.A.Cell).IsNone()&&!VolumeMaterialAt(B.B.Volume,B.B.Cell).IsNone())
        Data->BrokenBonds.Add(B);
    TSet<FGuid> Replaced;
    for(const auto& E:Runtime->PendingFragments)
    {
        const auto& P=*E.Value;
        if(P.Replaces.IsValid())Replaced.Add(P.Replaces);
        // Sources remain in the static save until their mesh handoff commits.
        if(P.Sources.IsEmpty())Data->Fragments.Add(P.State);
    }
    for(const auto& E:Fragments)if(IsValid(E.Value)&&!Replaced.Contains(E.Key))Data->Fragments.Add(E.Value->Snapshot());
    return Data;
}

void AVoxelBuildWorld::TickPersistence(bool bFlush)
{
    if(Runtime->SaveJob.IsValid())
    {
        if(bFlush)Runtime->SaveJob.Wait();
        if(!Runtime->SaveJob.IsReady())return;
        Runtime->bSaveFailed=!Runtime->SaveJob.Get();Runtime->SaveJob=TFuture<bool>();
        if(Runtime->bSaveFailed){Runtime->bSaveDirty=true;Runtime->SaveAt=GetWorld()->GetTimeSeconds()+5;}
    }
    if(bFlush)
    {
        Runtime->bSaveFailed=!VoxelPersistence::Write(SaveSlot,VoxelPersistence::Take(MakeSnapshot()));
        if(Runtime->bSaveFailed)UE_LOG(LogTemp,Error,TEXT("Voxel structure save failed at world shutdown: %s"),*SaveSlot);
        return;
    }
    if(!Runtime->bSaveDirty||GetWorld()->GetTimeSeconds()<Runtime->SaveAt)return;
    // 记录本次存档的开始时刻，供 MarkSaveDirty 做"相邻两次存档至少间隔 N 秒"的降频判定。
    LastSaveStartedSeconds=GetWorld()->GetTimeSeconds();
    auto Payload=VoxelPersistence::Take(MakeSnapshot());Runtime->bSaveDirty=false;
    Runtime->SaveJob=Async(EAsyncExecution::ThreadPool,[Slot=SaveSlot,Payload=MoveTemp(Payload)]() mutable
    {return VoxelPersistence::Write(MoveTemp(Slot),MoveTemp(Payload));});
}
