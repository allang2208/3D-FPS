#include "VoxelBuildWorld.h"
#include "VoxelBuildRuntime.h"
#include "VoxelBuildPalette.h"
#include "VoxelCollapseFragment.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/DamageEvents.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

namespace
{
    /**
     * DamageQueue 的读游标（审计 P19）：替代每弹一条一次的 `RemoveAt(0,1)` memmove。
     * TickDamage 是本队列的唯一读者，因此文件级游标安全；帧末统一压缩并归零。
     * 放在文件作用域（而非 Runtime 成员）是为了让这次改动保持"函数体 + 常量"级别，
     * 避免动 VoxelBuildRuntime.h 触发全量重编。
     */
    int32 DamageRead=0;
}

float AVoxelBuildWorld::TakeDamage(float Amount,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    if(!bReady||Amount<=0)return 0;
    if(Event.IsOfType(FPointDamageEvent::ClassID))
    {
        const auto& Point=static_cast<const FPointDamageEvent&>(Event);FVoxelBuildKey Key;
        if(!ResolveHit(Point.HitInfo,Key)||Runtime->PendingCells.Contains(Key))return 0;
        DamageBuilding(Point.HitInfo.ImpactPoint-Point.HitInfo.ImpactNormal*.25,Amount,0);
    }
    else if(Event.IsOfType(FRadialDamageEvent::ClassID))
    {
        const auto& Radial=static_cast<const FRadialDamageEvent&>(Event);
        DamageBuilding(Radial.Origin,Amount,Radial.Params.OuterRadius);
    }
    else return 0;
    return Super::TakeDamage(Amount,Event,EventInstigator,Causer);
}

void AVoxelBuildWorld::DamageBuilding(FVector Position,float Amount,float RadiusCm)
{
    if(!bReady||Position.ContainsNaN()||Amount<=0||!FMath::IsFinite(Amount))return;
    Runtime->DamageQueue.Add({nullptr,Position,Amount,FMath::Max(0.f,RadiusCm),0,true});
}

void AVoxelBuildWorld::QueueFragmentDamage(AVoxelCollapseFragment* Fragment,FVector Position,float Amount,float Radius,float Energy)
{
    if(!bReady||!IsValid(Fragment)||Position.ContainsNaN())return;
    Runtime->DamageQueue.Add({Fragment,Position,Amount,FMath::Max(0.f,Radius),FMath::Max(0.f,Energy),false});
}

void AVoxelBuildWorld::QueueCollapseImpact(AActor* Other,const FHitResult& Hit,float Energy)
{
    if(Other==this)
        Runtime->DamageQueue.Add({nullptr,Hit.ImpactPoint,0,FMath::Clamp(FMath::Sqrt(Energy)*.7f,15.f,100.f),Energy,true});
    else if(auto* Fragment=Cast<AVoxelCollapseFragment>(Other))
        QueueFragmentDamage(Fragment,Hit.ImpactPoint,0,FMath::Clamp(FMath::Sqrt(Energy)*.7f,15.f,100.f),Energy);
    else if(Other&&Other->CanBeDamaged())
        UGameplayStatics::ApplyPointDamage(Other,FMath::Min(500.f,FMath::Sqrt(Energy)*.7f),-Hit.ImpactNormal,Hit,nullptr,this,nullptr);
}

void AVoxelBuildWorld::TickDamage()
{
    // Physics callbacks only enqueue; topology and collision changes happen
    // here on the game thread, outside the Chaos contact dispatch.
    // 2026-09-21 性能修复（审计 P19）：
    //  a) 原来的 `RemoveAt(0,1,...)` 每弹一条就是一次 O(n) memmove（n = 队列长度）；
    //     改成读游标 DamageRead，帧末一次性压缩。
    //  b) 原来的 `++Processed` 与预算检查同一行、位于循环末尾，而 :67/:75/:78/:88 四处
    //     `continue` 会**跳过**它——一批碎片进入替换流程时，某些帧可以把整个队列
    //     （可能上万条）在一个 TickDamage 里全部弹完。现在预算在循环顶部，每次弹出都计数。
    // 本函数是 DamageQueue 的唯一读者，所以文件级游标是安全的；
    // 仍按 `DamageRead<=DamageQueue.Num()` 做防御性钳制。
    DamageRead=FMath::Min(DamageRead,Runtime->DamageQueue.Num());
    const double Start=FPlatformTime::Seconds();int32 Processed=0;
    while(DamageRead<Runtime->DamageQueue.Num())
    {
        if(++Processed>4||FPlatformTime::Seconds()-Start>.0015)break;
        const auto Request=Runtime->DamageQueue[DamageRead];
        TArray<FVoxelDebrisCell> Targets;AVoxelCollapseFragment* Fragment=Request.Fragment.Get();
        const bool bConsumed=++DamageRead>=Runtime->DamageQueue.Num();
        FVoxelFragmentSave FragmentState;
        const FVector Point=Fragment?Fragment->GetActorTransform().InverseTransformPosition(Request.Position):Request.Position;
        if(Request.bStatic)
        {
            for(const auto& Key:SupportGraph->Within(Point,FMath::Max(.5f,Request.Radius)))
            {
                if(Runtime->PendingCells.Contains(Key))continue;
                const auto& N=SupportGraph->Nodes.FindChecked(Key);
                Targets.Add({Key,N.Min,N.Material,CellDamage.FindRef(Key)});
            }
        }
        else if(Fragment)
        {
            bool Replacing=false;for(const auto& E:Runtime->PendingFragments)Replacing|=E.Value->Replaces==Fragment->Id();
            if(Replacing)continue;
            FragmentState=Fragment->Snapshot();Targets=FragmentState.Cells;
        }
        if(Targets.IsEmpty())continue;
        TMap<FVoxelBuildKey,float> Weights;float Total=0,Best=TNumericLimits<float>::Max();FVoxelBuildKey Closest;
        for(const auto& Cell:Targets)
        {
            const float Distance=float(FVector::Dist(Point,FBox(Cell.Min,Cell.Min+FVector(20)).GetClosestPointTo(Point)));
            if(Request.Radius<=0){if(Distance<Best){Best=Distance;Closest=Cell.Key;}continue;}
            if(Distance>Request.Radius)continue;
            const float Weight=FMath::Max(.01f,1-Distance/Request.Radius);Weights.Add(Cell.Key,Weight);Total+=Weight;
        }
        if(Request.Radius<=0&&Best<=1){Weights.Add(Closest,1);Total=1;}
        if(Total<=0)continue;
        TArray<FVoxelEditCell> Removed;bool Changed=false;
        for(auto& Cell:Targets)
        {
            const auto* Weight=Weights.Find(Cell.Key);if(!Weight)continue;
            const auto Physics=Palette->Physical(Cell.Material);
            // Collision energy is shared across the affected cells, not
            // multiplied by the number of voxels in the contact patch.
            const float Damage=Request.Amount*(*Weight)+Request.Energy*(*Weight/Total)/FMath::Max(1.f,Physics.JoulesPerDamage);
            if(Damage<=0)continue;
            Cell.Damage+=Damage;Changed=true;
            if(Request.bStatic)Runtime->NodeEpoch.Add(Cell.Key,Revision+1);
            if(Cell.Damage>=Physics.Durability)Removed.Add({Cell.Key.Cell,Cell.Material,NAME_None,Cell.Key.Volume});
            else if(Request.bStatic)
            {
                CellDamage.Add(Cell.Key,Cell.Damage);
                if(auto* N=SupportGraph->Nodes.Find(Cell.Key))N->Damage=Cell.Damage;
                Runtime->DirtySupport.Add(Cell.Key);
            }
        }
        if(Changed)
        {
            History.Reset();MarkSaveDirty();
            if(Request.bStatic)
            {
                if(!Removed.IsEmpty())ApplyChanges(Removed);
                else {++Revision;Runtime->NextIterations=256;}
            }
            else if(Fragment)
            {
                TSet<FVoxelBuildKey> Gone;for(const auto& E:Removed)Gone.Add({E.Volume,E.Position});
                Targets.RemoveAll([&](const auto& C){return Gone.Contains(C.Key);});
                if(Removed.IsEmpty())Fragment->UpdateCellDamage(MoveTemp(Targets));
                else if(Targets.IsEmpty()){Fragments.Remove(Fragment->Id());Fragment->Destroy();}
                else
                {
                    Fragment->FreezeForReplacement();FragmentState.Cells=MoveTemp(Targets);FragmentState.Id=FGuid::NewGuid();FragmentState.bSleeping=false;
                    EnqueueFragment(MoveTemp(FragmentState),{},Fragment->Id());
                }
            }
        }
        // 本帧已把队列读空：立刻压缩一次，避免游标与容量长期偏离。
        // 否则留到下一帧开头统一压缩——那个位置在 `bClosing` 早退之前，不会被跳过。
        if(bConsumed)break;
    }
    if(DamageRead>0)
    {
        const int32 Drop=FMath::Min(DamageRead,Runtime->DamageQueue.Num());
        if(Drop>0)Runtime->DamageQueue.RemoveAt(0,Drop,EAllowShrinking::No);
        DamageRead=0;
    }
    const double Now=GetWorld()->GetTimeSeconds();if(bClosing||Now<Runtime->LoadSampleAt)return;
    Runtime->LoadSampleAt=Now+.25;
    int32 Sampled=0;
    while(!Runtime->ContactLoads.IsEmpty()&&Sampled++<32)
    {
        Runtime->LoadRead%=Runtime->ContactLoads.Num();const auto Contact=Runtime->ContactLoads[Runtime->LoadRead];
        auto* Body=Contact.Body.Get();
        if(!Body)
        {
            SetAppliedLoad(Contact.Id,FVector::ZeroVector,0);Runtime->ContactLoads.RemoveAtSwap(Runtime->LoadRead);continue;
        }
        FVector Point=Body->GetComponentTransform().TransformPosition(Contact.LocalContact);float Mass=Body->IsSimulatingPhysics()?Body->GetMass():0;
        if(auto* Character=Cast<ACharacter>(Body->GetOwner()))
        {Point=Character->GetActorLocation()-FVector(0,0,Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());Mass=Character->GetCharacterMovement()->Mass;}
        // Collapse debris is not a live load. A 25-cell marble fragment (520 kg before the 2026-09-16
        // weight change) used to be registered on the cell under it; landing on a bridged course over a
        // window pushed the joints to 1.9-5.8x their limit and brought the standing wall down with it.
        else if(Cast<AVoxelCollapseFragment>(Body->GetOwner()))Mass=0;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(VoxelLiveLoad),true,Body->GetOwner());FHitResult Hit;
        const bool Supported=GetWorld()->LineTraceSingleByChannel(Hit,Point+FVector(0,0,2),Point-FVector(0,0,5),ECC_Visibility,Query)&&Hit.GetActor()==this&&Hit.ImpactNormal.Z>.5;
        SetAppliedLoad(Contact.Id,Supported?Hit.ImpactPoint:Point,Supported?Mass:0);
        ++Runtime->LoadRead;if(Sampled>=Runtime->ContactLoads.Num())break;
    }
}

void AVoxelBuildWorld::SetAppliedLoad(FName LoadId,FVector ContactPoint,float MassKg)
{
    if(!bReady||LoadId.IsNone()||ContactPoint.ContainsNaN()||!FMath::IsFinite(MassKg))return;
    FVoxelBuildKey NewKey;bool Found=false;double Best=TNumericLimits<double>::Max();
    if(MassKg>0)for(const auto& Key:SupportGraph->Near(ContactPoint-FVector(10)))
    {
        const auto& N=SupportGraph->Nodes.FindChecked(Key);
        if(ContactPoint.X<N.Min.X-.2||ContactPoint.X>N.Min.X+20.2||ContactPoint.Y<N.Min.Y-.2||ContactPoint.Y>N.Min.Y+20.2)continue;
        const double Distance=FMath::Abs(ContactPoint.Z-N.Min.Z-20);
        if(Distance<2&&Distance<Best&&!Runtime->PendingCells.Contains(Key)){Best=Distance;NewKey=Key;Found=true;}
    }
    const auto* Previous=Runtime->Loads.Find(LoadId);
    if(Previous&&Found&&Previous->Key==NewKey&&FMath::IsNearlyEqual(Previous->Mass,MassKg,.01f))return;
    if(!Previous&&!Found)return;
    if(Previous)if(auto* N=SupportGraph->Nodes.Find(Previous->Key))
    {
        N->AddedMassKg=FMath::Max(0.f,N->AddedMassKg-Previous->Mass);
        if(!LegacyProtected.Contains(N->Key))Runtime->DirtySupport.Add(N->Key);
        Runtime->NodeEpoch.Add(N->Key,Revision+1);
    }
    Runtime->Loads.Remove(LoadId);
    if(Found)
    {
        SupportGraph->Nodes.FindChecked(NewKey).AddedMassKg+=MassKg;Runtime->Loads.Add(LoadId,{NewKey,MassKg});
        if(!LegacyProtected.Contains(NewKey))Runtime->DirtySupport.Add(NewKey);
        Runtime->NodeEpoch.Add(NewKey,Revision+1);
    }
    ++Revision;Runtime->NextIterations=256;
}

void AVoxelBuildWorld::OnBuildingHit(UPrimitiveComponent* Component,AActor* Other,UPrimitiveComponent* OtherComponent,FVector Impulse,const FHitResult& Hit)
{
    if(!IsValid(Other)||!OtherComponent||(!OtherComponent->IsSimulatingPhysics()&&!Cast<ACharacter>(Other)))return;
    if(!Runtime->ContactLoads.ContainsByPredicate([&](const auto& E){return E.Body==OtherComponent;}))
        Runtime->ContactLoads.Add({OtherComponent,FName(*FString::Printf(TEXT("VoxelContact_%u"),OtherComponent->GetUniqueID())),
            OtherComponent->GetComponentTransform().InverseTransformPosition(Hit.ImpactPoint)});
    if(Cast<AVoxelCollapseFragment>(Other))return; // Its contact callback accounts for impact energy once.
    if(OtherComponent->IsSimulatingPhysics())
    {
        const float Speed=float(OtherComponent->GetComponentVelocity().Size())*.01f;
        const float Energy=FMath::Min(.5f*OtherComponent->GetMass()*Speed*Speed,float(Impulse.Size())*.01f*Speed*.5f);
        if(Energy>20)Runtime->DamageQueue.Add({nullptr,Hit.ImpactPoint,0,20,Energy,true});
    }
}
