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
        bool Stale=false;
        for(const auto& E:Runtime->JobEpoch)if(Runtime->NodeEpoch.FindRef(E.Key)!=E.Value){Stale=true;break;}
        Runtime->JobEpoch.Reset();
        if(Stale)
        {
            Runtime->DirtySupport.Append(Runtime->JobKeys);Runtime->JobKeys.Reset();return;
        }
        Runtime->JobKeys.Reset();Runtime->bStressApproximate=!Result.bConverged;
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
        bool bHeldBack=false,bBroke=false;
        TArray<FVoxelEditCell> Crushed;
        for(const auto& Key:Result.Crushed)if(!Runtime->PendingCells.Contains(Key))
        {
            // Standing structure is never the part that fails; the batch above it is (handled below).
            if(bProtecting&&!Fresh.Contains(Key)){bHeldBack=true;continue;}
            const FName Material=VolumeMaterialAt(Key.Volume,Key.Cell);
            if(!Material.IsNone())Crushed.Add({Key.Cell,Material,NAME_None,Key.Volume});
        }
        for(const auto& Bond:Result.Broken)
        {
            // Only joints that involve the fresh batch may fail; two standing cells keep their bond.
            if(bProtecting&&!Fresh.Contains(Bond.A)&&!Fresh.Contains(Bond.B)){bHeldBack=true;continue;}
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
            FVoxelFragmentSave State;State.Id=FGuid::NewGuid();FBox Bounds(ForceInit);
            for(const auto& Node:Island){Bounds+=Node.Min;Bounds+=Node.Min+FVector(20);}
            const FVector Origin=Bounds.GetCenter();State.Transform=FTransform(Origin);
            TArray<FVoxelBuildKey> Keys;
            for(const auto& Node:Island)
            {State.Cells.Add({Node.Key,Node.Min-Origin,Node.Material,Node.Damage});Keys.Add(Node.Key);}
            EnqueueFragment(MoveTemp(State),MoveTemp(Keys));History.Reset();
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
                EnqueueFragment(MoveTemp(State),MoveTemp(Keys));
            }
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
        Runtime->GatherRevision=Revision;
        for(const auto& Key:Runtime->DirtySupport)if(SupportGraph->Nodes.Contains(Key)&&!Runtime->PendingCells.Contains(Key))
        {Runtime->GatherQueue.Add(Key);Runtime->GatherSeen.Add(Key);}
        if(Runtime->GatherQueue.IsEmpty()){Runtime->DirtySupport.Reset();return;}
        Runtime->Gather.Revision=Revision;Runtime->Gather.Iterations=Runtime->NextIterations;
        Runtime->Gather.GravityMS2=GetWorld()->GetGravityZ()*.01f;
        Runtime->Gather.Broken=SupportGraph->Broken;
    }
    const double Start=FPlatformTime::Seconds();int32 Count=0;
    while(Runtime->GatherRead<Runtime->GatherQueue.Num())
    {
        const auto Key=Runtime->GatherQueue[Runtime->GatherRead++];const auto* Node=SupportGraph->Nodes.Find(Key);
        if(!Node||Runtime->PendingCells.Contains(Key))continue;
        Runtime->Gather.Nodes.Add(*Node);LegacyProtected.Remove(Key);
        if(const auto* Next=SupportGraph->Edges.Find(Key))for(const auto& Other:*Next)
            if(!Runtime->GatherSeen.Contains(Other)&&!Runtime->PendingCells.Contains(Other))
            {Runtime->GatherSeen.Add(Other);Runtime->GatherQueue.Add(Other);}
        if(++Count>=512||FPlatformTime::Seconds()-Start>.001)break;
    }
    if(Runtime->GatherRead<Runtime->GatherQueue.Num())return;
    Runtime->JobKeys=MoveTemp(Runtime->GatherSeen);Runtime->DirtySupport.Reset();Runtime->GatherQueue.Reset();
    Runtime->JobEpoch.Reset();for(const auto& Key:Runtime->JobKeys)Runtime->JobEpoch.Add(Key,Runtime->NodeEpoch.FindRef(Key));
    Runtime->Stress=Async(EAsyncExecution::ThreadPool,[Input=MoveTemp(Runtime->Gather)]() mutable
    {return VoxelStress::Solve(MoveTemp(Input));});
}
