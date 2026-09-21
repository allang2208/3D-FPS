#include "VoxelBuildWorld.h"
#include "../UI/ColdSteelStatusModel.h"
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
    /**
     * 审计 P18：残骸回收的每帧重做与退避。
     *  a) `voxel_block_<材质>` 的物品 ID 只取决于材质（有限几种），缓存掉每格一次的
     *     `FName::ToString()` + 字符串拼接。
     *  b) `GrantWorldBlocks` 在背包/地面物品达上限时返回 false（见 ColdSteelAreaPickup.cpp:55），
     *     此时残骸不会被删除。原实现下一帧立刻重试，等于**每帧**重做一次全部转换工作。
     *     改为失败后退避 1 s。
     */
    TMap<FName,FString> BlockItemIds;
    TMap<FGuid,double> RecycleRetryAt;
    const FString& BlockItemId(FName Material)
    {
        if(FString* Found=BlockItemIds.Find(Material))return *Found;
        return BlockItemIds.Add(Material,FString(TEXT("voxel_block_"))+Material.ToString());
    }
    constexpr double RecycleRetrySeconds=1.0;
}

void AVoxelBuildWorld::RemoveFragment(AVoxelCollapseFragment* Fragment)
{
    if(!IsValid(Fragment))return;
    Fragments.Remove(Fragment->Id());
    Fragment->Destroy();
    History.Reset();
    MarkSaveDirty();
}

void AVoxelBuildWorld::EnqueueFragment(FVoxelFragmentSave State,TArray<FVoxelBuildKey> Sources,FGuid Replaces,bool bFailureDebris)
{
    if(State.Cells.IsEmpty())return;
    auto Pending=MakeShared<FVoxelPendingFragment>();Pending->State=MoveTemp(State);Pending->Sources=MoveTemp(Sources);Pending->Replaces=Replaces;
    Pending->bFailureDebris=bFailureDebris;
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
            Actor->SetFailureDebris(P.bFailureDebris);
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
    // 审计 P21：原来这段对 Fragments 有三个各自独立的完整遍历（这里统计醒着的块与 KillZ、
    // 下面回收、再下面激活）。醒着统计与 KillZ 判定合并成一遍；回收扫描本来就要求碎片静止
    // （AccrueRestSeconds 只在 IsMoving()==false 时累加），因此不会与醒着统计互相影响，
    // 但**必须在 KillZ 销毁之后**跑到，否则刚销毁的条目会被重复处理——所以拆成两趟：
    // 第一趟统计 + 记账，销毁在回收之后统一执行。
    Runtime->AwakeBodies=0;Runtime->AwakeShapes=0;
    const double KillZ=GetWorld()->GetWorldSettings()->KillZ;
    // Settled debris comes back as pick-up-able voxel blocks: same 20 cm cube, same material, so a
    // collapsed wall turns into blocks the player can collect (Z) and build with again.
    TArray<FGuid> Recycled;TArray<FGuid> OutsideWorld;
    const float FrameDelta=GetWorld()->GetDeltaSeconds();
    const double NowSeconds=GetWorld()->GetTimeSeconds();
    for(const auto& E:Fragments)
    {
        AVoxelCollapseFragment* Fragment=E.Value;
        if(!IsValid(Fragment))continue;
        if(Fragment->IsMoving()){++Runtime->AwakeBodies;Runtime->AwakeShapes+=Fragment->ShapeCount();}
        if(Fragment->GetActorLocation().Z<KillZ){OutsideWorld.Add(E.Key);continue;}
        if(!Fragment->AccrueRestSeconds(FrameDelta,2.f))continue;
        // 上一次转换失败（通常是物品达上限）：退避期内不再重做整份转换工作。
        if(const double* RetryAt=RecycleRetryAt.Find(E.Key))if(NowSeconds<*RetryAt)continue;
        // 审计 P18：不再每帧 `Snapshot()` 拷一份完整 cells。`State.Cells` 就是当前格的权威副本
        // （由 UpdateCellDamage 维护，FreezeForReplacement 会自行保存），这里只需要材料计数。
        TMap<FString,int64> Blocks;
        for(const FVoxelDebrisCell& Cell:Fragment->Data().Cells)
            if(!Cell.Material.IsNone())Blocks.FindOrAdd(BlockItemId(Cell.Material))++;
        auto* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
        if(Model&&!Blocks.IsEmpty()&&Model->GrantWorldBlocks(Blocks,Fragment->GetActorLocation()))
        {Recycled.Add(E.Key);RecycleRetryAt.Remove(E.Key);}
        else RecycleRetryAt.Add(E.Key,NowSeconds+RecycleRetrySeconds);
    }
    for(const FGuid Id:Recycled)
    {
        RecycleRetryAt.Remove(Id);
        if(AVoxelCollapseFragment* Fragment=Fragments.FindRef(Id))Fragment->Destroy();
        Fragments.Remove(Id);MarkSaveDirty();
    }
    // KillZ 之下的碎片在回收之后统一销毁（顺序与改动前一致：先统计、再回收、最后销毁落出世界的）。
    for(const FGuid Id:OutsideWorld){RecycleRetryAt.Remove(Id);Fragments.FindChecked(Id)->Destroy();Fragments.Remove(Id);MarkSaveDirty();}
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
