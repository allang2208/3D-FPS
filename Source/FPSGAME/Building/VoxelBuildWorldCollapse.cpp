#include "VoxelBuildWorld.h"
#include "VoxelBuildRuntime.h"
#include "VoxelBuildPalette.h"
#include "VoxelCollapseFragment.h"
#include "Async/Async.h"
#include "HAL/IConsoleManager.h"
#include "GameFramework/WorldSettings.h"

namespace
{
    TAutoConsoleVariable<int32> Bodies(TEXT("fps.Building.MaxActiveBodies"),128,TEXT("Admission budget for newly activated collapse bodies."));
    TAutoConsoleVariable<int32> Shapes(TEXT("fps.Building.MaxActiveShapes"),2048,TEXT("Admission budget for active compound shapes."));
    TAutoConsoleVariable<int32> SpawnLimit(TEXT("fps.Building.SpawnsPerFrame"),8,TEXT("Maximum prepared fragment Actor creations per frame."));
    TAutoConsoleVariable<int32> ShapesPerBody(TEXT("fps.Building.ShapesPerBody"),64,TEXT("Maximum compound boxes per prepared piece."));
}

void AVoxelBuildWorld::EnqueueFragment(FVoxelFragmentSave State,TArray<FVoxelBuildKey> Sources,FGuid Replaces)
{
    if(State.Cells.IsEmpty())return;
    auto Pending=MakeShared<FVoxelPendingFragment>();Pending->State=MoveTemp(State);Pending->Sources=MoveTemp(Sources);Pending->Replaces=Replaces;
    for(const auto& Key:Pending->Sources)Runtime->PendingCells.Add(Key);
    Runtime->PendingFragments.Add(Pending->State.Id,Pending);
}

void AVoxelBuildWorld::TickFragments()
{
    bool WorkerBusy=false;
    for(auto& E:Runtime->PendingFragments)
    {
        auto& P=*E.Value;
        if(P.Future.IsValid()&&P.Future.IsReady())
        {P.Prepared=P.Future.Get();P.Future=TFuture<TArray<FVoxelPreparedFragment>>();P.bPrepared=true;}
        WorkerBusy|=P.Future.IsValid();
    }
    if(!WorkerBusy)for(auto& E:Runtime->PendingFragments)
    {
        auto& P=*E.Value;if(P.bPrepared)continue;
        TMap<FName,float> Densities;for(const auto& Material:Palette->Materials)Densities.Add(Material.Id,Palette->Physical(Material.Id).DensityKgM3);
        const double Radius=Palette->EdgeRadiusCm;const int32 MaxShapes=FMath::Clamp(ShapesPerBody.GetValueOnGameThread(),1,128);
        const bool Restore=P.Sources.IsEmpty()&&!P.Replaces.IsValid();
        P.Future=Async(EAsyncExecution::ThreadPool,[State=P.State,Broken=SupportGraph->Broken,Slots=MaterialSlots,Densities=MoveTemp(Densities),Radius,MaxShapes,Restore]()
        {
            TArray<FVoxelPreparedFragment> Result;
            FVector ParentCenter=FVector::ZeroVector;double ParentMass=0;
            for(const auto& Cell:State.Cells)
            {const double M=Densities.FindRef(Cell.Material)*.008;ParentCenter+=(Cell.Min+FVector(10))*M;ParentMass+=M;}
            if(ParentMass>0)ParentCenter/=ParentMass;
            auto Parts=Restore?TArray<FVoxelFragmentSave>{State}:VoxelGeometry::Split(State,Broken,MaxShapes);
            for(auto& Part:Parts)
            {
                auto Geometry=VoxelGeometry::Fragment(Part.Cells,Slots,Densities,Radius);
                Part.Velocity+=FVector::CrossProduct(Part.AngularVelocity,State.Transform.TransformVectorNoScale(Geometry->MassCenter-ParentCenter));
                Result.Add({MoveTemp(Part),MoveTemp(Geometry)});
            }
            return Result;
        });
        break;
    }
    int32 Spawned=0;const double Start=FPlatformTime::Seconds();TArray<FGuid> Finished;
    for(auto& E:Runtime->PendingFragments)
    {
        auto& P=*E.Value;if(!P.bPrepared)continue;
        while(P.NextSpawn<P.Prepared.Num()&&Spawned<FMath::Clamp(SpawnLimit.GetValueOnGameThread(),1,16))
        {
            auto& Ready=P.Prepared[P.NextSpawn];
            FActorSpawnParameters Parameters;Parameters.Owner=this;Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            auto* Actor=GetWorld()->SpawnActor<AVoxelCollapseFragment>(AVoxelCollapseFragment::StaticClass(),Ready.State.Transform,Parameters);
            if(!Actor)break;
            Actor->Initialize(this,Ready.State,MoveTemp(Ready.Geometry),SurfaceMaterials);
            P.Spawned.Add(Actor);++P.NextSpawn;++Spawned;
            if(FPlatformTime::Seconds()-Start>.0015)break;
        }
        if(P.NextSpawn==P.Prepared.Num())
        {
            auto Barrier=MakeShared<TMap<FVoxelBuildKey,uint64>>();TArray<FVoxelEditCell> Edit;
            for(const auto& Key:P.Sources)
            {
                Runtime->PendingCells.Remove(Key);const FName M=VolumeMaterialAt(Key.Volume,Key.Cell);
                if(!M.IsNone())Edit.Add({Key.Cell,M,NAME_None,Key.Volume});
            }
            if(!Edit.IsEmpty())
            {
                ApplyChanges(Edit);
                for(const auto& Cell:Edit)for(int32 Z=-1;Z<=1;++Z)for(int32 Y=-1;Y<=1;++Y)for(int32 X=-1;X<=1;++X)
                {const auto Key=RenderKey({Cell.Volume,ChunkFor(Cell.Position+FIntVector(X,Y,Z))});Barrier->Add(Key,Runtime->MeshRevisions.FindRef(Key));}
            }
            if(P.Replaces.IsValid())if(auto* Old=Fragments.Find(P.Replaces))
            {if(IsValid(*Old))(*Old)->Destroy();Fragments.Remove(P.Replaces);}
            for(const auto& Weak:P.Spawned)if(auto* Actor=Weak.Get())
            {
                Fragments.Add(Actor->Id(),Actor);Actor->SetActorHiddenInGame(false);
                Runtime->Activation.Add({Actor,Barrier,false});
            }
            Finished.Add(E.Key);MarkSaveDirty();
        }
        if(Spawned>=FMath::Clamp(SpawnLimit.GetValueOnGameThread(),1,16)||FPlatformTime::Seconds()-Start>.0015)break;
    }
    for(FGuid Id:Finished)Runtime->PendingFragments.Remove(Id);
    Runtime->AwakeBodies=0;Runtime->AwakeShapes=0;
    TArray<FGuid> OutsideWorld;
    for(const auto& E:Fragments)if(IsValid(E.Value))
    {
        if(E.Value->IsMoving()){++Runtime->AwakeBodies;Runtime->AwakeShapes+=E.Value->ShapeCount();}
        if(E.Value->GetActorLocation().Z<GetWorld()->GetWorldSettings()->KillZ)OutsideWorld.Add(E.Key);
    }
    for(FGuid Id:OutsideWorld){Fragments.FindChecked(Id)->Destroy();Fragments.Remove(Id);MarkSaveDirty();}
    int32 Activated=0;
    for(int32 I=0;I<Runtime->Activation.Num();)
    {
        auto& Entry=Runtime->Activation[I];auto* Actor=Entry.Actor.Get();
        if(!Actor){Runtime->Activation.RemoveAtSwap(I);continue;}
        bool Ready=true;for(const auto& B:*Entry.MeshBarrier)Ready&=Runtime->AppliedRevisions.FindRef(B.Key)>=B.Value;
        if(!Ready){++I;continue;}
        if(!Entry.bCollisionReady){Actor->EnableWaitingCollision();Entry.bCollisionReady=true;}
        const bool Sleeping=Actor->Data().bSleeping;
        if(!Sleeping&&(Runtime->AwakeBodies>=FMath::Max(1,Bodies.GetValueOnGameThread())||
            Runtime->AwakeShapes+Actor->ShapeCount()>FMath::Max(128,Shapes.GetValueOnGameThread()))){++I;continue;}
        Actor->Activate();
        if(!Sleeping){++Runtime->AwakeBodies;Runtime->AwakeShapes+=Actor->ShapeCount();}
        Runtime->Activation.RemoveAtSwap(I);
        if(++Activated>=FMath::Clamp(SpawnLimit.GetValueOnGameThread(),1,16))break;
    }
    const double Now=GetWorld()->GetTimeSeconds();
    if(Runtime->AwakeBodies>0&&Now>=Runtime->MotionSaveAt){MarkSaveDirty();Runtime->MotionSaveAt=Now+3;}
}
