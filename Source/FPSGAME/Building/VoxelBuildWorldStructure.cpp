#include "VoxelBuildWorld.h"
#include "VoxelBuildRuntime.h"
#include "Async/Async.h"

void AVoxelBuildWorld::TickStructure()
{
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
        TArray<FVoxelEditCell> Crushed;
        for(const auto& Key:Result.Crushed)if(!Runtime->PendingCells.Contains(Key))
        {
            const FName Material=VolumeMaterialAt(Key.Volume,Key.Cell);
            if(!Material.IsNone())Crushed.Add({Key.Cell,Material,NAME_None,Key.Volume});
        }
        for(const auto& Bond:Result.Broken)
        {
            SupportGraph->Break(Bond);Runtime->DirtySupport.Add(Bond.A);Runtime->DirtySupport.Add(Bond.B);
            Runtime->NodeEpoch.Add(Bond.A,Revision+1);Runtime->NodeEpoch.Add(Bond.B,Revision+1);
        }
        if(!Result.Broken.IsEmpty())
        {++Revision;History.Reset();MarkSaveDirty();Runtime->NextIterations=256;}
        if(!Crushed.IsEmpty()){History.Reset();ApplyChanges(Crushed);}
        for(auto& Island:Result.Detached)
        {
            bool Pending=false;for(const auto& Node:Island)Pending|=Runtime->PendingCells.Contains(Node.Key);
            if(Pending||Island.IsEmpty())continue;
            FVoxelFragmentSave State;State.Id=FGuid::NewGuid();FBox Bounds(ForceInit);
            for(const auto& Node:Island){Bounds+=Node.Min;Bounds+=Node.Min+FVector(20);}
            const FVector Origin=Bounds.GetCenter();State.Transform=FTransform(Origin);
            TArray<FVoxelBuildKey> Keys;
            for(const auto& Node:Island)
            {State.Cells.Add({Node.Key,Node.Min-Origin,Node.Material,Node.Damage});Keys.Add(Node.Key);}
            EnqueueFragment(MoveTemp(State),MoveTemp(Keys));History.Reset();
        }
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
