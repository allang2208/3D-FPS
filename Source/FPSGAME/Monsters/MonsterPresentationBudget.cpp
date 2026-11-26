#include "MonsterPresentationBudget.h"
#include "MonsterCombatComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Animation/AnimInstance.h"
#include "Engine/World.h"

void UMonsterPresentationBudget::Register(UMonsterCombatComponent* Combat)
{
    if(!Combat||GetWorld()->GetNetMode()==NM_DedicatedServer||!GetWorld()->IsGameWorld())return;
    auto* Character=Cast<ACharacter>(Combat->GetOwner());
    auto* Mesh=Character?Character->GetMesh():nullptr;
    if(!Mesh||Mesh->GetComponentTickInterval()>0||Entries.ContainsByPredicate([&](const FEntry& E){return E.Combat==Combat;}))return;
    FEntry& E=Entries.AddDefaulted_GetRef();E.Combat=Combat;E.Mesh=Mesh;
    E.OriginalInterval=E.AppliedInterval=Mesh->GetComponentTickInterval();
    if(!GetWorld()->GetTimerManager().IsTimerActive(Timer))
        GetWorld()->GetTimerManager().SetTimer(Timer,this,&UMonsterPresentationBudget::Update,.2f,true);
}

void UMonsterPresentationBudget::Restore(FEntry& E)
{
    if(auto* Mesh=E.Mesh.Get();Mesh&&E.AppliedInterval!=E.OriginalInterval)
        if(FMath::IsNearlyEqual(Mesh->GetComponentTickInterval(),E.AppliedInterval))
            Mesh->SetComponentTickInterval(E.OriginalInterval);
    E.AppliedInterval=E.OriginalInterval;E.Tier=0;
}

void UMonsterPresentationBudget::Promote(UMonsterCombatComponent* Combat)
{
    for(auto& E:Entries)if(E.Combat==Combat){Restore(E);break;}
}

void UMonsterPresentationBudget::Unregister(UMonsterCombatComponent* Combat)
{
    for(int32 I=Entries.Num()-1;I>=0;--I)if(!Entries[I].Combat.IsValid()||Entries[I].Combat==Combat)
    {Restore(Entries[I]);Entries.RemoveAtSwap(I,1,EAllowShrinking::No);}
    if(Entries.IsEmpty())GetWorld()->GetTimerManager().ClearTimer(Timer);
}

void UMonsterPresentationBudget::Update()
{
    TArray<FVector,TInlineAllocator<4>> Views;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(const auto* PC=It->Get();PC&&PC->IsLocalController())
        {FVector Location;FRotator Rotation;PC->GetPlayerViewPoint(Location,Rotation);Views.Add(Location);}
    const int32 Work=FMath::Min(32,Entries.Num());
    for(int32 I=0;I<Work&&!Entries.IsEmpty();++I)
    {
        Cursor%=Entries.Num();FEntry& E=Entries[Cursor];
        auto* Combat=E.Combat.Get();auto* Mesh=E.Mesh.Get();
        if(!Combat||!Mesh||Combat->IsDead())
        {Restore(E);Entries.RemoveAtSwap(Cursor,1,EAllowShrinking::No);continue;}
        ++Cursor;
        const auto* Character=Cast<ACharacter>(Combat->GetOwner());
        const auto* Anim=Mesh->GetAnimInstance();
        // Never throttle server hit-history/muzzle/socket policies or root motion.
        const bool Critical=Views.IsEmpty()||Combat->IsBusy()||Combat->IsControlled()||Mesh->IsSimulatingPhysics()||
            !Mesh->IsComponentTickEnabled()||Character->IsPlayingRootMotion()||(Anim&&Anim->IsAnyMontagePlaying())||
            (Character->HasAuthority()&&Mesh->VisibilityBasedAnimTickOption!=EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered);
        if(Critical){Restore(E);continue;}
        if(!FMath::IsNearlyEqual(Mesh->GetComponentTickInterval(),E.AppliedInterval))continue;
        double Distance=DBL_MAX;
        for(const FVector& View:Views)Distance=FMath::Min(Distance,FVector::DistSquared(View,Character->GetActorLocation()));
        const double Near=E.Tier>0?1800.:2200.,Far=E.Tier==2?4800.:5200.;
        E.Tier=Distance<FMath::Square(Near)?0:Distance<FMath::Square(Far)?1:2;
        // Existing URO owns its own skip/interpolation policy; do not double-throttle it.
        const float Interval=Mesh->bEnableUpdateRateOptimizations?E.OriginalInterval:E.Tier==0?E.OriginalInterval:E.Tier==1?1.f/30.f:1.f/15.f;
        if(!FMath::IsNearlyEqual(Interval,E.AppliedInterval))
        {Mesh->SetComponentTickInterval(Interval);E.AppliedInterval=Interval;}
    }
    if(Entries.IsEmpty())GetWorld()->GetTimerManager().ClearTimer(Timer);
}

void UMonsterPresentationBudget::Deinitialize()
{
    GetWorld()->GetTimerManager().ClearTimer(Timer);
    for(auto& E:Entries)Restore(E);
    Entries.Reset();Super::Deinitialize();
}
