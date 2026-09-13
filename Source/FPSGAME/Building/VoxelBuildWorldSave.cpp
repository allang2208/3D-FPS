#include "VoxelBuildWorld.h"
#include "VoxelBuildRuntime.h"
#include "VoxelBuildPersistence.h"
#include "VoxelCollapseFragment.h"
#include "Async/Async.h"

void AVoxelBuildWorld::MarkSaveDirty()
{
    if(!Runtime->bSaveDirty)Runtime->SaveAt=GetWorld()->GetTimeSeconds()+.75;
    Runtime->bSaveDirty=true;
}

bool AVoxelBuildWorld::Save()
{
    if(!bReady||GetNetMode()!=NM_Standalone)return false;
    MarkSaveDirty();Runtime->SaveAt=0;Message=TEXT("建筑保存已排队");return true;
}

UVoxelBuildSave* AVoxelBuildWorld::MakeSnapshot() const
{
    auto* Data=NewObject<UVoxelBuildSave>();Data->WorldKey=WorldKey;Data->Cells.Reserve(Cells.Num());
    for(const auto& E:Cells){auto& C=Data->Cells.AddDefaulted_GetRef();C.Position=E.Key;C.Material=E.Value;}
    for(const auto& E:FreeVolumes)if(!E.Value.Cells.IsEmpty())Data->FreeVolumes.Add(E.Value);
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
    auto Payload=VoxelPersistence::Take(MakeSnapshot());Runtime->bSaveDirty=false;
    Runtime->SaveJob=Async(EAsyncExecution::ThreadPool,[Slot=SaveSlot,Payload=MoveTemp(Payload)]() mutable
    {return VoxelPersistence::Write(MoveTemp(Slot),MoveTemp(Payload));});
}
