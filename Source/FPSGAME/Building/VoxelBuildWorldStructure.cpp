#include "VoxelBuildWorld.h"
#include "VoxelBuildRuntime.h"
#include "Async/Async.h"
#include "HAL/IConsoleManager.h"

namespace
{
    // How long a freshly placed batch keeps the "only the new part may collapse" rule. Long enough
    // for the settling solves that follow a commit, short enough that combat damage and later
    // overloads behave normally again. See Docs/Building/voxel-build-workflow.md 3.6.
    TAutoConsoleVariable<float> FreshWindowCVar(TEXT("fps.Building.FreshProtectionSeconds"),3.f,
        TEXT("Seconds after a placement during which only the newly added voxels may collapse."));
    // 过载渐进损伤（2026-09-16）：过载不再瞬间断键，而是按时间累积损伤，损伤满耐久才掉块。
    // 30 s 是"刚好过线"的时限上限，越超载越快（最低 3 s）；三种材质时间一致。
    TAutoConsoleVariable<float> OverloadGraceCVar(TEXT("fps.Building.OverloadGraceSeconds"),30.f,
        TEXT("Sustained-overload seconds to failure at ratio 1.0 (ceiling for mild overloads)."));
    TAutoConsoleVariable<float> OverloadMinCVar(TEXT("fps.Building.OverloadMinSeconds"),3.f,
        TEXT("Fastest overload failure time, used by heavy overloads."));
    TAutoConsoleVariable<float> OverloadTickCVar(TEXT("fps.Building.OverloadTickSeconds"),.5f,
        TEXT("Re-solve interval while a structure is overloaded, so damage keeps accumulating."));
    // 2026-09-16 简化：一次解算最多收集这么多连通节点；超过时只解变化附近的一块，边界视为固定
    // 支撑（fps.Building.MaxSolveNodes 可调，默认对当前规模完全不影响，超大城堡才有差别）。
    TAutoConsoleVariable<int32> MaxSolveNodesCVar(TEXT("fps.Building.MaxSolveNodes"),4096,
        TEXT("Maximum connected nodes gathered into one stress solve; the rest is treated as boundary."));
    // 活跃子图裁剪（2026-09-16）：只解算"改动/荷载/接近极限"附近 SolveRegionHops 格以内的一块，
    // 边界当固定支撑；每隔 FullSolveIntervalSeconds 做一次全量解算兜底，避免误差长期累积。
    TAutoConsoleVariable<int32> SolveRegionHopsCVar(TEXT("fps.Building.SolveRegionHops"),24,
        TEXT("Cells of graph distance solved around the dirty region; 0 = always solve everything."));
    TAutoConsoleVariable<float> FullSolveIntervalCVar(TEXT("fps.Building.FullSolveIntervalSeconds"),5.f,
        TEXT("Seconds between full-structure solves that backstop the pruned region."));
    TAutoConsoleVariable<float> LoadedSeedCVar(TEXT("fps.Building.SolveSeedUtilization"),.6f,
        TEXT("Joints at or above this utilisation also seed the solved region."));
}

void AVoxelBuildWorld::ApplyOverloadDamage(const TArray<FVoxelOverloadCell>& Overload,double Seconds)
{
    if(Overload.IsEmpty()||Seconds<=0.)return;
    TArray<FVoxelEditCell> Removed;bool bChanged=false;
    for(const FVoxelOverloadCell& Entry:Overload)
    {
        if(Runtime->PendingCells.Contains(Entry.Key))continue;
        const FName Material=VolumeMaterialAt(Entry.Key.Volume,Entry.Key.Cell);
        if(Material.IsNone()){CellDamage.Remove(Entry.Key);continue;}
        const FVoxelPhysicalMaterial Physics=Palette->Physical(Material);
        const float Damage=CellDamage.FindRef(Entry.Key)+Entry.RatePerSecond*float(Seconds);
        // 损伤满耐久 = 这一格承受不住：按摧毁处理，走既有倒塌/残骸流程。
        if(Damage>=Physics.Durability)
        {CellDamage.Remove(Entry.Key);Removed.Add({Entry.Key.Cell,Material,NAME_None,Entry.Key.Volume});bChanged=true;continue;}
        CellDamage.Add(Entry.Key,Damage);
        if(auto* Node=SupportGraph->Nodes.Find(Entry.Key))Node->Damage=Damage;
        if(!LegacyProtected.Contains(Entry.Key))Runtime->DirtySupport.Add(Entry.Key);
        Runtime->NodeEpoch.Add(Entry.Key,Revision+1);
        bChanged=true;
    }
    if(!Removed.IsEmpty()){History.Reset();ApplyChanges(Removed);}
    // 审计 C9：累加中的损伤以前没有置脏——只有"损伤满耐久→摧毁"走 ApplyChanges 才落盘，
    // 所以"被打伤但没打掉"的格其损伤值只靠 EndPlay 的无条件 flush 才写得下去（崩溃即丢失）。
    // 对照伤害路径 VoxelBuildWorldDamage.cpp 是有 MarkSaveDirty() 的。
    else if(bChanged)MarkSaveDirty();
    // 还有过载格在受伤：安排下一次解算，让损伤继续累积、面板占比随之上升。
    if(bChanged)Runtime->StructureAt=GetWorld()->GetTimeSeconds()+OverloadTickCVar.GetValueOnGameThread();
}

void AVoxelBuildWorld::TickStructure()
{
    // The fresh-placement protection is a time box, checked on every tick (not only when a solve has
    // just landed) so neither the immunity nor its status line can outlive the window.
    if(!Runtime->FreshCells.IsEmpty()&&GetWorld()->GetTimeSeconds()>Runtime->FreshAt+FreshWindowCVar.GetValueOnGameThread())
    {Runtime->FreshCells.Reset();Runtime->bFreshRolledBack=false;}
    if(Runtime->Stress.IsValid())
    {
        if(!Runtime->Stress.IsReady())return;
        auto Result=Runtime->Stress.Get();Runtime->Stress=TFuture<FVoxelStressResult>();
        Runtime->LastSolveSeconds=float(FPlatformTime::Seconds()-Runtime->SolveStartedAt);
        if(Runtime->bGatherFullSolve)Runtime->LastFullSolveAt=GetWorld()->GetTimeSeconds();
        bool Stale=false;
        for(const auto& E:Runtime->JobEpoch)if(Runtime->NodeEpoch.FindRef(E.Key)!=E.Value){Stale=true;break;}
        Runtime->JobEpoch.Reset();
        if(Stale)
        {
            Runtime->DirtySupport.Append(Runtime->JobKeys);Runtime->JobKeys.Reset();return;
        }
        Runtime->JobKeys.Reset();Runtime->bStressApproximate=!Result.bConverged;
        Runtime->WorstBond=Result.WorstBond;
        for(const auto& Key:Result.Evaluated)
        {
            if(Result.Supported.Contains(Key))SupportGraph->Supported.Add(Key);else SupportGraph->Supported.Remove(Key);
            Runtime->LoadRatios.Add(Key,Result.LoadRatios.FindRef(Key));
        }
        if(!Result.bConverged&&Result.Iterations<2048)
        {Runtime->DirtySupport.Append(Result.Evaluated);Runtime->NextIterations=Result.Iterations*2;}
        // 3.6 Build-failure isolation: only the batch that was just placed is allowed to fail on its
        // own placement. Everything the solver wants to crush, unstitch or drop outside that batch is
        // held back, and the batch itself is dropped as debris, so a failed placement can never take
        // the structure that was already standing down with it. Outside the window the normal
        // collapse rules apply unchanged.
        const bool bProtecting=!Runtime->FreshCells.IsEmpty();
        TSet<FVoxelBuildKey> Fresh;
        if(bProtecting)for(const auto& Key:Runtime->FreshCells)
            if(SupportGraph->Nodes.Contains(Key)&&!Runtime->PendingCells.Contains(Key))Fresh.Add(Key);
        // 过载渐进损伤：保护窗口内不动既有结构（仍按原逻辑回退新件），窗口外按时间累积损伤。
        if(!bProtecting)
        {
            const double Now=GetWorld()->GetTimeSeconds();
            ApplyOverloadDamage(Result.Overload,Runtime->OverloadAt>0?FMath::Min(Now-Runtime->OverloadAt,.5):0.);
            Runtime->OverloadAt=Now;
        }
        bool bHeldBack=false,bBroke=false;
        TArray<FVoxelEditCell> Crushed;
        for(const auto& Key:Result.Crushed)if(!Runtime->PendingCells.Contains(Key))
        {
            // 窗口外：过载不再瞬间压坏，交给 ApplyOverloadDamage 按时间累积损伤（2026-09-16）。
            if(!bProtecting)continue;
            // Standing structure is never the part that fails; the batch above it is (handled below).
            if(!Fresh.Contains(Key)){bHeldBack=true;continue;}
            const FName Material=VolumeMaterialAt(Key.Volume,Key.Cell);
            if(!Material.IsNone())Crushed.Add({Key.Cell,Material,NAME_None,Key.Volume});
        }
        for(const auto& Bond:Result.Broken)
        {
            // 窗口外：接缝不再瞬间断开，改由渐进损伤在耐久耗尽时掉块（2026-09-16）。
            if(!bProtecting)continue;
            // Only joints that involve the fresh batch may fail; two standing cells keep their bond.
            if(!Fresh.Contains(Bond.A)&&!Fresh.Contains(Bond.B)){bHeldBack=true;continue;}
            SupportGraph->Break(Bond);Runtime->DirtySupport.Add(Bond.A);Runtime->DirtySupport.Add(Bond.B);
            Runtime->NodeEpoch.Add(Bond.A,Revision+1);Runtime->NodeEpoch.Add(Bond.B,Revision+1);bBroke=true;
        }
        if(bBroke)
        {++Revision;History.Reset();MarkSaveDirty();Runtime->NextIterations=256;}
        for(auto& Island:Result.Detached)
        {
            bool Pending=false;for(const auto& Node:Island)Pending|=Runtime->PendingCells.Contains(Node.Key);
            if(Pending||Island.IsEmpty())continue;
            // A component that still contains standing cells must not fall because of a fresh build.
            bool bStanding=false;for(const auto& Node:Island)bStanding|=!Fresh.Contains(Node.Key);
            if(bProtecting&&bStanding){bHeldBack=true;continue;}
            // While the fresh window is open this island is the placement that just failed, so it
            // falls as failure debris (no impact damage on the standing structure).
            Runtime->FailureBond=Result.WorstBond;
            FVoxelFragmentSave State;State.Id=FGuid::NewGuid();FBox Bounds(ForceInit);
            for(const auto& Node:Island){Bounds+=Node.Min;Bounds+=Node.Min+FVector(20);}
            const FVector Origin=Bounds.GetCenter();State.Transform=FTransform(Origin);
            TArray<FVoxelBuildKey> Keys;
            for(const auto& Node:Island)
            {State.Cells.Add({Node.Key,Node.Min-Origin,Node.Material,Node.Damage});Keys.Add(Node.Key);}
            // Fresh-window islands are the failed placement falling off, not a structural collapse.
            EnqueueFragment(MoveTemp(State),MoveTemp(Keys),{},bProtecting);History.Reset();
        }
        if(bHeldBack)
        {
            // The placement itself is the part that fails: drop the whole batch as debris so the new
            // blocks visibly come down while the standing structure is left untouched.
            Crushed.Reset();
            TArray<FVoxelBuildKey> Rollback;
            for(const auto& Key:Fresh)if(!Runtime->PendingCells.Contains(Key))Rollback.Add(Key);
            if(!Rollback.IsEmpty())
            {
                FVoxelFragmentSave State;State.Id=FGuid::NewGuid();FBox Bounds(ForceInit);
                for(const auto& Key:Rollback){const auto& Node=SupportGraph->Nodes.FindChecked(Key);Bounds+=Node.Min;Bounds+=Node.Min+FVector(20);}
                const FVector Origin=Bounds.GetCenter();State.Transform=FTransform(Origin);
                TArray<FVoxelBuildKey> Keys;
                for(const auto& Key:Rollback)
                {const auto& Node=SupportGraph->Nodes.FindChecked(Key);
                    State.Cells.Add({Key,Node.Min-Origin,Node.Material,Node.Damage});Keys.Add(Key);}
                // Placement failure debris: it may fall on the player's head, but it must never chew
                // through the wall that is already standing (2026-09-16 damage spiral).
                EnqueueFragment(MoveTemp(State),MoveTemp(Keys),{},true);
            }
            Runtime->FailureBond=Result.WorstBond;
            UE_LOG(LogTemp,Warning,TEXT("VOXEL_FRESH rollback batch=%d rolled=%d"),
                Runtime->FreshCells.Num(),Rollback.Num());
            Runtime->bFreshRolledBack=true;History.Reset();
        }
        else if(!Crushed.IsEmpty()){History.Reset();ApplyChanges(Crushed);}
        // The batch is settled once one converged solve comes back completely clean: nothing was held
        // back and nothing about the new part failed. Until then every result stays filtered, because a
        // break or a crush can only show up on the solve that follows the one that caused it.
        if(bProtecting&&Result.bConverged&&Result.Crushed.IsEmpty()&&Result.Broken.IsEmpty()&&Result.Detached.IsEmpty())
        {Runtime->FreshCells.Reset();Runtime->bFreshRolledBack=false;}
    }
    if(Runtime->DirtySupport.IsEmpty()&&Runtime->GatherQueue.IsEmpty())return;
    if(GetWorld()->GetTimeSeconds()<Runtime->StructureAt)return;
    if(Runtime->GatherRevision!=Revision||Runtime->GatherQueue.IsEmpty())
    {
        // A changed topology invalidates the partially gathered snapshot, but
        // its seeds remain dirty until a matching result has been published.
        Runtime->Gather={};Runtime->GatherQueue.Reset();Runtime->GatherSeen.Reset();Runtime->GatherRead=0;
        Runtime->GatherHops.Reset();
        Runtime->GatherRevision=Revision;
        // 全量兜底：距离上次全量解算超过间隔就这次全解，否则只解改动附近。
        const double Now=GetWorld()->GetTimeSeconds();
        Runtime->bGatherFullSolve=SolveRegionHopsCVar.GetValueOnGameThread()<=0
            ||Now-Runtime->LastFullSolveAt>=FMath::Max(1.f,FullSolveIntervalCVar.GetValueOnGameThread());
        auto Seed=[&](const FVoxelBuildKey& Key)
        {
            if(Runtime->GatherSeen.Contains(Key)||!SupportGraph->Nodes.Contains(Key)||Runtime->PendingCells.Contains(Key))return;
            Runtime->GatherQueue.Add(Key);Runtime->GatherSeen.Add(Key);Runtime->GatherHops.Add(Key,0);
        };
        for(const auto& Key:Runtime->DirtySupport)Seed(Key);
        // 已登记的活荷载本身就是脏源（角色/道具落在建筑上、结构自重之外的外力）。
        for(const TPair<FName,FVoxelExternalLoad>& Load:Runtime->Loads)Seed(Load.Value.Key);
        // 已经接近极限的接缝也要作种子，否则远处的改动传不到它、面板读数会失真；上限 256 防止种子爆炸。
        if(!Runtime->bGatherFullSolve)
        {
            int32 Extra=0;const float Threshold=LoadedSeedCVar.GetValueOnGameThread();
            for(const TPair<FVoxelBuildKey,float>& Entry:Runtime->LoadRatios)
            {
                if(Entry.Value<Threshold)continue;
                Seed(Entry.Key);
                if(++Extra>=256)break;
            }
        }
        if(Runtime->GatherQueue.IsEmpty()){Runtime->DirtySupport.Reset();return;}
    Runtime->Gather.Revision=Revision;Runtime->Gather.Iterations=Runtime->NextIterations;
    Runtime->Gather.GravityMS2=GetWorld()->GetGravityZ()*.01f;
    Runtime->Gather.OverloadGraceSeconds=OverloadGraceCVar.GetValueOnGameThread();
    Runtime->Gather.OverloadMinSeconds=OverloadMinCVar.GetValueOnGameThread();
        Runtime->Gather.Broken=SupportGraph->Broken;
    }
    const double Start=FPlatformTime::Seconds();int32 Count=0;
    const int32 NodeCap=FMath::Max(64,MaxSolveNodesCVar.GetValueOnGameThread());
    const int32 HopLimit=Runtime->bGatherFullSolve?MAX_int32:FMath::Max(4,SolveRegionHopsCVar.GetValueOnGameThread());
    while(Runtime->GatherRead<Runtime->GatherQueue.Num())
    {
        const auto Key=Runtime->GatherQueue[Runtime->GatherRead++];const auto* Node=SupportGraph->Nodes.Find(Key);
        if(!Node||Runtime->PendingCells.Contains(Key))continue;
        Runtime->Gather.Nodes.Add(*Node);LegacyProtected.Remove(Key);
        const int32 Depth=Runtime->GatherHops.FindRef(Key);
        // 到达裁剪半径：邻居只作为固定支撑（边界），继续解下去就等于全量了。
        if(Depth>=HopLimit)
        {
            if(const auto* Next=SupportGraph->Edges.Find(Key))for(const auto& Other:*Next)
                if(!Runtime->GatherSeen.Contains(Other)&&!Runtime->PendingCells.Contains(Other))
                    Runtime->Gather.Boundary.Add(Other);
            continue;
        }
        if(const auto* Next=SupportGraph->Edges.Find(Key))for(const auto& Other:*Next)
            if(!Runtime->GatherSeen.Contains(Other)&&!Runtime->PendingCells.Contains(Other))
            {Runtime->GatherSeen.Add(Other);Runtime->GatherQueue.Add(Other);Runtime->GatherHops.Add(Other,Depth+1);}
        // 达到节点上限：停下并把还没收进来的邻居标成边界（视为固定支撑），不再整块解算。
        if(++Count>=NodeCap)
        {
            if(const auto* Next=SupportGraph->Edges.Find(Key))for(const auto& Other:*Next)
                if(!Runtime->GatherSeen.Contains(Other)&&!Runtime->PendingCells.Contains(Other))
                    Runtime->Gather.Boundary.Add(Other);
            Runtime->GatherRead=Runtime->GatherQueue.Num();
            break;
        }
        if(Count>=512&&FPlatformTime::Seconds()-Start>.001)break;   // 帧预算：下一帧接着收
    }
    if(Runtime->GatherRead<Runtime->GatherQueue.Num())return;
    Runtime->JobKeys=MoveTemp(Runtime->GatherSeen);Runtime->DirtySupport.Reset();Runtime->GatherQueue.Reset();
    Runtime->JobEpoch.Reset();for(const auto& Key:Runtime->JobKeys)Runtime->JobEpoch.Add(Key,Runtime->NodeEpoch.FindRef(Key));
    // 求解观测：节点数/边界数现在就记，耗时在结果回来时补上。
    Runtime->LastSolveNodes=Runtime->Gather.Nodes.Num();
    Runtime->LastSolveBoundary=Runtime->Gather.Boundary.Num();
    Runtime->SolveStartedAt=FPlatformTime::Seconds();
    Runtime->Stress=Async(EAsyncExecution::ThreadPool,[Input=MoveTemp(Runtime->Gather)]() mutable
    {return VoxelStress::Solve(MoveTemp(Input));});
}
